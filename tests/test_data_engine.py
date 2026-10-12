"""
Suite de pruebas unitarias para el Motor de Barras de Información (Dollar Bars)
y el Simulador de Microestructura y Deslizamiento (Almgren-Chriss).
PB-75, PB-76, PB-77 (Sprint 21).
"""

import pytest
import numpy as np
import pandas as pd

from data_engine.dollar_bars import InformationBarsGenerator, BarStats
from data_engine.slippage_engine import MicrostructureSlippageEngine, ExecutionResult


@pytest.fixture
def synthetic_market_data():
    """Genera datos sintéticos de alta resolución (10,000 observaciones)."""
    np.random.seed(42)
    n = 2000
    dates = pd.date_range("2025-01-01", periods=n, freq="1min")
    
    # Random walk con saltos de volatilidad
    returns = np.random.normal(0.0001, 0.002, size=n)
    # Introducir eventos de cola
    returns[100:110] -= 0.015
    returns[500:510] += 0.020
    
    prices = 100.0 * np.exp(np.cumsum(returns))
    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.001, n)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.001, n)))
    opens = prices * (1.0 + np.random.normal(0, 0.0005, n))
    volumes = np.random.uniform(500, 5000, size=n)
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': volumes
    })


def test_dollar_bars_generation(synthetic_market_data):
    """Verifica que las Dollar Bars se generen correctamente respetando el umbral notional."""
    generator = InformationBarsGenerator(notional_threshold=500_000.0)
    dollar_bars = generator.generate_dollar_bars(synthetic_market_data)
    
    assert not dollar_bars.empty
    assert len(dollar_bars) < len(synthetic_market_data)
    assert 'notional' in dollar_bars.columns
    assert 'returns' in dollar_bars.columns
    
    # Cada barra (salvo la última posible) debe acumular al menos el umbral
    for notional in dollar_bars['notional'][:-1]:
        assert notional >= 500_000.0


def test_volume_bars_generation(synthetic_market_data):
    """Verifica que las Volume Bars se cierren en los múltiplos correctos de volumen."""
    generator = InformationBarsGenerator(volume_threshold=10_000.0)
    vol_bars = generator.generate_volume_bars(synthetic_market_data)
    
    assert not vol_bars.empty
    assert len(vol_bars) < len(synthetic_market_data)
    for vol in vol_bars['volume']:
        assert vol >= 10_000.0


def test_tick_imbalance_bars_generation(synthetic_market_data):
    """Verifica la generación de barras basadas en desbalance de flujo de ticks."""
    generator = InformationBarsGenerator()
    tib_bars = generator.generate_tick_imbalance_bars(synthetic_market_data, expected_imbalance_window=30)
    
    assert not tib_bars.empty
    assert 'imbalance' in tib_bars.columns
    assert len(tib_bars) < len(synthetic_market_data)


def test_normality_evaluation():
    """Verifica que el evaluador de Jarque-Bera compute correctamente skewness y kurtosis."""
    np.random.seed(42)
    normal_returns = np.random.normal(0.0, 0.01, 1000)
    stats = InformationBarsGenerator.evaluate_normality_and_properties(normal_returns)
    
    assert isinstance(stats, BarStats)
    assert abs(stats.skewness) < 0.3
    assert abs(stats.kurtosis - 3.0) < 0.8  # Curtosis cercana a 3 en muestra gaussiana


def test_microstructure_slippage_maker():
    """Verifica la simulación de órdenes Maker pasivas con riesgo de fill condicional."""
    engine = MicrostructureSlippageEngine(base_maker_fee=0.0002)
    
    # En condiciones normales
    res_normal = engine.simulate_order_execution(
        side='sell',
        order_type='maker',
        price=10.0,
        order_size_usdt=500.0,
        daily_volume_usdt=50_000_000.0,
        volatility=0.02,
        rvol=1.0,
        is_breakdown_candle=False
    )
    assert res_normal.is_filled is True
    assert res_normal.executed_price == 10.0
    assert res_normal.slippage_bps == 0.0
    assert res_normal.liquidity_cost_usdt == pytest.approx(500.0 * 0.0002)


def test_microstructure_slippage_market_almgren_chriss():
    """Verifica que las órdenes Market sufran spread e impacto de mercado Almgren-Chriss."""
    engine = MicrostructureSlippageEngine(
        base_taker_fee=0.0005,
        gamma_impact_coeff=0.30,
        base_spread_bps=4.0
    )
    
    # Orden de compra Market
    res_buy = engine.simulate_order_execution(
        side='buy',
        order_type='market',
        price=100.0,
        order_size_usdt=10_000.0,
        daily_volume_usdt=1_000_000.0,
        volatility=0.05,
        rvol=2.5
    )
    
    assert res_buy.is_filled is True
    assert res_buy.executed_price > 100.0  # El precio empeora (compra más caro)
    assert res_buy.slippage_bps > 2.0
    assert res_buy.market_impact_bps > 0.0
    assert res_buy.liquidity_cost_usdt > (10_000.0 * 0.0005)

    # Orden de venta Market
    res_sell = engine.simulate_order_execution(
        side='sell',
        order_type='market',
        price=100.0,
        order_size_usdt=10_000.0,
        daily_volume_usdt=1_000_000.0,
        volatility=0.05,
        rvol=2.5
    )
    assert res_sell.executed_price < 100.0  # Venta vende más barato
