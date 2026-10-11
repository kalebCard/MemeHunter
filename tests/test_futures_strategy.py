"""Tests sin red para user_data/strategies/MemeHunterFuturesV1.py.

Ejecutar dentro del contenedor:
    docker run --rm -v "${PWD}:/freqtrade/proj" -w /freqtrade/proj --entrypoint python meme_hunter:2026.9 -m pytest -q tests
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "user_data" / "strategies"))
from MemeHunterFuturesV1 import MemeHunterFuturesV1  # noqa: E402


def make_strategy():
    return MemeHunterFuturesV1({
        "runmode": "dry_run",
        "dry_run_wallet": 1000,
        "stake_currency": "USDT"
    })


def base_frame(**overrides):
    row = {
        "close": 110.0,
        "ema_200": 100.0,
        "macd": 2.0,
        "macdsignal": 1.0,
        "rsi": 60.0,
        "volume": 1000.0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_futures_strategy_properties():
    s = make_strategy()
    assert s.can_short is True
    assert s.timeframe == "4h"
    assert s.stoploss == -0.15
    assert s.trailing_stop is True
    assert s.use_exit_signal is False


def test_leverage_is_always_1x():
    s = make_strategy()
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    assert s.leverage("BTC/USDT:USDT", now, 100.0, 5.0, 20.0, "long_momentum_ema200", "long") == 1.0
    assert s.leverage("BTC/USDT:USDT", now, 100.0, 5.0, 20.0, "short_breakdown_ema200", "short") == 1.0


def test_long_entry_conditions():
    s = make_strategy()
    df = s.populate_entry_trend(base_frame(), {"pair": "BTC/USDT:USDT"})
    assert df["enter_long"].iloc[0] == 1
    assert df["enter_short"].iloc[0] == 0
    assert df["enter_tag"].iloc[0] == "long_momentum_ema200"


def test_short_entry_conditions():
    s = make_strategy()
    # Para short: close < ema_200, macd < macdsignal, macd < 0, 24 <= rsi <= 44, volume > 0
    short_row = {
        "close": 90.0,
        "ema_200": 100.0,
        "macd": -2.0,
        "macdsignal": -1.0,
        "rsi": 35.0,
        "volume": 1000.0,
    }
    df = s.populate_entry_trend(base_frame(**short_row), {"pair": "BTC/USDT:USDT"})
    assert df["enter_long"].iloc[0] == 0
    assert df["enter_short"].iloc[0] == 1
    assert df["enter_tag"].iloc[0] == "short_breakdown_ema200"


@pytest.mark.parametrize("override", [
    {"close": 95.0},          # Bajo EMA200 bloquea long
    {"macd": 0.5},            # MACD < macdsignal bloquea long
    {"macd": -1.0},           # MACD bajo 0 bloquea long
    {"rsi": 50.0},            # RSI < 56 bloquea long
    {"rsi": 80.0},            # RSI > 76 sobrecompra bloquea long
    {"volume": 0.0},          # Sin volumen bloquea
])
def test_long_entry_filters(override):
    s = make_strategy()
    df = s.populate_entry_trend(base_frame(**override), {"pair": "BTC/USDT:USDT"})
    assert df["enter_long"].iloc[0] == 0


def test_custom_stake_amount_asymmetric():
    s = make_strategy()
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    # Para shorts aplica impulso de 1.15x
    short_stake = s.custom_stake_amount("BTC/USDT:USDT", now, 100.0, 100.0, 10.0, 500.0, 1.0, "short", "short")
    assert short_stake == pytest.approx(115.0)

    # Para longs aplica mitigación prudente de 0.70x
    long_stake = s.custom_stake_amount("BTC/USDT:USDT", now, 100.0, 100.0, 10.0, 500.0, 1.0, "long", "long")
    assert long_stake == pytest.approx(70.0)

    # Si el balance o propuesta es menor a $5, se ajusta al piso regulatorio de Binance ($5.00 USDT)
    clamped_stake = s.custom_stake_amount("BTC/USDT:USDT", now, 100.0, 3.0, None, 500.0, 1.0, "long", "long")
    assert clamped_stake == pytest.approx(5.0)

