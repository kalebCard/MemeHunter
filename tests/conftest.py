"""
tests/conftest.py - Fixtures Globales y Configuración Canónica de Pruebas Pytest (v8.0).
Garantiza resolución de rutas en sys.path y aislamiento hermético de bases de datos temporales.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
import pytest

# Configurar sys.path canónicamente para resolver 'src' y la raíz del repositorio
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from meme_hunter.core.config import AppSettings
from meme_hunter.storage.schema import init_database


@pytest.fixture
def test_settings() -> AppSettings:
    """Fixture de configuración en entorno de pruebas (ENV=test)."""
    return AppSettings(
        ENV="test",
        BINANCE_API_KEY="test_binance_key",
        BINANCE_API_SECRET="test_binance_secret",
        FREQTRADE_API_PASSWORD="test_freq_password",
        DASHBOARD_SECRET_KEY="test_dash_secret",
    )


@pytest.fixture
def temp_wal_db() -> Generator[str, None, None]:
    """Genera una base de datos SQLite temporal con WAL activado y esquema canónico inicializado."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    init_database(db_path)
    yield db_path

    # Teardown: Limpiar base de datos y archivos auxiliares WAL
    for suffix in ["", "-wal", "-shm"]:
        p = Path(db_path + suffix)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
