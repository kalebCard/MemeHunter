"""Tests sin red para user_data/strategies/MemeHunterV2.py.

Ejecutar dentro del contenedor:
    docker run --rm -v "${PWD}:/freqtrade/proj" -w /freqtrade/proj --entrypoint python meme_hunter:2026.9 -m pytest -q tests
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "user_data" / "strategies"))
from MemeHunterV2 import MemeHunterV2  # noqa: E402


def make_strategy(tmp_path, universe=None, runmode="backtest"):
    if universe is not None:
        d = tmp_path / "binance_vision"
        d.mkdir()
        (d / "universe.json").write_text(json.dumps(universe))
    return MemeHunterV2({"datadir": str(tmp_path), "runmode": runmode, "stake_currency": "USDT"})


def entry_frame(**overrides):
    """Una vela que cumple TODAS las condiciones de entrada; se pisan columnas para probar cada filtro."""
    row = {
        "close": 110.0, "ema_200": 100.0, "macd": 2.0, "macdsignal": 1.0,
        "atr": 3.0, "atr_sma": 2.0, "rsi": 60.0, "volume": 1000.0, "in_universe": True,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def enters(strategy, **overrides):
    df = strategy.populate_entry_trend(entry_frame(**overrides), {"pair": "BTC/USDT"})
    return df.get("enter_long", pd.Series([float("nan")])).iloc[0] == 1


def test_entry_when_all_conditions_met(tmp_path):
    assert enters(make_strategy(tmp_path))


@pytest.mark.parametrize("override", [
    {"close": 90.0},                      # bajo la EMA200
    {"macd": 0.5},                        # sin momentum
    {"atr": 1.0},                         # sin expansión de volatilidad
    {"rsi": 50.0},                        # RSI bajo (<= rsi_lower=56)
    {"rsi": 80.0},                        # sobrecompra (>= rsi_upper=76)
    {"volume": 0.0},                      # sin volumen
    {"in_universe": False},               # fuera del universo
])
def test_entry_blocked_by_each_filter(tmp_path, override):
    assert not enters(make_strategy(tmp_path), **override)


def test_strategy_is_long_only_spot_without_exit_signal(tmp_path):
    s = make_strategy(tmp_path)
    assert s.can_short is False
    assert s.use_exit_signal is False
    assert s.timeframe == "4h"
    assert s.stoploss == -0.15  # techo de seguridad


def test_protections_configured(tmp_path):
    methods = {p["method"] for p in make_strategy(tmp_path).protections}
    assert methods == {"CooldownPeriod", "StoplossGuard", "MaxDrawdown", "LowProfitPairs"}


def test_universe_loaded_from_datadir(tmp_path):
    s = make_strategy(tmp_path, universe={"2024-01": ["BTC/USDT"]})
    assert s._universe == {"2024-01": ["BTC/USDT"]}


def test_universe_missing_disables_filter(tmp_path):
    assert make_strategy(tmp_path)._universe == {}


def _indicator_frame(n=300):
    dates = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    close = pd.Series(range(100, 100 + n), dtype=float)
    return pd.DataFrame({"date": dates, "open": close, "high": close + 1,
                         "low": close - 1, "close": close, "volume": 100.0})


def test_universe_filter_applies_in_backtest_only(tmp_path):
    universe = {"2024-01": ["BTC/USDT"]}
    pair = {"pair": "BTC/USDT"}
    other = {"pair": "DOGE/USDT"}

    bt = make_strategy(tmp_path, universe=universe, runmode="backtest")
    bt.dp = None
    in_jan = bt.populate_indicators(_indicator_frame(), pair)
    assert in_jan.loc[in_jan["date"].dt.strftime("%Y-%m") == "2024-01", "in_universe"].all()
    assert not in_jan.loc[in_jan["date"].dt.strftime("%Y-%m") != "2024-01", "in_universe"].any()
    assert not bt.populate_indicators(_indicator_frame(), other)["in_universe"].any()

    # En dry_run/live el universo histórico NO se aplica (el exchange manda).
    live = make_strategy(tmp_path, universe=None, runmode="dry_run")
    live._universe = universe
    live.dp = None
    assert live.populate_indicators(_indicator_frame(), other)["in_universe"].all()


def _stoploss_strategy(tmp_path, atr, open_date):
    s = make_strategy(tmp_path)
    frame = pd.DataFrame({"date": [open_date - timedelta(hours=4), open_date], "atr": [atr, atr]})
    s.dp = MagicMock()
    s.dp.get_analyzed_dataframe.return_value = (frame, None)
    return s


def _trade(open_rate, open_date):
    return SimpleNamespace(open_date_utc=open_date, open_rate=open_rate)


def test_custom_stoploss_triggers_below_atr_stop(tmp_path):
    open_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    s = _stoploss_strategy(tmp_path, atr=5.0, open_date=open_date)
    # stop = 100 - 2.0*5 = 90
    assert s.custom_stoploss("X/USDT", _trade(100.0, open_date), open_date, 89.0, -0.11) == 1


def test_custom_stoploss_returns_relative_distance_above_stop(tmp_path):
    open_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    s = _stoploss_strategy(tmp_path, atr=5.0, open_date=open_date)
    result = s.custom_stoploss("X/USDT", _trade(100.0, open_date), open_date, 100.0, 0.0)
    assert result == pytest.approx((90.0 - 100.0) / 100.0)
    assert result < 0


def test_custom_stoploss_fallback_without_atr(tmp_path):
    open_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    s = _stoploss_strategy(tmp_path, atr=0.0, open_date=open_date)
    assert s.custom_stoploss("X/USDT", _trade(100.0, open_date), open_date, 100.0, 0.0) == -0.10
