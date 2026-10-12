"""
Pruebas Unitarias para el Monitor de Salud de Alphas y Detector CUSUM.
Sprint 1: Motor Cuantitativo Auto-Evolutivo (US-1.1 y US-1.2).
"""

import numpy as np
import pandas as pd
import pytest

from portfolio.alpha_health_monitor import (
    AlphaHealthMonitor,
    CUSUMDetector,
    HealthStatus,
    HealthReport,
)


def test_cusum_detector_nominal_and_break():
    np.random.seed(42)
    nominal_series = np.random.normal(0.0, 0.01, 150)
    detector = CUSUMDetector(threshold=4.0, drift_slack=0.5)

    is_break, stat, _, _ = detector.detect_break(nominal_series)
    assert not is_break, f"Serie nominal no debió detonar CUSUM break (stat={stat})"

    # Introducir quiebre estructural abrupto en media y volatilidad
    broken_series = nominal_series.copy()
    broken_series[100:] += 0.08  # Salto de +8% constante
    is_break_flag, stat_break, _, _ = detector.detect_break(broken_series)
    assert is_break_flag, "Serie alterada debió detonar quiebre estructural CUSUM"
    assert stat_break >= 4.0


def test_rolling_ic_computation():
    np.random.seed(101)
    n = 120
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    
    # Señal con fuerte poder predictivo positivo
    returns = np.random.normal(0.0, 0.02, n)
    signal = returns * 0.8 + np.random.normal(0.0, 0.005, n)

    sig_series = pd.Series(signal, index=dates)
    ret_series = pd.Series(returns, index=dates)

    monitor = AlphaHealthMonitor(rolling_window=40)
    rolling_df = monitor.compute_rolling_ic(sig_series, ret_series)

    assert not rolling_df.empty
    assert 'ic' in rolling_df.columns
    assert 'pvalue' in rolling_df.columns
    assert 'ic_ir' in rolling_df.columns
    assert len(rolling_df) == (n - 40 + 1)
    assert rolling_df['ic'].mean() > 0.40, "El IC promedio debe ser fuertemente positivo"


def test_data_drift_ks_test():
    np.random.seed(202)
    base_dist = np.random.normal(0.0, 0.01, 100)
    same_dist = np.random.normal(0.0, 0.01, 100)
    drifted_dist = np.random.normal(0.05, 0.05, 100)

    monitor = AlphaHealthMonitor()
    drift_no, p_val_no = monitor.detect_data_drift(base_dist, same_dist)
    assert not drift_no
    assert p_val_no > 0.05

    drift_yes, p_val_yes = monitor.detect_data_drift(base_dist, drifted_dist)
    assert drift_yes
    assert p_val_yes < 0.05


def test_diagnose_factor_states():
    np.random.seed(303)
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    returns = np.random.normal(0.001, 0.015, n)
    signal_healthy = returns * 0.9 + np.random.normal(0.0, 0.002, n)

    monitor = AlphaHealthMonitor(rolling_window=30, min_healthy_ic=0.05)

    # 1. Estado HEALTHY
    report_healthy = monitor.diagnose_factor(
        factor_id="ALPHA_ALPHA_01",
        signal=pd.Series(signal_healthy, index=dates),
        forward_returns=pd.Series(returns, index=dates)
    )
    assert report_healthy.status == HealthStatus.HEALTHY
    assert report_healthy.rolling_ic > 0.05

    # 2. Estado WARNING_DECAY (ruido sin correlación con retornos)
    noise_signal = np.random.normal(0.0, 1.0, n)
    report_decay = monitor.diagnose_factor(
        factor_id="ALPHA_DECAYED_02",
        signal=pd.Series(noise_signal, index=dates),
        forward_returns=pd.Series(returns, index=dates)
    )
    assert report_decay.status == HealthStatus.WARNING_DECAY

    # 3. Estado CRITICAL_BREAK (quiebre estructural CUSUM en retornos)
    broken_returns = returns.copy()
    broken_returns[70:] += 0.20  # Mega salto anómalo
    report_break = monitor.diagnose_factor(
        factor_id="ALPHA_BROKEN_03",
        signal=pd.Series(signal_healthy, index=dates),
        forward_returns=pd.Series(broken_returns, index=dates)
    )
    assert report_break.status == HealthStatus.CRITICAL_BREAK
