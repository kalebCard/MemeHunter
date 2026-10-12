"""
Suite de pruebas unitarias para el Asignador Hierarchical Risk Parity (HRP)
y el Orquestador de Ciclo de Vida de Estrategias (Incubadora).
PB-84, PB-85, PB-86 (Sprint 24).
"""

import pytest
import os
import numpy as np
import pandas as pd

from portfolio.hrp_allocator import HierarchicalRiskParityAllocator
from portfolio.strategy_incubator import (
    StrategyLifecycleIncubator,
    StrategyLifecycleStatus,
    StrategyRecord
)


@pytest.fixture
def synthetic_strategy_returns():
    """Genera matriz de rendimientos sintéticos para 4 estrategias descorrelacionadas."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2025-01-01", periods=n, freq="4h")
    
    # Strat A: Short bias (volatilidad media)
    ret_a = np.random.normal(0.001, 0.015, n)
    # Strat B: Funding arbitrage (baja volatilidad)
    ret_b = np.random.normal(0.0003, 0.003, n)
    # Strat C: Volatility breakout (alta volatilidad)
    ret_c = np.random.normal(0.0015, 0.035, n)
    # Strat D: Correlacionada con Strat A
    ret_d = 0.7 * ret_a + 0.3 * np.random.normal(0, 0.01, n)

    return pd.DataFrame({
        'STRAT_A': ret_a,
        'STRAT_B': ret_b,
        'STRAT_C': ret_c,
        'STRAT_D': ret_d
    }, index=dates)


def test_hrp_allocator_weights(synthetic_strategy_returns):
    """Verifica que el optimizador HRP asigne pesos que sumen 1.0 y favorezca activos con menor varianza."""
    allocator = HierarchicalRiskParityAllocator()
    weights = allocator.allocate_weights(synthetic_strategy_returns)

    assert len(weights) == 4
    total_w = sum(weights.values())
    assert total_w == pytest.approx(1.0, rel=1e-5)
    
    # STRAT_B (baja varianza) debe recibir significativamente más peso que STRAT_C (alta varianza)
    assert weights['STRAT_B'] > weights['STRAT_C']
    for k, w in weights.items():
        assert 0.0 < w < 1.0


def test_strategy_incubator_lifecycle():
    """Verifica las transiciones de estado de la máquina: SANDBOX -> LIVE -> ALPHA_DECAY -> RETIRED."""
    incubator = StrategyLifecycleIncubator(min_sandbox_days=10)
    
    # 1. Registro
    rec = incubator.register_strategy(
        strategy_id="V7_QUANTUM",
        name="MemeHunter V7 Quantum",
        backtest_sharpe=3.5
    )
    assert rec.status == StrategyLifecycleStatus.SANDBOX
    assert rec.target_capital_weight == 0.0

    # 2. Graduación a LIVE tras días y rendimiento positivo consistente
    live_returns_good = np.full(50, 0.005) + np.random.normal(0.0, 0.002, 50)
    rec = incubator.audit_and_transition("V7_QUANTUM", days_active=12, live_returns=live_returns_good)
    assert rec.status == StrategyLifecycleStatus.LIVE
    assert rec.live_sharpe > 1.0

    # 3. Detección de Alpha Decay ante choque negativo
    live_returns_bad = np.full(50, -0.010) + np.random.normal(0.0, 0.005, 50)
    rec = incubator.audit_and_transition("V7_QUANTUM", days_active=15, live_returns=live_returns_bad)
    assert rec.status == StrategyLifecycleStatus.ALPHA_DECAY
    assert rec.decay_zscore < -1.8

    # 4. Retiro definitivo
    rec = incubator.audit_and_transition("V7_QUANTUM", days_active=12, live_returns=live_returns_bad)
    assert rec.status == StrategyLifecycleStatus.RETIRED
    assert rec.target_capital_weight == 0.0


def test_incubator_rebalance_and_persistence(synthetic_strategy_returns, tmp_path):
    """Verifica el rebalanceo de capital multi-estrategia y la persistencia en JSON."""
    incubator = StrategyLifecycleIncubator()
    
    # Registrar dos estrategias activas
    incubator.register_strategy("STRAT_A", "Alpha Short", 2.0, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("STRAT_B", "Funding Arb", 2.5, status=StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("STRAT_C", "Experimental", 1.8, status=StrategyLifecycleStatus.SANDBOX)

    rebalance = incubator.rebalance_live_portfolio(synthetic_strategy_returns)
    assert len(rebalance) == 2  # Solo STRAT_A y STRAT_B reciben capital
    assert sum(rebalance.values()) == pytest.approx(1.0, rel=1e-5)
    assert incubator.strategies["STRAT_C"].target_capital_weight == 0.0

    # Probar persistencia
    state_file = os.path.join(tmp_path, "incubator_state.json")
    incubator.save_state(state_file)
    assert os.path.exists(state_file)
    assert os.path.getsize(state_file) > 50
