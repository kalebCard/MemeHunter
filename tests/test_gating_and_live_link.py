"""
test_gating_and_live_link.py - Suite de Pruebas Unitarias e Integración para Sprints 27 y 28.

Cubre:
- PB-93: Protocolo Estricto de Aceptación Fuera de Muestra (OOS Gating, PBO < 15%, DSR >= 95%).
- PB-94: Filtro de Multicolinealidad Estricto (Correlación cruzada < 0.40).
- PB-95: Banda Muerta de Rebalanceo (15% Turnover Deadband) en StrategyLifecycleIncubator.
- PB-96: Auto-compilación de la estrategia de ensamble (`scripts/compile_ensemble_strategy.py`).
- PB-97: Cliente API REST de Freqtrade (`client/freqtrade_client.py`).
- PB-98: Despacho de telemetría e integración con SQLite WAL (`client/telemetry_notifier.py`).
"""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest

from portfolio.strategy_incubator import (
    StrategyLifecycleIncubator,
    StrategyLifecycleStatus,
    StrategyRecord
)
from portfolio.oos_gating import OOSGatingValidator, GatingValidationResult
from scripts.pipelines.compile_ensemble_strategy import generate_ensemble_strategy_file, auto_compile_hook
from client.freqtrade_client import FreqtradeRestClient
from client.telemetry_notifier import TelemetryNotifier
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator
from portfolio.db_schema import init_alpha_factory_db, get_cycle_history_db


def test_turnover_deadband_preserves_weights():
    """PB-95: Verifica que una variación de pesos < 15% active la regla de no-intervención."""
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("ALPHA_01", "ts_rank(close, 14)", 2.0, StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_02", "ts_zscore(high, 10)", 1.8, StrategyLifecycleStatus.LIVE)

    # Fijar pesos iniciales al 50% cada una
    incubator.strategies["ALPHA_01"].target_capital_weight = 0.50
    incubator.strategies["ALPHA_02"].target_capital_weight = 0.50

    # Crear una matriz de retornos con correlación balanceada casi idéntica
    np.random.seed(42)
    n = 100
    r1 = np.random.normal(0.001, 0.02, n)
    # r2 con muy pequeña diferencia de volatilidad para inducir un cambio de peso de apenas ~2-3%
    r2 = r1 * 0.98 + np.random.normal(0, 0.001, n)
    df_returns = pd.DataFrame({"ALPHA_01": r1, "ALPHA_02": r2})

    # Ejecutar rebalanceo con banda muerta al 15%
    weights = incubator.rebalance_live_portfolio(df_returns, turnover_deadband=0.15)

    assert incubator.last_turnover < 0.15
    assert not incubator.last_rebalance_executed
    # Los pesos deben preservarse exactamente en 0.50 cada uno
    assert incubator.strategies["ALPHA_01"].target_capital_weight == pytest.approx(0.50, abs=1e-3)
    assert incubator.strategies["ALPHA_02"].target_capital_weight == pytest.approx(0.50, abs=1e-3)


def test_turnover_deadband_executes_on_large_shift():
    """PB-95: Verifica que un cambio de pesos >= 15% ejecute la rotación real."""
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("ALPHA_01", "ts_rank(close, 14)", 2.0, StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("ALPHA_02", "ts_zscore(high, 10)", 1.8, StrategyLifecycleStatus.LIVE)

    # Fijar pesos iniciales desbalanceados
    incubator.strategies["ALPHA_01"].target_capital_weight = 0.85
    incubator.strategies["ALPHA_02"].target_capital_weight = 0.15

    # Retornos donde ALPHA_02 tiene volatilidad 4 veces menor (fuerza un gran desplazamiento de pesos)
    np.random.seed(42)
    n = 100
    r1 = np.random.normal(0.001, 0.04, n)
    r2 = np.random.normal(0.001, 0.01, n)
    df_returns = pd.DataFrame({"ALPHA_01": r1, "ALPHA_02": r2})

    weights = incubator.rebalance_live_portfolio(df_returns, turnover_deadband=0.15)

    assert incubator.last_turnover >= 0.15
    assert incubator.last_rebalance_executed
    assert weights["ALPHA_02"] > weights["ALPHA_01"]


def test_multicollinearity_filter_rejection():
    """PB-94: Verifica que un factor con correlación cruzada >= 0.40 sea rechazado."""
    validator = OOSGatingValidator(max_correlation=0.40)

    # Retornos de estrategia viva existente
    np.random.seed(42)
    n = 100
    r_live = pd.Series(np.random.normal(0.002, 0.02, n))
    returns_matrix = pd.DataFrame({"LIVE_ALPHA_01": r_live})

    # Candidata con retornos casi idénticos (alta multicolinealidad ~0.90)
    cand_returns = r_live * 0.95 + np.random.normal(0, 0.003, n)

    passed, max_corr, conflict_id = validator.check_multicollinearity(
        candidate_returns=cand_returns,
        returns_matrix_df=returns_matrix,
        live_strategy_ids=["LIVE_ALPHA_01"]
    )

    assert not passed
    assert max_corr >= 0.40
    assert conflict_id == "LIVE_ALPHA_01"


def test_multicollinearity_filter_approval():
    """PB-94: Verifica que un factor ortogonal (< 0.40) apruebe el filtro de multicolinealidad."""
    validator = OOSGatingValidator(max_correlation=0.40)

    np.random.seed(123)
    n = 100
    r_live = pd.Series(np.random.normal(0.002, 0.02, n))
    returns_matrix = pd.DataFrame({"LIVE_ALPHA_01": r_live})

    # Candidata independiente
    cand_returns = pd.Series(np.random.normal(0.001, 0.02, n))

    passed, max_corr, conflict_id = validator.check_multicollinearity(
        candidate_returns=cand_returns,
        returns_matrix_df=returns_matrix,
        live_strategy_ids=["LIVE_ALPHA_01"]
    )

    assert passed
    assert max_corr < 0.40


def test_oos_gating_protocol_rejection_insufficient_sample():
    """PB-93: Rechazo por muestra insuficiente fuera de muestra."""
    validator = OOSGatingValidator(min_bars=100)
    sig = pd.Series([1.0] * 30)
    fwd_ret = pd.Series([0.01] * 30)

    result = validator.validate_candidate("TEST_ALPHA", sig, fwd_ret)
    assert not result.passed
    assert "Muestra insuficiente" in result.rejection_reason


def test_freqtrade_rest_client_offline_graceful():
    """PB-97: Verifica que el cliente maneje la desconexión del contenedor Freqtrade sin fallar."""
    client = FreqtradeRestClient(base_url="http://127.0.0.1:59999", timeout_sec=0.5)

    ping_res = client.ping()
    assert ping_res["status"] == "offline"

    reload_res = client.reload_config()
    assert reload_res["status"] == "offline"
    assert not reload_res["reloaded"]


def test_auto_compile_ensemble_strategy(tmp_path):
    """PB-96: Verifica la compilación automática de la estrategia para Freqtrade."""
    out_file = str(tmp_path / "MemeHunter_MinedEnsemble.py")
    res_path = generate_ensemble_strategy_file(
        output_strategy_path=out_file
    )

    assert os.path.exists(res_path)
    with open(res_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "class MemeHunter_MinedEnsemble(IStrategy):" in content
    assert "ACTIVE_WEIGHTS" in content
    assert "populate_entry_trend" in content
    assert "populate_exit_trend" in content


def test_autonomous_orchestrator_e2e_with_governance(tmp_path):
    """PB-93 a PB-98: Integración End-to-End del orquestador con gobernanza y telemetría."""
    db_file = str(tmp_path / "test_alpha_factory.db")
    init_alpha_factory_db(db_file)

    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy(
        strategy_id="ALPHA_LIVE_01",
        name="ts_rank(close, 14)",
        backtest_sharpe=2.2,
        status=StrategyLifecycleStatus.LIVE
    )
    incubator.register_strategy(
        strategy_id="ALPHA_CAND_02",
        name="ts_zscore((high - low), 10)",
        backtest_sharpe=1.9,
        status=StrategyLifecycleStatus.SANDBOX
    )

    notifier = TelemetryNotifier(db_path=db_file, log_jsonl_path=str(tmp_path / "loop.jsonl"))
    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        telemetry_notifier=notifier,
        auto_compile_on_change=False  # No sobreescribir archivo local de producción en este test
    )

    # Crear datos de señales y retornos sintéticos realistas
    np.random.seed(99)
    n_bars = 80
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="4h")
    fwd_ret = pd.Series(np.random.normal(0.001, 0.02, n_bars), index=dates)
    sig1 = pd.Series(np.sign(fwd_ret.replace(0, 1e-6)), index=dates)
    sig2 = pd.Series(np.random.choice([-1.0, 1.0], size=n_bars), index=dates)

    signals_df = pd.DataFrame({"ALPHA_LIVE_01": sig1, "ALPHA_CAND_02": sig2}, index=dates)
    returns_matrix = pd.DataFrame({
        "ALPHA_LIVE_01": sig1 * fwd_ret,
        "ALPHA_CAND_02": sig2 * fwd_ret
    }, index=dates)

    report = orchestrator.process_cycle(
        signals_df=signals_df,
        forward_returns=fwd_ret,
        returns_matrix_df=returns_matrix
    )

    assert report is not None
    assert len(report.actions_taken) > 0
    # Verificar persistencia en base de datos SQLite WAL de cycle_history
    history = get_cycle_history_db(limit=10, db_path=db_file)
    assert len(history) >= 1
    assert history[0]["active_strategies"] >= 1
