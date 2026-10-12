"""
Módulo de Control de Falsos Descubrimientos y Métricas de Múltiples Ensayos.
Implementa correcciones estadísticas de Benjamini-Hochberg (FDR), Bonferroni (FWER)
y cálculo estricto de Probability of Backtest Overfitting (PBO).

PB-82 y PB-83 (Sprint 23).
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class MultipleTestingAudit:
    """Resultado formal de la auditoría de control de descubrimientos espurios."""
    n_hypotheses: int
    alpha_significance: float
    fdr_threshold: float
    bonferroni_threshold: float
    pbo_estimate: float            # Probabilidad de Sobreajuste en el Backtest
    n_significant_fdr: int
    n_significant_bonferroni: int
    is_institutional_grade: bool   # True si PBO < 0.10 y al menos 1 factor sobrevive a FDR


class MultipleTestingController:
    """
    Controlador estadístico para evitar el autoengaño por minería extensiva de datos.
    Ajusta los p-valores según el número de estrategias ensayadas (Family-Wise Error Rate).
    """

    def __init__(self, target_alpha: float = 0.05):
        self.alpha = float(target_alpha)

    @staticmethod
    def benjamini_hochberg_fdr(p_values: np.ndarray, q: float = 0.05) -> Tuple[np.ndarray, float]:
        """
        Aplica el procedimiento de Benjamini-Hochberg para controlar la False Discovery Rate (FDR).
        Retorna una máscara booleana de hipótesis aceptadas y el umbral crítico p*.
        """
        m = len(p_values)
        if m == 0:
            return np.array([], dtype=bool), 0.0

        p_vals = np.asarray(p_values, dtype=float)
        sorted_indices = np.argsort(p_vals)
        sorted_p = p_vals[sorted_indices]

        # Umbrales críticos de Benjamini-Hochberg: (i / m) * q
        k_values = np.arange(1, m + 1)
        critical_values = (k_values / m) * q

        # Encontrar el mayor k tal que p_(k) <= (k/m)*q
        significant_mask_sorted = sorted_p <= critical_values
        
        if np.any(significant_mask_sorted):
            max_k = np.max(np.where(significant_mask_sorted)[0])
            critical_p = sorted_p[max_k]
        else:
            critical_p = 0.0

        is_significant = p_vals <= critical_p
        return is_significant, critical_p

    @staticmethod
    def bonferroni_fwer(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, float]:
        """
        Aplica la corrección conservadora de Bonferroni para controlar la Family-Wise Error Rate (FWER).
        alpha_ajustado = alpha / m.
        """
        m = len(p_values)
        if m == 0:
            return np.array([], dtype=bool), 0.0

        critical_p = alpha / float(m)
        is_significant = np.asarray(p_values, dtype=float) <= critical_p
        return is_significant, critical_p

    @staticmethod
    def compute_pbo_from_cpcv_matrix(cpcv_performance_matrix: np.ndarray) -> float:
        """
        Calcula la Probabilidad de Sobreajuste en el Backtest (PBO) a partir de una matriz
        de rendimientos CPCV de dimensiones (n_splits, n_modelos).
        
        PBO = Probabilidad de que el mejor modelo en entrenamiento tenga rendimiento
        inferior a la mediana en el conjunto de prueba fuera de muestra.
        """
        matrix = np.asarray(cpcv_performance_matrix, dtype=float)
        n_splits, n_models = matrix.shape
        if n_models < 2 or n_splits < 2:
            return 0.0

        # Para cada partición temporal, rankear modelos
        # Simular pares In-Sample (IS) vs Out-of-Sample (OOS)
        # Dividir los splits en dos mitades (ej. pares e impares)
        is_perf = matrix[::2, :].mean(axis=0)
        oos_perf = matrix[1::2, :].mean(axis=0)

        best_is_model = np.argmax(is_perf)
        # Calcular el rango percentil OOS del mejor modelo IS
        oos_ranks = pd.Series(oos_perf).rank(pct=True).to_numpy()
        rank_of_best = oos_ranks[best_is_model]

        # Si el mejor modelo en IS queda por debajo del percentil 0.50 en OOS, cuenta como sobreajuste
        # Se generaliza sobre permutaciones de splits
        overfit_count = 0
        total_trials = 0

        for i in range(n_splits):
            is_fold = matrix[i, :]
            best_model_idx = np.argmax(is_fold)
            
            # Evaluar en el resto de folds
            other_folds = np.delete(matrix, i, axis=0)
            oos_mean = other_folds.mean(axis=0)
            oos_median = np.median(oos_mean)

            if oos_mean[best_model_idx] < oos_median:
                overfit_count += 1
            total_trials += 1

        pbo = float(overfit_count / max(1, total_trials))
        return float(np.clip(pbo, 0.0, 1.0))

    def audit_mined_hypotheses(
        self,
        p_values: np.ndarray,
        cpcv_matrix: Optional[np.ndarray] = None
    ) -> MultipleTestingAudit:
        """
        Ejecuta la auditoría integral de multiplicidad de pruebas.
        """
        n_hyp = len(p_values)
        fdr_mask, fdr_crit = self.benjamini_hochberg_fdr(p_values, q=self.alpha)
        bonf_mask, bonf_crit = self.bonferroni_fwer(p_values, alpha=self.alpha)

        pbo = 0.0
        if cpcv_matrix is not None and cpcv_matrix.shape[1] >= 2:
            pbo = self.compute_pbo_from_cpcv_matrix(cpcv_matrix)

        is_institutional = (pbo <= 0.10) and (np.sum(fdr_mask) >= 1)

        return MultipleTestingAudit(
            n_hypotheses=n_hyp,
            alpha_significance=self.alpha,
            fdr_threshold=fdr_crit,
            bonferroni_threshold=bonf_crit,
            pbo_estimate=pbo,
            n_significant_fdr=int(np.sum(fdr_mask)),
            n_significant_bonferroni=int(np.sum(bonf_mask)),
            is_institutional_grade=is_institutional
        )
