"""
data_engine/polars_feed.py
--------------------------
Adaptador de Ingesta de Alto Rendimiento y Cálculo Cuantitativo con Polars (Sprint 33: PB-115).

Implementa:
1. Lectura ultra-rápida Zero-Copy de archivos .feather (Arrow IPC) mediante `pl.read_ipc`.
2. Cálculo nativo y vectorizado en Polars de características cuantitativas:
   - Retornos logarítmicos continuos.
   - Volatilidad realizada móvil.
   - HL-Spread y Ratios de volumen (RVOL).
   - Diferenciación Fraccionaria (FFD) acelerada con preservación de memoria.
3. Conversión bidireccional transparente Polars <-> Pandas para interoperabilidad con Freqtrade.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
import numpy as np
import pandas as pd
import polars as pl
import logging

logger = logging.getLogger("PolarsDataFeed")

DEFAULT_DATA_DIR = Path("C:/meme_hunter_data/binance/futures")


def load_feather_polars(file_path: Union[str, Path]) -> pl.DataFrame:
    """
    Carga un archivo .feather (Arrow IPC) utilizando Polars con aceleración Zero-Copy.
    Es de 10x a 30x más rápido que pd.read_feather y reduce el consumo de memoria.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {p}")

    try:
        # Polars soporta IPC / Feather nativamente
        df = pl.read_ipc(p)
        return df
    except Exception as e:
        logger.warning(f"Fallo al leer {p} con pl.read_ipc ({e}). Intentando fallback de interoperabilidad.")
        pd_df = pd.read_feather(p)
        return pl.from_pandas(pd_df)


def save_feather_polars(df: pl.DataFrame, file_path: Union[str, Path]) -> None:
    """
    Guarda un DataFrame de Polars directamente como archivo .feather (Arrow IPC).
    """
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.write_ipc(p)


def get_weights_ffd_vectorized(d: float, threshold: float = 1e-4, max_lags: int = 1000) -> np.ndarray:
    """Calcula pesos decrecientes de Hosking para FFD."""
    weights = [1.0]
    k = 1
    while k < max_lags:
        w_k = -weights[-1] / k * (d - k + 1)
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
        k += 1
    return np.array(weights[::-1])


def frac_diff_ffd_polars(
    series: Union[pl.Series, np.ndarray, pd.Series],
    d: float = 0.40,
    threshold: float = 1e-4
) -> pl.Series:
    """
    Diferenciación Fraccionaria con Ventana Fija (FFD) acelerada.
    Preserva la memoria de largo plazo estacionarizando la serie de precios.
    Retorna un pl.Series con valores flotantes y valores nulos para lags iniciales.
    """
    if isinstance(series, pl.Series):
        values = series.to_numpy()
        name = series.name
    elif isinstance(series, pd.Series):
        values = series.to_numpy()
        name = series.name or "ffd"
    else:
        values = np.asarray(series, dtype=np.float64)
        name = "ffd"

    weights = get_weights_ffd_vectorized(d, threshold=threshold)
    width = len(weights)
    n = len(values)

    if n < width:
        return pl.Series(name, [None] * n, dtype=pl.Float64)

    # Convolución rápida 1D en NumPy (C-speed)
    convolved = np.convolve(values, weights, mode="valid")
    pad_len = width - 1
    full_res = np.empty(n, dtype=np.float64)
    full_res[:pad_len] = np.nan
    full_res[pad_len:] = convolved

    return pl.Series(name, full_res, dtype=pl.Float64)


def compute_features_polars(df: pl.DataFrame, ffd_d: float = 0.40) -> pl.DataFrame:
    """
    Calcula el vector de características cuantitativas utilizando expresiones nativas de Polars:
    - Retornos logarítmicos
    - Volatilidad realizada anualizada (20 periodos)
    - HL Spread porcentual
    - Ratio de volumen (RVOL vs media de 20 periodos)
    - FFD del precio de cierre
    """
    df_feat = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1)).log().alias("log_ret"),
        ((pl.col("high") - pl.col("low")) / pl.col("close") * 100.0).alias("hl_spread"),
        (pl.col("volume") / (pl.col("volume").rolling_mean(window_size=20) + 1e-8)).alias("rvol")
    ])

    vol_scale = np.sqrt(365 * 6)
    df_feat = df_feat.with_columns([
        (pl.col("log_ret").rolling_std(window_size=20) * vol_scale).alias("realized_vol_20")
    ])

    ffd_series = frac_diff_ffd_polars(df_feat["close"], d=ffd_d)
    df_feat = df_feat.with_columns(ffd_series.alias("ffd_close"))

    return df_feat


def load_all_futures_pairs_polars(
    data_dir: Path = DEFAULT_DATA_DIR,
    pattern: str = "*4h*futures.feather"
) -> Dict[str, pl.DataFrame]:
    """
    Carga todos los pares de Binance Futures presentes en el directorio utilizando Polars.
    Retorna un diccionario mapeando el nombre del par a su DataFrame de Polars.
    """
    results: Dict[str, pl.DataFrame] = {}
    if not data_dir.exists():
        logger.warning(f"Directorio de datos {data_dir} no existe.")
        return results

    files = list(data_dir.glob(pattern))
    for f in files:
        pair_key = f.stem.replace("-", "_").split("_")[0]
        try:
            df = load_feather_polars(f)
            results[pair_key] = df
        except Exception as e:
            logger.warning(f"Error cargando {f}: {e}")

    return results


def polars_to_pandas(df: pl.DataFrame) -> pd.DataFrame:
    """Convierte un DataFrame de Polars a un DataFrame de Pandas (compatibilidad con Freqtrade)."""
    return df.to_pandas()


def pandas_to_polars(df: pd.DataFrame) -> pl.DataFrame:
    """Convierte un DataFrame de Pandas a Polars con tipado preservado."""
    return pl.from_pandas(df)
