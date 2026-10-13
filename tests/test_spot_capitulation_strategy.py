"""
tests/test_spot_capitulation_strategy.py - Tests unitarios para MemeHunterSpot_CapitulationAlpha.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "user_data" / "strategies"))

from MemeHunterSpot_CapitulationAlpha import (
    MemeHunterSpot_CapitulationAlpha,
    calculate_ffd_approx,
    compute_rsi,
    compute_bollinger_bands,
)


class MockTrade:
    def __init__(self, open_date_utc):
        self.open_date_utc = open_date_utc


def test_spot_strategy_properties():
    s = MemeHunterSpot_CapitulationAlpha()
    assert s.can_short is False, "Binance Spot debe ser can_short = False"
    assert s.timeframe == "1h"
    assert s.stoploss == -0.030
    assert s.use_custom_stoploss is True
    assert s.use_exit_signal is True
    assert s.order_types['entry'] == 'limit', "Entrada debe ser Limit para tarifa Maker"
    assert s.order_types['exit'] == 'market', "Salida debe ser Market para garantizar ejecución"


def test_indicator_helpers():
    # RSI vectorizado
    prices = pd.Series([100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25])
    rsi = compute_rsi(prices, length=7)
    assert len(rsi) == len(prices)
    assert rsi.iloc[-1] < 20, "Caída continua debe generar RSI bajo"

    # Bandas de Bollinger
    series = pd.Series(np.linspace(100, 80, 30))
    b_l, b_m, b_u = compute_bollinger_bands(series, length=20, std_dev=2.5)
    assert len(b_l) == len(series)
    assert b_l.iloc[-1] < b_m.iloc[-1] < b_u.iloc[-1]

    # FFD
    arr = np.linspace(100, 50, 50)
    ffd = calculate_ffd_approx(arr, d=0.40, lags=20)
    assert len(ffd) == 50
    assert not np.isnan(ffd[-1])


def test_custom_stoploss_ratchet():
    s = MemeHunterSpot_CapitulationAlpha()
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    trade = MockTrade(now)

    # 1. Pérdida o profit menor a +2.0% -> Debe retornar stoploss por defecto (-3.0%)
    sl_base = s.custom_stoploss("PEPE/USDT", trade, now, 100.0, 0.010)
    assert sl_base == -0.030

    # 2. Profit alcanza +2.5% (supera +2.0%) -> Breakeven garantizado
    sl_be = s.custom_stoploss("PEPE/USDT", trade, now, 102.5, 0.025)
    assert -0.030 < sl_be <= -0.005

    # 3. Profit alcanza +5.0% (supera +4.5%) -> asegura +2.5%
    sl_p5 = s.custom_stoploss("PEPE/USDT", trade, now, 105.0, 0.050)
    assert sl_p5 == -0.015

    # 4. Profit alcanza +7.0% (supera +6.5%) -> asegura +4.5%
    sl_p8 = s.custom_stoploss("PEPE/USDT", trade, now, 107.0, 0.070)
    assert sl_p8 == -0.015

    # 5. Profit explosivo +12.0% (supera +10.0%) -> asegura +8.0%
    sl_p12 = s.custom_stoploss("PEPE/USDT", trade, now, 112.0, 0.120)
    assert sl_p12 == -0.020


def test_custom_exit_guardrails():
    s = MemeHunterSpot_CapitulationAlpha()
    now = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)

    # Caso 1: Posición abierta hace 9 horas con ganancia de +0.5% (estancada)
    # -> Activa Time-Stop Anti-Bagholding
    old_trade = MockTrade(now - timedelta(hours=9))
    exit_reason = s.custom_exit("PEPE/USDT", old_trade, now, 100.5, 0.005)
    assert exit_reason == "time_stop_anti_bagholding"

    # Caso 2: Posición abierta hace 5 horas con pérdida de -2.5%
    # -> Activa Early Weakness Airbag
    weak_trade = MockTrade(now - timedelta(hours=5))
    exit_reason_weak = s.custom_exit("PEPE/USDT", weak_trade, now, 97.5, -0.025)
    assert exit_reason_weak == "early_weakness_airbag"

    # Caso 3: Posición abierta hace 2 horas con buen rendimiento (+4.0%)
    # -> No sale, deja correr el trade
    active_trade = MockTrade(now - timedelta(hours=2))
    assert s.custom_exit("PEPE/USDT", active_trade, now, 104.0, 0.040) is None


def test_populate_indicators_and_signals():
    s = MemeHunterSpot_CapitulationAlpha()
    n = 60
    dates = pd.date_range("2026-01-01", periods=n, freq="1h")

    close = np.linspace(100, 90, n)
    high = close + 1.0
    low = close - 1.0
    open_p = close + 0.2
    vol = np.full(n, 1000.0)

    # En la vela 55: Colapso del -15%, volumen x3, pánico
    close[55] = 72.0
    open_p[55] = 75.0
    low[55] = 65.0
    high[55] = 76.0
    vol[55] = 3500.0

    # En la vela 56: Vela de confirmación verde que rompe el giro
    close[56] = 76.0
    open_p[56] = 72.0
    low[56] = 71.5
    high[56] = 77.0
    vol[56] = 2000.0

    df = pd.DataFrame({
        "date": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": vol
    })

    df = s.populate_indicators(df, {"pair": "PEPE/USDT"})
    assert "panic_candle" in df.columns
    assert "confirmation_candle" in df.columns
    assert df["panic_candle"].iloc[55] == 1
    assert df["confirmation_candle"].iloc[56] == 1

    # Verificar generación de señales en vela 56
    df = s.populate_entry_trend(df, {"pair": "PEPE/USDT"})
    assert "enter_long" in df.columns
    assert df["enter_long"].iloc[56] == 1
    assert df["enter_tag"].iloc[56] == "spot_confirmed_capitulation"
