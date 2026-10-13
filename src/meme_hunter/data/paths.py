"""
meme_hunter.data.paths - Resolución Centralizada de Rutas de Datos y Portabilidad 12-Factor App.
Integrado con AppSettings para compatibilidad transparente en Docker Linux, Windows y Cloud.
"""

import os
from pathlib import Path
from meme_hunter.core.config import get_settings


def get_base_data_dir() -> Path:
    """
    Retorna el directorio base de datos de mercado.
    Prioridad:
    1. Variable de entorno MEME_DATA_DIR o AppSettings.DATA_DIR
    2. Directorio local 'C:/meme_hunter_data' si existe físicamente en Windows
    3. Fallback canónico relativo al repositorio: ROOT_DIR / 'user_data' / 'data'
    """
    env_dir = os.getenv("MEME_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    settings = get_settings()
    if settings.DATA_DIR and settings.DATA_DIR.exists():
        return settings.DATA_DIR

    if os.name == "nt":
        legacy_win_path = Path("C:/meme_hunter_data")
        if legacy_win_path.exists():
            return legacy_win_path

    return settings.ROOT_DIR / "user_data" / "data"


def get_futures_data_dir() -> Path:
    """
    Retorna el directorio de datos de Binance Futures.
    Si base_dir termina en 'binance/futures', lo devuelve directamente;
    de lo contrario añade el subdirectorio 'binance/futures'.
    """
    base = get_base_data_dir()
    norm_str = str(base).replace("\\", "/").rstrip("/")
    if norm_str.endswith("binance/futures"):
        return base

    futures_path = base / "binance" / "futures"
    if futures_path.exists():
        return futures_path

    if base.exists() and any(base.glob("*.feather")):
        return base

    return futures_path
