#!/usr/bin/env python3
"""
tests/test_triple_barrier_metalabeling.py
Pruebas unitarias para scripts/triple_barrier_metalabeling.py:
- get_daily_volatility
- apply_triple_barrier
- continuous_bet_sizing
"""

import numpy as np
import pandas as pd
import pytest
from scripts.triple_barrier_metalabeling import (
    get_daily_volatility,
    apply_triple_barrier,
    continuous_bet_sizing
)


def test_get_daily_volatility():
    prices = pd.Series([100, 102, 101, 105, 103, 108, 107], dtype=float)
    vol = get_daily_volatility(prices, span=3)
    assert len(vol) == len(prices)
    assert not np.isnan(vol.iloc[-1])
    assert vol.iloc[-1] > 0


def test_apply_triple_barrier():
    dates = pd.date_range("2024-01-01", periods=60, freq="4h")
    # Serie en caída libre (beneficia al Short)
    prices = pd.Series(np.linspace(100, 70, 60), index=dates)
    events = dates[[5, 15, 25]]
    
    tb_df = apply_triple_barrier(prices, events_idx=events, pt_sl=(1.0, 1.0), max_holding_periods=10)
    assert len(tb_df) == 3
    assert "barrier_hit" in tb_df.columns
    assert "return" in tb_df.columns
    assert "meta_label" in tb_df.columns
    # Como los precios caen, los shorts deben ganar (meta_label=1)
    assert (tb_df["meta_label"] == 1).all()


def test_continuous_bet_sizing():
    # Probabilidad por debajo del umbral debe retornar 0.0 (no operar)
    assert continuous_bet_sizing(0.50, min_prob_threshold=0.52) == 0.0
    assert continuous_bet_sizing(0.40, min_prob_threshold=0.52) == 0.0
    
    # Probabilidad media-alta debe escalar continuamente entre min y max leverage
    lev_55 = continuous_bet_sizing(0.55, min_prob_threshold=0.52, max_leverage=2.0, min_leverage=1.0)
    lev_75 = continuous_bet_sizing(0.75, min_prob_threshold=0.52, max_leverage=2.0, min_leverage=1.0)
    
    assert 1.0 <= lev_55 <= lev_75 <= 2.0
