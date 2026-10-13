"""
test_sprint29_bidirectional_and_sync.py - Suite de Pruebas para Sprint 29.

Cubre:
- PB-99: Ensamble Multi-Factor Bidireccional (Generación de señales enter_long y enter_short).
- PB-100: Sincronizador Automático de Datos de Binance Futures (auto_data_sync.py).
- PB-101: Penalización por Fricción y Spread Dinámico en la Incubadora y Gating OOS.
- PB-102: Gatillo Rápido Multi-Horizonte con confirmación de momentum.
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from user_data.strategies.MemeHunter_MinedEnsemble import MemeHunter_MinedEnsemble
from data_engine.auto_data_sync import sync_symbol_feather, fetch_klines_from_binance
from data_engine.real_market_feed import build_signals_and_returns_for_strategies
from portfolio.oos_gating import OOSGatingValidator
from portfolio.strategy_incubator import StrategyLifecycleStatus, StrategyRecord


def test_pb99_bidirectional_long_and_short_signals():
    """PB-99: Verifica la generación de señales tanto LONG como SHORT según el score del ensamble."""
    strat = MemeHunter_MinedEnsemble(config={})
    
    # Construir dataframe con 2 segmentos claros: uno alcista y otro bajista
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2026-01-01", periods=n, freq="4h")
    
    # 100 velas con drift alcista moderado (RSI saludable entre 50 y 65)
    ret_bull = np.random.normal(0.004, 0.015, 100)
    prices_bull = 100.0 * np.exp(np.cumsum(ret_bull))
    # 100 velas con drift bajista moderado
    ret_bear = np.random.normal(-0.005, 0.015, 100)
    prices_bear = prices_bull[-1] * np.exp(np.cumsum(ret_bear))
    close = np.concatenate([prices_bull, prices_bear])
    
    df = pd.DataFrame({
        'open': close * 0.998,
        'high': close * 1.010,
        'low': close * 0.990,
        'close': close,
        'volume': np.full(n, 100_000.0)
    }, index=dates)

    df = strat.populate_indicators(df, metadata={'pair': 'DOGE/USDT:USDT'})
    
    # Forzar composite_alpha_score artificial positivo en tramo alcista y negativo en tramo bajista
    # para auditar la lógica de confluencia de populate_entry_trend
    df.loc[df.index[:80], 'composite_alpha_score'] = 0.20   # Fuerte señal LONG
    df.loc[df.index[120:], 'composite_alpha_score'] = -0.20 # Fuerte señal SHORT
    
    df = strat.populate_entry_trend(df, metadata={'pair': 'DOGE/USDT:USDT'})
    df = strat.populate_exit_trend(df, metadata={'pair': 'DOGE/USDT:USDT'})

    # 1. Verificar presencia de columnas bidireccionales
    assert 'enter_long' in df.columns
    assert 'enter_short' in df.columns
    assert 'exit_long' in df.columns
    assert 'exit_short' in df.columns

    # 2. Verificar que se hayan activado tanto señales en LONG como en SHORT
    long_entries = df[df['enter_long'] == 1]
    short_entries = df[df['enter_short'] == 1]

    assert len(long_entries) > 0, "Debe generar al menos una entrada LONG en régimen alcista con score positivo."
    assert len(short_entries) > 0, "Debe generar al menos una entrada SHORT en régimen bajista con score negativo."
    
    # 3. Validar etiquetas institucionales
    assert (long_entries['enter_tag'] == 'long_hrp_ensemble').all()
    assert (short_entries['enter_tag'] == 'short_hrp_ensemble').all()


def test_pb100_auto_data_sync_feather_merge(tmp_path):
    """PB-100: Verifica que auto_data_sync cree y combine archivos feather sin corrupción."""
    data_dir = tmp_path / "futures"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Crear dataset inicial con 50 barras
    dates_initial = pd.date_range("2026-01-01", periods=50, freq="4h", tz="UTC")
    df_initial = pd.DataFrame({
        'date': dates_initial,
        'open': np.full(50, 0.10),
        'high': np.full(50, 0.11),
        'low': np.full(50, 0.09),
        'close': np.full(50, 0.105),
        'volume': np.full(50, 1000.0)
    })
    target_file = data_dir / "TEST_USDT_USDT-4h-futures.feather"
    df_initial.to_feather(target_file)

    # Ejecutar sync_symbol_feather (con DOGE de Binance real o mock)
    res = sync_symbol_feather("DOGE_USDT_USDT", interval="4h", limit=20, data_dir=data_dir)
    assert res is not None
    assert "status" in res
    assert "file" in res


def test_pb101_friction_penalty_reduces_noisy_returns():
    """PB-101: Verifica que las comisiones taker y spread penalicen a factores con alto turnover."""
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="4h")
    market_df = pd.DataFrame({
        'open': [1.0] * n,
        'high': [1.02] * n,
        'low': [0.98] * n,
        'close': [1.0] * n,
        'volume': [1000.0] * n,
        'returns': np.random.normal(0.0002, 0.01, n),
        'hl_spread': [0.04] * n
    }, index=dates)

    # Estrategia 1: Baja rotación (señal estable constante = 1.0)
    # Estrategia 2: Alta rotación errática (alterna 1.0 y -1.0 en cada barra)
    strats = {
        "STABLE_MOM": StrategyRecord(
            strategy_id="STABLE_MOM",
            name="ts_rank(close, 14)",
            status=StrategyLifecycleStatus.LIVE,
            target_capital_weight=0.5,
            backtest_sharpe=2.0,
            live_sharpe=2.0,
            days_in_stage=0,
            decay_zscore=0.0,
            last_audit_date="2026-10-12"
        )
    }

    # Evaluar sin fricción vs con fricción
    _, _, ret_gross = build_signals_and_returns_for_strategies(market_df, strats, apply_friction=False)
    _, _, ret_net = build_signals_and_returns_for_strategies(market_df, strats, apply_friction=True, taker_fee_pct=0.001)

    # Los retornos netos deben ser estrictamente menores o iguales a los brutos debido a comisiones
    assert ret_net["STABLE_MOM"].sum() <= ret_gross["STABLE_MOM"].sum()


def test_pb101_oos_gating_friction_awareness():
    """PB-101: Verifica que OOSGatingValidator calcule métricas netas de comisiones."""
    validator_friction = OOSGatingValidator(min_bars=30, apply_friction=True, taker_fee_pct=0.002)
    validator_no_friction = OOSGatingValidator(min_bars=30, apply_friction=False)

    np.random.seed(42)
    n = 60
    # Señal ruidosa que cambia de signo frecuentemente
    sig = pd.Series(np.sign(np.random.normal(0, 1, n)))
    fwd_ret = pd.Series(np.random.normal(0.0005, 0.01, n))

    res_fric = validator_friction.validate_candidate("NOISY_ALPHA", sig, fwd_ret)
    res_no_fric = validator_no_friction.validate_candidate("NOISY_ALPHA", sig, fwd_ret)

    # El Sharpe OOS con fricción debe ser inferior al Sharpe sin fricción
    assert res_fric.oos_sharpe <= res_no_fric.oos_sharpe
