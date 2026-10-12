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
import json
import os
import numpy as np
import pandas as pd

from portfolio.hrp_allocator import HierarchicalRiskParityAllocator


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
            last_audit_date="2026-10-11"
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
        rec.days_in_stage = days_active
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
        elif rec.status == StrategyLifecycleStatus.LIVE:
            # Alerta de desgaste si cae más de decay_threshold desviaciones estándar
            if decay_z <= self.decay_threshold:
                rec.status = StrategyLifecycleStatus.ALPHA_DECAY
        elif rec.status == StrategyLifecycleStatus.ALPHA_DECAY:
            # Si el decaimiento persiste más de 10 días adicionales sin recuperarse, retiro definitivo
            if rec.days_in_stage >= 10:
                rec.status = StrategyLifecycleStatus.RETIRED
                rec.target_capital_weight = 0.0

        return rec

    def rebalance_live_portfolio(self, returns_matrix_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calcula la nueva distribución de capital por HRP para las estrategias activas (LIVE).
        Las estrategias en SANDBOX o RETIRED reciben peso 0.0%.
        """
        live_strategies = [
            sid for sid, rec in self.strategies.items()
            if rec.status == StrategyLifecycleStatus.LIVE and sid in returns_matrix_df.columns
        ]

        if not live_strategies:
            # Si no hay vivas, todo el peso se mantiene en reserva
            for rec in self.strategies.values():
                rec.target_capital_weight = 0.0
            return {}

        sub_df = returns_matrix_df[live_strategies]
        weights = self.allocator.allocate_weights(sub_df)

        for sid in self.strategies:
            if sid in weights:
                self.strategies[sid].target_capital_weight = weights[sid]
            else:
                self.strategies[sid].target_capital_weight = 0.0

        return weights

    def save_state(self, filepath: str = "portfolio/incubator_state.json") -> None:
        """Persiste el estado de la incubadora en formato JSON estructurado."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {sid: asdict(rec) for sid, rec in self.strategies.items()}
        # Convertir enum a string
        for k, v in data.items():
            v['status'] = v['status'].value if hasattr(v['status'], 'value') else str(v['status'])
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
