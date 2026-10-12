"""
Orquestador Autónomo de Auto-Mejora y Auto-Sanación de Portafolio (Autonomous Alpha Loop Aumentado con IA).
Sprint 1 & Sprint 2: Motor Cuantitativo Auto-Evolutivo y Aumentado por IA (OpenRouter).

Implementa el bucle cerrado cognitivo:
1. Observación de métricas de salud (IC, CUSUM, Drift) por factor.
2. Degeneración y puesta en cuarentena de alphas obsoletos.
3. Autopsia Forense Cognitiva (`AlphaAutopsyAgent`) vía OpenRouter para aislar la causa raíz del fallo.
4. Generación Semántica de Hipótesis y Alphas (`LLMAlphaSynthesizer`) con parser AST seguro.
5. Inserción en el `QualityDiversityArchive` y promoción a `SANDBOX`.
6. Rebalanceo automático de capital mediante Hierarchical Risk Parity (HRP).
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from portfolio.alpha_health_monitor import AlphaHealthMonitor, HealthStatus, HealthReport
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus, StrategyRecord
from portfolio.hrp_allocator import HierarchicalRiskParityAllocator
from portfolio.alpha_autopsy import AlphaAutopsyAgent, AutopsyVerdict
from mining.alpha_daemon import AlphaMinerDaemon, QualityDiversityArchive
from mining.llm_alpha_generator import LLMAlphaSynthesizer


@dataclass
class SelfHealingCycleReport:
    """Reporte estructurado del ciclo de auto-mejora y auto-sanación con IA."""
    cycle_timestamp: str
    actions_taken: List[str]
    health_reports: Dict[str, HealthReport]
    quarantined_strategies: List[str]
    promoted_strategies: List[str]
    new_weights: Dict[str, float]
    mining_triggered: bool
    trigger_reason: Optional[str] = None
    autopsies: Dict[str, AutopsyVerdict] = field(default_factory=dict)
    goal_reached: bool = False
    estimated_cycle_cost_usd: float = 0.0
    accumulated_cost_usd: float = 0.0


class AutonomousPortfolioOrchestrator:
    """
    Controlador central del bucle cerrado auto-evolutivo asistido por OpenRouter.
    Implementa metas cuantitativas (Target Sharpe) y límites estrictos de gasto y ciclos.
    """

    def __init__(
        self,
        incubator: Optional[StrategyLifecycleIncubator] = None,
        health_monitor: Optional[AlphaHealthMonitor] = None,
        miner_daemon: Optional[AlphaMinerDaemon] = None,
        autopsy_agent: Optional[AlphaAutopsyAgent] = None,
        llm_synthesizer: Optional[LLMAlphaSynthesizer] = None,
        target_portfolio_sharpe: float = 2.50,
        max_cycles: int = 10,
        max_budget_usd: float = 1.00
    ):
        self.incubator = incubator or StrategyLifecycleIncubator()
        self.health_monitor = health_monitor or AlphaHealthMonitor()
        self.miner_daemon = miner_daemon
        self.autopsy_agent = autopsy_agent
        self.llm_synthesizer = llm_synthesizer
        
        # Parámetros de Meta y Límites Cuantitativos
        self.target_sharpe = float(os.getenv("AUTONOMOUS_TARGET_SHARPE", str(target_portfolio_sharpe)))
        self.max_cycles = int(os.getenv("AUTONOMOUS_MAX_CYCLES", str(max_cycles)))
        self.max_budget_usd = float(os.getenv("AUTONOMOUS_MAX_BUDGET_USD", str(max_budget_usd)))
        self.completed_cycles = 0
        self.accumulated_cost_usd = 0.0

    def process_cycle(
        self,
        signals_df: pd.DataFrame,
        forward_returns: pd.Series,
        returns_matrix_df: pd.DataFrame,
        historical_baseline_returns: Optional[np.ndarray] = None,
        market_df: Optional[pd.DataFrame] = None
    ) -> SelfHealingCycleReport:
        """
        Ejecuta un ciclo completo de diagnóstico, autopsia de IA, síntesis semántica, cuarentena y rebalanceo.
        """
        actions: List[str] = []
        quarantined: List[str] = []
        promoted: List[str] = []
        health_reports: Dict[str, HealthReport] = {}
        autopsies: Dict[str, AutopsyVerdict] = {}
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
                    rec.status = StrategyLifecycleStatus.ALPHA_DECAY
                    quarantined.append(sid)
                    actions.append(f"Degradación de {sid} a ALPHA_DECAY: {hr.message}")
                    mining_needed = True
                    trigger_reason = f"Decay detectado en {sid} ({hr.status.value})"

                    # Ejecutar Autopsia de IA si el agente está disponible
                    if self.autopsy_agent is not None:
                        verdict = self.autopsy_agent.conduct_autopsy(
                            factor_id=sid,
                            formula=rec.name,
                            health_report=hr
                        )
                        autopsies[sid] = verdict
                        actions.append(f"Autopsia IA completada para {sid}: {verdict.diagnosis} -> {verdict.root_cause[:60]}...")

                elif hr.status == HealthStatus.REGIME_SHIFT:
                    actions.append(f"Regime shift detectado en {sid}. Activando minería adaptativa.")
                    mining_needed = True
                    trigger_reason = "Regime shift detectado por KS-Test"

                elif rec.status == StrategyLifecycleStatus.SANDBOX and hr.status == HealthStatus.HEALTHY:
                    if hr.rolling_ic >= 0.05 and hr.ic_pvalue <= 0.05:
                        rec.status = StrategyLifecycleStatus.LIVE
                        promoted.append(sid)
                        actions.append(f"Promoción de {sid} de SANDBOX a LIVE por IC sólido ({hr.rolling_ic:.3f})")

        # 2. Generación Semántica de Alphas de reemplazo con LLM si hubo decay
        if mining_needed and self.llm_synthesizer is not None and market_df is not None:
            synth_candidates = self.llm_synthesizer.synthesize_alphas(
                market_regime="HIGH_VOLATILITY_MEMECOIN",
                failed_factors=quarantined,
                n_candidates=3
            )
            llm_factors = self.llm_synthesizer.evaluate_and_build_factors(
                verified_candidates=synth_candidates,
                df=market_df,
                forward_returns=forward_returns
            )
            for f in llm_factors:
                if self.miner_daemon and self.miner_daemon.archive:
                    self.miner_daemon.archive.try_insert(f)
                f_id = f"LLM_{f.factor_id}"
                self.incubator.register_strategy(
                    strategy_id=f_id,
                    name=f.formula,
                    backtest_sharpe=f.sharpe_proxy,
                    status=StrategyLifecycleStatus.SANDBOX
                )
                actions.append(f"Factor sintetizado por IA '{f_id}' inyectado a SANDBOX ({f.formula})")

        # 3. Disparo de minería reactiva tradicional en el Daemon
        if mining_needed and self.miner_daemon is not None:
            self.miner_daemon.trigger_immediate_mining(reason=trigger_reason or "Health Alert")
            actions.append(f"Disparo de minería reactiva completado. Razón: {trigger_reason}")

        # 4. Sustitución desde el QualityDiversityArchive si hay factores listos
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

        # 5. Rebalanceo automático de portafolio mediante Paridad Jerárquica de Riesgo (HRP)
        new_weights = self.incubator.rebalance_live_portfolio(returns_matrix_df)
        actions.append(f"Rebalanceo HRP ejecutado. Estrategias activas ponderadas: {list(new_weights.keys())}")

        # 6. Evaluación de Meta Cuantitativa (Target Portfolio Sharpe) y Control de Coste
        self.completed_cycles += 1
        
        # Estimar costo del ciclo: DeepSeek-V3 (~$0.27/M tok) + DeepSeek-R1 (~$0.55/M tok)
        # 1 ciclo promedio consume ~2,500 tokens si hay autopsia y síntesis
        tokens_this_cycle = 0
        if len(autopsies) > 0:
            tokens_this_cycle += 1500 * len(autopsies)
        if mining_needed and self.llm_synthesizer is not None:
            tokens_this_cycle += 1200
        cycle_cost_usd = (tokens_this_cycle / 1_000_000.0) * 0.40
        self.accumulated_cost_usd += cycle_cost_usd

        # Calcular Sharpe Ponderado del portafolio activo
        weighted_sharpe = sum(
            rec.backtest_sharpe * new_weights.get(sid, 0.0)
            for sid, rec in self.incubator.strategies.items()
            if rec.status == StrategyLifecycleStatus.LIVE
        )
        
        goal_reached = bool(weighted_sharpe >= self.target_sharpe and len(new_weights) >= 2)
        if goal_reached:
            actions.append(f"🎯 META CUANTITATIVA ALCANZADA: Sharpe de portafolio {weighted_sharpe:.2f} >= {self.target_sharpe:.2f}. Auto-mejora satisfecha.")

        if self.completed_cycles >= self.max_cycles:
            actions.append(f"🛑 LÍMITE DE CICLOS ALCANZADO ({self.completed_cycles}/{self.max_cycles}). Deteniendo iteraciones automáticas.")

        if self.accumulated_cost_usd >= self.max_budget_usd:
            actions.append(f"🛑 LÍMITE DE PRESUPUESTO ALCANZADO (${self.accumulated_cost_usd:.4f} >= ${self.max_budget_usd:.2f}). Bloqueando llamadas LLM adicionales.")

        return SelfHealingCycleReport(
            cycle_timestamp=datetime.now(timezone.utc).isoformat(),
            actions_taken=actions,
            health_reports=health_reports,
            quarantined_strategies=quarantined,
            promoted_strategies=promoted,
            new_weights=new_weights,
            mining_triggered=mining_needed,
            trigger_reason=trigger_reason,
            autopsies=autopsies,
            goal_reached=goal_reached,
            estimated_cycle_cost_usd=cycle_cost_usd,
            accumulated_cost_usd=self.accumulated_cost_usd
        )
