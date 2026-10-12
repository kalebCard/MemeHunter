"""
Demostración E2E del Bucle Autónomo Cuantitativo Aumentado por IA (OpenRouter).
Sprint 1 & Sprint 2: Motor Cuantitativo Auto-Evolutivo & Cognitivo.

Ejecuta una simulación completa donde:
1. Se diagnostica una cartera activa en producción.
2. Un factor sufre Alpha Decay forzado.
3. El `AlphaAutopsyAgent` ejecuta una autopsia cognitiva vía OpenRouter (DeepSeek-R1 / Claude 3.5).
4. El `LLMAlphaSynthesizer` formula hipótesis de reemplazo basadas en microestructura.
5. El `FormulaASTParser` valida y compila de forma segura las expresiones generadas por el LLM.
6. El factor nuevo es admitido a SANDBOX y el capital es rebalanceado vía Hierarchical Risk Parity (HRP).
"""

import os
import sys
import numpy as np
import pandas as pd

# Asegurar path raíz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio.alpha_health_monitor import AlphaHealthMonitor, HealthStatus
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator
from portfolio.alpha_autopsy import AlphaAutopsyAgent
from mining.alpha_daemon import AlphaMinerDaemon, QualityDiversityArchive
from mining.llm_client import OpenRouterClient
from mining.llm_alpha_generator import LLMAlphaSynthesizer
from mining.genetic_search import AlphaFactor


def run_demo():
    print("=" * 85)
    print(" [SISTEMA CUANTITATIVO AUTO-EVOLUTIVO CON IA] DEMOSTRACION E2E CON OPENROUTER")
    print("=" * 85)

    # 1. Configurar entorno y datos de mercado sintéticos de memecoins
    np.random.seed(42)
    n_bars = 100
    dates = pd.date_range("2026-03-01", periods=n_bars, freq="15min")
    
    returns = np.random.normal(0.0005, 0.015, n_bars)
    prices = 1.0 * np.exp(np.cumsum(returns))
    market_df = pd.DataFrame({
        'open': prices * 0.998,
        'high': prices * 1.012,
        'low': prices * 0.990,
        'close': prices,
        'volume': np.random.uniform(50_000, 500_000, n_bars),
        'vwap': prices * 0.999,
        'rvol': np.random.uniform(0.8, 2.5, n_bars),
        'hl_spread': (prices * 1.012 - prices * 0.990) / prices,
        'returns': returns
    }, index=dates)

    # Factor 1: Saludable (alta predictibilidad)
    sig_alpha_1 = returns * 0.85 + np.random.normal(0.0, 0.003, n_bars)
    # Factor 2: En decadencia (ruido descorrelacionado)
    sig_alpha_2 = np.random.normal(0.0, 1.0, n_bars)

    signals_df = pd.DataFrame({'ALPHA_MOM_01': sig_alpha_1, 'ALPHA_VOL_DECAY': sig_alpha_2}, index=dates)
    forward_returns = pd.Series(returns, index=dates)
    returns_matrix = pd.DataFrame({
        'ALPHA_MOM_01': np.random.normal(0.001, 0.012, n_bars),
        'ALPHA_VOL_DECAY': np.random.normal(-0.0005, 0.020, n_bars)
    }, index=dates)

    # 2. Inicializar Incubadora
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("ALPHA_MOM_01", "ts_rank(close, 14)", backtest_sharpe=2.1, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_VOL_DECAY", "ts_delay(close, 10)", backtest_sharpe=1.6, status=StrategyLifecycleStatus.LIVE)
    
    print("\n[Paso 1] Estado Inicial del Portafolio:")
    for sid, rec in incubator.strategies.items():
        print(f"  * {sid} -> Estado: {rec.status.value} | Backtest Sharpe: {rec.backtest_sharpe:.2f}")

    # 3. Inicializar Componentes de IA (OpenRouter)
    llm_client = OpenRouterClient()
    autopsy_agent = AlphaAutopsyAgent(client=llm_client)
    synthesizer = LLMAlphaSynthesizer(client=llm_client)
    daemon = AlphaMinerDaemon(archive_path="mining/diversity_archive.json")

    # 4. Orquestación del ciclo autónomo
    health_mon = AlphaHealthMonitor(rolling_window=30, min_healthy_ic=0.04)
    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        health_monitor=health_mon,
        miner_daemon=daemon,
        autopsy_agent=autopsy_agent,
        llm_synthesizer=synthesizer
    )

    print("\n[Paso 2] Ejecutando Diagnóstico, Autopsia Forense de IA y Síntesis de Factores...")
    report = orchestrator.process_cycle(
        signals_df=signals_df,
        forward_returns=forward_returns,
        returns_matrix_df=returns_matrix,
        market_df=market_df
    )

    print("\n" + "-" * 85)
    print(" [1] RESULTADOS DE LA AUDITORIA DE SALUD CUANTITATIVA")
    print("-" * 85)
    for sid, hr in report.health_reports.items():
        print(f"  [{sid}] -> {hr.status.value} | IC: {hr.rolling_ic:.4f} (p-val: {hr.ic_pvalue:.4f})")

    print("\n" + "-" * 85)
    print(" [2] AUTOPSIA FORENSE DE IA (ALPHA AUTOPSY)")
    print("-" * 85)
    for sid, verdict in report.autopsies.items():
        print(f"  Factor Auditado: {sid}")
        print(f"  * Diagnóstico IA:  {verdict.diagnosis}")
        print(f"  * Causa Raíz:      {verdict.root_cause}")
        print(f"  * Recomendación:   {verdict.recommendation}")
        print(f"  * Acciones IA:     {verdict.suggested_actions}")

    print("\n" + "-" * 85)
    print(" [3] ACCIONES DE AUTO-MEJORA & SINTESIS SEMANTICA")
    print("-" * 85)
    for act in report.actions_taken:
        print(f"  [x] {act}")

    print("\n" + "-" * 85)
    print(" [4] REASIGNACION OPTIMA DE CAPITAL (HRP)")
    print("-" * 85)
    for sid, w in report.new_weights.items():
        print(f"  -> {sid}: {w * 100:.2f}% de capital activo asignado")

    print("\n" + "-" * 85)
    print(" [5] ESTADO FINAL DE LA INCUBADORA")
    print("-" * 85)
    for sid, rec in incubator.strategies.items():
        print(f"  * {sid}: [{rec.status.value}] Peso: {rec.target_capital_weight * 100:.2f}% | Fórmula: {rec.name[:45]}")

    print("=" * 85)
    print(" [OK] BUCLE CERRADO COMPLETADO CON EXITO CON COGNICION IA.")
    print("=" * 85)


if __name__ == "__main__":
    run_demo()
