"""
tests/test_paths.py - Pruebas Unitarias de Portabilidad 12-Factor App (PB-137).
Sprint 41: Valida que la resolución de directorios sea dinámica, respete variables
de entorno (MEME_DATA_DIR) y funcione en Linux, Docker y Windows sin rutas fijas.
"""

import os
from pathlib import Path
from unittest.mock import patch

from data_engine.paths import get_base_data_dir, get_futures_data_dir, BASE_DIR


def test_paths_respects_custom_env_var(tmp_path):
    """PB-137: Valida que MEME_DATA_DIR tome prioridad absoluta."""
    custom_dir = tmp_path / "custom_market_data"
    custom_dir.mkdir(parents=True)

    with patch.dict(os.environ, {"MEME_DATA_DIR": str(custom_dir)}):
        resolved_base = get_base_data_dir()
        resolved_futures = get_futures_data_dir()

        assert resolved_base == custom_dir
        # Como no termina en binance/futures, añade el subdirectorio esperado
        assert resolved_futures == custom_dir / "binance" / "futures"


def test_paths_direct_futures_env_var(tmp_path):
    """PB-137: Si MEME_DATA_DIR apunta directamente a binance/futures, lo retorna directo."""
    direct_futures = tmp_path / "binance" / "futures"
    direct_futures.mkdir(parents=True)

    with patch.dict(os.environ, {"MEME_DATA_DIR": str(direct_futures)}):
        resolved_futures = get_futures_data_dir()
        assert resolved_futures == direct_futures


def test_paths_default_fallback_without_env(tmp_path):
    """PB-137: Valida fallback relativo sin MEME_DATA_DIR cuando el path legacy de Windows no existe."""
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(Path, "exists", return_value=False):
            resolved_base = get_base_data_dir()
            assert resolved_base == BASE_DIR / "user_data" / "data"
