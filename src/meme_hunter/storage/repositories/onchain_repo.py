"""
meme_hunter.storage.repositories.onchain_repo - Repositorio de Métricas On-Chain en SQLite WAL (PB-183).
Almacena y recupera snapshots estructurados de The Graph, DeFiLlama y TrueBlocks para el orquestador DAG.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from meme_hunter.core.config import get_settings
from meme_hunter.storage.db import sqlite_cursor_context


class OnChainDataRepository:
    """Repositorio transaccional para telemetría y métricas on-chain en SQLite WAL."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = db_path or get_settings().DB_PATH

    def save_metric(
        self,
        source: str,
        entity_id: str,
        metric_type: str,
        data: Union[Dict[str, Any], List[Any]],
        confidence: float = 1.0,
    ) -> int:
        """Guarda atómicamente un snapshot on-chain."""
        now_iso = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(data)
        sql = """
        INSERT INTO onchain_metrics (source, entity_id, metric_type, data_json, confidence, updated_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        with sqlite_cursor_context(self.db_path, commit=True) as cur:
            cur.execute(
                sql,
                (
                    source.lower(),
                    entity_id.lower(),
                    metric_type,
                    data_json,
                    float(confidence),
                    now_iso,
                ),
            )
            return cur.lastrowid or 0

    def get_latest_metric(
        self, source: str, entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Recupera la métrica más reciente de una fuente y entidad específica."""
        sql = """
        SELECT id, source, entity_id, metric_type, data_json, confidence, updated_at
        FROM onchain_metrics
        WHERE source = ? AND entity_id = ?
        ORDER BY id DESC
        LIMIT 1;
        """
        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql, (source.lower(), entity_id.lower()))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            result = dict(zip(cols, row))
            try:
                result["data"] = json.loads(result["data_json"])
            except Exception:
                result["data"] = {}
            return result

    def get_recent_metrics(
        self, source: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Recupera el historial reciente de métricas ingeridas."""
        if source:
            sql = """
            SELECT id, source, entity_id, metric_type, data_json, confidence, updated_at
            FROM onchain_metrics
            WHERE source = ?
            ORDER BY id DESC
            LIMIT ?;
            """
            params = (source.lower(), limit)
        else:
            sql = """
            SELECT id, source, entity_id, metric_type, data_json, confidence, updated_at
            FROM onchain_metrics
            ORDER BY id DESC
            LIMIT ?;
            """
            params = (limit,)

        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            if not rows:
                return []
            cols = [c[0] for c in cur.description]
            results = []
            for r in rows:
                item = dict(zip(cols, r))
                try:
                    item["data"] = json.loads(item["data_json"])
                except Exception:
                    item["data"] = {}
                results.append(item)
            return results
