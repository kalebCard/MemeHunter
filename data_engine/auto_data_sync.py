"""
auto_data_sync.py - Sincronizador Automático de Datos de Mercado de Binance Futures (Sprint 29: PB-100).

Permite actualizar continuamente los archivos .feather históricos en C:/meme_hunter_data/binance/futures/
consultando el endpoint público de Binance Futures REST API (fapi.binance.com).
Garantiza que la incubadora cuantitativa y el Cockpit Dashboard operen siempre con las velas más recientes.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from data_engine.paths import get_futures_data_dir

logger = logging.getLogger("AutoDataSync")

DEFAULT_DATA_DIR = get_futures_data_dir()

# Mapeo de pares institucionales a símbolos de la API de Binance Futures
SYMBOL_MAP = {
    "DOGE_USDT_USDT": "DOGEUSDT",
    "PEPE_USDT_USDT": "1000PEPEUSDT",
    "WIF_USDT_USDT": "WIFUSDT",
    "MEW_USDT_USDT": "MEWUSDT",
    "POPCAT_USDT_USDT": "POPCATUSDT",
    "NEIRO_USDT_USDT": "NEIROUSDT",
    "BONK_USDT_USDT": "1000BONKUSDT",
    "FLOKI_USDT_USDT": "1000FLOKIUSDT",
    "SHIB_USDT_USDT": "1000SHIBUSDT"
}


def fetch_klines_from_binance(
    api_symbol: str,
    interval: str = "4h",
    limit: int = 100,
    timeout_sec: float = 5.0
) -> Optional[pd.DataFrame]:
    """
    Descarga las últimas velas OHLCV desde la API pública de Binance Futures.
    No requiere API Keys para endpoints de mercado públicos.
    """
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={api_symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MemeHunter-AutoDataSync/2.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if not data or not isinstance(data, list):
                return None

            records = []
            for item in data:
                # Binance kline: [open_time, open, high, low, close, volume, ...]
                records.append({
                    "date": pd.to_datetime(item[0], unit='ms', utc=True),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5])
                })

            df = pd.DataFrame(records)
            return df
    except Exception as e:
        logger.warning(f"No se pudieron descargar velas de Binance para {api_symbol}: {e}")
        return None


def sync_symbol_feather(
    pair_name: str,
    interval: str = "4h",
    limit: int = 100,
    data_dir: Path = DEFAULT_DATA_DIR,
    force_write: bool = False
) -> Dict[str, Any]:
    """
    Actualiza incrementalmente el archivo .feather del par especificado.
    Fusiona los datos nuevos con los existentes sin duplicar marcas de tiempo.
    """
    clean_pair = pair_name.replace("/", "_").replace(":", "_").replace("-", "_")
    target_pattern = f"*{clean_pair}*{interval}*futures.feather"

    found_file: Optional[Path] = None
    if data_dir.exists():
        matches = list(data_dir.glob(target_pattern))
        if not matches:
            base_sym = clean_pair.split('_')[0]
            matches = list(data_dir.glob(f"*{base_sym}*{interval}*futures.feather"))
        if matches:
            found_file = matches[0]

    if not found_file:
        target_name = f"{clean_pair}-{interval}-futures.feather"
        found_file = data_dir / target_name

    api_symbol = SYMBOL_MAP.get(clean_pair)
    if not api_symbol:
        # Inferir de símbolo base
        base_sym = clean_pair.split('_')[0]
        api_symbol = f"{base_sym}USDT"

    new_df = fetch_klines_from_binance(api_symbol, interval=interval, limit=limit)
    if new_df is None or new_df.empty:
        return {
            "pair": clean_pair,
            "status": "offline_or_failed",
            "file": str(found_file),
            "rows_added": 0
        }

    # Si ya existe archivo en disco, unir y desduplicar
    if found_file.exists():
        try:
            old_df = pd.read_feather(found_file)
            if 'date' in old_df.columns:
                old_df['date'] = pd.to_datetime(old_df['date'], utc=True)
            elif 'timestamp' in old_df.columns:
                old_df['date'] = pd.to_datetime(old_df['timestamp'], utc=True)

            combined_df = pd.concat([old_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
            rows_added = len(combined_df) - len(old_df)
        except Exception as e:
            logger.warning(f"Error al leer feather existente {found_file}: {e}")
            combined_df = new_df
            rows_added = len(new_df)
    else:
        combined_df = new_df
        rows_added = len(new_df)

    # Guardar atómicamente
    try:
        os.makedirs(found_file.parent, exist_ok=True)
        combined_df.to_feather(found_file)
        return {
            "pair": clean_pair,
            "status": "synced",
            "file": str(found_file),
            "rows_added": rows_added,
            "total_rows": len(combined_df),
            "last_date": str(combined_df['date'].iloc[-1])
        }
    except Exception as e:
        logger.error(f"Error escribiendo archivo feather {found_file}: {e}")
        return {
            "pair": clean_pair,
            "status": "error_writing",
            "file": str(found_file),
            "error": str(e)
        }


def sync_all_active_symbols(
    pairs: Optional[List[str]] = None,
    interval: str = "4h",
    limit: int = 60,
    data_dir: Path = DEFAULT_DATA_DIR
) -> Dict[str, Any]:
    """
    Sincroniza todos los pares de memecoins activos de Binance Futures.
    """
    target_pairs = pairs or list(SYMBOL_MAP.keys())
    results = {}
    for p in target_pairs:
        res = sync_symbol_feather(p, interval=interval, limit=limit, data_dir=data_dir)
        results[p] = res

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "synced_pairs": len(results),
        "details": results
    }


if __name__ == "__main__":
    print("Iniciando sincronización de datos de Binance Futures...")
    r = sync_all_active_symbols(limit=50)
    print(json.dumps(r, indent=2))
