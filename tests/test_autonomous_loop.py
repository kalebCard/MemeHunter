"""
Pruebas de Integración E2E para el Bucle Autónomo Auto-Evolutivo.
Sprint 1: Motor Cuantitativo Auto-Evolutivo (US-2.1, US-2.2, US-3.1, US-3.2).
"""

import os
import numpy as np
import pandas as pd
import pytest

from mining.genetic_search import AlphaFactor
from mining.alpha_daemon import QualityDiversityArchive, AlphaMinerDaemon
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from portfolio.alpha_health_monitor import AlphaHealthMonitor, HealthStatus
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator


def test_quality_diversity_archive():
    archive = QualityDiversityArchive(max_inter_correlation=0.50)

    f1 = AlphaFactor(
        factor_id="F1_MOM",
        formula="ts_rank(close, 10)",
        ic_mean=0.08,
        ic_std=0.04,
        ic_ir=2.0,
        sharpe_proxy=1.8,
        turnover=0.15,
        depth=2,
        correlation_with_existing=0.10
    )

    inserted = archive.try_insert(f1)
    assert inserted, "f1 debe insertarse en el nicho correspondiente"
    assert len(archive.get_active_factors()) == 1

    # Factor de menor fitness en el mismo nicho debe rechazarse
    f2 = AlphaFactor(
        factor_id="F2_MOM_WEAK",
        formula="ts_rank(close, 5)",
        ic_mean=0.02,
        ic_std=0.05,
        ic_ir=0.4,
        sharpe_proxy=0.5,
        turnover=0.30,
        depth=2,
        correlation_with_existing=0.10
    )
    inserted_weak = archive.try_insert(f2)
    assert not inserted_weak, "f2 con menor fitness no debe reemplazar a f1"

    # Factor con alta correlación debe ser rechazado
    f3 = AlphaFactor(
        factor_id="F3_HIGH_CORR",
        formula="volume_delta(volume, 10)",
        ic_mean=0.10,
        ic_std=0.04,
        ic_ir=2.5,
        sharpe_proxy=2.0,
        turnover=0.10,
        depth=2,
        correlation_with_existing=0.85  # Sobrepasa el 0.50
    )
    inserted_corr = archive.try_insert(f3)
    assert not inserted_corr, "f3 debe ser rechazado por sobrepasar umbral de correlación"


def test_autonomous_orchestrator_self_healing_e2e(tmp_path):
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")

    returns = np.random.normal(0.001, 0.015, n)
    # Factor A sano (alta correlación positiva con retornos)
    sig_a = returns * 0.9 + np.random.normal(0.0, 0.002, n)
    # Factor B en decadencia (ruido aleatorio)
    sig_b = np.random.normal(0.0, 1.0, n)

    signals_df = pd.DataFrame({'STRAT_A': sig_a, 'STRAT_B': sig_b}, index=dates)
    fwd_ret = pd.Series(returns, index=dates)

    returns_matrix = pd.DataFrame({
        'STRAT_A': np.random.normal(0.001, 0.01, n),
        'STRAT_B': np.random.normal(-0.001, 0.02, n)
    }, index=dates)

    # Configurar incubadora con A y B en LIVE
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("STRAT_A", "Alpha_Alpha", backtest_sharpe=1.8, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("STRAT_B", "Alpha_Beta", backtest_sharpe=1.5, status=StrategyLifecycleStatus.LIVE)

    # Configurar Daemon y Archivo con un sustituto listo
    archive_file = str(tmp_path / "test_archive.json")
    daemon = AlphaMinerDaemon(archive_path=archive_file)
    substitute = AlphaFactor(
        factor_id="REPLACEMENT_01",
        formula="ts_rank(volume, 20)",
        ic_mean=0.07,
        ic_std=0.03,
        ic_ir=2.33,
        sharpe_proxy=1.9,
        turnover=0.10,
        depth=2,
        correlation_with_existing=0.05
    )
    daemon.archive.try_insert(substitute)

    health_mon = AlphaHealthMonitor(rolling_window=30, min_healthy_ic=0.04)
    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        health_monitor=health_mon,
        miner_daemon=daemon
    )

    report = orchestrator.process_cycle(
        signals_df=signals_df,
        forward_returns=fwd_ret,
        returns_matrix_df=returns_matrix
    )

    # Verificaciones:
    # 1. STRAT_B debió ser degradada a ALPHA_DECAY
    assert "STRAT_B" in report.quarantined_strategies
    assert incubator.strategies["STRAT_B"].status == StrategyLifecycleStatus.ALPHA_DECAY

    # 2. STRAT_A debe permanecer en LIVE y recibir el 100% del peso en rebalanceo HRP
    assert incubator.strategies["STRAT_A"].status == StrategyLifecycleStatus.LIVE
    assert "STRAT_A" in report.new_weights
    assert np.isclose(report.new_weights["STRAT_A"], 1.0, atol=1e-3)
    assert report.new_weights.get("STRAT_B", 0.0) == 0.0

    # 3. La minería debió ser activada por la degradación
    assert report.mining_triggered is True

    # 4. El sustituto debió ser inyectado a la incubadora en SANDBOX
    assert "ARCHIVE_REPLACEMENT_01" in incubator.strategies
    assert incubator.strategies["ARCHIVE_REPLACEMENT_01"].status == StrategyLifecycleStatus.SANDBOX
