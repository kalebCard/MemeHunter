"""
db_pool.py - Capa de Resiliencia y Concurrencia SQLite (Sprint 1: US-1.4).
Implementa:
- Activación de Write-Ahead Logging (WAL) para lecturas y escrituras concurrentes sin bloqueo.
- Sincronización normal (`PRAGMA synchronous = NORMAL`) para balance de rendimiento e integridad.
- Timeout de bloqueo tolerante a concurrencia (`busy_timeout = 15000` ms).
- Context managers seguros para consultas de solo lectura y transacciones atómicas.
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger("SQLitePool")


def configure_sqlite_wal(conn: sqlite3.Connection, read_only: bool = False) -> None:
    """Configura los pragmas óptimos de concurrencia y tolerancia a bloqueos en SQLite."""
    try:
        cur = conn.cursor()
        # busy_timeout en milisegundos (15 segundos)
        cur.execute("PRAGMA busy_timeout = 15000;")
        cur.execute("PRAGMA foreign_keys = ON;")
        if not read_only:
            cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA synchronous = NORMAL;")
        cur.close()
    except Exception as e:
        logger.debug(f"Aviso al configurar pragmas SQLite: {e}")


def get_sqlite_connection(db_path: str, timeout: float = 15.0, read_only: bool = False) -> sqlite3.Connection:
    """
    Abre una conexión SQLite configurada para alta concurrencia.
    Si read_only=True, intenta abrir con el URI 'mode=ro' para evitar bloqueos con procesos de escritura.
    """
    if not os.path.exists(db_path) and read_only:
        raise FileNotFoundError(f"Base de datos SQLite no encontrada: {db_path}")

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    if read_only:
        abs_db = os.path.abspath(db_path).replace("\\", "/")
        uri = f"file:{abs_db}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=timeout)
        except Exception:
            conn = sqlite3.connect(db_path, timeout=timeout)
    else:
        conn = sqlite3.connect(db_path, timeout=timeout)

    configure_sqlite_wal(conn, read_only=read_only)
    return conn


@contextmanager
def sqlite_cursor_context(db_path: str, timeout: float = 15.0, read_only: bool = False, commit: bool = False) -> Iterator[sqlite3.Cursor]:
    """Context manager para ejecutar consultas de forma segura con cierre y rollback automático."""
    conn = get_sqlite_connection(db_path, timeout=timeout, read_only=read_only)
    cur = conn.cursor()
    try:
        yield cur
        if commit and not read_only:
            conn.commit()
    except Exception:
        if not read_only:
            conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
