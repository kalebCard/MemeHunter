"""
Pruebas Unitarias para AgentBiasDaemon (Sprint 37: PB-123).
"""

import os
import pytest
from portfolio.dag_orchestrator import DAGSignalOrchestrator
from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from portfolio.bias_store import BiasStore
from portfolio.agent_bias_daemon import AgentBiasDaemon
from validation.schemas import MarketBiasPosture


class MockBullishAgent(BaseSignalAgent):
    def __init__(self):
        super().__init__(agent_id="mock_bull", agent_type="technical", weight=1.0, active=True)

    def _compute_proposal(self, market_data):
        return AgentProposal(
            agent_id=self.agent_id,
            direction=1,
            confidence=0.85,
            raw_score=0.80,
            metadata={"status": "OK"}
        )


class MockBearishAgent(BaseSignalAgent):
    def __init__(self):
        super().__init__(agent_id="mock_bear", agent_type="technical", weight=1.0, active=True)

    def _compute_proposal(self, market_data):
        return AgentProposal(
            agent_id=self.agent_id,
            direction=-1,
            confidence=0.90,
            raw_score=-0.85,
            metadata={"status": "OK"}
        )


@pytest.fixture
def test_setup(tmp_path):
    store_file = tmp_path / "daemon_bias_test.json"
    bias_store = BiasStore(filepath=str(store_file))

    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.60)
    daemon = AgentBiasDaemon(orchestrator=orchestrator, bias_store=bias_store, default_validity_hours=2.0)
    yield daemon, bias_store
    if os.path.exists(str(store_file)):
        os.remove(str(store_file))


def test_daemon_evaluate_bullish(test_setup):
    daemon, bias_store = test_setup
    daemon.orchestrator.register_agent(MockBullishAgent())

    bias = daemon.evaluate_symbol("DOGE/USDT", market_data={"close": 0.15})

    assert bias.symbol == "DOGE/USDT"
    assert bias.posture == MarketBiasPosture.ALLOW_LONG
    assert bias.confidence >= 0.80

    # Comprobar que quedó registrado en BiasStore
    is_auth, reason = bias_store.is_authorized("DOGE/USDT", side="LONG")
    assert is_auth is True


def test_daemon_evaluate_bearish(test_setup):
    daemon, bias_store = test_setup
    daemon.orchestrator.register_agent(MockBearishAgent())

    bias = daemon.evaluate_symbol("PEPE/USDT", market_data={"close": 0.00001})

    assert bias.symbol == "PEPE/USDT"
    assert bias.posture == MarketBiasPosture.ALLOW_SHORT
    assert bias.confidence >= 0.85

    # Comprobar autorización SHORT vs rechazo LONG
    is_auth_short, _ = bias_store.is_authorized("PEPE/USDT", side="SHORT")
    assert is_auth_short is True

    is_auth_long, reason = bias_store.is_authorized("PEPE/USDT", side="LONG")
    assert is_auth_long is False
    assert "POSTURE_MISMATCH" in reason
