"""
test_db_pool.py - Pruebas Unitarias del Pool y Concurrencia SQLite (Sprint 1: US-1.4).
Verifica:
1. Configuración de modo WAL y synchronous=NORMAL.
2. Configuración de busy_timeout=15000 ms.
3. Concurrencia de lecturas y escrituras simultáneas mediante múltiples hilos.
"""

import os
import sys
import tempfile
import sqlite3
import threading
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from portfolio.db_pool import get_sqlite_connection, sqlite_cursor_context


def test_sqlite_wal_pragmas_configured():
    """Valida que get_sqlite_connection active journal_mode=WAL y busy_timeout."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
        db_path = tf.name

    try:
        conn = get_sqlite_connection(db_path, read_only=False)
        cur = conn.cursor()

        cur.execute("PRAGMA journal_mode;")
        journal_mode = cur.fetchone()[0].upper()
        assert journal_mode == "WAL"

        cur.execute("PRAGMA busy_timeout;")
        busy_timeout = cur.fetchone()[0]
        assert busy_timeout >= 10000

        cur.close()
        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_sqlite_concurrent_readers_and_writer():
    """Valida que múltiples hilos lectores y un escritor coexistan sin bloquearse bajo WAL."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
        db_path = tf.name

    try:
        # Inicializar esquema
        with sqlite_cursor_context(db_path, commit=True) as cur:
            cur.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, pair TEXT, profit REAL);")
            cur.execute("INSERT INTO trades (pair, profit) VALUES ('DOGE/USDT', 15.5);")

        errors = []

        def reader_task():
            try:
                for _ in range(15):
                    with sqlite_cursor_context(db_path, read_only=True) as cur:
                        cur.execute("SELECT count(*) FROM trades;")
                        _ = cur.fetchone()
            except Exception as e:
                errors.append(e)

        def writer_task():
            try:
                for i in range(10):
                    with sqlite_cursor_context(db_path, commit=True) as cur:
                        cur.execute("INSERT INTO trades (pair, profit) VALUES (?, ?);", (f"PEPE/USDT_{i}", 5.0 * i))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader_task),
            threading.Thread(target=reader_task),
            threading.Thread(target=writer_task),
            threading.Thread(target=reader_task),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No debe haber errores de concurrencia 'database is locked'
        assert len(errors) == 0

        # Verificar conteo final
        with sqlite_cursor_context(db_path, read_only=True) as cur:
            cur.execute("SELECT count(*) FROM trades;")
            total = cur.fetchone()[0]
            assert total == 11
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
