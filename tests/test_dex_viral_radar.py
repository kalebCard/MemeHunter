"""Tests sin red para scripts/dex_viral_radar.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scripts.archive.legacy_satellites import dex_viral_radar as dvr  # noqa: E402


def test_parse_and_filter_dex_pair_valid():
    raw_pair = {
        "chainId": "solana",
        "dexId": "raydium",
        "url": "https://dexscreener.com/solana/abc",
        "baseToken": {"symbol": "PEPE", "name": "Pepe Meme"},
        "priceUsd": "0.000015",
        "liquidity": {"usd": 250000.0},
        "volume": {"h24": 1500000.0, "h1": 120000.0},
        "priceChange": {"h24": 35.5, "h1": 8.2},
        "txns": {"h1": {"buys": 700, "sells": 300}},
    }
    parsed = dvr.parse_and_filter_dex_pair(raw_pair, min_liquidity=50000.0, min_vol_24h=200000.0)

    assert parsed is not None
    assert parsed["symbol"] == "PEPE"
    assert parsed["chain"] == "solana"
    assert parsed["liquidity_usd"] == pytest.approx(250000.0)
    assert parsed["volume_24h_usd"] == pytest.approx(1500000.0)
    assert parsed["buy_pressure_pct"] == pytest.approx(70.0)  # 700 / 1000 = 70%


def test_parse_and_filter_dex_pair_filters_low_liquidity():
    raw_pair = {
        "baseToken": {"symbol": "SCAM"},
        "liquidity": {"usd": 5000.0},  # Muy baja
        "volume": {"h24": 10000.0},
    }
    assert dvr.parse_and_filter_dex_pair(raw_pair, min_liquidity=50000.0, min_vol_24h=200000.0) is None


@patch("requests.get")
def test_search_dex_pairs(mock_get):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"pairs": [{"baseToken": {"symbol": "DOGE"}}]}
    mock_get.return_value = mock_res

    res = dvr.search_dex_pairs("DOGE")
    assert len(res) == 1
    assert res[0]["baseToken"]["symbol"] == "DOGE"
