"""
meme_hunter.storage.db - Gestor de Conexiones y Concurrencia Transaccional SQLite WAL.
Implementa:
- Activación de Write-Ahead Logging (WAL) para lecturas y escrituras concurrentes sin bloqueo.
- Sincronización normal (PRAGMA synchronous = NORMAL) para equilibrio entre rendimiento e integridad.
- Timeout de bloqueo tolerante a concurrencia (busy_timeout = 15000 ms).
- Context managers seguros para transacciones y consultas de solo lectura.
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union

from meme_hunter.core.config import get_settings

logger = logging.getLogger("MemeHunterDB")


def configure_sqlite_wal(conn: sqlite3.Connection, read_only: bool = False) -> None:
    """Configura los pragmas óptimos de concurrencia y tolerancia a bloqueos en SQLite."""
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout = 15000;")
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        if not read_only:
            cur.execute("PRAGMA journal_mode = WAL;")
        cur.close()
    except Exception as e:
        logger.debug(f"Aviso al configurar pragmas SQLite: {e}")


def get_sqlite_connection(
    db_path: Optional[Union[str, Path]] = None,
    timeout: float = 15.0,
    read_only: bool = False,
) -> sqlite3.Connection:
    """
    Abre una conexión SQLite configurada para alta concurrencia.
    Si db_path es None, utiliza la ruta canónica configurada en AppSettings.
    """
    if db_path is None:
        db_path = get_settings().DB_PATH

    path_str = str(db_path)
    is_memory = path_str == ":memory:" or "mode=memory" in path_str

    if not is_memory:
        os.makedirs(os.path.dirname(os.path.abspath(path_str)), exist_ok=True)
        if read_only and not os.path.exists(path_str):
            raise FileNotFoundError(f"Base de datos SQLite no encontrada: {path_str}")

    if read_only and not is_memory:
        abs_db = os.path.abspath(path_str).replace("\\", "/")
        uri = f"file:{abs_db}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=timeout)
        except Exception:
            conn = sqlite3.connect(path_str, timeout=timeout)
    else:
        conn = sqlite3.connect(path_str, timeout=timeout)

    configure_sqlite_wal(conn, read_only=read_only)
    return conn


@contextmanager
def sqlite_cursor_context(
    db_path: Optional[Union[str, Path]] = None,
    timeout: float = 15.0,
    read_only: bool = False,
    commit: bool = False,
) -> Iterator[sqlite3.Cursor]:
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
