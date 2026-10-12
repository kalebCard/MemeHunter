"""
Pruebas de Integración y Validación para la Estrategia MemeHunter_MinedEnsemble.
Certifica que la estrategia generada por el compilador dinámico procese velas OHLCV,
calcule el composite_alpha_score y produzca señales de entrada/salida válidas.
"""

import pytest
import numpy as np
import pandas as pd

from user_data.strategies.MemeHunter_MinedEnsemble import MemeHunter_MinedEnsemble


@pytest.fixture
def ohlcv_dataframe():
    """Genera DataFrame sintético OHLCV de 300 velas de 4h."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2025-01-01", periods=n, freq="4h")
    # Generar tendencia bajista para activar señales de entrada short
    returns = np.random.normal(-0.001, 0.015, n)
    prices = 10.0 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'date': dates,
        'open': prices * 1.002,
        'high': prices * 1.010,
        'low': prices * 0.990,
        'close': prices,
        'volume': np.random.uniform(50_000, 500_000, size=n)
    })


def test_mined_ensemble_populate_indicators(ohlcv_dataframe):
    """Verifica que el cálculo de indicadores y factores no genere excepciones ni NaNs no controlados."""
    strat = MemeHunter_MinedEnsemble(config={})
    df = strat.populate_indicators(ohlcv_dataframe.copy(), metadata={'pair': 'PEPE/USDT:USDT'})

    assert 'composite_alpha_score' in df.columns
    assert 'ema_200' in df.columns
    assert 'rsi' in df.columns
    assert not df['composite_alpha_score'].isna().all()


def test_mined_ensemble_entry_and_exit_signals(ohlcv_dataframe):
    """Verifica la generación de señales enter_short y exit_short con tags institucionales."""
    strat = MemeHunter_MinedEnsemble(config={})
    df = strat.populate_indicators(ohlcv_dataframe.copy(), metadata={'pair': 'PEPE/USDT:USDT'})
    df = strat.populate_entry_trend(df, metadata={'pair': 'PEPE/USDT:USDT'})
    df = strat.populate_exit_trend(df, metadata={'pair': 'PEPE/USDT:USDT'})

    assert 'enter_short' in df.columns
    assert 'enter_tag' in df.columns
    assert 'exit_short' in df.columns
    assert 'exit_tag' in df.columns

    # Verificar apalancamiento
    lev = strat.leverage(
        pair='PEPE/USDT:USDT',
        current_time=None,
        current_rate=1.0,
        proposed_leverage=1.0,
        max_leverage=5.0,
        entry_tag='short_hrp_ensemble',
        side='short'
    )
    assert lev == 1.5
