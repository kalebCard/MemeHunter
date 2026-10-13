#!/usr/bin/env python3
"""
scripts/fractional_diff.py
--------------------------
Módulo de Diferenciación Fraccionaria (Fractional Differentiation) para Series Financieras.

Implementa:
1. Expansión binomial de Hosking con pesos decrecientes:
   (1 - B)^d = sum_{k=0}^inf (-1)^k * (d choose k) * B^k
2. Ventana de ancho fijo (Fixed-width Window Fractional Differentiation - FFD):
   Descarta pesos con magnitud inferior a un umbral (threshold) para evitar deriva de varianza.
3. Grid Search para encontrar el 'd' mínimo que logra estacionariedad (ADF test p-val < 0.05)
   reteniendo la máxima memoria y correlación (> 90%) con la serie de precios original.

Referencia:
- López de Prado, M. (2018). Advances in Financial Machine Learning, Capítulo 5: Fractional Differentiation.
"""

import math
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional
try:
    from statsmodels.tsa.stattools import adfuller
except ImportError:
    def adfuller(series, maxlag=1, regression='c', autolag=None):
        """
        Fallback autónomo de Dickey-Fuller Aumentado con OLS en NumPy/SciPy
        si statsmodels no está presente en el entorno.
        Δy_t = α + β * y_{t-1} + γ * Δy_{t-1} + ε_t
        """
        import scipy.stats as ss
        y = np.asarray(series, dtype=float)
        n = len(y)
        if n < 20:
            return 0.0, 1.0, 0, n, {}, 0.0
        dy = np.diff(y)
        dy_lag = dy[:-1]
        y_lag = y[1:-1]
        dy_curr = dy[1:]
        X = np.column_stack([np.ones_like(y_lag), y_lag, dy_lag])
        coeffs, residuals, rank, s = np.linalg.lstsq(X, dy_curr, rcond=None)
        beta = coeffs[1]
        res = dy_curr - X @ coeffs
        dof = len(dy_curr) - X.shape[1]
        sigma2 = np.sum(res**2) / dof
        inv_XTX = np.linalg.inv(X.T @ X)
        se_beta = np.sqrt(sigma2 * inv_XTX[1, 1])
        t_stat = float(beta / se_beta) if se_beta > 0 else 0.0
        # Valores críticos de MacKinnon para constante: 1%: -3.43, 5%: -2.86, 10%: -2.57
        if t_stat <= -3.43:
            p_val = 0.005
        elif t_stat <= -2.86:
            p_val = 0.040
        elif t_stat <= -2.57:
            p_val = 0.090
        else:
            p_val = 0.400
        return t_stat, p_val, 1, len(dy_curr), {'1%': -3.43, '5%': -2.86, '10%': -2.57}, 0.0


def get_weights_ffd(d: float, threshold: float = 1e-4, max_lags: int = 1000) -> np.ndarray:
    """
    Calcula los pesos de diferenciación fraccionaria FFD mediante expansión binomial
    hasta que el peso absoluto cae por debajo de threshold o alcanza max_lags.
    
    w_0 = 1
    w_k = -w_{k-1} / k * (d - k + 1)
    """
    weights = [1.0]
    k = 1
    while k < max_lags:
        w_k = -weights[-1] / k * (d - k + 1)
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
        k += 1
    return np.array(weights[::-1])  # Invertir para aplicar como convolución temporal


def frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-4) -> pd.Series:
    """
    Aplica diferenciación fraccionaria con ventana de ancho fijo (FFD) a una serie temporal.
    
    Retorna pd.Series con los valores diferenciados fraccionariamente.
    Los primeros lags donde no hay suficiente ventana se completan con NaN.
    """
    weights = get_weights_ffd(d, threshold=threshold)
    width = len(weights)
    
    values = series.values
    n = len(values)
    
    if n < width:
        # Longitud insuficiente
        return pd.Series(np.nan, index=series.index)
    
    # Convolución lineal directa
    diff_values = np.full(n, np.nan)
    for i in range(width - 1, n):
        window = values[i - width + 1 : i + 1]
        diff_values[i] = np.dot(weights, window)
        
    return pd.Series(diff_values, index=series.index)


def find_optimal_d(
    series: pd.Series,
    d_range: Tuple[float, float] = (0.0, 1.0),
    step: float = 0.05,
    threshold: float = 1e-4,
    significance_level: float = 0.05
) -> Dict[str, Any]:
    """
    Ejecuta un barrido de búsqueda (Grid Search) para encontrar el d óptimo:
    El valor mínimo de d que rechaza la hipótesis nula de raíz unitaria (ADF p-value < significance_level),
    preservando la máxima memoria histórica y correlación con la serie original.
    """
    d_values = np.arange(d_range[0], d_range[1] + step, step)
    results = []
    
    clean_series = series.dropna()
    
    for d in d_values:
        d = round(float(d), 3)
        if d == 0.0:
            diff = clean_series
        else:
            diff = frac_diff_ffd(clean_series, d=d, threshold=threshold).dropna()
            
        if len(diff) < 30:
            continue
            
        # ADF Test
        try:
            adf_stat, p_val, _, _, _, _ = adfuller(diff, maxlag=1, regression='c', autolag=None)
        except Exception:
            adf_stat, p_val = 0.0, 1.0
            
        # Correlación de Pearson con la serie original alineada
        aligned_orig = clean_series.loc[diff.index]
        corr = float(diff.corr(aligned_orig)) if len(diff) > 1 else 0.0
        
        is_stationary = bool(p_val < significance_level)
        results.append({
            "d": d,
            "adf_stat": float(adf_stat),
            "p_val": float(p_val),
            "correlation": corr,
            "is_stationary": is_stationary
        })
    
    df_res = pd.DataFrame(results)
    
    # Buscar el primer d donde is_stationary == True
    stationary_subset = df_res[df_res["is_stationary"] == True]
    if not stationary_subset.empty:
        optimal_row = stationary_subset.iloc[0]
        optimal_d = float(optimal_row["d"])
        optimal_corr = float(optimal_row["correlation"])
        optimal_pval = float(optimal_row["p_val"])
    else:
        # Si ninguno fue estacionario en el rango, tomar d=1.0 estándar
        optimal_d = 1.0
        optimal_corr = float(df_res.iloc[-1]["correlation"]) if not df_res.empty else 0.0
        optimal_pval = float(df_res.iloc[-1]["p_val"]) if not df_res.empty else 1.0
        
    return {
        "optimal_d": optimal_d,
        "correlation_retained": optimal_corr,
        "adf_p_value": optimal_pval,
        "full_grid": results
    }


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 EJECUCIÓN DEMOSTRATIVA DE FRAC_DIFF (MEMORIA ESTACIONARIA)")
    print("=" * 70)
    
    # Generar paseo aleatorio con tendencia (tipo precio cripto no estacionario)
    np.random.seed(42)
    steps = np.random.normal(0.0005, 0.02, 1000)
    prices = 100.0 * np.exp(np.cumsum(steps))
    ts = pd.Series(prices)
    
    print(f"Longitud de la serie: {len(ts)} velas")
    
    # Test ADF en serie original (d=0)
    adf_orig = adfuller(ts, maxlag=1, regression='c', autolag=None)
    print(f"Serie Original (d=0.0): ADF p-val = {adf_orig[1]:.4f} (¿Estacionaria?: {adf_orig[1] < 0.05})")
    
    # Buscar d óptimo
    opt = find_optimal_d(ts, d_range=(0.0, 1.0), step=0.1)
    print(f"\n🎯 Resultado de Optimización:")
    print(f"   d Óptimo Mínimo: {opt['optimal_d']:.2f}")
    print(f"   ADF p-value: {opt['adf_p_value']:.4e}")
    print(f"   Correlación retenida con precio original: {opt['correlation_retained']*100:.2f}%")
    print(f"   (Frente al retorno de primer orden d=1.0 que retiene sólo ~0-5% de memoria)")
