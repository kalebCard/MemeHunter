"""
Suite de pruebas unitarias para Escalabilidad Genética, Control de PBO y Pipeline MLOps.
US-4.1, US-4.2, US-4.3 (Sprint 4).
"""

import json
import os
import pytest
import numpy as np
import pandas as pd

from mining.alpha_grammar import FeatureNode, TimeSeriesOpNode, BinaryOpNode
from mining.genetic_search import GeneticAlphaMiner, AlphaFactor
from validation.data_manifest import DataManifestEngine, DatasetManifest, RunMetadata, set_global_seed


@pytest.fixture
def synthetic_market_data():
    """Genera datos OHLCV sintéticos reproducibles con propiedades de mercado real."""
    set_global_seed(42)
    n = 300
    dates = pd.date_range("2026-01-01", periods=n, freq="4h")
    returns = np.random.normal(0.0005, 0.025, size=n)
    prices = 100.0 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'date': dates,
        'open': prices * (1.0 + np.random.normal(0, 0.002, n)),
        'high': prices * (1.0 + np.abs(np.random.normal(0, 0.005, n))),
        'low': prices * (1.0 - np.abs(np.random.normal(0, 0.005, n))),
        'close': prices,
        'volume': np.random.uniform(50_000, 500_000, size=n)
    })


def test_data_manifest_generation(synthetic_market_data):
    """Verifica que el DataManifestEngine genere hashes SHA-256 inmutables y consistentes."""
    manifest_1 = DataManifestEngine.generate_manifest(synthetic_market_data, symbols=["DOGEUSDT"])
    manifest_2 = DataManifestEngine.generate_manifest(synthetic_market_data, symbols=["DOGEUSDT"])

    assert manifest_1.dataset_sha256 == manifest_2.dataset_sha256
    assert len(manifest_1.dataset_sha256) == 64
    assert manifest_1.n_rows == 300
    assert manifest_1.n_cols == 6
    assert "close" in manifest_1.columns
    assert manifest_1.symbols == ["DOGEUSDT"]
    assert manifest_1.start_timestamp is not None
    assert manifest_1.end_timestamp is not None

    # Alterar un valor y verificar que el hash cambie inmediatamente
    modified_data = synthetic_market_data.copy()
    modified_data.loc[0, 'close'] += 1.0
    manifest_mod = DataManifestEngine.generate_manifest(modified_data)
    assert manifest_mod.dataset_sha256 != manifest_1.dataset_sha256


def test_run_metadata_save_load(synthetic_market_data, tmp_path):
    """Verifica la persistencia y reconstrucción fiel de los metadatos MLOps en JSON."""
    hyperparams = {"population_size": 20, "generations": 2, "random_seed": 42}
    val_metrics = {"pbo": 0.12, "psr": 0.98}

    metadata = DataManifestEngine.build_run_metadata(
        df=synthetic_market_data,
        hyperparameters=hyperparams,
        random_seed=42,
        validation_metrics=val_metrics,
        factors_discovered_count=3
    )

    meta_file = os.path.join(tmp_path, "run_metadata.json")
    metadata.save_json(meta_file)

    assert os.path.exists(meta_file)
    loaded = RunMetadata.load_json(meta_file)
    assert loaded.random_seed == 42
    assert loaded.data_manifest.dataset_sha256 == metadata.data_manifest.dataset_sha256
    assert loaded.hyperparameters == hyperparams
    assert loaded.validation_metrics["pbo"] == 0.12
    assert loaded.factors_discovered_count == 3


def test_deterministic_mining_reproducibility(synthetic_market_data):
    """Verifica que dos ejecuciones con la misma semilla produzcan exactamente los mismos factores."""
    miner_1 = GeneticAlphaMiner(
        population_size=16,
        generations=2,
        n_jobs=1,
        random_seed=123,
        cpcv_splits=4,
        cpcv_test_splits=2
    )
    factors_1 = miner_1.run_mining(synthetic_market_data, max_factors_to_keep=2, enforce_validation=False)

    miner_2 = GeneticAlphaMiner(
        population_size=16,
        generations=2,
        n_jobs=1,
        random_seed=123,
        cpcv_splits=4,
        cpcv_test_splits=2
    )
    factors_2 = miner_2.run_mining(synthetic_market_data, max_factors_to_keep=2, enforce_validation=False)

    assert len(factors_1) == len(factors_2)
    for f1, f2 in zip(factors_1, factors_2):
        assert f1.formula == f2.formula
        assert np.isclose(f1.ic_ir, f2.ic_ir, equal_nan=True)
        assert np.isclose(f1.sharpe_proxy, f2.sharpe_proxy, equal_nan=True)


def test_parallel_evaluation_execution(synthetic_market_data):
    """Verifica que la evaluación paralela multi-hilo funcione de forma fluida y sin bloqueos."""
    miner_parallel = GeneticAlphaMiner(
        population_size=20,
        generations=2,
        n_jobs=4,
        random_seed=42,
        cpcv_splits=4,
        cpcv_test_splits=2
    )
    factors = miner_parallel.run_mining(synthetic_market_data, max_factors_to_keep=3, enforce_validation=False)
    assert isinstance(factors, list)
    assert len(factors) > 0
    assert miner_parallel.last_run_metadata is not None
    assert miner_parallel.last_run_metadata.hyperparameters["workers"] == 4


def test_cpcv_and_pbo_validation_gating(synthetic_market_data, tmp_path):
    """Verifica que la validación CPCV calcule PBO, PSR y OOS distributions y rechace sobreajuste."""
    miner = GeneticAlphaMiner(
        population_size=24,
        generations=3,
        n_jobs=2,
        random_seed=99,
        max_pbo_threshold=0.25,
        min_psr_threshold=0.95,
        cpcv_splits=4,
        cpcv_test_splits=2
    )
    factors = miner.run_mining(synthetic_market_data, max_factors_to_keep=3, enforce_validation=True)

    assert len(factors) > 0
    for f in factors:
        assert hasattr(f, "pbo")
        assert hasattr(f, "psr")
        assert hasattr(f, "oos_sharpe_distribution")
        assert 0.0 <= f.pbo <= 1.0
        assert 0.0 <= f.psr <= 1.0
        assert len(f.oos_sharpe_distribution) > 0

    # Guardar factor_library y run_metadata
    lib_path = os.path.join(tmp_path, "factor_library.json")
    miner.save_factor_library(lib_path)

    assert os.path.exists(lib_path)
    meta_path = os.path.join(tmp_path, "run_metadata.json")
    assert os.path.exists(meta_path)

    with open(lib_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == len(factors)
    assert "pbo" in data[0]
    assert "psr" in data[0]
    assert "oos_sharpe_distribution" in data[0]


def test_nsga2_non_dominated_sorting_and_crowding():
    """Verifica el algoritmo NSGA-II de frente de Pareto y distancia de apiñamiento."""
    miner = GeneticAlphaMiner()
    node_mock = FeatureNode("close")
    series_mock = pd.Series([1.0, 2.0, 3.0])

    # Construir individuos con diferentes combinaciones de IC_IR y correlación
    # Tupla: (node, fitness, ic_m, ic_r, sh, max_c, s_val)
    ind1 = (node_mock, 0.5, 0.05, 0.5, 1.5, 0.1, series_mock)  # Alto IC_IR, Baja corr (Excelente)
    ind2 = (node_mock, 0.2, 0.02, 0.2, 0.8, 0.7, series_mock)  # Bajo IC_IR, Alta corr (Pobre)
    ind3 = (node_mock, 0.5, 0.05, 0.5, 1.5, 0.5, series_mock)  # Alto IC_IR, Media corr
    ind4 = (node_mock, 0.1, 0.01, 0.1, 0.5, 0.1, series_mock)  # Bajo IC_IR, Baja corr

    evaluated = [ind1, ind2, ind3, ind4]
    fronts = miner.fast_non_dominated_sort_nsga2(evaluated)

    assert len(fronts) > 0
    # ind1 debe estar en el frente 0 (no dominado)
    assert 0 in fronts[0]

    # Crowding distance
    distances = miner.calculate_crowding_distance(fronts[0], evaluated)
    assert len(distances) == len(fronts[0])
    for dist in distances.values():
        assert dist >= 0.0 or dist == float('inf')
