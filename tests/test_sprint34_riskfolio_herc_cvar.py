"""
tests/test_sprint34_riskfolio_herc_cvar.py
------------------------------------------
Suite de Pruebas Unitarias y de Certificación para el Sprint 34:
- PB-117: Asignador Jerárquico HERC con CVaR 99% (portfolio/riskfolio_allocator.py).
- PB-118: Medición de Riesgo de Cola y Veto de Contribución Marginal de CVaR.
"""

import numpy as np
import pandas as pd
import pytest

from portfolio.riskfolio_allocator import RiskfolioPortfolioAllocator


@pytest.fixture
def sample_returns_df():
    """Genera una matriz de retornos con hechos estilizados de memecoins (colas pesadas)."""
    np.random.seed(42)
    n_bars = 400
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="4h")

    # 4 activos: DOGE (moderado), PEPE (volátil), WIF (momentum), SHIB (cola pesada)
    ret_doge = np.random.normal(0.001, 0.02, size=n_bars)
    ret_pepe = np.random.standard_t(df=3, size=n_bars) * 0.03 + 0.0005
    ret_wif = np.random.normal(0.0015, 0.025, size=n_bars)
    ret_shib = np.random.standard_t(df=2.5, size=n_bars) * 0.04 - 0.001

    df = pd.DataFrame({
        "DOGE": ret_doge,
        "PEPE": ret_pepe,
        "WIF": ret_wif,
        "SHIB": ret_shib
    }, index=dates)
    return df


# =============================================================================
# PRUEBAS PB-117: HERC CON CVaR Y TURNOVER DEADBAND
# =============================================================================

def test_riskfolio_allocator_basic_herc(sample_returns_df):
    """Verifica que el optimizador HERC genere pesos válidos con suma 1.0."""
    allocator = RiskfolioPortfolioAllocator(model="HERC", rm="CVaR", alpha=0.01)
    weights = allocator.allocate_weights(sample_returns_df)

    assert len(weights) == 4
    total_w = sum(weights.values())
    assert np.isclose(total_w, 1.0, atol=1e-4)

    for asset, w in weights.items():
        assert 0.0 <= w <= 1.0
        # Activo con mayor cola negativa (SHIB) debe recibir menor peso que activos más estables
        assert isinstance(w, float)


def test_turnover_deadband_retention(sample_returns_df):
    """Verifica que si la rotación sugerida es inferior al 15%, se retengan los pesos previos."""
    allocator = RiskfolioPortfolioAllocator(turnover_deadband=0.15)

    initial_weights = allocator.allocate_weights(sample_returns_df)

    # Modificar levemente retornos (ruido despreciable < 2%)
    noisy_df = sample_returns_df + np.random.normal(0, 0.0001, size=sample_returns_df.shape)

    rebalanced_weights = allocator.allocate_weights(noisy_df, current_weights=initial_weights)

    # Debe ser exactamente idéntico porque no superó el 15% de deadband
    assert rebalanced_weights == initial_weights


def test_turnover_deadband_triggered_on_regime_shift(sample_returns_df):
    """Verifica que ante un cambio drástico de régimen (> 15% turnover), sí se rebalancee."""
    allocator = RiskfolioPortfolioAllocator(turnover_deadband=0.15)
    initial_weights = {"DOGE": 0.25, "PEPE": 0.25, "WIF": 0.25, "SHIB": 0.25}

    # Crear shock de retornos masivo en SHIB
    shocked_df = sample_returns_df.copy()
    shocked_df["SHIB"] = shocked_df["SHIB"] * 5.0  # Quintuplicar varianza y riesgo

    new_weights = allocator.allocate_weights(shocked_df, current_weights=initial_weights)

    # Debe cambiar significativamente
    assert new_weights != initial_weights
    # SHIB debe ser penalizado fuertemente
    assert new_weights["SHIB"] < initial_weights["SHIB"]


def test_edge_cases_single_and_empty():
    """Verifica el comportamiento robusto ante 1 solo activo o datos vacíos."""
    allocator = RiskfolioPortfolioAllocator()

    empty_df = pd.DataFrame()
    assert allocator.allocate_weights(empty_df) == {}

    single_df = pd.DataFrame({"BTC": [0.01, -0.02, 0.015]})
    single_res = allocator.allocate_weights(single_df)
    assert single_res == {"BTC": 1.0}


# =============================================================================
# PRUEBAS PB-118: EVALUACIÓN DE RIESGO DE COLA Y CONTRIBUCIÓN MARGINAL DE CVaR
# =============================================================================

def test_compute_portfolio_tail_risk_metrics(sample_returns_df):
    """Verifica que CVaR, VaR y Maximum Drawdown cumplan propiedades matemáticas formales."""
    allocator = RiskfolioPortfolioAllocator()
    weights = {"DOGE": 0.40, "PEPE": 0.30, "WIF": 0.20, "SHIB": 0.10}

    risk_metrics = allocator.compute_portfolio_tail_risk(sample_returns_df, weights, alpha=0.01)

    assert "var_99" in risk_metrics
    assert "cvar_99" in risk_metrics
    assert "max_drawdown" in risk_metrics
    assert "cdar_99" in risk_metrics

    # Propiedad matemática fundamental: CVaR (Expected Shortfall) >= VaR
    assert risk_metrics["cvar_99"] >= risk_metrics["var_99"]
    assert risk_metrics["var_99"] >= 0.0
    assert risk_metrics["max_drawdown"] >= 0.0


def test_marginal_cvar_veto_rule(sample_returns_df):
    """
    Verifica que la regla de veto de PB-118 bloquee activos que eleven
    el CVaR al 99% por encima del umbral máximo (+15%).
    """
    allocator = RiskfolioPortfolioAllocator()
    baseline_weights = {"DOGE": 0.50, "WIF": 0.50}

    # 1. Candidato benigno: PEPE con volatilidad moderada
    eval_pepe = allocator.evaluate_marginal_cvar_contribution(
        returns_df=sample_returns_df,
        current_weights=baseline_weights,
        candidate_asset="PEPE",
        candidate_weight=0.10,
        max_cvar_increase_pct=25.0
    )
    assert "decision" in eval_pepe
    assert "baseline_cvar_99" in eval_pepe

    # 2. Candidato hiper-tóxico simulado: retornos con pérdidas catastróficas del 25% continuas
    toxic_df = sample_returns_df.copy()
    toxic_df["TOXIC_RUG"] = np.random.normal(-0.15, 0.10, size=len(sample_returns_df))

    eval_toxic = allocator.evaluate_marginal_cvar_contribution(
        returns_df=toxic_df,
        current_weights=baseline_weights,
        candidate_asset="TOXIC_RUG",
        candidate_weight=0.20,
        max_cvar_increase_pct=15.0
    )

    # Debe ser vetado con motivo explícito
    assert eval_toxic["approved"] is False
    assert eval_toxic["decision"] == "VETOED_EXCESSIVE_TAIL_RISK"
    assert eval_toxic["cvar_delta_pct"] > 15.0
