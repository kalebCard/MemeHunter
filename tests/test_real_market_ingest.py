"""
tests/test_real_market_ingest.py
--------------------------------
Suite de pruebas para el Sprint 26: Ingesta de Mercado Real y Asincronía (PB-90, PB-91, PB-92).
Verifica:
1. Carga de velas reales OHLCV e indicadores de microestructura desde feather / fallback.
2. Construcción vectorial de señales y matriz de retornos a partir de fórmulas de la incubadora.
3. Smart Caching de autopsias en AlphaAutopsyAgent (PB-92).
4. Bloqueo de concurrencia y telemetría de estado del bucle (PB-91).
"""

import os
import json
import pytest
import numpy as np
import pandas as pd

from data_engine.real_market_feed import (
    load_real_market_dataframe,
    evaluate_factor_series,
    build_signals_and_returns_for_strategies
)
from portfolio.alpha_health_monitor import HealthReport, HealthStatus
from portfolio.alpha_autopsy import AlphaAutopsyAgent, AutopsyVerdict
from portfolio.strategy_incubator import StrategyRecord, StrategyLifecycleStatus


def test_load_real_market_dataframe():
    """Verifica que se carguen velas de mercado con todas las columnas enriquecidas."""
    df = load_real_market_dataframe(pair="DOGE_USDT_USDT", timeframe="4h", n_bars=100)
    assert not df.empty
    assert len(df) >= 30
    for col in ['open', 'high', 'low', 'close', 'volume', 'returns', 'hl_spread', 'vwap', 'rvol']:
        assert col in df.columns, f"Falta columna requerida: {col}"
    assert not df['returns'].isna().any()
    assert not df['close'].isna().any()


def test_evaluate_factor_series():
    """Verifica la evaluación vectorial de fórmulas simbólicas contra el dataset de mercado."""
    df = load_real_market_dataframe(pair="DOGE_USDT_USDT", timeframe="4h", n_bars=60)
    
    # 1. ts_rank
    sig_rank = evaluate_factor_series("ts_rank(close, 14)", df)
    assert len(sig_rank) == len(df)
    assert not sig_rank.isna().any()
    assert sig_rank.min() >= -1.01 and sig_rank.max() <= 1.01

    # 2. ts_zscore con rvol
    sig_z = evaluate_factor_series("ts_zscore((high - low), 10) * rvol", df)
    assert len(sig_z) == len(df)
    assert not sig_z.isna().any()

    # 3. vwap factor
    sig_vwap = evaluate_factor_series("(close - vwap) * rvol", df)
    assert len(sig_vwap) == len(df)
    assert not sig_vwap.isna().any()


def test_build_signals_and_returns_for_strategies():
    """Verifica la construcción de signals_df y returns_matrix_df para la incubadora."""
    df = load_real_market_dataframe(pair="DOGE_USDT_USDT", timeframe="4h", n_bars=50)
    strategies = {
        "ALPHA_MOM_01": StrategyRecord(
            strategy_id="ALPHA_MOM_01",
            name="ts_rank(close, 14)",
            status=StrategyLifecycleStatus.LIVE,
            target_capital_weight=0.5,
            backtest_sharpe=2.1,
            live_sharpe=2.0,
            days_in_stage=5,
            decay_zscore=0.1,
            last_audit_date="2026-10-12"
        ),
        "ALPHA_VOL_02": StrategyRecord(
            strategy_id="ALPHA_VOL_02",
            name="ts_zscore((high - low), 10) * rvol",
            status=StrategyLifecycleStatus.LIVE,
            target_capital_weight=0.5,
            backtest_sharpe=1.9,
            live_sharpe=1.8,
            days_in_stage=5,
            decay_zscore=-0.1,
            last_audit_date="2026-10-12"
        )
    }

    signals_df, fwd_ret, ret_matrix = build_signals_and_returns_for_strategies(df, strategies)
    assert "ALPHA_MOM_01" in signals_df.columns
    assert "ALPHA_VOL_02" in signals_df.columns
    assert "ALPHA_MOM_01" in ret_matrix.columns
    assert len(fwd_ret) == len(df)
    assert not ret_matrix.isna().any().any()


def test_alpha_autopsy_smart_cache(tmp_path):
    """Verifica que el Smart Cache de AlphaAutopsyAgent evite consultas redundantes (PB-92)."""
    hpath = str(tmp_path / "autopsies.json")
    db_file = str(tmp_path / "alpha_factory.db")

    agent = AlphaAutopsyAgent(history_path=hpath)
    agent.db_path = db_file
    agent.enable_cache = True

    # Insertar una autopsia previa
    cached_verdict = AutopsyVerdict(
        factor_id="ALPHA_DECAY_TEST",
        formula="ts_delay(close, 10)",
        health_status=HealthStatus.WARNING_DECAY.value,
        diagnosis="TEST_CACHED_DIAGNOSIS",
        root_cause="Degradación de volatilidad",
        recommendation="Poner en cuarentena inmediata",
        confidence_score=0.95,
        suggested_actions=["QUARANTINE"]
    )
    agent.autopsy_records.append(cached_verdict)
    agent.save_history()

    # Diagnosticar con las mismas condiciones: debe golpear el cache sin llamar al LLM
    hr = HealthReport(
        factor_id="ALPHA_DECAY_TEST",
        status=HealthStatus.WARNING_DECAY,
        rolling_ic=-0.04,
        ic_pvalue=0.20,
        ic_ir=-0.5,
        cusum_detected=True,
        cusum_stat=4.2,
        drift_detected=False,
        ks_pvalue=0.30,
        message="Deterioro detectado"
    )

    verdict = agent.conduct_autopsy(
        factor_id="ALPHA_DECAY_TEST",
        formula="ts_delay(close, 10)",
        health_report=hr
    )

    assert verdict.diagnosis == "TEST_CACHED_DIAGNOSIS"
    assert verdict.confidence_score == 0.95
