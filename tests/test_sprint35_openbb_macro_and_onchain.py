"""
tests/test_sprint35_openbb_macro_and_onchain.py
-----------------------------------------------
Suite de Pruebas Unitarias y de Certificación para el Sprint 35:
- PB-119: Proveedor de Datos Asíncrono OpenBB y DeFi (data_engine/openbb_provider.py).
- PB-120: Condicionamiento Macro en RegimeHMMAgent y Enrutador DAG (portfolio/agents/regime_agent.py).
"""

import os
import time
import tempfile
import numpy as np
import pandas as pd
import pytest

from data_engine.openbb_provider import OpenBBDataProvider, MacroOnChainContext
from portfolio.agents.regime_agent import RegimeHMMAgent
from portfolio.dag_orchestrator import DAGSignalOrchestrator


@pytest.fixture
def sample_market_df():
    """Genera una serie de datos OHLCV de mercado para pruebas."""
    n = 60
    dates = pd.date_range("2024-01-01", periods=n, freq="4h")
    # Simular tendencia alcista técnica
    close = 100.0 + np.cumsum(np.random.normal(0.5, 0.2, size=n))
    high = close * 1.01
    low = close * 0.99
    open_p = close * 0.995
    volume = np.full(n, 1000.0)

    return pd.DataFrame({
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=dates)


# =============================================================================
# PRUEBAS PB-119: OPENBB DATA PROVIDER & CACHE
# =============================================================================

def test_openbb_provider_cache_and_latency():
    """Verifica que OpenBBDataProvider devuelva datos válidos y que el cache hit sea < 5ms."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "test_openbb_cache.json")
        provider = OpenBBDataProvider(cache_ttl_seconds=3600, cache_path=cache_path)

        # Primer llamado (genera o carga fallback determinista)
        ctx = provider.get_macro_context()
        assert isinstance(ctx, MacroOnChainContext)
        assert ctx.tvl_solana_usd > 0.0
        assert ctx.tvl_ethereum_usd > 0.0
        assert -1.0 <= ctx.macro_sentiment_score <= 1.0

        # Segundo llamado: debe ser un Cache Hit sub-milisegundo (< 5ms)
        t0 = time.perf_counter_ns()
        cached_ctx = provider.get_macro_context()
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6

        assert elapsed_ms < 5.0
        assert cached_ctx.tvl_solana_usd == ctx.tvl_solana_usd
        assert os.path.exists(cache_path)


def test_openbb_provider_disk_persistence():
    """Verifica la persistencia y carga desde archivo JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "disk_cache.json")
        p1 = OpenBBDataProvider(cache_ttl_seconds=3600, cache_path=cache_path)
        ctx1 = p1.get_macro_context()

        # Nuevo proveedor apuntando a la misma ruta de disco
        p2 = OpenBBDataProvider(cache_ttl_seconds=3600, cache_path=cache_path)
        ctx2 = p2.get_macro_context()

        assert ctx2.source == ctx1.source
        assert ctx2.tvl_solana_usd == ctx1.tvl_solana_usd


# =============================================================================
# PRUEBAS PB-120: CONDICIONAMIENTO MACRO EN REGIME AGENT Y DAG
# =============================================================================

def test_regime_agent_macro_bear_discount(sample_market_df):
    """
    Verifica que ante una contracción macro o caída de TVL severa (PB-120),
    el RegimeHMMAgent penalice la probabilidad alcista p_bull para evitar trampas de toros.
    """
    agent = RegimeHMMAgent()

    # Caso 1: Escenario Nominal sin macro
    prop_nominal = agent.evaluate({"df": sample_market_df})
    p_bull_nominal = prop_nominal.metadata["probabilities"]["p_bull"]

    # Caso 2: Mismo gráfico técnico alcista, pero con contracción macro severa (TVL cayendo)
    bear_macro = MacroOnChainContext(
        tvl_solana_usd=4e9,
        tvl_ethereum_usd=45e9,
        tvl_24h_change_pct=-5.5,
        macro_sentiment_score=-0.65,
        is_bear_contraction=True,
        source="TEST_MOCK_BEAR"
    )

    prop_discounted = agent.evaluate({
        "df": sample_market_df,
        "macro_context": bear_macro
    })
    p_bull_discounted = prop_discounted.metadata["probabilities"]["p_bull"]
    p_bear_discounted = prop_discounted.metadata["probabilities"]["p_bear"]

    # Debe haber un descuento significativo en p_bull
    assert p_bull_discounted < p_bull_nominal
    # Debe elevarse la probabilidad de cautela / oso
    assert p_bear_discounted > prop_nominal.metadata["probabilities"]["p_bear"]
    # La metadata debe registrar el contexto macro
    assert "macro_onchain" in prop_discounted.metadata
    assert prop_discounted.metadata["macro_onchain"]["is_bear_contraction"] is True


def test_regime_agent_macro_expansion(sample_market_df):
    """Verifica que un entorno de fuerte expansión de liquidez beneficie a p_bull."""
    agent = RegimeHMMAgent()

    bull_macro = MacroOnChainContext(
        tvl_solana_usd=6e9,
        tvl_ethereum_usd=60e9,
        tvl_24h_change_pct=4.2,
        macro_sentiment_score=0.75,
        is_bear_contraction=False,
        source="TEST_MOCK_BULL"
    )

    prop_bull = agent.evaluate({
        "df": sample_market_df,
        "macro_context": bull_macro
    })

    assert prop_bull.metadata["probabilities"]["p_bull"] > 0.40
    assert prop_bull.metadata["macro_onchain"]["macro_sentiment_score"] == 0.75


def test_dag_orchestrator_integration_with_macro(sample_market_df):
    """Verifica que el Orquestador DAG transmita el contexto macro en el ciclo de inferencia."""
    provider = OpenBBDataProvider(cache_ttl_seconds=3600)
    # Pre-calentar caché para no incurrir en latencia HTTP en la prueba de SLA (<20ms)
    provider.get_macro_context()

    regime_agent = RegimeHMMAgent(openbb_provider=provider)

    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.50)
    orchestrator.register_agent(regime_agent)

    t0 = time.perf_counter_ns()
    vector_alpha = orchestrator.run_inference_cycle({"df": sample_market_df})
    cycle_ms = (time.perf_counter_ns() - t0) / 1e6

    # SLA estricto del DAG: menos de 20 ms
    assert cycle_ms < 20.0
    assert vector_alpha.inference_cycle_ms < 20.0
    assert "regime_hmm_agent" in vector_alpha.agent_proposals

    agent_meta = vector_alpha.agent_proposals["regime_hmm_agent"]["metadata"]
    assert "macro_onchain" in agent_meta
    assert "tvl_solana_usd" in agent_meta["macro_onchain"]
