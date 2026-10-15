"""
portfolio.db_pool - Shim de Concurrencia y Persistencia SQLite WAL (Sprint 55: PB-212).
Consolidado en la Única Fuente de Verdad (SSOT): meme_hunter.storage.db.
Mantiene compatibilidad hacia atrás total mientras centraliza la lógica WAL en el core.
"""

from meme_hunter.storage.db import (
    configure_sqlite_wal,
    get_sqlite_connection,
    sqlite_cursor_context,
)

__all__ = [
    "configure_sqlite_wal",
    "get_sqlite_connection",
    "sqlite_cursor_context",
]
