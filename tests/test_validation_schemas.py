"""
Pruebas Unitarias para Esquemas Pydantic v2 (Sprint 36: PB-120).
"""

import pytest
from pydantic import ValidationError
from validation.schemas import (
    MarketCandleSchema,
    OrderBookL2Schema,
    MarketTickSchema,
    MarketSeriesInput,
    MarketBiasSchema,
    MarketBiasPosture
)


def test_market_tick_schema_valid():
    tick = MarketTickSchema(
        symbol="DOGE/USDT",
        price=0.155,
        qty=1000.0,
        side="buy",
        timestamp_ms=1700000000000
    )
    assert tick.price == 0.155
    assert tick.symbol == "DOGE/USDT"
    assert tick.side == "buy"


def test_market_tick_schema_invalid():
    # Precio negativo rechazado
    with pytest.raises(ValidationError):
        MarketTickSchema(
            symbol="DOGE/USDT",
            price=-0.15,
            qty=100.0,
            side="buy",
            timestamp_ms=1700000000000
        )

    # Campo no permitido (extra='forbid')
    with pytest.raises(ValidationError):
        MarketTickSchema(
            symbol="DOGE/USDT",
            price=0.15,
            qty=100.0,
            side="buy",
            timestamp_ms=1700000000000,
            hacked_field="malicious"
        )


def test_market_candle_schema_geometry():
    # Vela válida
    candle = MarketCandleSchema(
        timestamp_ms=1700000000000,
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=500.0
    )
    assert candle.high == 110.0

    # High menor que Open/Close
    with pytest.raises(ValidationError):
        MarketCandleSchema(
            timestamp_ms=1700000000000,
            open=100.0,
            high=98.0,  # Menor que open!
            low=95.0,
            close=97.0,
            volume=500.0
        )

    # Low mayor que Open
    with pytest.raises(ValidationError):
        MarketCandleSchema(
            timestamp_ms=1700000000000,
            open=100.0,
            high=110.0,
            low=102.0,  # Mayor que open!
            close=105.0,
            volume=500.0
        )


def test_orderbook_l2_integrity():
    # Libro sano
    ob = OrderBookL2Schema(
        symbol="PEPE/USDT",
        timestamp_ms=1700000000000,
        bids=[(0.000010, 50000.0), (0.000009, 100000.0)],
        asks=[(0.000011, 60000.0), (0.000012, 120000.0)]
    )
    assert ob.bids[0][0] < ob.asks[0][0]

    # Libro cruzado (Best Bid >= Best Ask) debe ser rechazado
    with pytest.raises(ValidationError):
        OrderBookL2Schema(
            symbol="PEPE/USDT",
            timestamp_ms=1700000000000,
            bids=[(0.000012, 50000.0)],
            asks=[(0.000010, 60000.0)]  # Ask menor que bid!
        )


def test_market_bias_schema():
    bias = MarketBiasSchema(
        symbol="DOGE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.85,
        consensus_score=0.90,
        regime_detected="BULL_MOMENTUM",
        valid_until_utc="2026-10-13T16:00:00Z",
        max_leverage=1.5,
        allowed_setups=["spot_confirmed_capitulation"]
    )
    assert bias.posture == MarketBiasPosture.ALLOW_LONG
    assert bias.confidence == 0.85
    assert bias.max_leverage == 1.5

    # Confianza fuera de rango [0, 1]
    with pytest.raises(ValidationError):
        MarketBiasSchema(
            symbol="DOGE/USDT",
            posture=MarketBiasPosture.ALLOW_LONG,
            confidence=1.5,  # > 1.0!
            consensus_score=0.9,
            valid_until_utc="2026-10-13T16:00:00Z"
        )
