"""
tests/test_sprint43_pipeline_e2e.py - Suite E2E de Validación de Pipeline Integral (Sprint 43: PB-142).
Certifica el flujo holístico:
Market Data -> DAG Kahn Ingestion -> Bayesian VectorAlpha -> Slow Brain BiasStore -> Fast Brain Gatekeeper -> KillSwitch.
"""

import os
import time
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from portfolio.dag_orchestrator import DAGSignalOrchestrator
from portfolio.agents.regime_agent import RegimeHMMAgent
from portfolio.agents.technical_agent import TechnicalMicroAgent
from portfolio.bias_store import BiasStore
from validation.schemas import MarketBiasSchema, MarketBiasPosture
from portfolio.kill_switch import EmergencyKillSwitch, KillSwitchLevel
from portfolio.execution_gatekeeper import ExecutionGatekeeper


def generate_market_data(n_bars: int = 60, trend: str = "bull") -> pd.DataFrame:
    """Genera serie sintética determinista OHLCV."""
    np.random.seed(1337)
    base = 50.0
    steps = np.random.normal(0.4 if trend == "bull" else -0.4, 0.3, n_bars)
    close = base + np.cumsum(steps)
    high = close + np.random.uniform(0.1, 0.3, n_bars)
    low = close - np.random.uniform(0.1, 0.3, n_bars)
    volume = np.random.uniform(2000.0, 8000.0, n_bars)
    return pd.DataFrame({
        "open": close - steps,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })


def test_full_pipeline_e2e_lifecycle(tmp_path):
    """
    PB-142: Flujo end-to-end completo:
    1. Ingesta y clasificación en DAG
    2. Emisión de directiva slow-brain a BiasStore
    3. Gatekeeper verifica autorización en fast-brain
    4. KillSwitch interviene y aborta operaciones
    """
    db_file = str(tmp_path / "alpha_factory.db")
    bias_json = str(tmp_path / "market_bias.json")
    ks_file = str(tmp_path / "kill_switch_state.json")

    # 1. Instanciación y topología del DAG
    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.60)
    regime_node = RegimeHMMAgent(agent_id="regime_classifier")
    tech_node = TechnicalMicroAgent(agent_id="tech_momentum")

    orchestrator.register_agent(regime_node, layer="input")
    orchestrator.register_agent(tech_node, dependencies=["regime_classifier"], layer="processing")

    # Verificar que el orden topológico sitúa tech_momentum después de regime_classifier
    topo_order = orchestrator.topological_sort()
    assert topo_order.index("tech_momentum") > topo_order.index("regime_classifier")

    # 2. Ejecutar inferencia en el DAG
    market_df = generate_market_data(60, trend="bull")
    vector_alpha = orchestrator.run_inference_cycle(market_df)

    assert vector_alpha.inference_cycle_ms > 0.0
    assert vector_alpha.regime_state is not None
    assert "regime_classifier" in vector_alpha.agent_proposals

    # 3. Emisión de Directiva del Slow Brain hacia BiasStore
    bias_store = BiasStore(filepath=bias_json, db_path=db_file)
    now = datetime.now(timezone.utc)
    valid_until = (now + timedelta(hours=2)).isoformat()

    posture = MarketBiasPosture.ALLOW_LONG if vector_alpha.direction >= 0 else MarketBiasPosture.ALLOW_SHORT

    directive = MarketBiasSchema(
        symbol="PEPE/USDT",
        posture=posture,
        confidence=0.88,
        consensus_score=0.85,
        valid_until_utc=valid_until,
        metadata={"cycle": orchestrator.cycle_count, "decision": vector_alpha.decision}
    )

    saved = bias_store.save_bias(directive)
    assert saved is True
    assert os.path.exists(bias_json)
    assert os.path.exists(db_file)

    # 4. Fast Brain Gatekeeper Consulta BiasStore
    kill_switch = EmergencyKillSwitch(state_file=ks_file)
    gatekeeper = ExecutionGatekeeper(kill_switch=kill_switch)

    # Evaluación normal para Long en BiasStore
    auth_allowed, reason = bias_store.is_authorized("PEPE/USDT", side="buy")
    assert auth_allowed is True
    assert reason == "AUTHORIZED"

    # Verificación de que side contrario es bloqueado por BiasStore
    auth_denied, reason_denied = bias_store.is_authorized("PEPE/USDT", side="sell")
    assert auth_denied is False
    assert "POSTURE_MISMATCH" in reason_denied

    # Auditoría por el Gatekeeper de Broker (Stoploss y límites duros)
    ok_gk, reason_gk = gatekeeper.intercept_order(
        symbol="PEPE/USDT",
        side="buy",
        order_size_usdt=20.0,
        price=0.000015,
        stoploss_pct=-0.04,
        current_open_trades=0
    )
    assert ok_gk is True
    assert reason_gk == "APPROVED_FOR_DISPATCH"

    # 5. Intervención de Emergencia Kill-Switch
    kill_switch.trigger(target_level=KillSwitchLevel.LEVEL_1_SOFT_LOCK, reason="Flash crash detectado en mercado global")
    assert kill_switch.is_active is True

    # Gatekeeper debe vetar de inmediato cualquier nueva entrada
    gk_allowed, gk_reason = gatekeeper.intercept_order(
        symbol="PEPE/USDT",
        side="buy",
        order_size_usdt=20.0,
        price=0.000015,
        stoploss_pct=-0.04,
        current_open_trades=0
    )
    assert gk_allowed is False
    assert "KILL_SWITCH" in gk_reason

    # 6. Reset del Kill-Switch con token autenticado
    success_reset = kill_switch.reset(auth_token="secure_reset_token", expected_token="secure_reset_token")
    assert success_reset is True
    assert kill_switch.is_active is False

    gk_allowed_restored, gk_reason_restored = gatekeeper.intercept_order(
        symbol="PEPE/USDT",
        side="buy",
        order_size_usdt=20.0,
        price=0.000015,
        stoploss_pct=-0.04,
        current_open_trades=0
    )
    assert gk_allowed_restored is True
    assert gk_reason_restored == "APPROVED_FOR_DISPATCH"


def test_pipeline_ttl_expiration(tmp_path):
    """PB-142: Certifica que una directiva con TTL expirado es vetada automáticamente."""
    db_file = str(tmp_path / "alpha_factory.db")
    bias_json = str(tmp_path / "market_bias.json")

    bias_store = BiasStore(filepath=bias_json, db_path=db_file)
    # Directiva expirada hace 10 segundos
    expired_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()

    expired_bias = MarketBiasSchema(
        symbol="FLOKI/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.85,
        consensus_score=0.90,
        valid_until_utc=expired_time,
        metadata={"test": "expired_ttl"}
    )
    bias_store.save_bias(expired_bias)

    is_auth, reason = bias_store.is_authorized("FLOKI/USDT", side="buy")
    assert is_auth is False
    assert "BIAS_EXPIRED" in reason
