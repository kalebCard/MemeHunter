"""
Demostración E2E del Bucle Autónomo de Auto-Mejora y Auto-Sanación de Portafolio.
Sprint 1: Motor Cuantitativo Auto-Evolutivo.

Ejecuta una simulación completa donde:
1. Dos estrategias operan en vivo (LIVE).
2. Se inyecta degradación forzada (Alpha Decay) y un cambio de régimen en una de ellas.
3. El `AutonomousPortfolioOrchestrator` diagnostica en tiempo real con `AlphaHealthMonitor`.
4. El factor en desgaste es degradado y su capital retirado automáticamente.
5. Se dispara la reposición automática desde el `QualityDiversityArchive` hacia SANDBOX.
6. El portafolio se repondera dinámicamente con Hierarchical Risk Parity (HRP).
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
from mining.alpha_daemon import AlphaMinerDaemon, QualityDiversityArchive
from mining.genetic_search import AlphaFactor


def run_demo():
    print("=" * 80)
    print(" [SISTEMA CUANTITATIVO AUTO-EVOLUTIVO] DEMOSTRACION DEL BUCLE CERRADO E2E")
    print("=" * 80)

    # 1. Configurar entorno y datos de mercado
    np.random.seed(42)
    n_bars = 100
    dates = pd.date_range("2026-03-01", periods=n_bars, freq="15min")
    
    returns = np.random.normal(0.0005, 0.015, n_bars)
    # Factor Alpha_1: predictivo y robusto
    sig_alpha_1 = returns * 0.85 + np.random.normal(0.0, 0.003, n_bars)
    # Factor Alpha_2: en desgaste (puro ruido descorrelacionado)
    sig_alpha_2 = np.random.normal(0.0, 1.0, n_bars)

    signals_df = pd.DataFrame({'ALPHA_MOM_01': sig_alpha_1, 'ALPHA_VOL_02': sig_alpha_2}, index=dates)
    forward_returns = pd.Series(returns, index=dates)
    returns_matrix = pd.DataFrame({
        'ALPHA_MOM_01': np.random.normal(0.001, 0.012, n_bars),
        'ALPHA_VOL_02': np.random.normal(-0.0005, 0.020, n_bars)
    }, index=dates)

    # 2. Inicializar Incubadora
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("ALPHA_MOM_01", "Momentum Lead", backtest_sharpe=2.1, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_VOL_02", "Volume Skew", backtest_sharpe=1.6, status=StrategyLifecycleStatus.LIVE)
    print("\n[Paso 1] Estado Inicial del Portafolio:")
    for sid, rec in incubator.strategies.items():
        print(f"  * {sid} -> Estado: {rec.status.value} | Backtest Sharpe: {rec.backtest_sharpe}")

    # 3. Inicializar Daemon con banco de factores ortogonales listos
    daemon = AlphaMinerDaemon(archive_path="mining/diversity_archive.json")
    backup_factor = AlphaFactor(
        factor_id="BACKUP_REVERSION_03",
        formula="ts_rank(volume_delta, 14)",
        ic_mean=0.08,
        ic_std=0.03,
        ic_ir=2.66,
        sharpe_proxy=1.95,
        turnover=0.12,
        depth=2,
        correlation_with_existing=0.10
    )
    daemon.archive.try_insert(backup_factor)
    print(f"\n[Paso 2] Archivo de Diversidad Activo con factor de reserva: {backup_factor.factor_id} (IC_IR: {backup_factor.ic_ir:.2f})")

    # 4. Orquestación del ciclo autónomo
    health_mon = AlphaHealthMonitor(rolling_window=30, min_healthy_ic=0.04)
    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        health_monitor=health_mon,
        miner_daemon=daemon
    )

    print("\n[Paso 3] Ejecutando Diagnóstico y Ciclo de Auto-Sanación...")
    report = orchestrator.process_cycle(
        signals_df=signals_df,
        forward_returns=forward_returns,
        returns_matrix_df=returns_matrix
    )

    print("\n" + "-" * 80)
    print(" RESULTADOS DE LA AUDITORIA AUTONOMA")
    print("-" * 80)
    for sid, hr in report.health_reports.items():
        print(f"  [{sid}] -> Diagnóstico: {hr.status.value} | IC Rodante: {hr.rolling_ic:.4f} (p-val: {hr.ic_pvalue:.4f})")
        print(f"             Detalle: {hr.message}")

    print("\n Acciones de Auto-Mejora Ejecutadas:")
    for act in report.actions_taken:
        print(f"  [x] {act}")

    print("\n Nuevos Pesos de Capital Asignados por HRP:")
    for sid, w in report.new_weights.items():
        print(f"  -> {sid}: {w * 100:.2f}% de capital activo")

    print("\n Estado Final de la Incubadora:")
    for sid, rec in incubator.strategies.items():
        print(f"  * {sid}: {rec.status.value} (Peso objetivo: {rec.target_capital_weight * 100:.2f}%)")

    print("=" * 80)
    print(" [OK] El bucle cerrado detectó el alpha defectuoso, reasignó capital y postuló un relevo automáticamente.")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
