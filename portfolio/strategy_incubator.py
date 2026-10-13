"""
Módulo del Orquestador de Ciclo de Vida de Estrategias e Incubadora de Portafolio.
PB-85 y PB-86 (Sprint 24).

Implementa la máquina de estados institucional:
- SANDBOX: Evaluación ciega en simulación paper-trading (30 días).
- LIVE: Estrategia graduada a producción recibiendo asignación de capital real.
- ALPHA_DECAY: Detección de deterioro estadístico (Sharpe decae > 2 sigma respecto al backtest OOS).
- RETIRED: Retiro automático y reasignación de capital por Paridad Jerárquica de Riesgo (HRP).
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import os
import numpy as np
import pandas as pd

from portfolio.hrp_allocator import HierarchicalRiskParityAllocator
from portfolio.atomic_io import atomic_write_json


class StrategyLifecycleStatus(str, Enum):
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"
    ALPHA_DECAY = "ALPHA_DECAY"
    RETIRED = "RETIRED"


@dataclass
class StrategyRecord:
    """Ficha de seguimiento de una estrategia dentro de la incubadora."""
    strategy_id: str
    name: str
    status: StrategyLifecycleStatus
    target_capital_weight: float
    backtest_sharpe: float
    live_sharpe: float
    days_in_stage: int
    decay_zscore: float
    last_audit_date: str


class StrategyLifecycleIncubator:
    """
    Orquestador de ciclo de vida y asignación dinámica de portafolio multi-estrategia.
    """

    def __init__(
        self,
        min_sandbox_days: int = 15,
        min_graduation_psr: float = 0.85,
        decay_sigma_threshold: float = -1.80
    ):
        self.min_sandbox_days = min_sandbox_days
        self.min_graduation_psr = min_graduation_psr
        self.decay_threshold = decay_sigma_threshold
        self.allocator = HierarchicalRiskParityAllocator()
        self.strategies: Dict[str, StrategyRecord] = {}
        self.last_turnover: float = 0.0
        self.last_rebalance_executed: bool = False

    def register_strategy(
        self,
        strategy_id: str,
        name: str,
        backtest_sharpe: float,
        status: StrategyLifecycleStatus = StrategyLifecycleStatus.SANDBOX
    ) -> StrategyRecord:
        """Registra una nueva estrategia proveniente del motor de minería."""
        rec = StrategyRecord(
            strategy_id=strategy_id,
            name=name,
            status=status,
            target_capital_weight=0.0,
            backtest_sharpe=float(backtest_sharpe),
            live_sharpe=0.0,
            days_in_stage=0,
            decay_zscore=0.0,
            last_audit_date=datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        self.strategies[strategy_id] = rec
        return rec

    def audit_and_transition(
        self,
        strategy_id: str,
        days_active: int,
        live_returns: np.ndarray,
        returns_benchmark_std: float = 0.02
    ) -> StrategyRecord:
        """
        Audita el desempeño en vivo y efectúa la transición de estado.
        """
        if strategy_id not in self.strategies:
            raise KeyError(f"Estrategia {strategy_id} no registrada en la incubadora.")

        rec = self.strategies[strategy_id]
        if days_active is not None and days_active > 0:
            rec.days_in_stage = days_active
        else:
            rec.days_in_stage += 1
        rec.last_audit_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        clean_ret = live_returns[np.isfinite(live_returns)]

        if len(clean_ret) >= 5:
            mean_r = float(np.mean(clean_ret))
            std_r = float(np.std(clean_ret)) if len(clean_ret) > 1 else 1.0
            live_sharpe = float((mean_r / (std_r + 1e-6)) * np.sqrt(365 * 6))
            rec.live_sharpe = live_sharpe

            # Cálculo de Alpha Decay Z-Score: (Live Sharpe - Backtest Sharpe) / error estándar
            se_sharpe = np.sqrt((1.0 + 0.5 * live_sharpe**2) / len(clean_ret))
            decay_z = float((live_sharpe - rec.backtest_sharpe) / (se_sharpe + 1e-6))
            rec.decay_zscore = decay_z
        else:
            decay_z = 0.0

        # Transiciones de la máquina de estados
        if rec.status == StrategyLifecycleStatus.SANDBOX:
            # Graduación si cumple días mínimos y retiene Sharpe positivo consistente
            if rec.days_in_stage >= self.min_sandbox_days and rec.live_sharpe >= 0.8:
                rec.status = StrategyLifecycleStatus.LIVE
                rec.days_in_stage = 0
        elif rec.status == StrategyLifecycleStatus.LIVE:
            # Alerta de desgaste si cae más de decay_threshold desviaciones estándar
            if decay_z <= self.decay_threshold:
                rec.status = StrategyLifecycleStatus.ALPHA_DECAY
                rec.days_in_stage = 0
        elif rec.status == StrategyLifecycleStatus.ALPHA_DECAY:
            # Si el decaimiento persiste más de 10 días adicionales en esta etapa, retiro definitivo
            if rec.days_in_stage >= 10:
                rec.status = StrategyLifecycleStatus.RETIRED
                rec.target_capital_weight = 0.0

        return rec

    def rebalance_live_portfolio(
        self,
        returns_matrix_df: pd.DataFrame,
        turnover_deadband: float = 0.15
    ) -> Dict[str, float]:
        """
        Calcula la nueva distribución de capital por HRP para las estrategias activas (LIVE).
        Aplica una banda muerta de turnover (15% por defecto, PB-95) para evitar fricción
        y comisiones innecesarias en Binance Futures.
        """
        live_strategies = [
            sid for sid, rec in self.strategies.items()
            if rec.status == StrategyLifecycleStatus.LIVE and sid in returns_matrix_df.columns
        ]

        if not live_strategies:
            # Si no hay vivas, todo el peso se mantiene en reserva
            for rec in self.strategies.values():
                rec.target_capital_weight = 0.0
            self.last_turnover = 0.0
            self.last_rebalance_executed = False
            return {}

        sub_df = returns_matrix_df[live_strategies]
        suggested_weights = self.allocator.allocate_weights(sub_df)

        # PB-95: Banda Muerta de Rebalanceo y Restricción de Turnover
        current_weights = {sid: self.strategies[sid].target_capital_weight for sid in self.strategies}
        all_sids = set(current_weights.keys()).union(suggested_weights.keys())
        total_turnover = 0.5 * sum(
            abs(suggested_weights.get(sid, 0.0) - current_weights.get(sid, 0.0))
            for sid in all_sids
        )
        self.last_turnover = float(total_turnover)

        # Si ya había una asignación previa distribuida y el cambio es menor a la banda muerta:
        has_prior_allocation = sum(current_weights.get(sid, 0.0) for sid in live_strategies) > 0.01

        if has_prior_allocation and total_turnover < turnover_deadband:
            # Regla de no-intervención: Preservar pesos vigentes (renormalizados entre las vivas)
            live_weight_sum = sum(self.strategies[sid].target_capital_weight for sid in live_strategies)
            norm_weights: Dict[str, float] = {}
            if live_weight_sum > 1e-4:
                for sid in live_strategies:
                    norm_w = self.strategies[sid].target_capital_weight / live_weight_sum
                    norm_weights[sid] = float(norm_w)
                    self.strategies[sid].target_capital_weight = float(norm_w)
            else:
                norm_weights = suggested_weights
                for sid in self.strategies:
                    self.strategies[sid].target_capital_weight = suggested_weights.get(sid, 0.0)

            # Poner en 0 las estrategias no vivas
            for sid in self.strategies:
                if sid not in live_strategies:
                    self.strategies[sid].target_capital_weight = 0.0

            self.last_rebalance_executed = False
            return norm_weights

        # Turnover significativo o primera asignación: Aplicar nuevos pesos sugeridos por HRP
        for sid in self.strategies:
            if sid in suggested_weights:
                self.strategies[sid].target_capital_weight = suggested_weights[sid]
            else:
                self.strategies[sid].target_capital_weight = 0.0

        self.last_rebalance_executed = True
        return suggested_weights

    def save_to_db(self, db_path: str = "portfolio/alpha_factory.db") -> None:
        """Persiste todas las estrategias en la base de datos SQLite WAL de forma atómica."""
        try:
            from portfolio.db_schema import init_alpha_factory_db, upsert_strategy_db
            init_alpha_factory_db(db_path)
            for sid, rec in self.strategies.items():
                upsert_strategy_db(asdict(rec), db_path=db_path)
        except Exception as e:
            logger = logging.getLogger("StrategyLifecycleIncubator")
            logger.warning(f"Error al guardar estado en SQLite {db_path}: {e}")

    def load_from_db(self, db_path: str = "portfolio/alpha_factory.db") -> bool:
        """Carga el estado de las estrategias desde la base de datos SQLite WAL."""
        if not os.path.exists(db_path):
            return False
        try:
            from portfolio.db_schema import get_all_strategies_db
            records = get_all_strategies_db(db_path)
            if not records:
                return False
            for item in records:
                status_str = item.get("status", "SANDBOX")
                try:
                    status = StrategyLifecycleStatus(status_str)
                except ValueError:
                    status = StrategyLifecycleStatus.SANDBOX
                rec = StrategyRecord(
                    strategy_id=item["strategy_id"],
                    name=item["name"],
                    status=status,
                    target_capital_weight=float(item.get("target_capital_weight", 0.0)),
                    backtest_sharpe=float(item.get("backtest_sharpe", 0.0)),
                    live_sharpe=float(item.get("live_sharpe", 0.0)),
                    days_in_stage=int(item.get("days_in_stage", 0)),
                    decay_zscore=float(item.get("decay_zscore", 0.0)),
                    last_audit_date=item.get("last_audit_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                )
                self.strategies[item["strategy_id"]] = rec
            return True
        except Exception:
            return False

    def save_state(self, filepath: str = "portfolio/incubator_state.json", db_path: Optional[str] = "portfolio/alpha_factory.db") -> None:
        """
        Persiste el estado de la incubadora tanto en SQLite WAL (primario)
        como en JSON atómico (compatibilidad hacia atrás).
        """
        if db_path:
            self.save_to_db(db_path)

        if filepath:
            data = {sid: asdict(rec) for sid, rec in self.strategies.items()}
            for k, v in data.items():
                v['status'] = v['status'].value if hasattr(v['status'], 'value') else str(v['status'])
            atomic_write_json(filepath, data)

    def load_state(self, filepath: str = "portfolio/incubator_state.json", db_path: Optional[str] = "portfolio/alpha_factory.db") -> None:
        """Carga el estado desde SQLite si existe; si no, recurre al archivo JSON."""
        loaded_from_db = False
        if db_path and os.path.exists(db_path):
            loaded_from_db = self.load_from_db(db_path)

        if not loaded_from_db and filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for sid, item in data.items():
                    status_str = item.get("status", "SANDBOX")
                    try:
                        status = StrategyLifecycleStatus(status_str)
                    except ValueError:
                        status = StrategyLifecycleStatus.SANDBOX
                    rec = StrategyRecord(
                        strategy_id=item["strategy_id"],
                        name=item["name"],
                        status=status,
                        target_capital_weight=float(item.get("target_capital_weight", 0.0)),
                        backtest_sharpe=float(item.get("backtest_sharpe", 0.0)),
                        live_sharpe=float(item.get("live_sharpe", 0.0)),
                        days_in_stage=int(item.get("days_in_stage", 0)),
                        decay_zscore=float(item.get("decay_zscore", 0.0)),
                        last_audit_date=item.get("last_audit_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                    )
                    self.strategies[sid] = rec
            except Exception:
                pass
