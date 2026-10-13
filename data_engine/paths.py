"""
data_engine/paths.py - Gestor Centralizado de Rutas de Datos y Portabilidad 12-Factor App (PB-137).
Sprint 41: Resuelve dinámicamente las rutas de mercado para permitir ejecución idéntica
en Linux, Docker, macOS y Windows, erradicando paths absolutos hardcodeados.
"""

import os
from pathlib import Path

# Raíz del repositorio
BASE_DIR = Path(__file__).resolve().parent.parent


def get_base_data_dir() -> Path:
    """
    Retorna el directorio base de datos de mercado.
    Prioridad:
    1. Variable de entorno MEME_DATA_DIR
    2. Directorio local 'C:/meme_hunter_data' si existe físicamente en Windows
    3. Fallback relativo del repositorio: BASE_DIR / 'user_data' / 'data'
    """
    env_dir = os.getenv("MEME_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    # Compatibilidad transparente con setups existentes en Windows
    if os.name == "nt":
        legacy_win_path = Path("C:/meme_hunter_data")
        if legacy_win_path.exists():
            return legacy_win_path

    # Fallback canónico relativo al repositorio
    return BASE_DIR / "user_data" / "data"


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

    # Si base ya contiene archivos .feather directamente
    if base.exists() and any(base.glob("*.feather")):
        return base

    return futures_path
