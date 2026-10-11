"""Tests sin red para scripts/regime_classifier.py."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import regime_classifier as rc  # noqa: E402


def test_classify_current_regime_bull_momentum():
    row = pd.Series({
        "close": 115.0,
        "ema_50": 105.0,
        "ema_200": 100.0,
        "ema_dispersion_pct": 15.0,  # > 2.0%
        "natr_14": 3.0,
        "vol_ratio": 1.5,            # >= 1.0
    })
    assert rc.classify_current_regime(row) == rc.REGIME_BULL_MOMENTUM
    rec = rc.get_regime_recommendation(rc.REGIME_BULL_MOMENTUM)
    assert "EXPANCION ALCISTA" in rec["mode"]


def test_classify_current_regime_bear_bleed():
    row = pd.Series({
        "close": 85.0,
        "ema_50": 95.0,
        "ema_200": 100.0,
        "ema_dispersion_pct": -15.0,  # < -2.0%
        "natr_14": 4.0,
        "vol_ratio": 0.8,
    })
    assert rc.classify_current_regime(row) == rc.REGIME_BEAR_BLEED
    rec = rc.get_regime_recommendation(rc.REGIME_BEAR_BLEED)
    assert "INVIERNO" in rec["mode"]


def test_classify_current_regime_choppy_range():
    # Precio oscilando alrededor de la EMA 200 sin tendencia clara
    row = pd.Series({
        "close": 100.5,
        "ema_50": 100.2,
        "ema_200": 100.0,
        "ema_dispersion_pct": 0.5,   # Entre -2.0% y +2.0%
        "natr_14": 1.5,
        "vol_ratio": 0.7,
    })
    assert rc.classify_current_regime(row) == rc.REGIME_CHOPPY_RANGE
    rec = rc.get_regime_recommendation(rc.REGIME_CHOPPY_RANGE)
    assert "RANGO LATERAL" in rec["mode"]
    assert "0.0x" in rec["risk_multiplier"]


def test_compute_regime_features():
    dates = pd.date_range("2026-01-01", periods=50, freq="4h")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": np.linspace(100, 150, 50),
        "high": np.linspace(102, 152, 50),
        "low": np.linspace(98, 148, 50),
        "close": np.linspace(100, 150, 50),
        "volume": [1000.0] * 50,
    })
    res = rc.compute_regime_features(df)
    assert "ema_50" in res.columns
    assert "ema_200" in res.columns
    assert "ema_dispersion_pct" in res.columns
    assert "natr_14" in res.columns
