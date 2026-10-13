"""
meme_hunter.storage.repositories.autopsy_repo - Repositorio de Autopsias Forenses Cognitivas.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from meme_hunter.core.config import get_settings
from meme_hunter.storage.db import sqlite_cursor_context


class AutopsyRepository:
    """Repositorio transaccional de dictámenes cognitivos emitidos por agentes LLM."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = db_path or get_settings().DB_PATH

    def insert_autopsy(self, verdict: Dict[str, Any]) -> int:
        """Registra una autopsia forense y retorna el ID autoincremental generado."""
        now_iso = datetime.now(timezone.utc).isoformat()
        actions = verdict.get("suggested_actions", [])
        actions_json = json.dumps(actions) if isinstance(actions, list) else str(actions)

        sql = """
        INSERT INTO alpha_autopsies (
            factor_id, formula, health_status, diagnosis, root_cause,
            recommendation, confidence_score, suggested_actions, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with sqlite_cursor_context(self.db_path, commit=True) as cur:
            cur.execute(
                sql,
                (
                    verdict["factor_id"],
                    verdict["formula"],
                    verdict.get("health_status", "WARNING_DECAY"),
                    verdict.get("diagnosis", ""),
                    verdict.get("root_cause", ""),
                    verdict.get("recommendation", ""),
                    float(verdict.get("confidence_score", 0.0)),
                    actions_json,
                    verdict.get("timestamp", now_iso),
                ),
            )
            return cur.lastrowid or 0

    def get_latest(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Recupera los dictámenes forenses más recientes."""
        sql = """
        SELECT id, factor_id, formula, health_status, diagnosis, root_cause,
               recommendation, confidence_score, suggested_actions, timestamp
        FROM alpha_autopsies
        ORDER BY id DESC
        LIMIT ?
        """
        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            results = []
            for row in rows:
                item = dict(zip(cols, row))
                try:
                    item["suggested_actions"] = json.loads(item["suggested_actions"])
                except Exception:
                    pass
                results.append(item)
            return results
