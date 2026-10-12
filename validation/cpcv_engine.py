"""
Módulo de Combinatorial Purged Cross-Validation (CPCV) Industrial.
Implementa el algoritmo de validación cruzada combinatoria purgada con embargo temporal
propuesto por Marcos López de Prado en 'Advances in Financial Machine Learning' (Capítulo 12).

PB-81 (Sprint 23).
"""

from dataclasses import dataclass
from typing import List, Tuple, Generator, Optional
import itertools
import numpy as np
import pandas as pd


@dataclass
class CPCVSplit:
    """Representa una partición individual del ensamble CPCV."""
    split_id: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    test_groups: Tuple[int, ...]


class CPCVEngine:
    """
    Generador y evaluador de Combinatorial Purged Cross-Validation.
    Divide la serie temporal en N grupos y genera C(N, k) combinaciones de prueba.
    Aplica purga de solapamiento de eventos y cuarentena (embargo) temporal.
    """

    def __init__(
        self,
        n_splits: int = 6,
        n_test_splits: int = 2,
        embargo_pct: float = 0.01,
        purge_window_bars: int = 2
    ):
        """
        :param n_splits: Número total de grupos temporales (N).
        :param n_test_splits: Número de grupos tomados para evaluación fuera de muestra (k).
        :param embargo_pct: Porcentaje de la muestra aplicado como cuarentena post-test.
        :param purge_window_bars: Barras de solapamiento purgadas alrededor del set de test.
        """
        self.n_splits = int(n_splits)
        self.n_test_splits = int(n_test_splits)
        self.embargo_pct = float(embargo_pct)
        self.purge_window = int(purge_window_bars)

    @property
    def total_combinations(self) -> int:
        """Calcula el número de caminos de backtest C(N, k)."""
        import math
        return math.comb(self.n_splits, self.n_test_splits)

    def split(self, df_or_n: int) -> Generator[CPCVSplit, None, None]:
        """
        Genera los splits de entrenamiento y evaluación fuera de muestra purgados.
        """
        n_samples = len(df_or_n) if isinstance(df_or_n, (pd.DataFrame, pd.Series, np.ndarray)) else int(df_or_n)
        indices = np.arange(n_samples)
        
        # Asignar cada observación a uno de los N grupos temporales contiguos
        group_sizes = np.full(self.n_splits, n_samples // self.n_splits)
        group_sizes[:n_samples % self.n_splits] += 1
        
        group_indices = []
        current = 0
        for sz in group_sizes:
            group_indices.append(indices[current:current + sz])
            current += sz

        # Calcular tamaño del embargo en barras
        embargo_bars = int(n_samples * self.embargo_pct)

        # Generar combinaciones C(N, k)
        comb_idx = 0
        for test_groups in itertools.combinations(range(self.n_splits), self.n_test_splits):
            test_mask = np.zeros(n_samples, dtype=bool)
            for g in test_groups:
                test_mask[group_indices[g]] = True

            test_idx = indices[test_mask]

            # Construir máscara de purga y embargo para el conjunto de entrenamiento
            train_mask = np.ones(n_samples, dtype=bool)
            train_mask[test_mask] = False  # Quitar el test set

            # Purga: Remover observaciones inmediatamente adyacentes a las fronteras del test set
            for g in test_groups:
                g_start = group_indices[g][0]
                g_end = group_indices[g][-1]

                # Purga anterior
                p_start = max(0, g_start - self.purge_window)
                train_mask[p_start:g_start] = False

                # Embargo posterior (cuarentena)
                e_end = min(n_samples, g_end + 1 + embargo_bars + self.purge_window)
                train_mask[g_end + 1:e_end] = False

            train_idx = indices[train_mask]
            
            yield CPCVSplit(
                split_id=comb_idx,
                train_indices=train_idx,
                test_indices=test_idx,
                test_groups=test_groups
            )
            comb_idx += 1
