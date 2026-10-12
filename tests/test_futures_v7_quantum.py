"""
tests/test_futures_v7_quantum.py - Tests unitarios para MemeHunterFuturesV7_Quantum (PB-74).
"""

import numpy as np
import pandas as pd
import pytest

from user_data.strategies.MemeHunterFuturesV7_Quantum import (
    calculate_ffd_approx,
    continuous_leverage_calc
)


def test_continuous_leverage_calc():
    # Convicción nula o muy baja -> apalancamiento mínimo 1.0x
    lev_low = continuous_leverage_calc(0.0, min_lev=1.0, max_lev=2.0)
    assert lev_low == 1.0

    # Convicción media -> apalancamiento intermedio
    lev_mid = continuous_leverage_calc(0.55, min_lev=1.0, max_lev=2.0)
    assert 1.2 <= lev_mid <= 1.6

    # Convicción alta -> apalancamiento elevado
    lev_high = continuous_leverage_calc(0.90, min_lev=1.0, max_lev=2.0)
    assert 1.6 <= lev_high <= 2.0

    # Monotonía: a mayor convicción, mayor o igual apalancamiento
    assert lev_low <= lev_mid <= lev_high


def test_calculate_ffd_approx():
    np.random.seed(42)
    prices = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.02, 100)))
    ffd = calculate_ffd_approx(prices, d=0.40, lags=20)
    assert len(ffd) == len(prices)
    # Los últimos puntos deben ser valores finitos reales
    assert not np.isnan(ffd[-1])
    assert not np.isnan(ffd[-10])
