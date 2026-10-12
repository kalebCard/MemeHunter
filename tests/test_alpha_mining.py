"""
Suite de pruebas unitarias para el Motor Simbólico de Minería de Alphas
y Búsqueda Genética NSGA-II.
PB-78, PB-79, PB-80 (Sprint 22).
"""

import pytest
import os
import numpy as np
import pandas as pd

from mining.alpha_grammar import (
    AlphaGrammar, ASTNode, FeatureNode, ConstantNode,
    BinaryOpNode, UnaryOpNode, TimeSeriesOpNode
)
from mining.genetic_search import GeneticAlphaMiner, AlphaFactor


@pytest.fixture
def sample_ohlcv_data():
    """Genera datos OHLCV sintéticos para minería."""
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2025-01-01", periods=n, freq="4h")
    returns = np.random.normal(0.0005, 0.02, size=n)
    prices = 50.0 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'date': dates,
        'open': prices * (1.0 + np.random.normal(0, 0.002, n)),
        'high': prices * (1.0 + np.abs(np.random.normal(0, 0.005, n))),
        'low': prices * (1.0 - np.abs(np.random.normal(0, 0.005, n))),
        'close': prices,
        'volume': np.random.uniform(10_000, 100_000, size=n)
    })


def test_ast_evaluation_and_formula(sample_ohlcv_data):
    """Verifica que los árboles sintácticos se evalúen vectorialmente y produzcan fórmulas limpias."""
    # Factor: ts_zscore(close, 10) - ts_delta(volume, 5)
    node = BinaryOpNode(
        '-',
        TimeSeriesOpNode('ts_zscore', FeatureNode('close'), 10),
        TimeSeriesOpNode('ts_delta', FeatureNode('volume'), 5)
    )
    
    formula = node.to_formula()
    assert formula == "(ts_zscore(close, 10) - ts_delta(volume, 5))"
    assert node.get_depth() == 3
    
    evaluated = node.evaluate(sample_ohlcv_data)
    assert isinstance(evaluated, pd.Series)
    assert len(evaluated) == len(sample_ohlcv_data)
    assert not evaluated.isna().any()


def test_alpha_grammar_random_expression():
    """Verifica que el generador estocástico cree árboles válidos sin ciclos infinitos."""
    expr = AlphaGrammar.random_expression(max_depth=3)
    assert isinstance(expr, ASTNode)
    assert expr.get_depth() <= 4
    formula = expr.to_formula()
    assert len(formula) > 0


def test_genetic_miner_execution(sample_ohlcv_data, tmp_path):
    """Verifica el ciclo evolutivo de minería genética y descubrimiento de factores."""
    miner = GeneticAlphaMiner(
        population_size=15,
        generations=3,
        target_forward_bars=1,
        max_tree_depth=2
    )
    
    factors = miner.run_mining(sample_ohlcv_data, max_factors_to_keep=3)
    
    assert isinstance(factors, list)
    assert len(factors) > 0
    top_factor = factors[0]
    assert isinstance(top_factor, AlphaFactor)
    assert top_factor.factor_id.startswith("ALPHA_")
    assert len(top_factor.formula) > 0
    
    # Probar persistencia en JSON
    json_path = os.path.join(tmp_path, "test_factors.json")
    miner.save_factor_library(json_path)
    assert os.path.exists(json_path)
    assert os.path.getsize(json_path) > 10


def test_mutation_and_crossover():
    """Verifica que los operadores genéticos muten y crucen sin romper la integridad del árbol."""
    node_a = TimeSeriesOpNode('ts_rank', FeatureNode('high'), 14)
    node_b = BinaryOpNode('+', FeatureNode('low'), ConstantNode(1.0))
    
    miner = GeneticAlphaMiner()
    mutated = miner.mutate_tree(node_a)
    assert isinstance(mutated, ASTNode)
    
    crossed = miner.crossover_trees(node_a, node_b)
    assert isinstance(crossed, ASTNode)
