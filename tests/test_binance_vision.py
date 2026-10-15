"""Tests sin red para scripts/binance_vision.py.

Ejecutar dentro del contenedor:
    docker compose run --rm --entrypoint python freqtrade -m pytest -q tests
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.archive.legacy_satellites import binance_vision as bv  # noqa: E402

ROW_MS = b"1577836800000,7195.24,7255.0,7175.15,7200.85,16792.388165,1577923199999,121214452.116,194010,8946.955535,64597785.212,0\n"
ROW_US = b"1788220800000000,78581.3,79220.61,76420.0,77439.0,14130.63949,1788307199999999,1101387276.65,3662805,7128.14511,555981558.22,0\n"


def test_parse_ms_timestamps():
    df = bv.parse_kline_csv(ROW_MS)
    assert list(df.columns) == bv.FULL_COLUMNS
    assert df["date"].iloc[0] == pd.Timestamp("2020-01-01", tz="UTC")
    assert df["quote_volume"].iloc[0] == pytest.approx(121214452.116)
    assert df["trades"].dtype == "int64"


def test_parse_us_timestamps():
    df = bv.parse_kline_csv(ROW_US)
    assert df["date"].iloc[0] == pd.Timestamp("2026-09-01", tz="UTC")


def test_parse_with_header():
    header = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
    df = bv.parse_kline_csv(header + ROW_MS)
    assert len(df) == 1


def test_merge_dedupes_and_sorts():
    a = bv.parse_kline_csv(ROW_US)
    b = bv.parse_kline_csv(ROW_MS)
    merged = bv.merge_frames([a, b, a])
    assert len(merged) == 2
    assert merged["date"].is_monotonic_increasing


def test_split_symbol_prefers_longest_quote():
    assert bv.split_symbol("BTCUSDT", ["USDT"]) == ("BTC", "USDT")
    assert bv.split_symbol("BTCFDUSD", ["USD", "FDUSD"]) == ("BTC", "FDUSD")
    assert bv.split_symbol("USDT", ["USDT"]) is None
    assert bv.split_symbol("ETHBTC", ["USDT"]) is None
    assert bv.to_freqtrade_pair("1000SATSUSDT", ["USDT"]) == "1000SATS/USDT"


def test_month_helpers():
    assert str(bv.Month.parse("2020-01")) == "2020-01"
    assert bv.Month.last_complete(date(2026, 1, 15)) == bv.Month(2025, 12)
    assert bv.Month.last_complete(date(2026, 10, 9)) == bv.Month(2026, 9)
    assert bv.Month(2020, 1) < bv.Month(2020, 2) <= bv.Month(2020, 2)
    with pytest.raises(ValueError):
        bv.Month.parse("2020-13")


def test_parse_month_from_key_and_checksum():
    key = "data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2026-09.zip"
    assert bv.parse_month_from_key(key) == bv.Month(2026, 9)
    assert bv.parse_month_from_key(key + ".CHECKSUM") is None
    digest = "a" * 64
    assert bv.parse_checksum(f"{digest}  BTCUSDT-1d-2026-09.zip") == digest
    with pytest.raises(ValueError):
        bv.parse_checksum("nope")


def test_find_gaps_detects_ticker_reuse():
    dates = list(pd.date_range("2022-05-10", "2022-05-13", freq="1D", tz="UTC")) + \
        list(pd.date_range("2022-05-31", "2022-06-02", freq="1D", tz="UTC"))
    df = pd.DataFrame({"date": dates, "open": [80, 60, 1, 0.0001, 5, 6, 7],
                       "close": [60, 1, 0.0001, 0.00005, 6, 7, 8]})
    gaps = bv.find_gaps(df, "1d")
    assert len(gaps) == 1
    assert gaps[0]["missing"] == 17
    assert gaps[0]["price_ratio"] == pytest.approx(100000)
    # Huecos pequeños (mantenimiento del exchange) no se reportan
    assert bv.find_gaps(df.drop(index=[1]).reset_index(drop=True).iloc[:3], "1d") == []
