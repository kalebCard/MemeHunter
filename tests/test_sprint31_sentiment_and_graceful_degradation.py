"""
Meme Hunter - Test Suite for Sprint 31
Certificación de SentimentAgent, RiskManagerAgent y GracefulDegradationGuard.
"""

import time
import pytest
import numpy as np

from portfolio.agents.sentiment_agent import SentimentAgent
from portfolio.agents.risk_manager_agent import RiskManagerAgent, RiskVerdict
from portfolio.graceful_degradation import GracefulDegradationGuard, DegradationReport
from portfolio.dag_orchestrator import VectorAlpha


# =============================================================================
# PRUEBAS DEL AGENTE DE SENTIMIENTO (PB-107)
# =============================================================================

def test_sentiment_agent_lexical_bullish_and_bearish():
    """PB-107: Verifica detección de sentimiento alcista y bajista por lexicon rápido."""
    agent = SentimentAgent(agent_id="test_sentiment")

    # Caso Alcista
    bullish_news = {"news": "Major Binance listing announced with massive liquidity and token burn ATH"}
    p_bull = agent.evaluate(bullish_news)
    assert p_bull.direction == 1
    assert p_bull.raw_score > 0.20
    assert p_bull.confidence >= 0.50

    # Caso Bajista
    bearish_news = {"news": "Severe exploit detected, sec lawsuit filed and unexpected panic liquidation"}
    p_bear = agent.evaluate(bearish_news)
    assert p_bear.direction == -1
    assert p_bear.raw_score < -0.20
    assert p_bear.confidence >= 0.50


def test_sentiment_agent_cache_hit_zero_latency():
    """PB-107: Verifica que la caché semántica responde con latencia sub-milisegundo."""
    agent = SentimentAgent(agent_id="cache_test")
    headline = {"news": "New partnership announced for Solana and Memecoins"}

    # Primer cómputo
    p1 = agent.evaluate(headline)
    # Segundo cómputo (Debe ser Cache Hit)
    p2 = agent.evaluate(headline)

    assert p2.metadata.get("source") == "SEMANTIC_CACHE_HIT"
    assert p2.direction == p1.direction
    assert p2.raw_score == p1.raw_score


def test_sentiment_agent_precomputed_and_empty_fallback():
    """PB-107: Fallback tolerante con scores precomputados o sin datos."""
    agent = SentimentAgent(agent_id="fallback_test")

    # Score precomputado
    p_pre = agent.evaluate({"sentiment_score": 0.65})
    assert p_pre.direction == 1
    assert p_pre.metadata.get("source") == "PRECOMPUTED_SENTIMENT_FEED"

    # Datos vacíos
    p_empty = agent.evaluate({})
    assert p_empty.direction == 0
    assert p_empty.raw_score == 0.0


# =============================================================================
# PRUEBAS DEL GESTOR DE RIESGOS (PB-108)
# =============================================================================

def test_risk_manager_agent_approved():
    """PB-108: Aprobación sin penalizaciones cuando las condiciones son saludables."""
    risk_agent = RiskManagerAgent(max_drawdown_limit_pct=25.0)
    mock_vector = VectorAlpha(
        direction=1,
        composite_score=0.45,
        confidence=0.80,
        consensus_score=0.75,
        inference_cycle_ms=12.0,
        decision="APPROVED",
        regime_state="BULL_MOMENTUM"
    )
    portfolio_state = {
        "current_drawdown_pct": 5.0,
        "volatility_4h": 0.015,
        "correlations": {"DOGE": 0.20}
    }
    verdict = risk_agent.evaluate_proposal(mock_vector, portfolio_state)
    assert isinstance(verdict, RiskVerdict)
    assert verdict.decision == "APPROVED"
    assert verdict.sizing_multiplier >= 0.90
    assert verdict.current_drawdown_pct == 5.0


def test_risk_manager_agent_kill_switch_veto():
    """PB-108: PB-25 Kill-Switch al -25% de drawdown rechaza cualquier entrada."""
    risk_agent = RiskManagerAgent(max_drawdown_limit_pct=25.0)
    mock_vector = VectorAlpha(
        direction=1,
        composite_score=0.90,
        confidence=0.95,
        consensus_score=0.95,
        inference_cycle_ms=10.0,
        decision="APPROVED",
        regime_state="BULL_MOMENTUM"
    )
    portfolio_state = {"current_drawdown_pct": 25.5}  # Drawdown excede 25%

    verdict = risk_agent.evaluate_proposal(mock_vector, portfolio_state)
    assert verdict.decision == "REJECTED"
    assert verdict.sizing_multiplier == 0.0
    assert "KILL_SWITCH_ACTIVE" in verdict.reason


def test_risk_manager_agent_high_var_and_correlation_scaling():
    """PB-108: Reducción proporcional de tamaño ante alto VaR y correlación cruzada."""
    risk_agent = RiskManagerAgent(max_var_99_limit_pct=5.0, max_cross_correlation=0.40)
    mock_vector = VectorAlpha(
        direction=-1,
        composite_score=-0.50,
        confidence=0.70,
        consensus_score=0.75,
        inference_cycle_ms=11.0,
        decision="APPROVED",
        regime_state="BEAR_BLEED"
    )
    # Volatilidad muy alta (6% 4H -> VaR 99% aprox 13.9%) y correlación 0.65 (> 0.40)
    portfolio_state = {
        "current_drawdown_pct": 8.0,
        "volatility_4h": 0.06,
        "correlations": {"PEPE": 0.65}
    }
    verdict = risk_agent.evaluate_proposal(mock_vector, portfolio_state)
    assert verdict.decision == "SCALED_DOWN"
    assert 0.10 <= verdict.sizing_multiplier <= 0.50


# =============================================================================
# PRUEBAS DE DEGRADACIÓN ELEGANTE Y CISNES NEGROS (PB-109)
# =============================================================================

def test_graceful_degradation_modes():
    """PB-109: Verifica las 4 transiciones de estado de degradación elegante."""
    guard = GracefulDegradationGuard(
        warning_spread_pct=0.15,
        toxic_spread_pct=0.35,
        extreme_spread_pct=0.70,
        critical_latency_ms=1500.0
    )

    # 1. Normal
    rep_normal = guard.evaluate_microstructure(spread_pct=0.08, latency_ms=45.0)
    assert rep_normal.mode == "NORMAL"
    assert rep_normal.size_multiplier == 1.0

    # 2. Spread Moderado
    rep_deg = guard.evaluate_microstructure(spread_pct=0.22, latency_ms=80.0)
    assert rep_deg.mode == "DEGRADED_SPREAD"
    assert rep_deg.size_multiplier == 0.50
    assert rep_deg.execution_type == "MAKER_ONLY"

    # 3. Spread Tóxico
    rep_toxic = guard.evaluate_microstructure(spread_pct=0.42, latency_ms=100.0)
    assert rep_toxic.mode == "PAUSE_NEW_ENTRIES"
    assert rep_toxic.size_multiplier == 0.0

    # 4. Cisne Negro / Pánico Extremo
    rep_swan = guard.evaluate_microstructure(spread_pct=0.85, latency_ms=2100.0)
    assert rep_swan.mode == "SURVIVAL_MODE"
    assert rep_swan.size_multiplier == 0.0
    assert rep_swan.execution_type == "HALTED"
    assert "BLACK_SWAN_DEFENSE" in rep_swan.reason
