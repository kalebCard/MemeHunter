"""
db_schema.py - Esquema Relacional e Inicializador de Base de Datos para la Fábrica de Alphas (Sprint 25: PB-87).

Define el esquema SQLite optimizado para alta concurrencia (WAL mode):
- `strategies`: Estado de la incubadora de estrategias (SANDBOX, LIVE, ALPHA_DECAY, RETIRED).
- `portfolio_allocations`: Historial inmutable de asignaciones y pesos HRP.
- `alpha_autopsies`: Dictámenes forenses cognitivos de autopsias de factores caídos.
- `diversity_archive`: Celdas del archivo MAP-Elites para preservación de diversidad.
- `cycle_history`: Historial de ejecuciones del bucle autónomo.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from portfolio.db_pool import get_sqlite_connection, sqlite_cursor_context, configure_sqlite_wal

logger = logging.getLogger("AlphaFactoryDB")

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "portfolio",
    "alpha_factory.db"
)


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
"""


def init_alpha_factory_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Inicializa el esquema de la base de datos de la fábrica de alphas con WAL activado."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.executescript(CREATE_TABLES_SQL)
    logger.info(f"Esquema de base de datos inicializado exitosamente en {db_path}")


def upsert_strategy_db(strat: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    """Inserta o actualiza atómicamente una estrategia en la base de datos."""
    now_iso = datetime.now(timezone.utc).isoformat()
    status_str = strat['status'].value if hasattr(strat['status'], 'value') else str(strat['status'])
    sql = """
    INSERT INTO strategies (
        strategy_id, name, status, target_capital_weight, backtest_sharpe,
        live_sharpe, days_in_stage, decay_zscore, last_audit_date, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(strategy_id) DO UPDATE SET
        name = excluded.name,
        status = excluded.status,
        target_capital_weight = excluded.target_capital_weight,
        backtest_sharpe = excluded.backtest_sharpe,
        live_sharpe = excluded.live_sharpe,
        days_in_stage = excluded.days_in_stage,
        decay_zscore = excluded.decay_zscore,
        last_audit_date = excluded.last_audit_date,
        updated_at = excluded.updated_at;
    """
    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.execute(sql, (
            strat["strategy_id"],
            strat["name"],
            status_str,
            float(strat.get("target_capital_weight", 0.0)),
            float(strat.get("backtest_sharpe", 0.0)),
            float(strat.get("live_sharpe", 0.0)),
            int(strat.get("days_in_stage", 0)),
            float(strat.get("decay_zscore", 0.0)),
            strat.get("last_audit_date", now_iso[:10]),
            now_iso
        ))


def get_all_strategies_db(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Obtiene todas las estrategias registradas desde la base de datos."""
    if not os.path.exists(db_path):
        return []
    sql = "SELECT strategy_id, name, status, target_capital_weight, backtest_sharpe, live_sharpe, days_in_stage, decay_zscore, last_audit_date, updated_at FROM strategies"
    with sqlite_cursor_context(db_path, read_only=True) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [col[0] for col in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def record_allocations_db(weights: Dict[str, float], status_map: Dict[str, str], db_path: str = DEFAULT_DB_PATH) -> None:
    """Registra una instantánea de asignaciones HRP en el historial inmutable."""
    now_iso = datetime.now(timezone.utc).isoformat()
    sql = "INSERT INTO portfolio_allocations (timestamp, strategy_id, weight, status) VALUES (?, ?, ?, ?)"
    with sqlite_cursor_context(db_path, commit=True) as cur:
        for sid, w in weights.items():
            cur.execute(sql, (now_iso, sid, float(w), status_map.get(sid, "LIVE")))


def insert_autopsy_db(verdict: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> int:
    """Registra una autopsia forense cognitiva en la base de datos."""
    sql = """
    INSERT INTO alpha_autopsies (
        factor_id, formula, health_status, diagnosis, root_cause,
        recommendation, confidence_score, suggested_actions, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    actions_json = json.dumps(verdict.get("suggested_actions", []), ensure_ascii=False)
    timestamp = verdict.get("timestamp", datetime.now(timezone.utc).isoformat())
    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.execute(sql, (
            verdict["factor_id"],
            verdict["formula"],
            verdict["health_status"],
            verdict["diagnosis"],
            verdict["root_cause"],
            verdict["recommendation"],
            float(verdict.get("confidence_score", 0.0)),
            actions_json,
            timestamp
        ))
        return cur.lastrowid


def get_autopsies_db(limit: int = 50, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Recupera los dictámenes forenses más recientes."""
    if not os.path.exists(db_path):
        return []
    sql = """
    SELECT id, factor_id, formula, health_status, diagnosis, root_cause, recommendation, confidence_score, suggested_actions, timestamp
    FROM alpha_autopsies ORDER BY id DESC LIMIT ?
    """
    with sqlite_cursor_context(db_path, read_only=True) as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        cols = [col[0] for col in cur.description]
    res = []
    for row in rows:
        d = dict(zip(cols, row))
        try:
            d["suggested_actions"] = json.loads(d["suggested_actions"])
        except Exception:
            d["suggested_actions"] = []
        res.append(d)
    return res


def upsert_diversity_cell_db(cell_dict: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    """Inserta o actualiza un nicho fenotípico en el archivo de diversidad MAP-Elites."""
    now_iso = datetime.now(timezone.utc).isoformat()
    factor_data_str = json.dumps(cell_dict.get("factor", {}), ensure_ascii=False) if cell_dict.get("factor") else None
    factor_id = cell_dict.get("factor", {}).get("factor_id") if cell_dict.get("factor") else None
    formula = cell_dict.get("factor", {}).get("formula") if cell_dict.get("factor") else None

    sql = """
    INSERT INTO diversity_archive (
        niche_id, feature_type, complexity_tier, fitness_score, factor_id, formula, factor_data, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(niche_id) DO UPDATE SET
        feature_type = excluded.feature_type,
        complexity_tier = excluded.complexity_tier,
        fitness_score = excluded.fitness_score,
        factor_id = excluded.factor_id,
        formula = excluded.formula,
        factor_data = excluded.factor_data,
        updated_at = excluded.updated_at;
    """
    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.execute(sql, (
            cell_dict["niche_id"],
            cell_dict["feature_type"],
            cell_dict["complexity_tier"],
            float(cell_dict.get("fitness_score", -1.0)),
            factor_id,
            formula,
            factor_data_str,
            now_iso
        ))


def get_diversity_archive_db(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Carga todas las celdas del archivo de diversidad MAP-Elites."""
    if not os.path.exists(db_path):
        return {}
    sql = "SELECT niche_id, feature_type, complexity_tier, fitness_score, factor_id, formula, factor_data FROM diversity_archive"
    result = {}
    with sqlite_cursor_context(db_path, read_only=True) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        for row in rows:
            niche_id, ft, ct, fit, fid, formula, fdata_str = row
            factor_dict = None
            if fdata_str:
                try:
                    factor_dict = json.loads(fdata_str)
                except Exception:
                    factor_dict = None
            result[niche_id] = {
                "niche_id": niche_id,
                "feature_type": ft,
                "complexity_tier": ct,
                "fitness_score": fit,
                "factor": factor_dict
            }
    return result


def record_cycle_history_db(entry: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> int:
    """Registra una iteración del ciclo de auto-mejora en la base de datos."""
    sql = """
    INSERT INTO cycle_history (
        timestamp, actions, quarantined, promoted, new_weights,
        goal_reached, cycle_cost_usd, accumulated_cost_usd, active_strategies
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.execute(sql, (
            entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
            json.dumps(entry.get("actions", []), ensure_ascii=False),
            json.dumps(entry.get("quarantined", []), ensure_ascii=False),
            json.dumps(entry.get("promoted", []), ensure_ascii=False),
            json.dumps(entry.get("new_weights", {}), ensure_ascii=False),
            1 if entry.get("goal_reached") else 0,
            float(entry.get("estimated_cycle_cost_usd", entry.get("cycle_cost_usd", 0.0))),
            float(entry.get("accumulated_cost_usd", 0.0)),
            int(entry.get("active_strategies", 0))
        ))
        return cur.lastrowid


insert_cycle_history_db = record_cycle_history_db


def get_cycle_history_db(limit: int = 50, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Obtiene el historial reciente de ciclos ejecutados."""
    if not os.path.exists(db_path):
        return []
    sql = "SELECT id, timestamp, actions, quarantined, promoted, new_weights, goal_reached, cycle_cost_usd, accumulated_cost_usd, active_strategies FROM cycle_history ORDER BY id DESC LIMIT ?"
    with sqlite_cursor_context(db_path, read_only=True) as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        cols = [col[0] for col in cur.description]
    res = []
    for row in rows:
        d = dict(zip(cols, row))
        for jcol in ["actions", "quarantined", "promoted"]:
            try:
                d[jcol] = json.loads(d[jcol])
            except Exception:
                d[jcol] = []
        try:
            d["new_weights"] = json.loads(d["new_weights"])
        except Exception:
            d["new_weights"] = {}
        d["goal_reached"] = bool(d["goal_reached"])
        res.append(d)
    return res


def upsert_market_bias_db(
    symbol: str,
    posture: str,
    confidence: float,
    valid_until_utc: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Inserta o actualiza atómicamente la directiva de sesgo en SQLite WAL."""
    now_iso = datetime.now(timezone.utc).isoformat()
    sql = """
    INSERT INTO market_biases (symbol, posture, confidence, valid_until_utc, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(symbol) DO UPDATE SET
        posture = excluded.posture,
        confidence = excluded.confidence,
        valid_until_utc = excluded.valid_until_utc,
        updated_at = excluded.updated_at;
    """
    with sqlite_cursor_context(db_path, commit=True) as cur:
        cur.execute(sql, (
            symbol.upper(),
            str(posture),
            float(confidence),
            valid_until_utc,
            now_iso
        ))


def get_market_bias_db(symbol: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Consulta el sesgo directivo activo de un símbolo desde SQLite WAL."""
    if not os.path.exists(db_path):
        return None
    sql = "SELECT symbol, posture, confidence, valid_until_utc, updated_at FROM market_biases WHERE symbol = ?"
    with sqlite_cursor_context(db_path, read_only=True) as cur:
        cur.execute(sql, (symbol.upper(),))
        row = cur.fetchone()
        if not row:
            return None
        cols = [col[0] for col in cur.description]
        return dict(zip(cols, row))


def get_all_market_biases_db(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Dict[str, Any]]:
    """Recupera todos los sesgos directivos indexados por símbolo desde SQLite WAL."""
    if not os.path.exists(db_path):
        return {}
    sql = "SELECT symbol, posture, confidence, valid_until_utc, updated_at FROM market_biases"
    result = {}
    with sqlite_cursor_context(db_path, read_only=True) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        for row in rows:
            sym, post, conf, valid, upd = row
            result[sym] = {
                "symbol": sym,
                "posture": post,
                "confidence": conf,
                "valid_until_utc": valid,
                "updated_at": upd
            }
    return result

