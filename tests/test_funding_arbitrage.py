"""Tests sin red para scripts/funding_arbitrage.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import funding_arbitrage as fa  # noqa: E402


def test_calculate_annualized_rates_positive():
    # Tasa de 0.01% (0.0001) por 8h (estándar de Binance)
    res = fa.calculate_annualized_rates(0.0001)
    assert res["rate_8h_pct"] == pytest.approx(0.01)
    assert res["daily_pct"] == pytest.approx(0.03)
    assert res["apr_pct"] == pytest.approx(10.95)


def test_calculate_annualized_rates_extreme_meme_rate():
    # Tasa eufórica de memecoin: 0.1% (0.001) cada 8 horas
    res = fa.calculate_annualized_rates(0.001)
    assert res["rate_8h_pct"] == pytest.approx(0.1)
    assert res["daily_pct"] == pytest.approx(0.3)
    assert res["apr_pct"] == pytest.approx(109.5)


def test_scan_funding_opportunities_filters_and_sorts():
    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rates.return_value = {
        "DOGE/USDT:USDT": {"fundingRate": 0.0005, "fundingDatetime": "2026-10-11T16:00:00Z"},  # APR ~54.7%
        "PEPE/USDT:USDT": {"fundingRate": 0.0015, "fundingDatetime": "2026-10-11T16:00:00Z"},  # APR ~164.2%
        "BTC/BUSD": {"fundingRate": 0.005},  # No termina en :USDT
        "LOW/USDT:USDT": {"fundingRate": 0.00001},  # APR ~1% (bajo el umbral de 15%)
    }

    opps = fa.scan_funding_opportunities(mock_exchange, min_apr=15.0)

    assert len(opps) == 2
    # Ordenado por mayor APR primero
    assert opps[0]["symbol"] == "PEPE/USDT:USDT"
    assert opps[0]["direction"] == "Short Fut / Long Spot"
    assert opps[1]["symbol"] == "DOGE/USDT:USDT"
