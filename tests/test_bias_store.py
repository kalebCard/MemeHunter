"""
Pruebas Unitarias para BiasStore y Control de Expiración TTL (Sprint 37: PB-125).
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from validation.schemas import MarketBiasSchema, MarketBiasPosture
from portfolio.bias_store import BiasStore


@pytest.fixture
def temp_bias_store(tmp_path):
    store_file = tmp_path / "test_market_bias.json"
    store = BiasStore(filepath=str(store_file))
    yield store
    if os.path.exists(str(store_file)):
        os.remove(str(store_file))


def test_bias_store_save_and_retrieve(temp_bias_store):
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=4)

    bias = MarketBiasSchema(
        symbol="DOGE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.82,
        consensus_score=0.88,
        regime_detected="BULL_MOMENTUM",
        valid_until_utc=future.isoformat(),
        max_leverage=1.0,
        allowed_setups=["spot_confirmed_capitulation"]
    )

    success = temp_bias_store.save_bias(bias)
    assert success is True

    loaded = temp_bias_store.get_bias("DOGE/USDT")
    assert loaded is not None
    assert loaded.symbol == "DOGE/USDT"
    assert loaded.posture == MarketBiasPosture.ALLOW_LONG
    assert loaded.confidence == 0.82

    # Consulta de autorización en vivo
    is_auth, reason = temp_bias_store.is_authorized("DOGE/USDT", side="LONG", min_confidence=0.75)
    assert is_auth is True
    assert reason == "AUTHORIZED"


def test_bias_store_expiry_rejection(temp_bias_store):
    now = datetime.now(timezone.utc)
    past = now - timedelta(minutes=10)  # Ya venció hace 10 minutos!

    bias = MarketBiasSchema(
        symbol="PEPE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.90,
        consensus_score=0.95,
        regime_detected="BULL_MOMENTUM",
        valid_until_utc=past.isoformat(),
        max_leverage=1.0
    )

    temp_bias_store.save_bias(bias)

    # Debe rechazar por expiración
    is_auth, reason = temp_bias_store.is_authorized("PEPE/USDT", side="LONG")
    assert is_auth is False
    assert "BIAS_EXPIRED" in reason


def test_bias_store_veto_and_side_mismatch(temp_bias_store):
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=2)

    # 1. Caso STRICT_VETO
    bias_veto = MarketBiasSchema(
        symbol="SHIB/USDT",
        posture=MarketBiasPosture.STRICT_VETO,
        confidence=0.99,
        consensus_score=0.99,
        regime_detected="CHOPPY_HIGH_VOLATILITY",
        valid_until_utc=future.isoformat()
    )
    temp_bias_store.save_bias(bias_veto)

    is_auth, reason = temp_bias_store.is_authorized("SHIB/USDT", side="LONG")
    assert is_auth is False
    assert "STRICT_VETO" in reason

    # 2. Caso POSTURE_MISMATCH (postura es ALLOW_SHORT y se pide LONG)
    bias_short = MarketBiasSchema(
        symbol="BONK/USDT",
        posture=MarketBiasPosture.ALLOW_SHORT,
        confidence=0.85,
        consensus_score=0.85,
        valid_until_utc=future.isoformat()
    )
    temp_bias_store.save_bias(bias_short)

    is_auth, reason = temp_bias_store.is_authorized("BONK/USDT", side="LONG")
    assert is_auth is False
    assert "POSTURE_MISMATCH" in reason


def test_bias_store_concurrent_multithread_writes(temp_bias_store):
    """PB-135: Valida que escrituras concurrentes simultáneas no provoquen colisiones ni WinError 32."""
    import concurrent.futures

    symbols = [f"COIN_{i}/USDT" for i in range(12)]
    future = datetime.now(timezone.utc) + timedelta(hours=4)

    def write_worker(sym):
        bias = MarketBiasSchema(
            symbol=sym,
            posture=MarketBiasPosture.ALLOW_LONG,
            confidence=0.80,
            consensus_score=0.85,
            valid_until_utc=future.isoformat()
        )
        return temp_bias_store.save_bias(bias)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(write_worker, symbols))

    assert all(results) is True
    all_biases = temp_bias_store.get_all_biases()
    for sym in symbols:
        assert sym in all_biases
