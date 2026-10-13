"""
meme_hunter.storage.schema - Definición DDL y Esquema Canónico de Base de Datos (Meme Hunter v8.0).
Centraliza todas las tablas relacionales para SQLite WAL:
- strategies: Ciclo de vida completo (SANDBOX, LIVE, ALPHA_DECAY, RETIRED).
- portfolio_allocations: Historial inmutable de asignaciones y pesos HRP / Riskfolio.
- alpha_autopsies: Dictámenes forenses cognitivos de autopsias de factores caídos.
- diversity_archive: Celdas del archivo MAP-Elites para preservación de diversidad.
- cycle_history: Historial y telemetría de ejecuciones del bucle autónomo.
- market_biases: Sesgos y predicciones direccionales de mercado por símbolo con TTL.
- risk_events: Auditoría de eventos de riesgo (Kill Switch, violaciones de drawdown, fricción).
"""

import logging
from pathlib import Path
from typing import Optional, Union

from meme_hunter.core.config import get_settings
from meme_hunter.storage.db import sqlite_cursor_context

logger = logging.getLogger("MemeHunterSchema")

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    target_capital_weight REAL NOT NULL DEFAULT 0.0,
    backtest_sharpe REAL NOT NULL DEFAULT 0.0,
    live_sharpe REAL NOT NULL DEFAULT 0.0,
    days_in_stage INTEGER NOT NULL DEFAULT 0,
    decay_zscore REAL NOT NULL DEFAULT 0.0,
    last_audit_date TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);

CREATE TABLE IF NOT EXISTS portfolio_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    weight REAL NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_allocations_timestamp ON portfolio_allocations(timestamp);
CREATE INDEX IF NOT EXISTS idx_allocations_strategy ON portfolio_allocations(strategy_id);

CREATE TABLE IF NOT EXISTS alpha_autopsies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_id TEXT NOT NULL,
    formula TEXT NOT NULL,
    health_status TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    suggested_actions TEXT NOT NULL DEFAULT '[]',
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_autopsies_factor ON alpha_autopsies(factor_id);
CREATE INDEX IF NOT EXISTS idx_autopsies_timestamp ON alpha_autopsies(timestamp);

CREATE TABLE IF NOT EXISTS diversity_archive (
    niche_id TEXT PRIMARY KEY,
    feature_type TEXT NOT NULL,
    complexity_tier TEXT NOT NULL,
    fitness_score REAL NOT NULL DEFAULT -1.0,
    factor_id TEXT,
    formula TEXT,
    factor_data TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_diversity_fitness ON diversity_archive(fitness_score);

CREATE TABLE IF NOT EXISTS cycle_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actions TEXT NOT NULL DEFAULT '[]',
    quarantined TEXT NOT NULL DEFAULT '[]',
    promoted TEXT NOT NULL DEFAULT '[]',
    new_weights TEXT NOT NULL DEFAULT '{}',
    goal_reached INTEGER NOT NULL DEFAULT 0,
    cycle_cost_usd REAL NOT NULL DEFAULT 0.0,
    accumulated_cost_usd REAL NOT NULL DEFAULT 0.0,
    active_strategies INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cycle_timestamp ON cycle_history(timestamp);

CREATE TABLE IF NOT EXISTS market_biases (
    symbol TEXT PRIMARY KEY,
    posture TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    valid_until_utc TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_biases_updated ON market_biases(updated_at);

CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    symbol TEXT,
    metric_value REAL,
    threshold_value REAL,
    timestamp_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_events_type ON risk_events(event_type);
CREATE INDEX IF NOT EXISTS idx_risk_events_timestamp ON risk_events(timestamp_utc);
"""


def init_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """Inicializa todas las tablas e índices canónicos con WAL activado."""
    if db_path is None:
        db_path = get_settings().DB_PATH

    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.executescript(CREATE_TABLES_SQL)
    logger.info(f"Esquema relacional canónico inicializado exitosamente en {db_path}")
