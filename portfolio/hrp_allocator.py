"""
Módulo de Asignación de Portafolio por Paridad Jerárquica de Riesgo (Hierarchical Risk Parity - HRP).
Implementación basada en Marcos López de Prado (2016), 'Building Diversified Portfolios that Outperform Out-of-Sample'.

Resuelve la inestabilidad de la optimización clásica de media-varianza de Markowitz
mediante teoría de grafos, agrupamiento jerárquico de correlaciones y paridad inversa recursiva.

PB-84 (Sprint 24).
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import squareform


class HierarchicalRiskParityAllocator:
    """
    Asignador óptimo de pesos para factores o estrategias utilizando HRP:
    1. Tree Clustering (Agrupamiento jerárquico sobre matriz de distancia de correlación).
    2. Quasi-Diagonalization (Ordenamiento jerárquico que preserva adyacencia de clústeres).
    3. Recursive Bisection (Distribución recursiva de capital inversamente proporcional a la varianza).
    """

    @staticmethod
    def correlation_to_distance(corr_matrix: np.ndarray) -> np.ndarray:
        """
        Calcula la métrica de distancia ultramétrica de López de Prado:
        d(i, j) = sqrt(0.5 * (1 - rho(i, j)))
        """
        corr = np.clip(corr_matrix, -1.0, 1.0)
        dist = np.sqrt(0.5 * (1.0 - corr))
        np.fill_diagonal(dist, 0.0)
        return dist

    @classmethod
    def get_quasi_diagonal_order(cls, link_matrix: np.ndarray) -> List[int]:
        """
        Ordena los índices para que los activos correlacionados queden contiguos en la matriz.
        """
        link = link_matrix.astype(float)
        root = to_tree(link, rd=False)
        
        def _get_leaves(node):
            if node.is_leaf():
                return [node.id]
            return _get_leaves(node.left) + _get_leaves(node.right)
            
        return _get_leaves(root)

    @classmethod
    def get_cluster_variance(cls, cov_matrix: np.ndarray, cluster_indices: List[int]) -> float:
        """Calcula la varianza del clúster con ponderación de paridad de riesgo inversa simple."""
        sub_cov = cov_matrix[np.ix_(cluster_indices, cluster_indices)]
        inv_diag = 1.0 / np.diag(sub_cov).clip(1e-8)
        w = inv_diag / np.sum(inv_diag)
        cluster_var = float(np.dot(w.T, np.dot(sub_cov, w)))
        return cluster_var

    @classmethod
    def recursive_bisection(
        cls,
        cov_matrix: np.ndarray,
        sorted_indices: List[int]
    ) -> pd.Series:
        """
        Asigna recursivamente los pesos del portafolio entre subárboles jerárquicos.
        """
        weights = pd.Series(1.0, index=sorted_indices)
        clusters = [sorted_indices]

        while len(clusters) > 0:
            next_clusters = []
            for cl in clusters:
                if len(cl) > 1:
                    # Dividir clúster en dos mitades
                    mid = len(cl) // 2
                    c1 = cl[:mid]
                    c2 = cl[mid:]

                    var1 = cls.get_cluster_variance(cov_matrix, c1)
                    var2 = cls.get_cluster_variance(cov_matrix, c2)

                    # Factor de reparto de peso alpha = 1 - var1 / (var1 + var2)
                    alpha = 1.0 - (var1 / (var1 + var2 + 1e-12))
                    alpha = np.clip(alpha, 0.05, 0.95)

                    weights[c1] *= alpha
                    weights[c2] *= (1.0 - alpha)

                    if len(c1) > 1:
                        next_clusters.append(c1)
                    if len(c2) > 1:
                        next_clusters.append(c2)

            clusters = next_clusters

        return weights / weights.sum()

    def allocate_weights(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calcula la asignación HRP de los activos o factores dados sus retornos históricos.
        """
        clean_df = returns_df.dropna(how='all').fillna(0.0)
        assets = list(clean_df.columns)
        n = len(assets)
        if n == 0:
            return {}
        if n == 1:
            return {assets[0]: 1.0}

        corr = clean_df.corr().to_numpy()
        cov = clean_df.cov().to_numpy()

        corr = np.nan_to_num(corr, copy=True, nan=0.0)
        cov = np.nan_to_num(cov, copy=True, nan=0.0)
        np.fill_diagonal(corr, 1.0)

        # 1. Distancia y enlace jerárquico
        dist_mat = self.correlation_to_distance(corr)
        condensed_dist = squareform(dist_mat, checks=False)
        link = linkage(condensed_dist, method='single')

        # 2. Orden cuasi-diagonal
        sorted_indices = self.get_quasi_diagonal_order(link)

        # 3. Bisección recursiva
        weights_series = self.recursive_bisection(cov, sorted_indices)
        
        # Mapear nombres originales
        out_weights = {assets[i]: float(weights_series[i]) for i in sorted_indices}
        return out_weights
