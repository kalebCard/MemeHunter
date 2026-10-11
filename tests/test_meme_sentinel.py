"""Tests sin red para scripts/meme_sentinel.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import meme_sentinel as ms  # noqa: E402


def test_analyze_symbol_calculates_rvol_and_score():
    # 20 velas anteriores con volumen 100, última con volumen 500 (5x) y subida de 10%
    rows = []
    base_ts = 1700000000000
    for i in range(20):
        rows.append([base_ts + i * 300000, 10.0, 10.5, 9.5, 10.0, 100.0])
    # Última vela explosiva
    rows.append([base_ts + 20 * 300000, 10.0, 11.2, 9.8, 11.0, 500.0])

    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = rows

    res = ms.analyze_symbol(mock_exchange, "DOGE/USDT:USDT", timeframe="5m")

    assert res is not None
    assert res["symbol"] == "DOGE/USDT:USDT"
    assert res["rvol"] == pytest.approx(5.0)
    assert res["price_change_pct"] == pytest.approx(10.0)
    assert res["score"] == pytest.approx(50.0)


def test_analyze_symbol_ignores_insufficient_data():
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = [[1, 1, 1, 1, 1, 1]] * 5  # Menos de 15 velas
    assert ms.analyze_symbol(mock_exchange, "PEPE/USDT:USDT") is None


def test_get_usdt_futures_markets_filters_majors_and_non_linear():
    mock_exchange = MagicMock()
    mock_exchange.markets = {
        "BTC/USDT:USDT": {"linear": True, "quote": "USDT", "active": True},
        "ETH/USDT:USDT": {"linear": True, "quote": "USDT", "active": True},
        "PEPE/USDT:USDT": {"linear": True, "quote": "USDT", "active": True},
        "SOL/BUSD": {"linear": False, "quote": "BUSD", "active": True},
    }
    symbols = ms.get_usdt_futures_markets(mock_exchange)
    assert symbols == ["PEPE/USDT:USDT"]
