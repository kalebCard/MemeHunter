#!/usr/bin/env python3
"""
tests/test_fractional_diff.py
Pruebas unitarias para scripts/fractional_diff.py:
- get_weights_ffd
- frac_diff_ffd
- find_optimal_d
"""

import numpy as np
import pandas as pd
import pytest
from scripts.research.fractional_diff import get_weights_ffd, frac_diff_ffd, find_optimal_d


def test_get_weights_ffd():
    weights = get_weights_ffd(d=0.5, threshold=1e-3, max_lags=100)
    assert len(weights) > 1
    # El primer elemento convolucionado (más reciente) es 1.0
    assert abs(weights[-1] - 1.0) < 1e-6
    # Los pesos deben decaer en magnitud absoluta
    assert abs(weights[0]) < 1e-2


def test_frac_diff_ffd():
    np.random.seed(42)
    series = pd.Series(np.cumsum(np.random.normal(0, 1, 150)))
    diff = frac_diff_ffd(series, d=0.4, threshold=1e-3)
    assert len(diff) == len(series)
    # Debe haber algunos NaNs al inicio debido al ancho de ventana
    valid_diff = diff.dropna()
    assert len(valid_diff) > 50


def test_find_optimal_d():
    np.random.seed(42)
    # Serie no estacionaria
    series = pd.Series(100.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 200))))
    opt = find_optimal_d(series, d_range=(0.0, 1.0), step=0.2)
    assert "optimal_d" in opt
    assert 0.0 <= opt["optimal_d"] <= 1.0
    assert "correlation_retained" in opt
    assert "adf_p_value" in opt
