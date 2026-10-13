"""
tests/test_sprint42_sqlite_wal.py - Certificación de Consolidación Canónica SQLite WAL (PB-139).
Verifica persistencia y recuperación sinérgica de estrategias y sesgos directivos.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from validation.schemas import MarketBiasSchema, MarketBiasPosture
from portfolio.db_schema import (
    init_alpha_factory_db,
    upsert_market_bias_db,
    get_market_bias_db,
    get_all_market_biases_db,
    get_all_strategies_db
)
from portfolio.bias_store import BiasStore
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus


def test_market_biases_db_schema_crud(tmp_path):
    """PB-139: Verifica operaciones CRUD de market_biases en SQLite WAL."""
    db_file = str(tmp_path / "test_alpha.db")
    init_alpha_factory_db(db_file)

    now = datetime.now(timezone.utc)
    valid_until = (now + timedelta(hours=4)).isoformat()

    # 1. Insert
    upsert_market_bias_db(
        symbol="PEPE/USDT",
        posture="ALLOW_LONG",
        confidence=0.88,
        valid_until_utc=valid_until,
        db_path=db_file
    )

    # 2. Query individual
    bias = get_market_bias_db("PEPE/USDT", db_path=db_file)
    assert bias is not None
    assert bias["symbol"] == "PEPE/USDT"
    assert bias["posture"] == "ALLOW_LONG"
    assert abs(bias["confidence"] - 0.88) < 1e-4

    # 3. Upsert / Update
    upsert_market_bias_db(
        symbol="PEPE/USDT",
        posture="ALLOW_SHORT",
        confidence=0.92,
        valid_until_utc=valid_until,
        db_path=db_file
    )
    updated = get_market_bias_db("PEPE/USDT", db_path=db_file)
    assert updated["posture"] == "ALLOW_SHORT"
    assert abs(updated["confidence"] - 0.92) < 1e-4

    # 4. Query all
    all_b = get_all_market_biases_db(db_path=db_file)
    assert "PEPE/USDT" in all_b
    assert all_b["PEPE/USDT"]["posture"] == "ALLOW_SHORT"


def test_bias_store_sqlite_sync_and_fallback(tmp_path):
    """PB-139: Verifica persistencia dual en BiasStore y recuperación fallback desde SQLite."""
    json_path = str(tmp_path / "market_bias.json")
    db_path = str(tmp_path / "alpha_factory.db")

    store = BiasStore(filepath=json_path, db_path=db_path)
    now = datetime.now(timezone.utc)

    schema_bias = MarketBiasSchema(
        symbol="DOGE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.95,
        consensus_score=0.90,
        valid_until_utc=(now + timedelta(hours=2)).isoformat(),
        metadata={"justification": "Strong breakout"}
    )

    # Guardar sesgo (debe escribir JSON y sincronizar SQLite WAL)
    success = store.save_bias(schema_bias)
    assert success is True
    assert os.path.exists(json_path)

    # Verificar que también se guardó en SQLite
    db_entry = get_market_bias_db("DOGE/USDT", db_path=db_path)
    assert db_entry is not None
    assert db_entry["posture"] == "ALLOW_LONG"

    # Simular pérdida/corrupción del archivo JSON y comprobar recuperación desde SQLite
    os.remove(json_path)
    assert not os.path.exists(json_path)

    fallback_bias = store.get_bias("DOGE/USDT")
    assert fallback_bias is not None
    assert fallback_bias.symbol == "DOGE/USDT"
    assert fallback_bias.posture == MarketBiasPosture.ALLOW_LONG
    assert abs(fallback_bias.confidence - 0.95) < 1e-4


def test_strategy_incubator_sqlite_persistence(tmp_path):
    """PB-139: Verifica persistencia y recuperación canónica de la incubadora en SQLite WAL."""
    db_file = str(tmp_path / "alpha_factory.db")
    json_file = str(tmp_path / "incubator_state.json")

    incubator = StrategyLifecycleIncubator()
    s1 = incubator.register_strategy("strat_alpha", "Meme Momentum", backtest_sharpe=2.4)
    s2 = incubator.register_strategy("strat_beta", "Mean Reversion", backtest_sharpe=1.9)

    s1.status = StrategyLifecycleStatus.LIVE
    s1.target_capital_weight = 0.65
    s2.status = StrategyLifecycleStatus.LIVE
    s2.target_capital_weight = 0.35

    # Persistir estado
    incubator.save_state(filepath=json_file, db_path=db_file)
    assert os.path.exists(db_file)

    # Cargar en una nueva instancia desde SQLite
    new_incubator = StrategyLifecycleIncubator()
    loaded = new_incubator.load_from_db(db_file)
    assert loaded is True
    assert len(new_incubator.strategies) == 2
    assert "strat_alpha" in new_incubator.strategies
    assert new_incubator.strategies["strat_alpha"].status == StrategyLifecycleStatus.LIVE
    assert abs(new_incubator.strategies["strat_alpha"].target_capital_weight - 0.65) < 1e-4
