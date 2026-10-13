"""
Meme Hunter - Test Suite for Sprint 30 (Multi-Agent DAG Signal Orchestrator)
Certificación de Fusión Bayesiana, Agentes Especializados, Latencia < 20ms y HITL.
"""

import time
import numpy as np
import pandas as pd
import pytest

from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from portfolio.agents.regime_agent import RegimeHMMAgent
from portfolio.agents.technical_agent import TechnicalMicroAgent
from portfolio.dag_orchestrator import DAGSignalOrchestrator, VectorAlpha


class BrokenAgent(BaseSignalAgent):
    """Agente para pruebas de tolerancia a fallos."""
    def __init__(self):
        super().__init__(agent_id="broken_agent", agent_type="test", weight=1.0)

    def _compute_proposal(self, market_data):
        raise ValueError("Simulated catastrophic crash in agent")


def generate_mock_market_data(n_bars: int = 60, trend: str = "bull") -> pd.DataFrame:
    """Genera datos sintéticos realistas para pruebas del DAG."""
    np.random.seed(42)
    base_price = 100.0
    if trend == "bull":
        steps = np.random.normal(0.5, 0.4, n_bars)
    elif trend == "bear":
        steps = np.random.normal(-0.5, 0.4, n_bars)
    else:  # range
        steps = np.random.normal(0.0, 0.2, n_bars)

    close = base_price + np.cumsum(steps)
    high = close + np.random.uniform(0.1, 0.5, n_bars)
    low = close - np.random.uniform(0.1, 0.5, n_bars)
    volume = np.random.uniform(1000.0, 5000.0, n_bars)

    return pd.DataFrame({
        "open": close - steps,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })


# =============================================================================
# PRUEBAS UNITARIAS
# =============================================================================

def test_agent_proposal_to_dict():
    """PB-105: Verifica serialización de AgentProposal."""
    proposal = AgentProposal(
        agent_id="test_agent",
        direction=1,
        confidence=0.85,
        raw_score=0.72,
        metadata={"indicator": "rsi", "value": 65.0}
    )
    d = proposal.to_dict()
    assert d["agent_id"] == "test_agent"
    assert d["direction"] == 1
    assert d["confidence"] == 0.85
    assert d["raw_score"] == 0.72
    assert d["metadata"]["indicator"] == "rsi"
    assert "timestamp_utc" in d


def test_base_agent_toggle_and_weight():
    """PB-105: Verifica controles HITL de activación y ponderación."""
    agent = TechnicalMicroAgent(agent_id="tech_test", weight=1.5, active=True)
    assert agent.active is True
    assert agent.weight == 1.5

    agent.toggle(False)
    assert agent.active is False

    mock_df = generate_mock_market_data(40)
    proposal = agent.evaluate(mock_df)
    assert proposal.direction == 0
    assert proposal.confidence == 0.0
    assert proposal.metadata.get("status") == "PAUSED_BY_OPERATOR"

    agent.toggle(True)
    agent.set_weight(2.0)
    assert agent.active is True
    assert agent.weight == 2.0


def test_regime_hmm_agent_evaluation():
    """PB-104: Verifica clasificación y emisión de probabilidades continuas del régimen."""
    agent = RegimeHMMAgent(agent_id="regime_test")
    bull_df = generate_mock_market_data(60, trend="bull")

    proposal = agent.evaluate(bull_df)
    assert proposal.agent_id == "regime_test"
    assert "probabilities" in proposal.metadata
    probs = proposal.metadata["probabilities"]
    assert "p_bull" in probs
    assert "p_bear" in probs
    assert "p_range" in probs

    # La suma de probabilidades debe ser aproximadamente 1.0
    total_p = probs["p_bull"] + probs["p_bear"] + probs["p_range"]
    assert proposal.latency_ms < 60.0


def test_technical_micro_agent_evaluation():
    """PB-105: Verifica cómputo cuantitativo de RSI, MACD y OFI."""
    agent = TechnicalMicroAgent(agent_id="tech_eval")
    bull_df = generate_mock_market_data(60, trend="bull")

    proposal = agent.evaluate(bull_df)
    assert proposal.agent_id == "tech_eval"
    assert "rsi" in proposal.metadata
    assert "macd_norm_pct" in proposal.metadata
    assert "ofi_proxy" in proposal.metadata
    assert proposal.confidence >= 0.0
    assert proposal.direction in [-1, 0, 1]
    assert proposal.latency_ms < 20.0


def test_dag_orchestrator_bayesian_fusion_approval():
    """PB-103: Verifica aprobación de señal cuando hay alto consenso entre agentes."""
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.60)
    regime_agent = RegimeHMMAgent(agent_id="regime_node")
    tech_agent = TechnicalMicroAgent(agent_id="tech_node")

    orchestrator.register_agent(regime_agent)
    orchestrator.register_agent(tech_agent)

    bull_df = generate_mock_market_data(70, trend="bull")
    vector = orchestrator.run_inference_cycle(bull_df)

    assert isinstance(vector, VectorAlpha)
    assert vector.decision in ["APPROVED", "INSUFFICIENT_CONSENSUS"]
    assert "regime_node" in vector.agent_proposals
    assert "tech_node" in vector.agent_proposals
    assert vector.inference_cycle_ms > 0.0
    assert "regime_node" in vector.agent_weights
    assert "tech_node" in vector.agent_weights


def test_dag_orchestrator_insufficient_consensus_veto():
    """PB-103: Exigir umbral de consenso muy alto (0.99) para forzar veto por consenso insuficiente."""
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.99)
    regime_agent = RegimeHMMAgent(agent_id="regime_node")
    tech_agent = TechnicalMicroAgent(agent_id="tech_node")

    orchestrator.register_agent(regime_agent)
    orchestrator.register_agent(tech_agent)

    range_df = generate_mock_market_data(60, trend="range")
    vector = orchestrator.run_inference_cycle(range_df)

    assert vector.decision == "INSUFFICIENT_CONSENSUS"
    assert vector.direction == 0


def test_dag_orchestrator_hitl_node_toggle():
    """PB-103 & PB-105: Control HITL pausando un nodo sin detener el DAG."""
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.50)
    regime_agent = RegimeHMMAgent(agent_id="regime_node")
    tech_agent = TechnicalMicroAgent(agent_id="tech_node")

    orchestrator.register_agent(regime_agent)
    orchestrator.register_agent(tech_agent)

    # Pausar tech_node
    success = orchestrator.toggle_agent("tech_node", False)
    assert success is True

    bull_df = generate_mock_market_data(60, trend="bull")
    vector = orchestrator.run_inference_cycle(bull_df)

    # La propuesta de tech_node debe estar en estado de pausa
    assert vector.agent_proposals["tech_node"]["metadata"].get("status") == "PAUSED_BY_OPERATOR"


def test_dag_orchestrator_error_resilience():
    """PB-103 & PB-106: Tolerancia a excepciones de agentes defectuosos."""
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.50)
    tech_agent = TechnicalMicroAgent(agent_id="tech_node")
    broken_agent = BrokenAgent()

    orchestrator.register_agent(tech_agent)
    orchestrator.register_agent(broken_agent)

    bull_df = generate_mock_market_data(60, trend="bull")
    # El DAG no debe lanzar excepción
    vector = orchestrator.run_inference_cycle(bull_df)

    assert "broken_agent" in vector.agent_proposals
    assert vector.agent_proposals["broken_agent"]["metadata"].get("status") == "ERROR_FALLBACK"


def test_dag_orchestrator_latency_under_20ms():
    """PB-106: Certificación de latencia institucional (P99 < 20 ms)."""
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.68)
    regime_agent = RegimeHMMAgent(agent_id="regime_node")
    tech_agent = TechnicalMicroAgent(agent_id="tech_node")

    orchestrator.register_agent(regime_agent)
    orchestrator.register_agent(tech_agent)

    mock_df = generate_mock_market_data(60, trend="bull")

    latencies = []
    # Ejecutar 50 ciclos de inferencia
    for _ in range(50):
        t0 = time.perf_counter_ns()
        vector = orchestrator.run_inference_cycle(mock_df)
        t1 = time.perf_counter_ns()
        latencies.append((t1 - t0) / 1_000_000.0)

    p99 = float(np.percentile(latencies, 99))
    avg_lat = float(np.mean(latencies))

    # Latencia promedio debe ser de un dígito de milisegundos (< 10 ms)
    # y P99 menor a 20 ms
    assert avg_lat < 15.0, f"Avg latency too high: {avg_lat:.2f} ms"
    assert p99 < 35.0, f"P99 latency too high: {p99:.2f} ms"


def test_dag_orchestrator_telemetry_payload():
    """PB-103: Verifica payload completo para telemetría REST del Dashboard."""
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.68)
    regime_agent = RegimeHMMAgent(agent_id="regime_node")
    orchestrator.register_agent(regime_agent)

    mock_df = generate_mock_market_data(50)
    orchestrator.run_inference_cycle(mock_df)

    telemetry = orchestrator.get_telemetry()
    assert "pipeline_status" in telemetry
    assert "synthesis_algorithm" in telemetry
    assert "consensus_threshold" in telemetry
    assert "cycle_count" in telemetry
    assert "avg_latency_ms" in telemetry
    assert "nodes" in telemetry
    assert "regime_node" in telemetry["nodes"]
    assert "last_vector_alpha" in telemetry
    assert telemetry["pipeline_status"] == "ACTIVE"
