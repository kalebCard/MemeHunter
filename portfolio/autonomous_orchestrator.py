"""
Orquestador Autónomo de Auto-Mejora y Auto-Sanación de Portafolio (Autonomous Alpha Loop).
Sprint 1: Motor Cuantitativo Auto-Evolutivo (US-3.1 y US-3.2).

Implementa el bucle cerrado:
1. Observación de métricas de salud (IC, CUSUM, Drift) por factor.
2. Degeneración y puesta en cuarentena de alphas obsoletos.
3. Disparo automático de minería reactiva si la salud de la cartera decae.
4. Sustitución de factores caídos utilizando el QualityDiversityArchive.
5. Rebalanceo automático de capital mediante Hierarchical Risk Parity (HRP).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from portfolio.alpha_health_monitor import AlphaHealthMonitor, HealthStatus, HealthReport
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus, StrategyRecord
from portfolio.hrp_allocator import HierarchicalRiskParityAllocator
from mining.alpha_daemon import AlphaMinerDaemon, QualityDiversityArchive


@dataclass
class SelfHealingCycleReport:
    """Reporte estructurado del ciclo de auto-mejora y auto-sanación."""
    cycle_timestamp: str
    actions_taken: List[str]
    health_reports: Dict[str, HealthReport]
    quarantined_strategies: List[str]
    promoted_strategies: List[str]
    new_weights: Dict[str, float]
    mining_triggered: bool
    trigger_reason: Optional[str] = None


class AutonomousPortfolioOrchestrator:
    """
    Controlador central del bucle cerrado auto-evolutivo.
    """

    def __init__(
        self,
        incubator: Optional[StrategyLifecycleIncubator] = None,
        health_monitor: Optional[AlphaHealthMonitor] = None,
        miner_daemon: Optional[AlphaMinerDaemon] = None
    ):
        self.incubator = incubator or StrategyLifecycleIncubator()
        self.health_monitor = health_monitor or AlphaHealthMonitor()
        self.miner_daemon = miner_daemon

    def process_cycle(
        self,
        signals_df: pd.DataFrame,
        forward_returns: pd.Series,
        returns_matrix_df: pd.DataFrame,
        historical_baseline_returns: Optional[np.ndarray] = None
    ) -> SelfHealingCycleReport:
        """
        Ejecuta un ciclo completo de diagnóstico, cuarentena, sustitución y rebalanceo.
        """
        actions: List[str] = []
        quarantined: List[str] = []
        promoted: List[str] = []
        health_reports: Dict[str, HealthReport] = {}
        mining_needed = False
        trigger_reason = None

        # 1. Auditar salud de cada estrategia activa o en sandbox
        for sid, rec in list(self.incubator.strategies.items()):
            if sid in signals_df.columns:
                sig = signals_df[sid]
                hr = self.health_monitor.diagnose_factor(
                    factor_id=sid,
                    signal=sig,
                    forward_returns=forward_returns,
                    historical_baseline_returns=historical_baseline_returns
                )
                health_reports[sid] = hr

                if hr.status in (HealthStatus.WARNING_DECAY, HealthStatus.CRITICAL_BREAK):
                    # Transición hacia decaimiento
                    rec.status = StrategyLifecycleStatus.ALPHA_DECAY
                    quarantined.append(sid)
                    actions.append(f"Degradación de {sid} a ALPHA_DECAY: {hr.message}")
                    mining_needed = True
                    trigger_reason = f"Decay detectado en {sid} ({hr.status.value})"

                elif hr.status == HealthStatus.REGIME_SHIFT:
                    actions.append(f"Regime shift detectado en {sid}. Activando minería adaptativa.")
                    mining_needed = True
                    trigger_reason = "Regime shift detectado por KS-Test"

                elif rec.status == StrategyLifecycleStatus.SANDBOX and hr.status == HealthStatus.HEALTHY:
                    if hr.rolling_ic >= 0.05 and hr.ic_pvalue <= 0.05:
                        rec.status = StrategyLifecycleStatus.LIVE
                        promoted.append(sid)
                        actions.append(f"Promoción de {sid} de SANDBOX a LIVE por IC sólido ({hr.rolling_ic:.3f})")

        # 2. Si hay alphas caídos o régimen roto, detonar minería inmediata
        if mining_needed and self.miner_daemon is not None:
            self.miner_daemon.trigger_immediate_mining(reason=trigger_reason or "Health Alert")
            actions.append(f"Disparo de minería reactiva completado. Razón: {trigger_reason}")

        # 3. Intentar sustitución de estrategias caídas con el archivo de diversidad
        if self.miner_daemon is not None and self.miner_daemon.archive is not None:
            active_bank = self.miner_daemon.archive.get_active_factors()
            for cand in active_bank:
                cand_id = f"ARCHIVE_{cand.factor_id}"
                if cand_id not in self.incubator.strategies and cand.ic_ir >= 1.2:
                    self.incubator.register_strategy(
                        strategy_id=cand_id,
                        name=f"Evolved_{cand.formula[:25]}",
                        backtest_sharpe=cand.sharpe_proxy,
                        status=StrategyLifecycleStatus.SANDBOX
                    )
                    actions.append(f"Inyección de factor {cand_id} desde QualityDiversityArchive a SANDBOX.")

        # 4. Rebalanceo automático de portafolio mediante Paridad Jerárquica de Riesgo (HRP)
        new_weights = self.incubator.rebalance_live_portfolio(returns_matrix_df)
        actions.append(f"Rebalanceo HRP ejecutado. Estrategias activas ponderadas: {list(new_weights.keys())}")

        return SelfHealingCycleReport(
            cycle_timestamp="2026-10-11T22:35:00Z",
            actions_taken=actions,
            health_reports=health_reports,
            quarantined_strategies=quarantined,
            promoted_strategies=promoted,
            new_weights=new_weights,
            mining_triggered=mining_needed,
            trigger_reason=trigger_reason
        )
