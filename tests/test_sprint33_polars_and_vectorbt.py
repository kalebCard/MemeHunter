"""
tests/test_sprint33_polars_and_vectorbt.py
------------------------------------------
Suite de Pruebas Unitarias y de Rendimiento para el Sprint 33:
- PB-115: Ingesta Feather Zero-Copy y Características FFD con Polars (data_engine/polars_feed.py).
- PB-116: Motor de Evaluación Vectorial de Alphas con VectorBT / NumPy (mining/vectorbt_evaluator.py).
"""

import os
import time
import tempfile
import numpy as np
import pandas as pd
import polars as pl
import pytest

from data_engine.polars_feed import (
    load_feather_polars,
    save_feather_polars,
    compute_features_polars,
    frac_diff_ffd_polars,
    polars_to_pandas,
    pandas_to_polars
)
from mining.vectorbt_evaluator import VectorBTEvaluator, VectorizedFactorMetrics


@pytest.fixture
def sample_ohlcv_polars():
    """Genera una serie OHLCV sintética en Polars con 300 velas."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2024-01-01", periods=n, freq="4h")
    close = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.02, n)))
    high = close * (1.0 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1.0 - np.abs(np.random.normal(0, 0.01, n)))
    open_p = close * (1.0 + np.random.normal(0, 0.005, n))
    volume = np.random.lognormal(mean=10, sigma=0.5, size=n)

    df_pd = pd.DataFrame({
        "date": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })
    return pl.from_pandas(df_pd)


# =============================================================================
# PRUEBAS PB-115: POLARS DATA ENGINE & FFD
# =============================================================================

def test_save_and_load_feather_polars(sample_ohlcv_polars):
    """Verifica que Polars guarde y cargue archivos Feather (Arrow IPC) sin pérdidas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = os.path.join(tmpdir, "test_pair_4h_futures.feather")
        save_feather_polars(sample_ohlcv_polars, temp_file)
        assert os.path.exists(temp_file)

        loaded_df = load_feather_polars(temp_file)
        assert isinstance(loaded_df, pl.DataFrame)
        assert loaded_df.shape == sample_ohlcv_polars.shape
        assert "close" in loaded_df.columns
        assert np.isclose(loaded_df["close"][0], sample_ohlcv_polars["close"][0])


def test_compute_features_polars(sample_ohlcv_polars):
    """Verifica el cálculo vectorizado de características en Polars."""
    t0 = time.perf_counter_ns()
    df_feat = compute_features_polars(sample_ohlcv_polars, ffd_d=0.40)
    t_elapsed_ms = (time.perf_counter_ns() - t0) / 1e6

    assert "log_ret" in df_feat.columns
    assert "hl_spread" in df_feat.columns
    assert "rvol" in df_feat.columns
    assert "realized_vol_20" in df_feat.columns
    assert "ffd_close" in df_feat.columns

    # Debe ser sub-milisegundo o extremadamente rápido
    assert t_elapsed_ms < 50.0

    # Comprobar que no todos los valores sean nulos
    assert df_feat["log_ret"].drop_nulls().len() > 250
    assert df_feat["realized_vol_20"].drop_nulls().len() > 250


def test_frac_diff_ffd_polars_short_series():
    """Verifica que FFD maneje longitudes insuficientes de forma segura."""
    short_series = pl.Series("close", [10.0, 11.0, 12.0])
    res = frac_diff_ffd_polars(short_series, d=0.40)
    assert len(res) == 3
    assert res.null_count() == 3


def test_polars_pandas_interop(sample_ohlcv_polars):
    """Verifica la interoperabilidad sin fisuras con Pandas y Freqtrade."""
    pd_df = polars_to_pandas(sample_ohlcv_polars)
    assert isinstance(pd_df, pd.DataFrame)
    assert len(pd_df) == len(sample_ohlcv_polars)

    re_pl = pandas_to_polars(pd_df)
    assert isinstance(re_pl, pl.DataFrame)
    assert re_pl.shape == sample_ohlcv_polars.shape


# =============================================================================
# PRUEBAS PB-116: VECTORBT & EVALUACIÓN VECTORIAL DE ALPHAS
# =============================================================================

def test_vectorbt_evaluator_batch_matrix():
    """Evalúa simultáneamente un lote de 10 factores cuantitativos sobre 250 barras."""
    evaluator = VectorBTEvaluator(use_vbt_if_available=False)  # Test motor NumPy vectorizado

    np.random.seed(42)
    T = 250
    N = 10
    signals = np.random.uniform(-1.0, 1.0, size=(T, N))
    close = 100.0 + np.cumsum(np.random.normal(0, 1.0, size=T))
    forward_returns = np.random.normal(0.001, 0.02, size=T)

    factor_ids = [f"alpha_{i}" for i in range(N)]

    t0 = time.perf_counter_ns()
    metrics = evaluator.evaluate_factor_matrix(
        factor_signals=signals,
        close_prices=close,
        forward_returns=forward_returns,
        factor_ids=factor_ids
    )
    t_eval_ms = (time.perf_counter_ns() - t0) / 1e6

    assert len(metrics) == N
    # Debe ser instantáneo (< 30 ms para 10 factores)
    assert t_eval_ms < 50.0

    for m in metrics:
        assert isinstance(m, VectorizedFactorMetrics)
        assert -1.0 <= m.ic_mean <= 1.0
        assert m.ic_std >= 0.0
        assert isinstance(m.sharpe_proxy, float)
        assert 0.0 <= m.win_rate <= 1.0
        assert m.is_valid is True


def test_vectorbt_evaluator_high_correlation_signal():
    """Verifica que un factor perfectamente correlacionado con los retornos obtenga un IC cercano a 1.0."""
    evaluator = VectorBTEvaluator()

    T = 200
    forward_returns = np.linspace(-0.05, 0.05, T)
    # Señal casi idéntica a los retornos
    signals = forward_returns.reshape(-1, 1) + np.random.normal(0, 0.001, size=(T, 1))
    close = np.full(T, 100.0)

    metrics = evaluator.evaluate_factor_matrix(
        factor_signals=signals,
        close_prices=close,
        forward_returns=forward_returns,
        factor_ids=["perfect_alpha"]
    )

    assert len(metrics) == 1
    assert metrics[0].ic_mean > 0.90  # Spearman IC debe ser muy alto
