"""
Pruebas Unitarias e Integración para el Motor Cuantitativo Aumentado por IA (OpenRouter).
Sprint 2: Motor de Investigación Cuantitativa Aumentado por IA.
"""

import os
import json
import numpy as np
import pandas as pd
import pytest

from mining.formula_parser import FormulaASTParser
from mining.llm_client import OpenRouterClient, OpenRouterModel
from mining.llm_alpha_generator import LLMAlphaSynthesizer
from portfolio.alpha_health_monitor import AlphaHealthMonitor, HealthStatus, HealthReport
from portfolio.alpha_autopsy import AlphaAutopsyAgent, AutopsyVerdict
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator


def test_formula_ast_parser_valid():
    # Expresión con operadores temporales y binarios
    f1 = "ts_rank(close, 10)"
    node1 = FormulaASTParser.parse(f1)
    assert node1.to_formula() == "ts_rank(close, 10)"
    assert node1.get_depth() == 2

    # Expresión matemática compuesta
    f2 = "(close - vwap) * rvol"
    node2 = FormulaASTParser.parse(f2)
    assert node2.get_depth() >= 2

    # Operadores funcionales
    f3 = "div(ts_delta(volume, 5), add(vwap, 1.0))"
    node3 = FormulaASTParser.parse(f3)
    assert node3.get_depth() >= 3


def test_formula_ast_parser_security_rejections():
    # Intento de inyección de funciones no autorizadas
    with pytest.raises(ValueError):
        FormulaASTParser.parse("__import__('os').system('ls')")

    with pytest.raises(ValueError):
        FormulaASTParser.parse("eval('close + 1')")

    with pytest.raises(ValueError):
        FormulaASTParser.parse("non_existent_feature * 2")


def test_openrouter_client_fallback_mode():
    # Cliente sin API key entra en modo offline automático
    client = OpenRouterClient(api_key="")
    assert client.is_offline_mode is True

    resp_synth = client.complete("sintetizar alphas para memecoins", json_mode=True)
    assert "formulas" in resp_synth
    assert len(resp_synth["formulas"]) >= 3

    resp_auto = client.complete("autopsia forense para factor caído", json_mode=True)
    assert "diagnosis" in resp_auto
    assert "root_cause" in resp_auto


def test_llm_alpha_synthesizer():
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    prices = 100.0 + np.cumsum(np.random.normal(0, 0.5, n))
    market_df = pd.DataFrame({
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.uniform(1000, 5000, n),
        'vwap': prices,
        'rvol': np.ones(n),
        'hl_spread': np.ones(n) * 0.02,
        'returns': np.random.normal(0, 0.01, n)
    }, index=dates)
    fwd_ret = pd.Series(np.random.normal(0, 0.01, n), index=dates)

    synthesizer = LLMAlphaSynthesizer()
    verified = synthesizer.synthesize_alphas(market_regime="HIGH_VOLATILITY", n_candidates=3)
    assert len(verified) > 0

    factors = synthesizer.evaluate_and_build_factors(verified, market_df, fwd_ret)
    assert len(factors) > 0
    assert hasattr(factors[0], "ic_ir")


def test_alpha_autopsy_agent(tmp_path):
    history_file = str(tmp_path / "test_autopsies.json")
    agent = AlphaAutopsyAgent(history_path=history_file)

    hr = HealthReport(
        factor_id="ALPHA_TEST_DECAY",
        status=HealthStatus.WARNING_DECAY,
        rolling_ic=-0.05,
        ic_pvalue=0.45,
        ic_ir=-0.3,
        cusum_detected=False,
        cusum_stat=1.2,
        drift_detected=True,
        ks_pvalue=0.01,
        message="Factor decayed"
    )

    verdict = agent.conduct_autopsy(
        factor_id="ALPHA_TEST_DECAY",
        formula="ts_rank(close, 20)",
        health_report=hr
    )

    assert verdict.factor_id == "ALPHA_TEST_DECAY"
    assert verdict.diagnosis != ""
    assert os.path.exists(history_file)


def test_orchestrator_with_ai_integration(tmp_path):
    np.random.seed(99)
    n = 80
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    returns = np.random.normal(0.001, 0.01, n)
    sig_healthy = returns * 0.8 + np.random.normal(0.0, 0.002, n)
    sig_failing = np.random.normal(0.0, 1.0, n)

    signals_df = pd.DataFrame({'HEALTHY_01': sig_healthy, 'FAILING_02': sig_failing}, index=dates)
    fwd_ret = pd.Series(returns, index=dates)
    ret_matrix = pd.DataFrame({'HEALTHY_01': returns, 'FAILING_02': -returns}, index=dates)

    market_df = pd.DataFrame({
        'open': np.ones(n) * 10,
        'high': np.ones(n) * 10.5,
        'low': np.ones(n) * 9.5,
        'close': np.ones(n) * 10,
        'volume': np.random.uniform(500, 2000, n),
        'vwap': np.ones(n) * 10,
        'rvol': np.ones(n),
        'hl_spread': np.ones(n) * 0.1,
        'returns': returns
    }, index=dates)

    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("HEALTHY_01", "ts_rank(close, 5)", 2.0, StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("FAILING_02", "ts_delay(close, 10)", 1.5, StrategyLifecycleStatus.LIVE)

    autopsy_agent = AlphaAutopsyAgent(history_path=str(tmp_path / "autopsies.json"))
    synthesizer = LLMAlphaSynthesizer()

    orchestrator = AutonomousPortfolioOrchestrator(
        incubator=incubator,
        health_monitor=AlphaHealthMonitor(rolling_window=25, min_healthy_ic=0.03),
        autopsy_agent=autopsy_agent,
        llm_synthesizer=synthesizer
    )

    report = orchestrator.process_cycle(
        signals_df=signals_df,
        forward_returns=fwd_ret,
        returns_matrix_df=ret_matrix,
        market_df=market_df
    )

    assert "FAILING_02" in report.quarantined_strategies
    assert "FAILING_02" in report.autopsies
    # Verificamos que se generó y agregó un factor por IA
    injected_llm = [s for s in incubator.strategies if s.startswith("LLM_")]
    assert len(injected_llm) > 0
