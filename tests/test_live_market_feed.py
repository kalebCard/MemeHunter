"""
Pruebas Unitarias para el Módulo de Ingesta en Vivo y Dollar Bars en Tiempo Real.
Sprint 4: Live Market Feed.
"""

import time
import numpy as np
import pandas as pd
import pytest

from data_engine.live_market_feed import LiveMarketFeed


def test_live_market_feed_initialization():
    feed = LiveMarketFeed(symbols=["DOGE/USDT"], notional_threshold=500_000.0)
    assert feed.symbols == ["DOGE/USDT"]
    assert feed.notional_threshold == 500_000.0
    assert feed.get_latest_dollar_bars("DOGE/USDT").empty


def test_process_incoming_candles_generates_dollar_bars():
    feed = LiveMarketFeed(symbols=["PEPE/USDT"], notional_threshold=100_000.0)

    # Crear 80 velas sintéticas con volumen y precios cambiantes
    np.random.seed(42)
    n = 80
    dates = pd.date_range("2026-03-01", periods=n, freq="1min")
    prices = 0.000010 + np.cumsum(np.random.normal(0, 0.0000002, n))
    candles_df = pd.DataFrame({
        'timestamp': [int(d.timestamp() * 1000) for d in dates],
        'date': dates,
        'open': prices,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.uniform(5_000_000_000, 20_000_000_000, n)  # Notional grande para cruzar umbral
    })

    closed_bars = []
    def on_bar_closed(symbol, bar):
        closed_bars.append((symbol, bar['close']))

    feed.subscribe_bar_closed(on_bar_closed)
    feed.process_incoming_candles("PEPE/USDT", candles_df)

    bars = feed.get_latest_dollar_bars("PEPE/USDT")
    assert not bars.empty, "Debieron generarse Dollar Bars a partir de las velas"
    assert 'vwap' in bars.columns
    assert 'rvol' in bars.columns
    assert 'hl_spread' in bars.columns
    assert 'returns' in bars.columns
    assert len(closed_bars) > 0, "El callback de barra cerrada debió ser invocado"


def test_live_feed_thread_lifecycle():
    feed = LiveMarketFeed(symbols=["DOGE/USDT"], poll_interval_seconds=0.2)
    feed.start()
    assert feed._running is True
    time.sleep(0.5)
    feed.stop()
    assert feed._running is False
