"""
Módulo de Búsqueda Genética y Minería de Factores (NSGA-II Multi-Objetivo).
US-4.1, US-4.2, US-4.3 (Sprint 4) & PB-79, PB-80 (Sprint 22).

Implementa:
- Evaluación paralela multi-núcleo de Information Coefficient (IC) e Information Ratio (IC_IR).
- Optimización Multi-Objetivo NSGA-II: Maximizar |IC_IR| y minimizar correlación cruzada (niching y crowding distance).
- Validación estricta con Combinatorial Purged Cross-Validation (CPCV) y control de Probability of Backtest Overfitting (PBO).
- Cálculo de Probabilistic Sharpe Ratio (PSR) y deflación por pruebas múltiples.
- Versionado inmutable de datasets con DataManifestEngine y fijación determinista de semillas.
- Catálogo y persistencia de factores descubiertos (factor_library.json) y auditoría MLOps (run_metadata.json).
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple
import concurrent.futures
import json
import math
import os
import numpy as np
import pandas as pd
import scipy.stats as ss

from mining.alpha_grammar import AlphaGrammar, ASTNode, FeatureNode, BinaryOpNode, TimeSeriesOpNode, UnaryOpNode
from validation.cpcv_engine import CPCVEngine
from validation.multiple_testing import MultipleTestingController
from validation.data_manifest import DataManifestEngine, RunMetadata, set_global_seed
from scripts.research.advanced_metrics import probabilistic_sharpe_ratio, calculate_moments


@dataclass
class AlphaFactor:
    """Representación formal de un factor cuantitativo minado y validado institucionalmente."""
    factor_id: str
    formula: str
    ic_mean: float                  # Information Coefficient medio (correlación Spearman con retornos futuros)
    ic_std: float                   # Desviación estándar del IC
    ic_ir: float                    # Information Ratio = ic_mean / ic_std
    sharpe_proxy: float             # Proxy de Sharpe de la señal long-short
    turnover: float                 # Rotación estimada del factor
    depth: int
    correlation_with_existing: float = 0.0
    psr: float = 0.0                # Probabilistic Sharpe Ratio (debe ser >= 0.95)
    pbo: float = 0.0                # Probability of Backtest Overfitting (debe ser < 0.25)
    cpcv_oos_sharpe_mean: float = 0.0
    cpcv_oos_sharpe_std: float = 0.0
    oos_sharpe_distribution: List[float] = field(default_factory=list)
    is_validated: bool = True


class GeneticAlphaMiner:
    """
    Motor institucional de minería genética de factores cuantitativos.
    Evoluciona expresiones simbólicas buscando el frente de Pareto entre predictibilidad y descorrelación,
    validando candidatos mediante Combinatorial Purged Cross-Validation (CPCV) y control de PBO.
    """

    def __init__(
        self,
        population_size: int = 150,
        generations: int = 25,
        target_forward_bars: int = 1,
        max_tree_depth: int = 3,
        correlation_penalty_threshold: float = 0.60,
        n_jobs: int = -1,
        random_seed: int = 42,
        max_pbo_threshold: float = 0.25,
        min_psr_threshold: float = 0.95,
        cpcv_splits: int = 6,
        cpcv_test_splits: int = 2
    ):
        self.pop_size = int(population_size)
        self.generations = int(generations)
        self.forward_bars = int(target_forward_bars)
        self.max_depth = int(max_tree_depth)
        self.corr_threshold = float(correlation_penalty_threshold)
        self.random_seed = int(random_seed)
        self.max_pbo_threshold = float(max_pbo_threshold)
        self.min_psr_threshold = float(min_psr_threshold)
        self.cpcv_splits = int(cpcv_splits)
        self.cpcv_test_splits = int(cpcv_test_splits)

        # Configuración de paralelismo multi-núcleo
        if n_jobs is None or n_jobs == 0 or n_jobs < 0:
            cpu_count = os.cpu_count() or 4
            self.workers = min(32, max(2, cpu_count))
        else:
            self.workers = max(1, int(n_jobs))

        self.discovered_factors: List[AlphaFactor] = []
        self.last_run_metadata: Optional[RunMetadata] = None

        # Fijar semilla determinista inicial
        set_global_seed(self.random_seed)

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
            std_val = factor_series.std()
            if std_val < 1e-8 or not np.isfinite(std_val):
                return 0.0, 0.0, 0.0, 0.0, factor_series

            # Normalizar z-score
            norm_factor = (factor_series - factor_series.mean()) / (std_val + 1e-8)
            
            # Information Coefficient (correlación rolling con retornos futuros)
            rolling_corr = norm_factor.rolling(30, min_periods=10).corr(forward_returns).dropna()
            
            if len(rolling_corr) == 0:
                return 0.0, 0.0, 0.0, 0.0, factor_series

            rc_mean = float(rolling_corr.mean())
            ic_mean = rc_mean if np.isfinite(rc_mean) else 0.0

            rc_std = float(rolling_corr.std()) if len(rolling_corr) > 1 else 1.0
            ic_std = rc_std if np.isfinite(rc_std) and rc_std > 1e-8 else 1.0

            ic_ir = float(ic_mean / (ic_std + 1e-6))
            if not np.isfinite(ic_ir):
                ic_ir = 0.0
            
            # Retorno simulado ponderado por factor
            sim_returns = norm_factor * forward_returns
            sim_mean = sim_returns.mean()
            sim_std = sim_returns.std()
            if np.isfinite(sim_mean) and np.isfinite(sim_std) and sim_std > 1e-8:
                sharpe_proxy = float(sim_mean / (sim_std + 1e-6) * np.sqrt(365 * 6))
            else:
                sharpe_proxy = 0.0

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

    def _evaluate_population_parallel(
        self,
        population: List[ASTNode],
        df: pd.DataFrame,
        forward_returns: pd.Series,
        existing_factor_values: List[pd.Series]
    ) -> List[Tuple[ASTNode, float, float, float, float, float, pd.Series]]:
        """
        Evalúa toda la población en paralelo utilizando hilos de ejecución multi-núcleo.
        Retorna lista de tuplas: (node, fitness, ic_mean, ic_ir, sharpe, max_corr, norm_series).
        """
        def _eval_single(ind: ASTNode):
            ic_m, ic_r, sh, max_c, s_val = self.evaluate_factor_fitness(
                ind, df, forward_returns, existing_factor_values
            )
            # Fitness base: |IC_IR| con penalización por redundancia
            fitness = abs(ic_r)
            if max_c > self.corr_threshold:
                fitness *= 0.20
            return ind, fitness, ic_m, ic_r, sh, max_c, s_val

        if self.workers <= 1 or len(population) <= 5:
            return [_eval_single(ind) for ind in population]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            results = list(executor.map(_eval_single, population))

        return results

    def fast_non_dominated_sort_nsga2(
        self,
        evaluated: List[Tuple[ASTNode, float, float, float, float, float, pd.Series]]
    ) -> List[List[int]]:
        """
        Clasifica a los individuos en frentes no dominados (NSGA-II).
        Objetivos:
        - Obj 1: Max |IC_IR| (predictibilidad)
        - Obj 2: Min max_corr (equivalente a Max -max_corr)
        """
        n = len(evaluated)
        domination_counts = [0] * n
        dominated_indices = [[] for _ in range(n)]
        fronts: List[List[int]] = [[]]

        for p in range(n):
            p_obj1 = abs(evaluated[p][3])  # |IC_IR|
            p_obj2 = -evaluated[p][5]      # -max_corr

            for q in range(n):
                if p == q:
                    continue
                q_obj1 = abs(evaluated[q][3])
                q_obj2 = -evaluated[q][5]

                # p domina a q si es >= en todo y > en al menos uno
                if (p_obj1 >= q_obj1 and p_obj2 >= q_obj2) and (p_obj1 > q_obj1 or p_obj2 > q_obj2):
                    dominated_indices[p].append(q)
                elif (q_obj1 >= p_obj1 and q_obj2 >= p_obj2) and (q_obj1 > p_obj1 or q_obj2 > p_obj2):
                    domination_counts[p] += 1

            if domination_counts[p] == 0:
                fronts[0].append(p)

        current_front = 0
        while len(fronts[current_front]) > 0:
            next_front = []
            for p in fronts[current_front]:
                for q in dominated_indices[p]:
                    domination_counts[q] -= 1
                    if domination_counts[q] == 0:
                        next_front.append(q)
            current_front += 1
            if next_front:
                fronts.append(next_front)
            else:
                break

        return [f for f in fronts if f]

    def calculate_crowding_distance(
        self,
        front: List[int],
        evaluated: List[Tuple[ASTNode, float, float, float, float, float, pd.Series]]
    ) -> Dict[int, float]:
        """
        Calcula la distancia de apiñamiento (crowding distance) para los individuos de un frente.
        """
        if len(front) <= 2:
            return {idx: float('inf') for idx in front}

        distances = {idx: 0.0 for idx in front}
        objectives = [
            lambda idx: abs(evaluated[idx][3]),  # |IC_IR|
            lambda idx: -evaluated[idx][5]       # -max_corr
        ]

        for obj_func in objectives:
            sorted_front = sorted(front, key=obj_func)
            distances[sorted_front[0]] = float('inf')
            distances[sorted_front[-1]] = float('inf')

            obj_min = obj_func(sorted_front[0])
            obj_max = obj_func(sorted_front[-1])
            spread = obj_max - obj_min

            if spread > 1e-8:
                for i in range(1, len(sorted_front) - 1):
                    distances[sorted_front[i]] += (
                        obj_func(sorted_front[i + 1]) - obj_func(sorted_front[i - 1])
                    ) / spread

        return distances

    def mutate_tree(self, node: ASTNode) -> ASTNode:
        """Aplica mutación estocástica a un subnodo del árbol."""
        if np.random.rand() < 0.3 or node.get_depth() >= self.max_depth:
            return AlphaGrammar.random_expression(max_depth=2)

        if isinstance(node, BinaryOpNode):
            if np.random.rand() < 0.5:
                return BinaryOpNode(node.op, self.mutate_tree(node.left), node.right)
            else:
                return BinaryOpNode(node.op, node.left, self.mutate_tree(node.right))
        elif isinstance(node, TimeSeriesOpNode):
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

    def validate_candidate_with_cpcv(
        self,
        candidate_series_list: List[pd.Series],
        forward_returns: pd.Series,
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Valida candidatos calculando CPCV y Probability of Backtest Overfitting (PBO).
        """
        if not candidate_series_list:
            return []

        cpcv = CPCVEngine(
            n_splits=self.cpcv_splits,
            n_test_splits=self.cpcv_test_splits,
            embargo_pct=0.01,
            purge_window_bars=2
        )
        splits = list(cpcv.split(df))
        n_splits = len(splits)
        n_models = len(candidate_series_list)

        # Matriz de rendimiento CPCV (n_splits, n_models)
        perf_matrix = np.zeros((n_splits, n_models), dtype=float)

        for s_idx, split in enumerate(splits):
            test_idx = split.test_indices
            fwd_test = forward_returns.iloc[test_idx].to_numpy()

            for m_idx, s_cand in enumerate(candidate_series_list):
                cand_test = s_cand.iloc[test_idx].to_numpy()
                sim_test = cand_test * fwd_test
                std_ret = np.std(sim_test)
                if std_ret > 1e-8:
                    sharpe = float(np.mean(sim_test) / std_ret * np.sqrt(365 * 6))
                else:
                    sharpe = 0.0
                perf_matrix[s_idx, m_idx] = sharpe

        # Calcular PBO global mediante MultipleTestingController
        global_pbo = 0.0
        if n_models >= 2 and n_splits >= 2:
            global_pbo = MultipleTestingController.compute_pbo_from_cpcv_matrix(perf_matrix)

        # Métricas individuales por factor
        results = []
        for m_idx in range(n_models):
            oos_sharpes = perf_matrix[:, m_idx].tolist()
            oos_mean = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
            oos_std = float(np.std(oos_sharpes)) if len(oos_sharpes) > 1 else 1.0

            # PBO individual: proporción de folds OOS donde el rendimiento es <= 0 o bajo
            median_oos = float(np.median(perf_matrix)) if n_models > 1 else 0.0
            individual_pbo = float(np.mean(perf_matrix[:, m_idx] < median_oos)) if n_models > 1 else global_pbo

            # Calcular PSR usando los retornos completos
            cand_full = candidate_series_list[m_idx].to_numpy()
            full_ret = cand_full * forward_returns.to_numpy()
            _, std_f, skew_f, kurt_f = calculate_moments(full_ret)
            observed_sr = oos_mean if oos_mean > 0 else (np.mean(full_ret) / (std_f + 1e-6) * np.sqrt(365 * 6))
            
            psr_val = probabilistic_sharpe_ratio(
                observed_sr=observed_sr,
                benchmark_sr=0.0,
                n_samples=len(df),
                skewness=skew_f,
                kurtosis=kurt_f
            )

            results.append({
                "pbo": float(min(1.0, max(0.0, individual_pbo))),
                "psr": float(min(1.0, max(0.0, psr_val))),
                "oos_sharpe_mean": float(oos_mean),
                "oos_sharpe_std": float(oos_std),
                "oos_sharpe_distribution": [round(float(x), 4) for x in oos_sharpes]
            })

        return results

    def run_mining(
        self,
        df: pd.DataFrame,
        max_factors_to_keep: int = 5,
        enforce_validation: bool = True
    ) -> List[AlphaFactor]:
        """
        Ejecuta el ciclo evolutivo de minería genética NSGA-II con validación CPCV/PBO.
        """
        set_global_seed(self.random_seed)
        forward_returns = self.compute_forward_returns(df)

        # Generar población inicial
        population: List[ASTNode] = [
            AlphaGrammar.random_expression(max_depth=self.max_depth)
            for _ in range(self.pop_size)
        ]

        factor_pool: List[Tuple[AlphaFactor, pd.Series]] = []

        for gen in range(self.generations):
            existing_series = [s for _, s in factor_pool]
            evaluated = self._evaluate_population_parallel(
                population, df, forward_returns, existing_series
            )

            # Clasificación NSGA-II (Frentes de Pareto y Crowding Distance)
            fronts = self.fast_non_dominated_sort_nsga2(evaluated)

            # Promover los mejores individuos del frente Pareto al pool global
            if fronts and len(fronts[0]) > 0:
                top_indices = fronts[0]
                crowd_dist = self.calculate_crowding_distance(top_indices, evaluated)
                # Ordenar frente 0 por crowding distance descendente
                sorted_top = sorted(top_indices, key=lambda idx: crowd_dist.get(idx, 0.0), reverse=True)

                for idx in sorted_top[:4]:
                    ind, fit, ic_m, ic_r, sh, max_c, s_val = evaluated[idx]
                    if abs(ic_r) >= 0.08 and max_c < self.corr_threshold:
                        formula_str = ind.to_formula()
                        if not any(f.formula == formula_str for f, _ in factor_pool):
                            factor_obj = AlphaFactor(
                                factor_id=f"ALPHA_{len(factor_pool) + 1:03d}",
                                formula=formula_str,
                                ic_mean=float(np.nan_to_num(ic_m, nan=0.0)),
                                ic_std=float(abs(ic_m / (ic_r + 1e-6))) if abs(ic_r) > 1e-6 else 1.0,
                                ic_ir=float(np.nan_to_num(ic_r, nan=0.0)),
                                sharpe_proxy=float(np.nan_to_num(sh, nan=0.0)),
                                turnover=float(np.nan_to_num(s_val.diff().abs().mean(), nan=0.0)),
                                depth=ind.get_depth(),
                                correlation_with_existing=max_c
                            )
                            factor_pool.append((factor_obj, s_val))

            # Selección para la siguiente generación usando NSGA-II
            survivor_nodes: List[ASTNode] = []
            for front in fronts:
                if len(survivor_nodes) + len(front) <= self.pop_size // 2:
                    survivor_nodes.extend([evaluated[i][0] for i in front])
                else:
                    needed = (self.pop_size // 2) - len(survivor_nodes)
                    if needed > 0:
                        crowd_dist = self.calculate_crowding_distance(front, evaluated)
                        sorted_front = sorted(front, key=lambda idx: crowd_dist.get(idx, 0.0), reverse=True)
                        survivor_nodes.extend([evaluated[i][0] for i in sorted_front[:needed]])
                    break

            if not survivor_nodes:
                survivor_nodes = [evaluated[i][0] for i in range(min(len(evaluated), self.pop_size // 2))]

            next_generation = survivor_nodes.copy()
            while len(next_generation) < self.pop_size:
                p1_idx, p2_idx = np.random.choice(len(survivor_nodes), size=2, replace=(len(survivor_nodes) < 2))
                child = self.crossover_trees(survivor_nodes[p1_idx], survivor_nodes[p2_idx])
                if np.random.rand() < 0.4:
                    child = self.mutate_tree(child)
                next_generation.append(child)

            population = next_generation

        # Si el pool está vacío o tiene pocos factores, incluir los mejores evaluados de la última generación
        if len(factor_pool) < max_factors_to_keep:
            evaluated_last = self._evaluate_population_parallel(
                population, df, forward_returns, [s for _, s in factor_pool]
            )
            evaluated_last.sort(key=lambda x: abs(x[3]), reverse=True)
            for ind, fit, ic_m, ic_r, sh, max_c, s_val in evaluated_last:
                formula_str = ind.to_formula()
                if not any(f.formula == formula_str for f, _ in factor_pool):
                    factor_obj = AlphaFactor(
                        factor_id=f"ALPHA_{len(factor_pool) + 1:03d}",
                        formula=formula_str,
                        ic_mean=float(np.nan_to_num(ic_m, nan=0.0)),
                        ic_std=float(abs(ic_m / (ic_r + 1e-6))) if abs(ic_r) > 1e-6 else 1.0,
                        ic_ir=float(np.nan_to_num(ic_r, nan=0.0)),
                        sharpe_proxy=float(np.nan_to_num(sh, nan=0.0)),
                        turnover=float(np.nan_to_num(s_val.diff().abs().mean(), nan=0.0)),
                        depth=ind.get_depth(),
                        correlation_with_existing=max_c
                    )
                    factor_pool.append((factor_obj, s_val))
                if len(factor_pool) >= max_factors_to_keep * 2:
                    break

        # -------------------------------------------------------------
        # Validación Estricta CPCV & PBO (US-4.2)
        # -------------------------------------------------------------
        candidate_series = [s for _, s in factor_pool]
        cpcv_results = self.validate_candidate_with_cpcv(candidate_series, forward_returns, df)

        validated_factors: List[AlphaFactor] = []
        for (cand_factor, _), cpcv_m in zip(factor_pool, cpcv_results):
            cand_factor.pbo = cpcv_m["pbo"]
            cand_factor.psr = cpcv_m["psr"]
            cand_factor.cpcv_oos_sharpe_mean = cpcv_m["oos_sharpe_mean"]
            cand_factor.cpcv_oos_sharpe_std = cpcv_m["oos_sharpe_std"]
            cand_factor.oos_sharpe_distribution = cpcv_m["oos_sharpe_distribution"]

            # Filtro institucional: PBO < max_pbo_threshold y PSR >= min_psr_threshold
            passes_pbo = cand_factor.pbo < self.max_pbo_threshold
            passes_psr = cand_factor.psr >= self.min_psr_threshold
            cand_factor.is_validated = bool(passes_pbo and passes_psr)

            if not enforce_validation or cand_factor.is_validated:
                validated_factors.append(cand_factor)
            elif not enforce_validation:
                validated_factors.append(cand_factor)

        # Si el filtro institucional estricto rechazó a todos, retener los factores con menor PBO
        # para permitir análisis de laboratorio pero marcados con is_validated=False
        if enforce_validation and len(validated_factors) == 0 and len(factor_pool) > 0:
            factor_pool.sort(key=lambda x: (x[0].pbo, -x[0].psr, -abs(x[0].ic_ir)))
            for f, _ in factor_pool[:max_factors_to_keep]:
                validated_factors.append(f)

        validated_factors.sort(key=lambda x: (x.is_validated, -x.pbo, abs(x.ic_ir)), reverse=True)
        self.discovered_factors = validated_factors[:max_factors_to_keep]

        # Construir y registrar RunMetadata MLOps (US-4.3)
        hyperparams = {
            "population_size": self.pop_size,
            "generations": self.generations,
            "target_forward_bars": self.forward_bars,
            "max_tree_depth": self.max_depth,
            "correlation_penalty_threshold": self.corr_threshold,
            "random_seed": self.random_seed,
            "workers": self.workers,
            "cpcv_splits": self.cpcv_splits,
            "max_pbo_threshold": self.max_pbo_threshold,
            "min_psr_threshold": self.min_psr_threshold
        }
        val_summary = {
            "total_candidates_evaluated": len(factor_pool),
            "factors_promoted": len(self.discovered_factors),
            "avg_pbo": float(np.mean([f.pbo for f in self.discovered_factors])) if self.discovered_factors else 0.0,
            "avg_psr": float(np.mean([f.psr for f in self.discovered_factors])) if self.discovered_factors else 0.0,
            "avg_ic_ir": float(np.mean([abs(f.ic_ir) for f in self.discovered_factors])) if self.discovered_factors else 0.0,
        }
        self.last_run_metadata = DataManifestEngine.build_run_metadata(
            df=df,
            hyperparameters=hyperparams,
            random_seed=self.random_seed,
            validation_metrics=val_summary,
            factors_discovered_count=len(self.discovered_factors)
        )

        return self.discovered_factors

    def save_factor_library(
        self,
        filepath: str = "mining/factor_library.json",
        metadata_filepath: Optional[str] = None
    ) -> None:
        """
        Persiste el catálogo de factores minados en JSON y exporta el manifiesto run_metadata.json.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = [asdict(f) for f in self.discovered_factors]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Exportar metadatos MLOps acompañantes
        if self.last_run_metadata is not None:
            if metadata_filepath is None:
                dirname = os.path.dirname(filepath) or "."
                metadata_filepath = os.path.join(dirname, "run_metadata.json")
            self.last_run_metadata.save_json(metadata_filepath)
