#!/usr/bin/env python3
"""
scripts/advanced_metrics.py
---------------------------
Suite de Métricas Cuantitativas Avanzadas y Detección de Falsos Descubrimientos:
1. Probabilistic Sharpe Ratio (PSR) con ajuste por asimetría (skewness) y curtosis (kurtosis).
2. Deflated Sharpe Ratio (DSR) de Marcos López de Prado para corrección de pruebas múltiples.
3. Combinatorial Purged Cross-Validation (CPCV) y Probability of Backtest Overfitting (PBO).

Referencias:
- Bailey, D. H., & López de Prado, M. (2012). The Sharpe Ratio Efficient Frontier.
- Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
"""

import math
import numpy as np
import scipy.stats as ss
from typing import Dict, Any, List, Tuple, Optional


def calculate_moments(returns: np.ndarray) -> Tuple[float, float, float, float]:
    """
    Calcula los 4 momentos estadísticos de una serie de retornos:
    media, desviación estándar, asimetría (skewness) y curtosis (Fisher kurtosis donde normal=0).
    """
    clean_returns = returns[~np.isnan(returns)]
    if len(clean_returns) < 2:
        return 0.0, 0.0, 0.0, 0.0

    mean = float(np.mean(clean_returns))
    std = float(np.std(clean_returns, ddof=1))
    if std == 0.0:
        return mean, 0.0, 0.0, 0.0

    skew = float(ss.skew(clean_returns, bias=False))
    # kurtosis de scipy: Fisher kurtosis (normal = 0.0)
    kurt = float(ss.kurtosis(clean_returns, bias=False))
    return mean, std, skew, kurt


def probabilistic_sharpe_ratio(
    observed_sr: float,
    benchmark_sr: float = 0.0,
    n_samples: int = 100,
    skewness: float = 0.0,
    kurtosis: float = 3.0  # Pearson kurtosis (normal = 3.0)
) -> float:
    """
    Calcula el Probabilistic Sharpe Ratio (PSR).
    
    Estima la probabilidad de que el Sharpe Ratio verdadero sea superior a benchmark_sr,
    corrigiendo el error estándar según la asimetría y la curtosis de la serie.
    
    PSR(SR*) = Z[ (SR - SR*) * sqrt(T - 1) / sqrt(1 - skew * SR + (kurt - 1)/4 * SR^2) ]
    
    Nota: kurtosis aquí es el cuarto momento no centrado estandarizado (Pearson: normal = 3.0).
    """
    if n_samples <= 1:
        return 0.5

    # Si se pasa curtosis de Fisher (donde normal=0), convertir a Pearson
    pearson_kurt = kurtosis if kurtosis > 1.0 else kurtosis + 3.0

    denom_sq = 1.0 - skewness * observed_sr + ((pearson_kurt - 1.0) / 4.0) * (observed_sr ** 2)
    if denom_sq <= 1e-8:
        denom_sq = 1e-8

    se_sr = math.sqrt(denom_sq / (n_samples - 1))
    z_stat = (observed_sr - benchmark_sr) / se_sr
    psr = float(ss.norm.cdf(z_stat))
    return psr


def deflated_sharpe_ratio(
    observed_sr: float,
    all_trials_sr: List[float],
    n_samples: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0
) -> Dict[str, Any]:
    """
    Calcula el Deflated Sharpe Ratio (DSR) de López de Prado.
    
    Ajusta el Sharpe Ratio por sesgo de selección y pruebas múltiples (Data Snooping),
    descontando el número total de variantes exploradas N y la varianza entre ellas V[SR].
    
    E[max(SR_n)] ~= sqrt(V[SR_n]) * ((1 - gamma)*Z^-1(1 - 1/N) + gamma*Z^-1(1 - 1/(N*e)))
    donde gamma ~= 0.5772156649 (constante de Euler-Mascheroni).
    """
    trials = np.array(all_trials_sr, dtype=float)
    n_trials = len(trials)
    if n_trials <= 1:
        # Sin pruebas múltiples, el benchmark esperado es 0
        expected_max_sr = 0.0
        var_sr = 0.0
    else:
        var_sr = float(np.var(trials, ddof=1))
        std_sr = math.sqrt(var_sr) if var_sr > 0 else 0.0
        
        euler_mascheroni = 0.5772156649
        z_term1 = float(ss.norm.ppf(1.0 - 1.0 / n_trials)) if n_trials > 1 else 0.0
        z_term2 = float(ss.norm.ppf(1.0 - 1.0 / (n_trials * math.e))) if n_trials > 1 else 0.0
        
        expected_max_sr = std_sr * ((1.0 - euler_mascheroni) * z_term1 + euler_mascheroni * z_term2)

    dsr = probabilistic_sharpe_ratio(
        observed_sr=observed_sr,
        benchmark_sr=expected_max_sr,
        n_samples=n_samples,
        skewness=skewness,
        kurtosis=kurtosis
    )

    return {
        "observed_sr": float(observed_sr),
        "expected_max_sr": float(expected_max_sr),
        "n_trials": n_trials,
        "n_samples": n_samples,
        "var_trials": float(var_sr),
        "deflated_sharpe_ratio": float(dsr),
        "is_statistically_significant_95": bool(dsr >= 0.95),
        "is_statistically_significant_99": bool(dsr >= 0.99)
    }


def combinatorial_purged_cv(
    returns_series: np.ndarray,
    n_splits: int = 6,
    n_test_splits: int = 2,
    embargo_pct: float = 0.01
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Genera particiones para Combinatorial Purged Cross-Validation (CPCV).
    
    Divide los datos en n_splits bloques temporales contiguos y toma combinaciones
    de n_test_splits como conjuntos de test.
    Aplica Purging (elimina solapamientos en train) y Embargo (cuarentena post-test).
    """
    from itertools import combinations
    
    n_samples = len(returns_series)
    split_size = n_samples // n_splits
    splits = []
    for i in range(n_splits):
        start = i * split_size
        end = n_samples if i == n_splits - 1 else (i + 1) * split_size
        splits.append((start, end))

    embargo_samples = int(n_samples * embargo_pct)
    cv_partitions = []

    for test_split_indices in combinations(range(n_splits), n_test_splits):
        test_mask = np.zeros(n_samples, dtype=bool)
        embargo_mask = np.zeros(n_samples, dtype=bool)

        for idx in test_split_indices:
            start, end = splits[idx]
            test_mask[start:end] = True
            # Embargo al final del tramo de test
            embargo_end = min(n_samples, end + embargo_samples)
            embargo_mask[end:embargo_end] = True

        train_mask = ~(test_mask | embargo_mask)
        train_indices = np.where(train_mask)[0]
        test_indices = np.where(test_mask)[0]
        
        cv_partitions.append((train_indices, test_indices))

    return cv_partitions


def calculate_pbo(
    performance_matrix_is: np.ndarray,
    performance_matrix_oos: np.ndarray
) -> Dict[str, Any]:
    """
    Calcula la Probability of Backtest Overfitting (PBO) mediante combinaciones CSCV/CPCV.
    
    performance_matrix_is: Matriz (N_particiones, N_estrategias) con métrica In-Sample.
    performance_matrix_oos: Matriz (N_particiones, N_estrategias) con métrica Out-of-Sample.
    
    PBO es la proporción de veces que la estrategia que fue 'ganadora absoluta' en IS
    terminó rindiendo por debajo de la mediana del universo en OOS.
    """
    n_partitions, n_strategies = performance_matrix_is.shape
    below_median_count = 0
    relative_ranks_oos = []

    for p in range(n_partitions):
        best_is_idx = int(np.argmax(performance_matrix_is[p, :]))
        oos_scores = performance_matrix_oos[p, :]
        median_oos = float(np.median(oos_scores))
        
        if oos_scores[best_is_idx] < median_oos:
            below_median_count += 1
            
        # Calcular rango percentil de la estrategia elegida en OOS (0=peor, 1=mejor)
        rank = float(np.mean(oos_scores <= oos_scores[best_is_idx]))
        relative_ranks_oos.append(rank)

    pbo = float(below_median_count / n_partitions) if n_partitions > 0 else 0.0

    return {
        "pbo": pbo,
        "n_partitions": n_partitions,
        "n_strategies": n_strategies,
        "mean_oos_rank_of_best_is": float(np.mean(relative_ranks_oos)) if relative_ranks_oos else 0.5,
        "is_overfitting_critical": bool(pbo > 0.50),
        "is_acceptable": bool(pbo < 0.25)
    }


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 EJECUCIÓN DEMOSTRATIVA DE ADVANCED_METRICS (PSR, DSR & CPCV)")
    print("=" * 70)
    
    # Simulación de retornos tipo memecoin con curtosis pesada y asimetría
    np.random.seed(42)
    sim_returns = np.random.normal(0.005, 0.04, 300)
    # Inyectar cola pesada
    sim_returns[:10] = np.random.uniform(-0.15, -0.05, 10)
    
    mean, std, skew, kurt = calculate_moments(sim_returns)
    observed_sr = (mean / std) * math.sqrt(365 * 6) if std > 0 else 0.0  # Anualizado velas 4h
    
    print(f"Momentos: Media={mean:.4f}, Std={std:.4f}, Skew={skew:.3f}, Kurtosis (Fisher)={kurt:.3f}")
    print(f"Sharpe Anualizado Observado: {observed_sr:.2f}")
    
    # 1. PSR contra Benchmark de 0.0 y contra 1.0
    psr_0 = probabilistic_sharpe_ratio(observed_sr=observed_sr, benchmark_sr=0.0, n_samples=len(sim_returns), skewness=skew, kurtosis=kurt+3.0)
    psr_1 = probabilistic_sharpe_ratio(observed_sr=observed_sr, benchmark_sr=1.0, n_samples=len(sim_returns), skewness=skew, kurtosis=kurt+3.0)
    print(f"\n📊 Probabilistic Sharpe Ratio (PSR > 0.0): {psr_0*100:.2f}%")
    print(f"📊 Probabilistic Sharpe Ratio (PSR > 1.0): {psr_1*100:.2f}%")
    
    # 2. DSR simulando 6 versiones previas (V1 a V6) con diferentes Sharpes
    historical_sharpes = [0.45, 0.85, 1.10, 1.45, 1.73, observed_sr]
    dsr_res = deflated_sharpe_ratio(
        observed_sr=observed_sr,
        all_trials_sr=historical_sharpes,
        n_samples=len(sim_returns),
        skewness=skew,
        kurtosis=kurt+3.0
    )
    print(f"\n🔬 Deflated Sharpe Ratio (DSR) tras {dsr_res['n_trials']} ensayos:")
    print(f"   Benchmark Esperado por Minería E[max(SR)]: {dsr_res['expected_max_sr']:.2f}")
    print(f"   DSR: {dsr_res['deflated_sharpe_ratio']*100:.2f}%")
    print(f"   ¿Significativo al 95%?: {dsr_res['is_statistically_significant_95']}")
