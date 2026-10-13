"""
tests/test_e2e_four_tier_architecture.py - Certificación E2E de la Arquitectura de 4 Capas (Sprint 39: PB-131).
Valida la integración completa del sistema:
- Capa 1: Cortafuegos de Datos (Pydantic v2 & Gap Detector).
- Capa 2: Cerebro Lento (Desacoplamiento Asíncrono & MarketBiasSchema).
- Capa 3: Cerebro Rápido (Gatillo Determinista & Filtro de Rentabilidad Pre-Trade).
- Capa 4: Kill Switch Absoluto (AI Output Guard & Execution Gatekeeper).
"""

import os
import pytest
from datetime import datetime, timezone, timedelta

# Capa 1: Cortafuegos
from validation.schemas import MarketCandleSchema, MarketBiasPosture, MarketBiasSchema
from validation.data_firewall import DataFirewallGuard, FirewallMode

# Capa 2: Cerebro Lento
from portfolio.dag_orchestrator import DAGSignalOrchestrator
from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from portfolio.bias_store import BiasStore
from portfolio.agent_bias_daemon import AgentBiasDaemon

# Capa 3: Cerebro Rápido
from portfolio.pre_trade_profitability import PreTradeProfitabilityGate

# Capa 4: Kill Switch Absoluto
from validation.ai_output_guard import AIOutputGuard
from portfolio.kill_switch import EmergencyKillSwitch, KillSwitchLevel
from portfolio.execution_gatekeeper import ExecutionGatekeeper


class E2EBullishAgent(BaseSignalAgent):
    def __init__(self):
        super().__init__(agent_id="e2e_bull", agent_type="technical", weight=1.0, active=True)

    def _compute_proposal(self, market_data):
        return AgentProposal(
            agent_id=self.agent_id,
            direction=1,
            confidence=0.88,
            raw_score=0.85,
            metadata={"status": "OK"}
        )


@pytest.fixture
def e2e_system(tmp_path):
    store_file = tmp_path / "e2e_market_bias.json"
    ks_file = tmp_path / "e2e_ks_state.json"

    firewall = DataFirewallGuard()
    bias_store = BiasStore(filepath=str(store_file))

    orchestrator = DAGSignalOrchestrator(consensus_threshold=0.60)
    orchestrator.register_agent(E2EBullishAgent())

    daemon = AgentBiasDaemon(
        orchestrator=orchestrator,
        bias_store=bias_store,
        default_validity_hours=4.0,
        min_confidence_to_authorize=0.70
    )

    profit_gate = PreTradeProfitabilityGate(default_safety_multiplier=2.5)
    output_guard = AIOutputGuard()

    kill_switch = EmergencyKillSwitch(
        max_intraday_drawdown_pct=3.5,
        max_1h_loss_pct=1.5,
        state_file=str(ks_file)
    )

    gatekeeper = ExecutionGatekeeper(
        kill_switch=kill_switch,
        max_concurrent_slots=3,
        min_notional_usdt=5.0
    )

    yield {
        "firewall": firewall,
        "bias_store": bias_store,
        "daemon": daemon,
        "profit_gate": profit_gate,
        "output_guard": output_guard,
        "kill_switch": kill_switch,
        "gatekeeper": gatekeeper
    }

    for f in [store_file, ks_file]:
        if os.path.exists(str(f)):
            os.remove(str(f))


def test_e2e_happy_path_pipeline(e2e_system):
    """
    Ruta Dorada: Datos limpios -> Agente autoriza -> Setup rentable -> Gatekeeper aprueba orden.
    """
    sys = e2e_system
    step_4h = 4 * 3600 * 1000
    start_ts = 1700000000000

    # 1. CAPA 1: Cortafuegos de Datos valida velas sanas
    raw_candles = [
        {
            "timestamp_ms": start_ts + i * step_4h,
            "open": 0.150 + i * 0.001,
            "high": 0.155 + i * 0.001,
            "low": 0.148 + i * 0.001,
            "close": 0.152 + i * 0.001,
            "volume": 10000.0
        }
        for i in range(12)
    ]
    now_ms = start_ts + 11 * step_4h + 1000
    ok_data, valid_candles, _ = sys["firewall"].validate_timeseries(
        symbol="DOGE/USDT",
        candles_raw=raw_candles,
        timeframe="4h",
        current_time_ms=now_ms
    )
    assert ok_data is True
    assert sys["firewall"].current_mode == FirewallMode.NORMAL

    # 2. CAPA 2: Cerebro Lento evalúa y emite autorización en JSON
    bias = sys["daemon"].evaluate_symbol("DOGE/USDT", market_data=valid_candles)
    assert bias.posture == MarketBiasPosture.ALLOW_LONG
    assert bias.confidence >= 0.80

    # 3. CAPA 3: Cerebro Rápido consulta sesgo y evalúa rentabilidad pre-trade
    is_auth, _ = sys["bias_store"].is_authorized("DOGE/USDT", side="LONG")
    assert is_auth is True

    # Filtro de rentabilidad con spread institucional bajo (0.10%)
    profit_dec = sys["profit_gate"].evaluate_entry(
        symbol="DOGE/USDT",
        current_price=0.152,
        target_price=0.159,  # +4.6% ganancia esperada
        spread_pct=0.0010    # 0.10%
    )
    assert profit_dec.is_approved is True

    # 4. CAPA 4: Gatekeeper valida límites duros y stop-loss obligatorio
    ok_dispatch, reason_dispatch = sys["gatekeeper"].intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.152,
        stoploss_pct=-0.030, # -3.0% stoploss en código
        current_open_trades=1,
        intraday_drawdown_pct=0.8
    )
    assert ok_dispatch is True
    assert reason_dispatch == "APPROVED_FOR_DISPATCH"


def test_e2e_blocked_at_tier1_data_gap(e2e_system):
    """
    Falla en Capa 1: Hueco temporal (Gap) en datos detiene el sistema en Standby antes del LLM.
    """
    sys = e2e_system
    step_4h = 4 * 3600 * 1000
    start_ts = 1700000000000

    # Inyectar un salto de tiempo (falta la vela 6)
    corrupted_candles = [
        {
            "timestamp_ms": start_ts + (i if i < 6 else i + 2) * step_4h,
            "open": 0.15,
            "high": 0.16,
            "low": 0.14,
            "close": 0.155,
            "volume": 5000.0
        }
        for i in range(10)
    ]

    ok_data, _, reason = sys["firewall"].validate_timeseries(
        symbol="DOGE/USDT",
        candles_raw=corrupted_candles,
        timeframe="4h",
        current_time_ms=start_ts + 12 * step_4h
    )

    # El cortafuegos detecta el gap y frena el pipeline
    assert ok_data is False
    assert sys["firewall"].current_mode == FirewallMode.GAP_DETECTED_STANDBY
    assert "GAP TEMPORAL DETECTADO" in reason


def test_e2e_blocked_at_tier3_toxic_spread(e2e_system):
    """
    Falla en Capa 3: Autorización concedida, pero spread tóxico del 0.70% destruye el trade.
    """
    sys = e2e_system

    # Simular autorización activa
    future = datetime.now(timezone.utc) + timedelta(hours=4)
    sys["bias_store"].save_bias(MarketBiasSchema(
        symbol="PEPE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.85,
        consensus_score=0.90,
        valid_until_utc=future.isoformat()
    ))

    # Filtro de rentabilidad con spread tóxico
    profit_dec = sys["profit_gate"].evaluate_entry(
        symbol="PEPE/USDT",
        current_price=0.00001,
        target_price=0.0000102, # +2.0%
        spread_pct=0.0070       # 0.70% de spread destruye el trade!
    )

    assert profit_dec.is_approved is False
    assert "FRICCION_EXCESIVA" in profit_dec.rejection_reason


def test_e2e_blocked_at_tier4_missing_stoploss_or_drawdown(e2e_system):
    """
    Falla en Capa 4: Kill switch bloquea orden sin stop-loss o ante drawdown intradía.
    """
    sys = e2e_system

    # 1. Falta de stop-loss obligatorio
    ok_no_sl, reason_no_sl = sys["gatekeeper"].intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.15,
        stoploss_pct=None # Falta stoploss!
    )
    assert ok_no_sl is False
    assert "MANDATORY_STOPLOSS_MISSING" in reason_no_sl

    # 2. Drawdown intradía extremo (5.2%) dispara corte total
    ok_dd, reason_dd = sys["gatekeeper"].intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.15,
        stoploss_pct=-0.030,
        intraday_drawdown_pct=5.20
    )
    assert ok_dd is False
    assert "KILL_SWITCH_ACTIVE" in reason_dd
    assert sys["kill_switch"].current_level == KillSwitchLevel.LEVEL_3_HARD_CUT
