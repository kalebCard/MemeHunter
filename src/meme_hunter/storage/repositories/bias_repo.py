"""
meme_hunter.storage.repositories.bias_repo - Repositorio de Sesgos de Mercado (SSOT en SQLite WAL).
Sustituye completamente la persistencia en market_bias.json y previene WinError 32 y colisiones concurrentes.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from meme_hunter.core.config import get_settings
from meme_hunter.storage.db import sqlite_cursor_context


class MarketBiasRepository:
    """Repositorio transaccional de sesgos direccionales y clasificaciones de régimen."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = db_path or get_settings().DB_PATH

    def save_bias(
        self,
        symbol: str,
        posture: str,
        confidence: float,
        valid_until_utc: Optional[str] = None,
    ) -> None:
        """Guarda o actualiza atómicamente el sesgo de mercado para un símbolo específico."""
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
        with sqlite_cursor_context(self.db_path, commit=True) as cur:
            cur.execute(sql, (symbol, posture, float(confidence), valid_until_utc, now_iso))

    def get_bias(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Recupera el sesgo más reciente de un símbolo verificando si sigue vigente (TTL)."""
        sql = "SELECT symbol, posture, confidence, valid_until_utc, updated_at FROM market_biases WHERE symbol = ?"
        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql, (symbol,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            bias = dict(zip(cols, row))

        # Validación de vigencia si existe fecha de caducidad
        valid_until = bias.get("valid_until_utc")
        if valid_until:
            try:
                exp_dt = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp_dt:
                    bias["is_expired"] = True
                else:
                    bias["is_expired"] = False
            except Exception:
                bias["is_expired"] = False
        else:
            bias["is_expired"] = False

        return bias

    def get_all_active(self) -> List[Dict[str, Any]]:
        """Recupera todos los sesgos vigentes no expirados."""
        sql = "SELECT symbol, posture, confidence, valid_until_utc, updated_at FROM market_biases"
        now = datetime.now(timezone.utc)
        active = []

        with sqlite_cursor_context(self.db_path, read_only=True) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            for row in rows:
                item = dict(zip(cols, row))
                valid_until = item.get("valid_until_utc")
                if valid_until:
                    try:
                        exp_dt = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
                        if now > exp_dt:
                            continue
                    except Exception:
                        pass
                active.append(item)

        return active
