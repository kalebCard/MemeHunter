#!/usr/bin/env python3
"""
tests/test_advanced_metrics.py
Pruebas unitarias para scripts/advanced_metrics.py:
- PSR (Probabilistic Sharpe Ratio)
- DSR (Deflated Sharpe Ratio)
- CPCV (Combinatorial Purged CV)
- PBO (Probability of Backtest Overfitting)
"""

import math
import numpy as np
import pytest
from scripts.advanced_metrics import (
    calculate_moments,
    probabilistic_sharpe_ratio,
    deflated_sharpe_ratio,
    combinatorial_purged_cv,
    calculate_pbo
)


def test_calculate_moments():
    np.random.seed(123)
    data = np.random.normal(0.01, 0.05, 500)
    mean, std, skew, kurt = calculate_moments(data)
    assert abs(mean - 0.01) < 0.01
    assert abs(std - 0.05) < 0.01
    assert abs(skew) < 0.3
    assert abs(kurt) < 0.5


def test_probabilistic_sharpe_ratio_normal():
    # Con Sharpe alto y N grande, PSR debe ser > 0.95
    psr = probabilistic_sharpe_ratio(
        observed_sr=2.0,
        benchmark_sr=0.0,
        n_samples=250,
        skewness=0.0,
        kurtosis=3.0
    )
    assert psr > 0.99

    # Con Sharpe igual al benchmark, PSR debe ser 0.5
    psr_neutral = probabilistic_sharpe_ratio(
        observed_sr=1.0,
        benchmark_sr=1.0,
        n_samples=250,
        skewness=0.0,
        kurtosis=3.0
    )
    assert abs(psr_neutral - 0.5) < 0.01


def test_deflated_sharpe_ratio():
    trials = [0.2, 0.5, 0.8, 1.2, 1.5, 2.1]
    res = deflated_sharpe_ratio(
        observed_sr=2.1,
        all_trials_sr=trials,
        n_samples=300,
        skewness=-0.5,
        kurtosis=4.5
    )
    assert "deflated_sharpe_ratio" in res
    assert res["expected_max_sr"] > 0.0
    assert 0.0 <= res["deflated_sharpe_ratio"] <= 1.0


def test_combinatorial_purged_cv():
    series = np.arange(120)
    partitions = combinatorial_purged_cv(series, n_splits=6, n_test_splits=2, embargo_pct=0.02)
    # 6 choose 2 = 15 particiones
    assert len(partitions) == 15
    for train_idx, test_idx in partitions:
        assert len(test_idx) > 0
        assert len(train_idx) > 0
        # No debe haber intersección entre train y test
        assert len(set(train_idx).intersection(set(test_idx))) == 0


def test_calculate_pbo():
    # Caso 1: Sin overfitting (el mejor de IS rinde bien en OOS)
    is_matrix = np.array([
        [1.5, 0.5, 0.2],
        [1.8, 0.3, 0.1],
        [1.4, 0.6, 0.4]
    ])
    oos_matrix = np.array([
        [1.3, 0.4, 0.1],
        [1.6, 0.2, 0.2],
        [1.2, 0.5, 0.3]
    ])
    res = calculate_pbo(is_matrix, oos_matrix)
    assert res["pbo"] == 0.0
    assert res["is_overfitting_critical"] is False
