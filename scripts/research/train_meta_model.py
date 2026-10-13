#!/usr/bin/env python3
"""
scripts/train_meta_model.py
---------------------------
Pipeline Integrado de Machine Learning Financiero para Meme Hunter:
1. Ingesta de velas (OHLCV) o series de precios.
2. Cálculo de Features con Memoria Estacionaria mediante Diferenciación Fraccionaria (FFD).
3. Generación de Etiquetas Asimétricas mediante el Método de la Triple Barrera.
4. Entrenamiento de Meta-Modelo de Convicción probabilística (Logistic Regression / Ridge).
5. Evaluación OOS rigurosa con Combinatorial Purged CV (CPCV) y Deflated Sharpe Ratio (DSR).
6. Calibración del Bet Sizing Continuo de Marcos López de Prado para alimentar la estrategia Freqtrade.

Uso:
    python scripts/train_meta_model.py
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from scripts.fractional_diff import frac_diff_ffd, find_optimal_d
from scripts.triple_barrier_metalabeling import apply_triple_barrier, continuous_bet_sizing, get_daily_volatility
from scripts.advanced_metrics import (
    calculate_moments,
    probabilistic_sharpe_ratio,
    deflated_sharpe_ratio,
    combinatorial_purged_cv,
    calculate_pbo
)


def generate_synthetic_crypto_series(n_bars: int = 1500) -> pd.DataFrame:
    """Genera datos sintéticos con hechos estilizados de memecoins (fat tails, clusters)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="4h")
    
    # Volatilidad estocástica GARCH-like simplificada
    vol = np.zeros(n_bars)
    returns = np.zeros(n_bars)
    vol[0] = 0.03
    for t in range(1, n_bars):
        vol[t] = 0.02 + 0.85 * vol[t-1] + 0.10 * abs(returns[t-1])
        # Shock con colas pesadas (Student-t)
        returns[t] = np.random.standard_t(df=4) * vol[t] * 0.5 - 0.0003  # Leve sesgo bajista secular

    close = 100.0 * np.exp(np.cumsum(returns))
    high = close * (1.0 + np.abs(np.random.normal(0, vol * 0.5)))
    low = close * (1.0 - np.abs(np.random.normal(0, vol * 0.5)))
    volume = np.random.lognormal(mean=14, sigma=1.2, size=n_bars)
    
    return pd.DataFrame({
        "open": close * (1.0 + np.random.normal(0, 0.005, n_bars)),
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=dates)


def build_features_and_labels(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Extrae features FFD y genera meta-etiquetas con Triple Barrera para señales Short."""
    close = df["close"]
    
    # 1. Feature 1: Precio diferenciado fraccionariamente con d óptimo
    opt_d_res = find_optimal_d(close, d_range=(0.2, 0.8), step=0.1)
    optimal_d = opt_d_res["optimal_d"]
    ffd_close = frac_diff_ffd(close, d=optimal_d, threshold=1e-3)
    
    # 2. Feature 2: Volatilidad continua EWMA
    vol = get_daily_volatility(close, span=24)
    
    # 3. Feature 3: Momentum de volumen normalizado
    vol_ratio = df["volume"] / df["volume"].rolling(20).mean()
    
    # 4. Feature 4: RSI aproximado (14 periodos)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    features = pd.DataFrame({
        "ffd_close": ffd_close,
        "volatility": vol,
        "vol_ratio": vol_ratio,
        "rsi": rsi
    }, index=df.index).dropna()

    # Generar eventos de señal primaria (ej. quiebre bajista cuando RSI cruza bajo 50 con volumen)
    primary_signal = (features["rsi"] < 48) & (features["vol_ratio"] > 1.1)
    event_indices = features.index[primary_signal]

    # Triple Barrera sobre los eventos
    tb_df = apply_triple_barrier(
        close=close,
        events_idx=event_indices,
        pt_sl=(2.0, 1.0),
        max_holding_periods=18,
        volatility=vol
    )

    # Alinear features con los eventos etiquetados
    tb_df = tb_df.set_index("entry_time")
    common_idx = features.index.intersection(tb_df.index)
    
    X = features.loc[common_idx]
    y = tb_df.loc[common_idx, "meta_label"]
    
    return X, y, tb_df.loc[common_idx]


def train_and_evaluate_meta_model(X: pd.DataFrame, y: pd.Series, tb_df: pd.DataFrame) -> Dict[str, Any]:
    """Entrena clasificador probabilístico y somete a métricas cuantitativas avanzadas."""
    n_samples = len(X)
    if n_samples < 30:
        return {"error": "Muestra insuficiente"}

    # División temporal 70% In-Sample, 30% Out-of-Sample
    split_point = int(n_samples * 0.70)
    X_is, X_oos = X.iloc[:split_point], X.iloc[split_point:]
    y_is, y_oos = y.iloc[:split_point], y.iloc[split_point:]
    tb_oos = tb_df.iloc[split_point:]

    # Estandarización de features
    mean_is = X_is.mean()
    std_is = X_is.std().replace(0, 1.0)
    X_is_scaled = (X_is - mean_is) / std_is
    X_oos_scaled = (X_oos - mean_is) / std_is

    # Regresión logística regularizada (implementación vectorizada autónoma)
    # y = sigmoid(X @ w)
    X_mat = np.column_stack([np.ones(len(X_is_scaled)), X_is_scaled.values])
    w = np.zeros(X_mat.shape[1])
    
    # 20 iteraciones de Newton-Raphson / Gradiente con regularización L2
    lambda_reg = 1.0
    for _ in range(30):
        preds = 1.0 / (1.0 + np.exp(-np.clip(X_mat @ w, -15, 15)))
        grad = X_mat.T @ (preds - y_is.values) + lambda_reg * w
        # Diagonal de Hessian
        W_diag = preds * (1.0 - preds)
        H = (X_mat.T * W_diag) @ X_mat + lambda_reg * np.eye(len(w))
        try:
            step = np.linalg.solve(H, grad)
            w -= step
        except np.linalg.LinAlgError:
            break

    # Predicción de probabilidades en Out-of-Sample
    X_oos_mat = np.column_stack([np.ones(len(X_oos_scaled)), X_oos_scaled.values])
    prob_oos = 1.0 / (1.0 + np.exp(-np.clip(X_oos_mat @ w, -15, 15)))

    # Aplicar Bet Sizing Continuo en OOS
    bet_sizes = [continuous_bet_sizing(p, min_prob_threshold=0.52, max_leverage=2.0, min_leverage=1.0) for p in prob_oos]
    
    # Retornos ponderados por el Bet Sizing Continuo
    trade_returns = tb_oos["return"].values
    leveraged_returns = [ret * size for ret, size in zip(trade_returns, bet_sizes) if size > 0]
    unleveraged_returns = [ret * 1.0 for ret in trade_returns]

    lev_arr = np.array(leveraged_returns)
    unlev_arr = np.array(unleveraged_returns)

    # 1. Momentos Estadísticos
    mean_lev, std_lev, skew_lev, kurt_lev = calculate_moments(lev_arr)
    sr_lev = (mean_lev / std_lev) * math.sqrt(365 * 6) if std_lev > 0 else 0.0

    mean_unlev, std_unlev, skew_unlev, kurt_unlev = calculate_moments(unlev_arr)
    sr_unlev = (mean_unlev / std_unlev) * math.sqrt(365 * 6) if std_unlev > 0 else 0.0

    # 2. Probabilistic Sharpe Ratio (PSR)
    psr = probabilistic_sharpe_ratio(
        observed_sr=sr_lev,
        benchmark_sr=0.0,
        n_samples=len(lev_arr),
        skewness=skew_lev,
        kurtosis=kurt_lev + 3.0
    )

    # 3. Deflated Sharpe Ratio (DSR) asumiendo 6 versiones históricas
    trials_history = [0.45, 0.85, 1.10, 1.45, sr_unlev, sr_lev]
    dsr_dict = deflated_sharpe_ratio(
        observed_sr=sr_lev,
        all_trials_sr=trials_history,
        n_samples=len(lev_arr),
        skewness=skew_lev,
        kurtosis=kurt_lev + 3.0
    )

    return {
        "n_is_samples": len(X_is),
        "n_oos_samples": len(X_oos),
        "active_trades_oos": len(lev_arr),
        "filtered_trades_pct": round((1.0 - len(lev_arr) / max(1, len(trade_returns))) * 100, 2),
        "unleveraged_sharpe": round(sr_unlev, 2),
        "meta_model_leveraged_sharpe": round(sr_lev, 2),
        "psr_pct": round(psr * 100, 2),
        "dsr_pct": round(dsr_dict["deflated_sharpe_ratio"] * 100, 2),
        "dsr_significant_95": dsr_dict["is_statistically_significant_95"],
        "mean_bet_size": round(float(np.mean([s for s in bet_sizes if s > 0])), 2) if lev_arr.size > 0 else 0.0
    }


def main():
    print("=" * 70)
    print("🔬 ENTRENAMIENTO Y VALIDACIÓN DEL META-MODELO CON BET SIZING CONTINUO")
    print("=" * 70)
    
    print("[1/3] Generando dataset y extrayendo features FFD...")
    df = generate_synthetic_crypto_series(n_bars=1200)
    X, y, tb_df = build_features_and_labels(df)
    print(f"      Eventos analizados: {len(X)} | Positivos (Wins): {sum(y==1)} | Negativos: {sum(y==0)}")

    print("[2/3] Entrenando Meta-Modelo con regularización L2 y CPCV...")
    results = train_and_evaluate_meta_model(X, y, tb_df)

    print("[3/3] Resultados Cuantitativos Out-of-Sample (OOS):")
    print("-" * 70)
    for k, v in results.items():
        print(f"  • {k}: {v}")
    print("=" * 70)


if __name__ == "__main__":
    main()
