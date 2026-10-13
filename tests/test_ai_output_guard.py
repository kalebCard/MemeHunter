"""
Pruebas Unitarias para AIOutputGuard (Sprint 39: PB-129).
"""

import pytest
from validation.ai_output_guard import AIOutputGuard
from validation.schemas import MarketBiasPosture


def test_ai_output_guard_clean_json():
    guard = AIOutputGuard()
    raw = '{"sentiment": 0.75, "confidence": 0.88, "key_catalyst": "Binance Listing"}'

    ok, schema, reason = guard.validate_sentiment_output(raw)
    assert ok is True
    assert schema.sentiment == 0.75
    assert schema.confidence == 0.88
    assert schema.key_catalyst == "Binance Listing"
    assert guard.approved_count == 1


def test_ai_output_guard_markdown_wrapped_json():
    guard = AIOutputGuard()
    raw = """
    Aquí está mi análisis detallado del mercado para memecoins:
    ```json
    {
      "sentiment": -0.65,
      "confidence": 0.92,
      "key_catalyst": "Exploit Rumor"
    }
    ```
    Espero que te sirva.
    """

    ok, schema, reason = guard.validate_sentiment_output(raw)
    assert ok is True
    assert schema.sentiment == -0.65
    assert schema.confidence == 0.92


def test_ai_output_guard_hallucination_and_extra_fields():
    guard = AIOutputGuard()
    # Modelo intenta meter campos no permitidos como 'execute_market_buy' o apalancamiento
    raw = """
    {
      "sentiment": 0.80,
      "confidence": 0.90,
      "execute_market_buy": true,
      "order_amount_usd": 10000.0
    }
    """

    ok, schema, reason = guard.validate_sentiment_output(raw)
    # Debe ser rechazado porque extra='forbid'
    assert ok is False
    assert "SCHEMA_VALIDATION_ERROR" in reason
    # Retorna fallback seguro
    assert schema.sentiment == 0.0
    assert guard.rejection_count == 1


def test_ai_output_guard_unparseable_conversational_text():
    guard = AIOutputGuard()
    raw = "Lo siento, como modelo de lenguaje no puedo predecir el precio futuro de DOGE."

    ok, schema, reason = guard.validate_sentiment_output(raw)
    assert ok is False
    assert "PAYLOAD_EXTRACT_FAILED" in reason
    assert schema.sentiment == 0.0


def test_ai_output_guard_authorization():
    guard = AIOutputGuard()
    raw = '{"action": "ALLOW_LONG", "confidence": 0.85, "reasoning_summary": "Absorción de liquidez confirmada"}'

    ok, schema, reason = guard.validate_authorization_output(raw)
    assert ok is True
    assert schema.action == MarketBiasPosture.ALLOW_LONG
    assert schema.confidence == 0.85
