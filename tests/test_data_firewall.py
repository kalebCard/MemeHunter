"""
Pruebas Unitarias para Cortafuegos de Datos y Detección de Gaps (Sprint 36: PB-121 / PB-122).
"""

import pytest
import pandas as pd
from validation.data_firewall import DataFirewallGuard, FirewallMode
from data_engine.sanitized_feed import SanitizedFeedAdapter


def test_firewall_timeseries_healthy():
    firewall = DataFirewallGuard()
    step_4h = 4 * 3600 * 1000
    start_ts = 1700000000000

    candles = [
        {
            "timestamp_ms": start_ts + i * step_4h,
            "open": 100.0 + i,
            "high": 105.0 + i,
            "low": 98.0 + i,
            "close": 102.0 + i,
            "volume": 1000.0
        }
        for i in range(10)
    ]

    now_ms = start_ts + 9 * step_4h + 1000  # Apenas 1 segundo después de la última vela
    ok, valid_candles, reason = firewall.validate_timeseries(
        symbol="DOGE/USDT",
        candles_raw=candles,
        timeframe="4h",
        current_time_ms=now_ms
    )

    assert ok is True
    assert len(valid_candles) == 10
    assert firewall.current_mode == FirewallMode.NORMAL


def test_firewall_gap_detection():
    firewall = DataFirewallGuard()
    step_4h = 4 * 3600 * 1000
    start_ts = 1700000000000

    # Crear lista con un hueco en la vela 5 (falta una vela de 4h)
    candles = [
        {
            "timestamp_ms": start_ts + (i if i < 5 else i + 1) * step_4h,
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 102.0,
            "volume": 1000.0
        }
        for i in range(10)
    ]

    now_ms = start_ts + 11 * step_4h
    ok, valid_candles, reason = firewall.validate_timeseries(
        symbol="DOGE/USDT",
        candles_raw=candles,
        timeframe="4h",
        current_time_ms=now_ms
    )

    assert ok is False
    assert firewall.current_mode == FirewallMode.GAP_DETECTED_STANDBY
    assert "GAP TEMPORAL DETECTADO" in reason


def test_firewall_stale_data_detection():
    firewall = DataFirewallGuard()
    step_1h = 3600 * 1000
    start_ts = 1700000000000

    candles = [
        {
            "timestamp_ms": start_ts + i * step_1h,
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 102.0,
            "volume": 1000.0
        }
        for i in range(5)
    ]

    # Tiempo actual 10 horas después de la última vela (muy obsoleto)
    now_ms = start_ts + 4 * step_1h + (10 * 3600 * 1000)
    ok, valid_candles, reason = firewall.validate_timeseries(
        symbol="DOGE/USDT",
        candles_raw=candles,
        timeframe="1h",
        current_time_ms=now_ms
    )

    assert ok is False
    assert firewall.current_mode == FirewallMode.DATA_FEED_STALE_STANDBY
    assert "FEED OBSOLETO" in reason


def test_firewall_flash_spike_detection():
    firewall = DataFirewallGuard()
    step_4h = 4 * 3600 * 1000
    start_ts = 1700000000000

    candles = [
        {
            "timestamp_ms": start_ts,
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 100.0,
            "volume": 1000.0
        },
        {
            # Salto del 50% en 1 sola vela (Flash Spike anómalo)
            "timestamp_ms": start_ts + step_4h,
            "open": 140.0,
            "high": 155.0,
            "low": 138.0,
            "close": 150.0,
            "volume": 1000.0
        }
    ]

    ok, valid_candles, reason = firewall.validate_timeseries(
        symbol="DOGE/USDT",
        candles_raw=candles,
        timeframe="4h",
        current_time_ms=start_ts + step_4h + 1000
    )

    assert ok is False
    assert firewall.current_mode == FirewallMode.CORRUPTED_FEED_HALT
    assert "FLASH SPIKE ANÓMALO" in reason


def test_sanitized_feed_adapter_dataframe():
    adapter = SanitizedFeedAdapter()
    step_4h = 4 * 3600 * 1000
    start_ts = 1700000000000

    df = pd.DataFrame([
        {
            "timestamp_ms": start_ts + i * step_4h,
            "open": 10.0 + i,
            "high": 12.0 + i,
            "low": 9.0 + i,
            "close": 11.0 + i,
            "volume": 5000.0
        }
        for i in range(8)
    ])

    now_ms = start_ts + 7 * step_4h + 500
    ok, clean_df, reason = adapter.sanitize_dataframe(
        symbol="PEPE/USDT",
        df=df,
        timeframe="4h",
        current_time_ms=now_ms
    )

    assert ok is True
    assert clean_df is not None
    assert len(clean_df) == 8
    assert adapter.is_healthy is True

    status = adapter.get_firewall_status()
    assert status["mode"] == "NORMAL"
    assert status["is_healthy"] is True
