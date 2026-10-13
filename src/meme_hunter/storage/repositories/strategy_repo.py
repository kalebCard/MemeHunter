"""
meme_hunter.storage.repositories.strategy_repo - Repositorio de Estrategias y Asignaciones HRP.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from meme_hunter.core.config import get_settings
from meme_hunter.core.types import StrategyStatus
from meme_hunter.storage.db import sqlite_cursor_context


class StrategyRepository:
    """Repositorio transaccional para la gestión del ciclo de vida de alfas en SQLite WAL."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = db_path or get_settings().DB_PATH

    def upsert_strategy(self, data: Dict[str, Any]) -> None:
        """Inserta o actualiza una estrategia en la base de datos de manera atómica."""
        now_iso = datetime.now(timezone.utc).isoformat()
        status_val = data["status"].value if isinstance(data["status"], StrategyStatus) else str(data["status"])

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
        with sqlite_cursor_context(self.db_path, commit=True) as cur:
            cur.execute(
                sql,
                (
                    data["strategy_id"],
                    data["name"],
                    status_val,
                    float(data.get("target_capital_weight", 0.0)),
                    float(data.get("backtest_sharpe", 0.0)),
                    float(data.get("live_sharpe", 0.0)),
                    int(data.get("days_in_stage", 0)),
                    float(data.get("decay_zscore", 0.0)),
                    data.get("last_audit_date", now_iso[:10]),
                    now_iso,
                ),
            )

    def get_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Recupera una estrategia por su identificador único."""
        sql = """
        SELECT strategy_id, name, status, target_capital_weight, backtest_sharpe,
               live_sharpe, days_in_stage, decay_zscore, last_audit_date, updated_at
        FROM strategies WHERE strategy_id = ?
        """
        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql, (strategy_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def get_all(self, status: Optional[Union[StrategyStatus, str]] = None) -> List[Dict[str, Any]]:
        """Obtiene todas las estrategias, opcionalmente filtradas por su estado en el ciclo."""
        sql = """
        SELECT strategy_id, name, status, target_capital_weight, backtest_sharpe,
               live_sharpe, days_in_stage, decay_zscore, last_audit_date, updated_at
        FROM strategies
        """
        params = []
        if status:
            status_val = status.value if isinstance(status, StrategyStatus) else str(status)
            sql += " WHERE status = ?"
            params.append(status_val)

        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in rows]

    def record_allocations(
        self, weights: Dict[str, float], status_map: Optional[Dict[str, str]] = None
    ) -> None:
        """Registra un snapshot inmutable de asignaciones HRP/Riskfolio."""
        now_iso = datetime.now(timezone.utc).isoformat()
        status_map = status_map or {}
        sql = "INSERT INTO portfolio_allocations (timestamp, strategy_id, weight, status) VALUES (?, ?, ?, ?)"

        with sqlite_cursor_context(self.db_path, commit=True) as cur:
            for sid, weight in weights.items():
                cur.execute(sql, (now_iso, sid, float(weight), status_map.get(sid, "LIVE")))
