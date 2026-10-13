"""
test_storage_repositories.py - Pruebas Unitarias del Esquema y Repositorios SQLite WAL.
"""

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

# Asegurar importación de src/meme_hunter
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from meme_hunter.core.types import StrategyStatus
from meme_hunter.storage.db import get_sqlite_connection
from meme_hunter.storage.schema import init_database
from meme_hunter.storage.repositories import (
    StrategyRepository,
    MarketBiasRepository,
    AutopsyRepository,
)


@pytest.fixture
def temp_db_path():
    """Genera un archivo temporal de base de datos para pruebas aisladas."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_database(path)
    yield path
    try:
        Path(path).unlink(missing_ok=True)
        Path(path + "-wal").unlink(missing_ok=True)
        Path(path + "-shm").unlink(missing_ok=True)
    except Exception:
        pass


def test_schema_initialization(temp_db_path):
    """Verifica que las tablas canónicas se hayan creado correctamente en WAL mode."""
    conn = get_sqlite_connection(temp_db_path, read_only=True)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    conn.close()

    expected_tables = {
        "strategies",
        "portfolio_allocations",
        "alpha_autopsies",
        "diversity_archive",
        "cycle_history",
        "market_biases",
        "risk_events",
    }
    assert expected_tables.issubset(tables)


def test_strategy_repository_lifecycle(temp_db_path):
    """Verifica inserción, actualización, filtrado y registro de asignaciones en StrategyRepository."""
    repo = StrategyRepository(db_path=temp_db_path)

    # 1. Inserción inicial
    strat_data = {
        "strategy_id": "alpha_001",
        "name": "MemeMomentum_V1",
        "status": StrategyStatus.SANDBOX,
        "target_capital_weight": 0.25,
        "backtest_sharpe": 2.15,
        "live_sharpe": 1.80,
    }
    repo.upsert_strategy(strat_data)

    retrieved = repo.get_by_id("alpha_001")
    assert retrieved is not None
    assert retrieved["name"] == "MemeMomentum_V1"
    assert retrieved["status"] == "SANDBOX"
    assert retrieved["target_capital_weight"] == 0.25

    # 2. Promoción a LIVE
    strat_data["status"] = StrategyStatus.LIVE
    strat_data["target_capital_weight"] = 0.50
    repo.upsert_strategy(strat_data)

    live_strats = repo.get_all(status=StrategyStatus.LIVE)
    assert len(live_strats) == 1
    assert live_strats[0]["strategy_id"] == "alpha_001"
    assert live_strats[0]["target_capital_weight"] == 0.50

    # 3. Registro de asignaciones
    repo.record_allocations({"alpha_001": 0.50}, status_map={"alpha_001": "LIVE"})


def test_market_bias_repository(temp_db_path):
    """Verifica guardado de sesgo, comprobación de TTL y consulta activa."""
    repo = MarketBiasRepository(db_path=temp_db_path)

    # 1. Sesgo vigente en el futuro (+2 horas)
    valid_until = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    repo.save_bias(
        symbol="DOGE/USDT:USDT",
        posture="BEARISH_SHORT",
        confidence=0.88,
        valid_until_utc=valid_until,
    )

    bias = repo.get_bias("DOGE/USDT:USDT")
    assert bias is not None
    assert bias["posture"] == "BEARISH_SHORT"
    assert bias["confidence"] == 0.88
    assert bias["is_expired"] is False

    # 2. Sesgo caducado en el pasado (-1 hora)
    past_until = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    repo.save_bias(
        symbol="PEPE/USDT:USDT",
        posture="BULLISH_LONG",
        confidence=0.60,
        valid_until_utc=past_until,
    )

    expired_bias = repo.get_bias("PEPE/USDT:USDT")
    assert expired_bias is not None
    assert expired_bias["is_expired"] is True

    # 3. Consulta de solo activos
    active = repo.get_all_active()
    symbols = [a["symbol"] for a in active]
    assert "DOGE/USDT:USDT" in symbols
    assert "PEPE/USDT:USDT" not in symbols


def test_autopsy_repository(temp_db_path):
    """Verifica inserción y lectura de autopsias forenses cognitivas."""
    repo = AutopsyRepository(db_path=temp_db_path)

    verdict = {
        "factor_id": "factor_decay_42",
        "formula": "ts_mean(rsi(14), 5) / stddev(close, 20)",
        "health_status": "CRITICAL_BREAK",
        "diagnosis": "Quiebre estructural por compresión de volatilidad",
        "root_cause": "Régimen Choppy Range redujo IC por debajo de cero",
        "recommendation": "Mutar ventana temporal a 30 barras y aplicar filtro de volumen",
        "confidence_score": 0.94,
        "suggested_actions": ["ISOLATE_FACTOR", "REDUCE_WEIGHT", "TRIGGER_GENETIC_MUTATION"],
    }

    autopsy_id = repo.insert_autopsy(verdict)
    assert autopsy_id > 0

    latest = repo.get_latest(limit=5)
    assert len(latest) >= 1
    assert latest[0]["factor_id"] == "factor_decay_42"
    assert latest[0]["confidence_score"] == 0.94
    assert latest[0]["suggested_actions"] == ["ISOLATE_FACTOR", "REDUCE_WEIGHT", "TRIGGER_GENETIC_MUTATION"]
