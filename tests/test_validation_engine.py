"""
Suite de pruebas unitarias para el motor de Combinatorial Purged Cross-Validation (CPCV)
y el control de falsos descubrimientos (Benjamini-Hochberg FDR, Bonferroni, PBO).
PB-81, PB-82, PB-83 (Sprint 23).
"""

import pytest
import numpy as np
import pandas as pd

from validation.cpcv_engine import CPCVEngine, CPCVSplit
from validation.multiple_testing import MultipleTestingController, MultipleTestingAudit


def test_cpcv_engine_split_generation():
    """Verifica que el generador CPCV produzca el número exacto de combinaciones con purga y embargo."""
    # N=6 grupos, k=2 test splits -> C(6, 2) = 15 particiones
    engine = CPCVEngine(n_splits=6, n_test_splits=2, embargo_pct=0.01, purge_window_bars=3)
    assert engine.total_combinations == 15

    n_samples = 600
    splits = list(engine.split(n_samples))
    assert len(splits) == 15

    for s in splits:
        assert isinstance(s, CPCVSplit)
        # Verificar que ningún índice de test esté en el conjunto de entrenamiento
        overlap = np.intersect1d(s.train_indices, s.test_indices)
        assert len(overlap) == 0
        assert len(s.test_indices) > 0
        assert len(s.train_indices) > 0
        # Debido a purga y embargo, train + test debe ser estrictamente menor que el total de muestras
        assert len(s.train_indices) + len(s.test_indices) < n_samples


def test_benjamini_hochberg_fdr_control():
    """Verifica la corrección de Benjamini-Hochberg sobre hipótesis verdaderas vs espurias."""
    controller = MultipleTestingController(target_alpha=0.05)
    
    # 10 hipótesis: 2 con fuerte significancia y 8 con p-valores altos (ruido)
    p_values = np.array([0.001, 0.004, 0.15, 0.22, 0.45, 0.60, 0.75, 0.82, 0.91, 0.98])
    sig_mask, crit_p = controller.benjamini_hochberg_fdr(p_values, q=0.05)

    assert sig_mask[0] is np.True_  # 0.001 debe ser aceptado
    assert sig_mask[1] is np.True_  # 0.004 debe ser aceptado
    assert not sig_mask[2]         # 0.15 debe ser rechazado
    assert np.sum(sig_mask) == 2


def test_bonferroni_fwer_control():
    """Verifica el umbral conservador de Bonferroni alpha / m."""
    controller = MultipleTestingController(target_alpha=0.05)
    p_values = np.array([0.002, 0.04, 0.20, 0.80])  # m=4 -> umbral = 0.05 / 4 = 0.0125
    sig_mask, crit_p = controller.bonferroni_fwer(p_values, alpha=0.05)

    assert crit_p == pytest.approx(0.0125)
    assert sig_mask[0] is np.True_
    assert not sig_mask[1]  # 0.04 es menor que 0.05 pero mayor que 0.0125 (rechazado por Bonferroni)


def test_pbo_calculation_from_matrix():
    """Verifica que el cálculo de PBO penalice el sobreajuste sintético."""
    controller = MultipleTestingController()
    
    # Matriz sintética: 10 folds x 5 modelos
    np.random.seed(42)
    # Modelos consistentes
    matrix_consistent = np.array([
        [1.5, 1.2, 0.8, 0.5, 0.1],
        [1.4, 1.1, 0.9, 0.4, 0.2],
        [1.6, 1.3, 0.7, 0.6, 0.0],
        [1.5, 1.2, 0.8, 0.5, 0.1],
        [1.3, 1.0, 0.6, 0.3, 0.0]
    ])
    pbo_low = controller.compute_pbo_from_cpcv_matrix(matrix_consistent)
    assert pbo_low == 0.0  # El modelo 0 siempre gana

    # Auditoría integral
    p_values = np.array([0.001, 0.005, 0.10, 0.50])
    audit = controller.audit_mined_hypotheses(p_values, matrix_consistent)
    assert isinstance(audit, MultipleTestingAudit)
    assert audit.is_institutional_grade is True
    assert audit.pbo_estimate == 0.0
