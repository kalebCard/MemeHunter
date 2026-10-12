"""
test_streaming_engine.py - Pruebas Unitarias del Motor de Streaming WebSocket y Barras Adaptativas (Sprint 2).
Verifica:
1. Agregación incremental O(1) con StreamingDollarBarAggregator sin reprocesar histórico.
2. Calibración dinámica del umbral notional (ADV_20 / target_bars) y suavizado rodante EMA.
3. Construcción y procesamiento de mensajes del BinanceFuturesWebSocketFeed y orderbook L2.
4. Despacho desacoplado de eventos de barra cerrada en LiveMarketFeed.
"""

import time
import pytest
import numpy as np
import pandas as pd

from data_engine.dollar_bars import (
    InformationBarsGenerator,
    StreamingDollarBarAggregator,
    AccumulatorState
)
from data_engine.live_market_feed import LiveMarketFeed, BinanceFuturesWebSocketFeed


def test_streaming_aggregator_o1_ticks():
    """Valida que los ticks individuales se acumulen en O(1) y cierren barra al cruzar umbral."""
    aggregator = StreamingDollarBarAggregator(default_threshold=10_000.0)

    # 1. Tick inicial de $1,000 (100 tokens * $10) -> no debe cerrar barra
    bar1 = aggregator.add_tick("DOGE/USDT", price=10.0, volume=100.0, timestamp=1000)
    assert bar1 is None

    in_progress = aggregator.get_in_progress_bar("DOGE/USDT")
    assert in_progress is not None
    assert in_progress['open'] == 10.0
    assert in_progress['high'] == 10.0
    assert in_progress['low'] == 10.0
    assert in_progress['close'] == 10.0
    assert in_progress['cum_notional'] == 1_000.0
    assert in_progress['progress_pct'] == 0.10

    # 2. Tick intermedio de $4,000 (380.95 tokens * $10.50)
    bar2 = aggregator.add_tick("DOGE/USDT", price=10.5, volume=380.95238, timestamp=2000)
    assert bar2 is None

    in_prog2 = aggregator.get_in_progress_bar("DOGE/USDT")
    assert in_prog2['high'] == 10.5
    assert in_prog2['low'] == 10.0
    assert in_prog2['close'] == 10.5

    # 3. Tick final de $6,000 (545.45 tokens * $11.00) -> Total supera $11,000 >= $10,000
    closed_bar = aggregator.add_tick("DOGE/USDT", price=11.0, volume=545.45455, timestamp=3000)
    assert closed_bar is not None
    assert closed_bar['open'] == 10.0
    assert closed_bar['high'] == 11.0
    assert closed_bar['low'] == 10.0
    assert closed_bar['close'] == 11.0
    assert closed_bar['notional'] >= 10_000.0
    assert closed_bar['duration_ticks'] == 3
    assert closed_bar['vwap'] > 10.0 and closed_bar['vwap'] < 11.0

    # El acumulador debe haberse reiniciado a cero
    assert aggregator.get_in_progress_bar("DOGE/USDT") is None


def test_dynamic_threshold_calibration():
    """Valida que la calibración dinámica por símbolo produzca el número esperado de barras diarias."""
    generator = InformationBarsGenerator()

    # Crear 3 días de datos simulados con $1,500,000 USD de volumen diario
    n = 3 * 1440  # 3 días de velas 1m
    dates = pd.date_range("2026-03-01", periods=n, freq="1min")
    daily_target_bars = 50.0

    # Cada vela tiene ~$1,041.67 USD -> $1,500,000 al día
    prices = np.full(n, 0.10)
    volumes = np.full(n, 10_416.7)  # notional = 1041.67
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': volumes
    })

    calibrated_thresh = generator.calibrate_threshold_from_history(df, target_bars_per_day=daily_target_bars)
    # Esperado: 1,500,000 / 50 = $30,000 USD por barra
    assert 25_000.0 <= calibrated_thresh <= 35_000.0

    # Probar actualización rodante EMA
    smoothed = generator.update_symbol_threshold_rolling("DOGE/USDT", new_threshold=40_000.0, smoothing_alpha=0.5)
    # Si estaba en 1,000,000 (default), se suaviza hacia 40,000
    assert smoothed < 1_000_000.0


def test_ws_url_builder():
    """Valida la generación de streams multiplexados para Binance Futures."""
    symbols = ["DOGE/USDT", "PEPE/USDT"]
    ws_feed = BinanceFuturesWebSocketFeed(symbols=symbols, on_trade_callback=lambda s, p, q, t: None)

    url = ws_feed._ws_url
    assert "dogeusdt@aggTrade" in url
    assert "dogeusdt@depth20@100ms" in url
    assert "pepeusdt@aggTrade" in url
    assert "pepeusdt@depth20@100ms" in url
    assert ws_feed._symbol_to_raw("DOGE/USDT") == "dogeusdt"
    assert ws_feed._raw_to_symbol("DOGEUSDT") == "DOGE/USDT"


def test_live_market_feed_ws_trade_and_orderbook():
    """Valida que los callbacks de trades y depth actualicen Dollar Bars y L2 Orderbook."""
    feed = LiveMarketFeed(
        symbols=["DOGE/USDT"],
        notional_threshold=5_000.0,
        use_websocket=False
    )

    closed_events = []
    feed.subscribe_bar_closed(lambda s, b: closed_events.append((s, b['close'])))

    # 1. Simular trade tick desde WebSocket
    feed._on_ws_trade("DOGE/USDT", price=0.20, qty=10_000.0, timestamp_ms=1700000000000)  # $2,000 notional
    assert len(closed_events) == 0

    feed._on_ws_trade("DOGE/USDT", price=0.20, qty=20_000.0, timestamp_ms=1700000001000)  # $4,000 -> Total $6,000 >= $5,000
    assert len(closed_events) == 1
    assert closed_events[0][0] == "DOGE/USDT"
    assert closed_events[0][1] == 0.20

    # 2. Simular actualización de profundidad de libro
    bids = [[0.1999, 50000.0], [0.1998, 80000.0]]
    asks = [[0.2001, 45000.0], [0.2002, 60000.0]]
    feed._on_ws_depth("DOGE/USDT", bids, asks)

    ob = feed.get_latest_orderbook("DOGE/USDT")
    assert len(ob["bids"]) == 2
    assert ob["bids"][0][0] == 0.1999
    assert len(ob["asks"]) == 2
    assert ob["asks"][0][0] == 0.2001
