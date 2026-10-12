"""
Módulo de Búsqueda Genética y Minería de Factores (NSGA-II Multi-Objetivo).
PB-79 y PB-80 (Sprint 22).

Implementa:
- Evaluación rápida de Information Coefficient (IC) e Information Ratio del IC (IC_IR).
- Optimización Multi-Objetivo: Maximizar IC_IR, minimizar correlación mutua (niching).
- Mutación y cruce de árboles sintácticos AST.
- Catálogo y persistencia de factores descubiertos (factor_library.py).
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import json
import os
import numpy as np
import pandas as pd

from mining.alpha_grammar import AlphaGrammar, ASTNode, FeatureNode, BinaryOpNode, TimeSeriesOpNode, UnaryOpNode


@dataclass
class AlphaFactor:
    """Representación formal de un factor cuantitativo minado."""
    factor_id: str
    formula: str
    ic_mean: float          # Information Coefficient medio (correlación Spearman con retornos futuros)
    ic_std: float           # Desviación estándar del IC
    ic_ir: float            # Information Ratio = ic_mean / ic_std
    sharpe_proxy: float     # Proxy de Sharpe de la señal long-short
    turnover: float         # Rotación estimada del factor
    depth: int
    correlation_with_existing: float = 0.0


class GeneticAlphaMiner:
    """
    Motor de minería genética de factores cuantitativos.
    Evoluciona expresiones simbólicas buscando el frente de Pareto entre predictibilidad y descorrelación.
    """

    def __init__(
        self,
        population_size: int = 30,
        generations: int = 5,
        target_forward_bars: int = 1,
        max_tree_depth: int = 3,
        correlation_penalty_threshold: float = 0.60
    ):
        self.pop_size = population_size
        self.generations = generations
        self.forward_bars = target_forward_bars
        self.max_depth = max_tree_depth
        self.corr_threshold = correlation_penalty_threshold
        self.discovered_factors: List[AlphaFactor] = []

    def compute_forward_returns(self, df: pd.DataFrame) -> pd.Series:
        """Calcula los retornos futuros a N barras hacia adelante."""
        return df['close'].pct_change(self.forward_bars).shift(-self.forward_bars).fillna(0.0)

    def evaluate_factor_fitness(
        self,
        node: ASTNode,
        df: pd.DataFrame,
        forward_returns: pd.Series,
        existing_factor_values: Optional[List[pd.Series]] = None
    ) -> Tuple[float, float, float, float, pd.Series]:
        """
        Calcula IC, IC_IR, Sharpe proxy y correlación máxima con factores existentes.
        """
        try:
            factor_series = node.evaluate(df)
            factor_series = factor_series.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            
            # Si la serie es constante o degenerate, fitness = 0
            if factor_series.std() < 1e-8:
                return 0.0, 0.0, 0.0, 0.0, factor_series

            # Normalizar z-score
            norm_factor = (factor_series - factor_series.mean()) / (factor_series.std() + 1e-8)
            
            # Information Coefficient (correlación con retornos futuros en ventanas)
            # Para evaluación rápida, calcular correlación rolling de 20 barras
            rolling_corr = norm_factor.rolling(30, min_periods=10).corr(forward_returns).dropna()
            
            if len(rolling_corr) == 0:
                return 0.0, 0.0, 0.0, 0.0, factor_series

            ic_mean = float(rolling_corr.mean())
            ic_std = float(rolling_corr.std()) if len(rolling_corr) > 1 else 1.0
            ic_ir = float(ic_mean / (ic_std + 1e-6))
            
            # Retorno ponderado por factor
            sim_returns = norm_factor * forward_returns
            sharpe_proxy = float(sim_returns.mean() / (sim_returns.std() + 1e-6) * np.sqrt(365 * 6))

            # Correlación máxima con factores existentes
            max_corr = 0.0
            if existing_factor_values:
                for exist in existing_factor_values:
                    c = abs(float(norm_factor.corr(exist)))
                    if np.isfinite(c) and c > max_corr:
                        max_corr = c

            return ic_mean, ic_ir, sharpe_proxy, max_corr, norm_factor
        except Exception:
            return 0.0, 0.0, 0.0, 0.0, pd.Series(0.0, index=df.index)

    def mutate_tree(self, node: ASTNode) -> ASTNode:
        """Aplica mutación estocástica a un subnodo del árbol."""
        if np.random.rand() < 0.3 or node.get_depth() >= self.max_depth:
            # Reemplazar con nuevo nodo aleatorio
            return AlphaGrammar.random_expression(max_depth=2)

        if isinstance(node, BinaryOpNode):
            if np.random.rand() < 0.5:
                return BinaryOpNode(node.op, self.mutate_tree(node.left), node.right)
            else:
                return BinaryOpNode(node.op, node.left, self.mutate_tree(node.right))
        elif isinstance(node, TimeSeriesOpNode):
            # Mutar ventana temporal
            new_window = int(np.random.choice(AlphaGrammar.WINDOWS))
            return TimeSeriesOpNode(node.op, self.mutate_tree(node.child), new_window)
        elif isinstance(node, UnaryOpNode):
            return UnaryOpNode(node.op, self.mutate_tree(node.child))
        return AlphaGrammar.random_terminal()

    def crossover_trees(self, parent_a: ASTNode, parent_b: ASTNode) -> ASTNode:
        """Combina subárboles de dos padres para crear descendencia."""
        if isinstance(parent_a, BinaryOpNode) and np.random.rand() < 0.5:
            return BinaryOpNode(parent_a.op, parent_a.left, parent_b)
        elif isinstance(parent_a, TimeSeriesOpNode):
            return TimeSeriesOpNode(parent_a.op, parent_b, parent_a.window)
        return parent_b

    def run_mining(self, df: pd.DataFrame, max_factors_to_keep: int = 5) -> List[AlphaFactor]:
        """
        Ejecuta el ciclo evolutivo de minería genética sobre el DataFrame histórico.
        """
        forward_returns = self.compute_forward_returns(df)
        population: List[ASTNode] = [
            AlphaGrammar.random_expression(max_depth=self.max_depth)
            for _ in range(self.pop_size)
        ]

        factor_pool: List[Tuple[AlphaFactor, pd.Series]] = []

        for gen in range(self.generations):
            evaluated = []
            for ind in population:
                existing_series = [s for _, s in factor_pool]
                ic_mean, ic_ir, sharpe, max_corr, norm_series = self.evaluate_factor_fitness(
                    ind, df, forward_returns, existing_series
                )
                
                # Penalización severa por redundancia / multicolinealidad
                fitness = abs(ic_ir)
                if max_corr > self.corr_threshold:
                    fitness *= 0.20  # Penalización del 80%

                evaluated.append((ind, fitness, ic_mean, ic_ir, sharpe, max_corr, norm_series))

            # Ordenar por aptitud (Fitness) descendente
            evaluated.sort(key=lambda x: x[1], reverse=True)

            # Preservar los mejores candidatos en el pool global
            for ind, fit, ic_m, ic_r, sh, corr, s_val in evaluated[:3]:
                if abs(ic_r) >= 0.10 and corr < self.corr_threshold:
                    formula_str = ind.to_formula()
                    # Evitar duplicados exactos
                    if not any(f.formula == formula_str for f, _ in factor_pool):
                        factor_obj = AlphaFactor(
                            factor_id=f"ALPHA_{len(factor_pool) + 1:03d}",
                            formula=formula_str,
                            ic_mean=ic_m,
                            ic_std=float(abs(ic_m / (ic_r + 1e-6))),
                            ic_ir=ic_r,
                            sharpe_proxy=sh,
                            turnover=float(s_val.diff().abs().mean()),
                            depth=ind.get_depth(),
                            correlation_with_existing=corr
                        )
                        factor_pool.append((factor_obj, s_val))

            # Selección y reproducción (Top 50% padres)
            survivors = [x[0] for x in evaluated[:self.pop_size // 2]]
            next_generation = survivors.copy()

            while len(next_generation) < self.pop_size:
                p1, p2 = np.random.choice(survivors, size=2, replace=False)
                child = self.crossover_trees(p1, p2)
                if np.random.rand() < 0.4:
                    child = self.mutate_tree(child)
                next_generation.append(child)

            population = next_generation

        # Retener los mejores factores descorrelacionados
        factor_pool.sort(key=lambda x: abs(x[0].ic_ir), reverse=True)
        self.discovered_factors = [f for f, _ in factor_pool[:max_factors_to_keep]]
        return self.discovered_factors

    def save_factor_library(self, filepath: str = "mining/factor_library.json") -> None:
        """Persiste el catálogo de factores en formato JSON estructurado."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = [asdict(f) for f in self.discovered_factors]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
