"""
Suite de Pruebas de Caos (Chaos Testing) e Inyección de Fallos para MemeHunter 2026.
US-5.1, US-5.2, US-5.3 (Sprint 5).

Verifica:
1. Centinela Anti-Manipulación (Volume-to-Depth Imbalance, Divergencia Cross-Exchange, Funding extremo, Pump & Dump).
2. Gobernanza de LLM 2026 (Presupuesto diario en USD, Circuit Breaker al 90%, Fallback ante cortes de red).
3. Kill-Switch de Emergencia Institucional (Disparadores automáticos, Liquidación masiva en < 1 segundo, Resistencia a fallos).
"""

import os
import time
import pytest
import urllib.error
from unittest.mock import MagicMock, patch

from portfolio.adversarial_sentinel import AdversarialMarketSentinel, AdversarialAuditResult
from mining.llm_client import OpenRouterClient, OpenRouterModel
from portfolio.kill_switch import EmergencyKillSwitch, KillSwitchLevel


# ==============================================================================
# 1. PRUEBAS DE CENTINELA ANTI-MANIPULACIÓN (US-5.1)
# ==============================================================================

def test_volume_to_depth_imbalance():
    """Detecta volúmenes artificiales o vacíos de liquidez donde el ratio excede 10.0x."""
    sentinel = AdversarialMarketSentinel(max_vol_to_depth_ratio=10.0)

    # Caso seguro: $500k volumen en $100k bids + $100k asks (ratio = 2.5x)
    safe, ratio, _ = sentinel.check_volume_to_depth_imbalance("PEPEUSDT", 500_000.0, 100_000.0, 100_000.0)
    assert safe is True
    assert ratio == 2.5

    # Caso tóxico (manipulación/wash trading): $3,000,000 en sólo $50k + $50k (ratio = 30x)
    unsafe, ratio_toxic, msg = sentinel.check_volume_to_depth_imbalance("PUMPUSDT", 3_000_000.0, 50_000.0, 50_000.0)
    assert unsafe is False
    assert ratio_toxic == 30.0
    assert "ALERTA Volume-to-Depth Imbalance" in msg


def test_cross_exchange_divergence():
    """Detecta desacoplamiento o manipulación unilateral frente al índice Spot/DEX."""
    sentinel = AdversarialMarketSentinel(max_price_divergence_pct=0.80)

    # Caso seguro: futuros 1.005 vs índice 1.000 (divergencia = 0.50% <= 0.80%)
    safe, div, _ = sentinel.check_cross_exchange_divergence(1.005, 1.000)
    assert safe is True
    assert pytest.approx(div, rel=1e-3) == 0.50

    # Caso anómalo: futuros 1.015 vs índice 1.000 (divergencia = 1.50% > 0.80%)
    unsafe, div_high, msg = sentinel.check_cross_exchange_divergence(1.015, 1.000)
    assert unsafe is False
    assert pytest.approx(div_high, rel=1e-3) == 1.50
    assert "ALERTA Divergencia Cross-Exchange" in msg


def test_funding_rate_imbalance():
    """Rechaza memecoins con funding rate excesivo (> +- 0.20% por intervalo)."""
    sentinel = AdversarialMarketSentinel(max_funding_imbalance_pct=0.20)

    # Caso normal (+0.02%)
    safe, _, _ = sentinel.check_funding_rate_imbalance(0.02)
    assert safe is True

    # Caso trampa de liquidez (+0.35%)
    unsafe, f_val, msg = sentinel.check_funding_rate_imbalance(0.35)
    assert unsafe is False
    assert f_val == 0.35
    assert "ALERTA Funding Rate Anómalo" in msg


def test_pump_and_dump_signature_detection():
    """Identifica alzas parabólicas en libros delgados con spreads dilatados."""
    sentinel = AdversarialMarketSentinel()

    # Movimiento orgánico: +3% de precio, RVOL 1.5x, spread 5 bps
    safe, _ = sentinel.check_pump_and_dump_signature(3.0, 1.5, 5.0)
    assert safe is True

    # Firma Pump & Dump: +22% de precio, RVOL 6.0x, spread 60 bps
    unsafe, msg = sentinel.check_pump_and_dump_signature(22.0, 6.0, 60.0)
    assert unsafe is False
    assert "Firma Pump & Dump detectada" in msg


def test_comprehensive_market_health_audit():
    """Verifica que el centinela integre todos los controles y bloquee entradas tóxicas."""
    sentinel = AdversarialMarketSentinel()

    # Métrica limpia
    clean_metrics = {
        "recent_volume_5m_usd": 150_000.0,
        "l2_bids_usd": 100_000.0,
        "l2_asks_usd": 100_000.0,
        "futures_price": 0.050,
        "reference_index_price": 0.0501,
        "funding_rate_pct": 0.015,
        "price_change_5m_pct": 1.2,
        "rvol_5m": 1.4,
        "bid_ask_spread_bps": 6.0
    }
    result_clean = sentinel.evaluate_market_health("DOGEUSDT", clean_metrics)
    assert result_clean.is_safe_to_trade is True
    assert result_clean.action_recommended == "ALLOW"

    # Métrica con anomalía de funding rate y pump & dump
    toxic_metrics = {
        "recent_volume_5m_usd": 5_000_000.0,
        "l2_bids_usd": 50_000.0,
        "l2_asks_usd": 50_000.0,
        "futures_price": 0.120,
        "reference_index_price": 0.100,
        "funding_rate_pct": 0.28,
        "price_change_5m_pct": 18.0,
        "rvol_5m": 5.5,
        "bid_ask_spread_bps": 55.0
    }
    result_toxic = sentinel.evaluate_market_health("TOXICUSDT", toxic_metrics)
    assert result_toxic.is_safe_to_trade is False
    assert result_toxic.action_recommended == "FORCE_EXIT"
    assert len(result_toxic.reasons) >= 3


# ==============================================================================
# 2. PRUEBAS DE GOBERNANZA PRESUPUESTARIA LLM 2026 Y RESILIENCIA (US-5.2)
# ==============================================================================

def test_llm_cost_calculation_2026():
    """Valida los costes de tokens 2026 para DeepSeek-R1 y Claude 3.5 Sonnet."""
    client = OpenRouterClient(api_key="mock_key", daily_budget_usd=20.0)

    # 1,000,000 prompt + 1,000,000 completion en DeepSeek-R1 ($0.55 + $2.19 = $2.74)
    cost_r1 = client._calculate_call_cost(OpenRouterModel.DEEPSEEK_R1, 1_000_000, 1_000_000)
    assert pytest.approx(cost_r1, rel=1e-4) == 2.74

    # 100,000 prompt + 50,000 completion en Claude 3.5 Sonnet ($0.30 + $0.75 = $1.05)
    cost_claude = client._calculate_call_cost(OpenRouterModel.CLAUDE_35_SONNET, 100_000, 50_000)
    assert pytest.approx(cost_claude, rel=1e-4) == 1.05


def test_llm_circuit_breaker_at_90_percent():
    """Verifica que el circuit breaker se dispare al 90% del presupuesto diario."""
    client = OpenRouterClient(api_key="mock_key", daily_budget_usd=10.0)

    # Simular que el gasto previo ya alcanzó $9.05 (90.5% del presupuesto de $10)
    client.total_cost_usd = 9.05

    # Al ejecutar una consulta, debe activar el circuit breaker y llamar al fallback
    response = client.complete("Genera factores de volumen")
    assert client.circuit_breaker_triggered is True
    assert client.fallback_calls == 1
    assert "formulas" in response

    telemetry = client.get_sla_telemetry()
    assert telemetry["circuit_breaker_triggered"] is True
    assert telemetry["budget_utilization_pct"] >= 90.0


def test_llm_network_failure_chaos_injection():
    """Inyecta un fallo simulado de conexión (HTTP 502 / timeout) y valida recuperación transparente."""
    client = OpenRouterClient(api_key="mock_live_key_simulate", daily_budget_usd=15.0)

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
        response = client.complete("Diagnostica alpha decay")
        assert "diagnosis" in response
        assert response["diagnosis"] == "ALPHA_DECAY_VOLATILITY_COMPRESSION"
        assert client.fallback_calls == 1

    telemetry = client.get_sla_telemetry()
    assert telemetry["fallback_ratio"] == 1.0


# ==============================================================================
# 3. PRUEBAS DE CAOS Y KILL-SWITCHES INDUSTRIALES EN SUB-SEGUNDO (US-5.3)
# ==============================================================================

class MockExchangeAdapter:
    """Simulador de exchange para inyección de fallos y auditoría de órdenes."""
    def __init__(self, open_orders_count: int = 15, open_positions_count: int = 4):
        self.orders = [f"ORD_{i:04d}" for i in range(open_orders_count)]
        self.positions = [f"POS_{i:02d}" for i in range(open_positions_count)]
        self.is_connected = True

    def cancel_all_orders(self):
        cancelled = list(self.orders)
        self.orders.clear()
        return cancelled

    def close_all_positions(self, market: bool = True):
        closed = list(self.positions)
        self.positions.clear()
        return closed

    def disconnect(self):
        self.is_connected = False


def test_kill_switch_automated_triggers(tmp_path):
    """Verifica la activación automática de niveles según métricas de drawdown y latencia."""
    state_file = os.path.join(tmp_path, "kill_switch_state.json")
    ks = EmergencyKillSwitch(state_file=state_file)

    # 1. Pérdida 1h de 1.8% -> Debe activar LEVEL 1 (Soft Lock)
    t1 = ks.evaluate_triggers(intraday_drawdown_pct=1.0, rolling_1h_loss_pct=1.8, ws_latency_seconds=1.0)
    assert t1 is not None
    assert t1[0] == KillSwitchLevel.LEVEL_1_SOFT_LOCK

    # 2. Drawdown intradía de 3.8% -> Debe activar LEVEL 2 (Graceful Unwind)
    t2 = ks.evaluate_triggers(intraday_drawdown_pct=3.8, rolling_1h_loss_pct=0.5, ws_latency_seconds=2.0)
    assert t2 is not None
    assert t2[0] == KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND

    # 3. Drawdown intradía de 5.5% o WebSocket perdido por 25s -> Debe activar LEVEL 3 (Hard Cut)
    t3 = ks.evaluate_triggers(intraday_drawdown_pct=5.5, rolling_1h_loss_pct=2.0, ws_latency_seconds=1.0)
    assert t3 is not None
    assert t3[0] == KillSwitchLevel.LEVEL_3_HARD_CUT

    t4 = ks.evaluate_triggers(intraday_drawdown_pct=1.0, rolling_1h_loss_pct=0.2, ws_latency_seconds=22.0)
    assert t4 is not None
    assert t4[0] == KillSwitchLevel.LEVEL_3_HARD_CUT


def test_kill_switch_sub_second_level3_execution(tmp_path):
    """Demuestra que el corte de Nivel 3 cancela 100% de órdenes y asegura la cuenta en < 1 segundo (< 1000 ms)."""
    state_file = os.path.join(tmp_path, "kill_switch_state.json")
    ks = EmergencyKillSwitch(state_file=state_file)
    mock_exchange = MockExchangeAdapter(open_orders_count=50, open_positions_count=8)

    assert ks.can_open_new_position() is True

    # Ejecutar LEVEL 3 HARD CUT
    res = ks.trigger(
        target_level=KillSwitchLevel.LEVEL_3_HARD_CUT,
        reason="Test de caos: Disparo forzado por brecha de riesgo de mercado",
        exchange_adapter=mock_exchange
    )

    # Verificaciones de latencia y completitud
    assert res["success"] is True
    assert res["sub_second_guarantee"] is True
    assert res["execution_time_ms"] < 1000.0  # Menos de 1 segundo
    assert res["orders_cancelled"] == 50
    assert res["positions_closed"] == 8
    assert len(mock_exchange.orders) == 0
    assert len(mock_exchange.positions) == 0
    assert mock_exchange.is_connected is False

    # Estado del sistema bloqueado
    assert ks.is_active is True
    assert ks.can_open_new_position() is False


def test_kill_switch_reset_with_token(tmp_path):
    """Verifica que el reseteo requiera token de autenticación válido."""
    state_file = os.path.join(tmp_path, "kill_switch_state.json")
    ks = EmergencyKillSwitch(state_file=state_file)
    ks.trigger(KillSwitchLevel.LEVEL_1_SOFT_LOCK, "Bloqueo preventivo")

    assert ks.is_active is True

    # Intento con token inválido
    unauthorized = ks.reset(auth_token="token_falso_invalido", expected_token="secure_token_secret_2026")
    assert unauthorized is False
    assert ks.is_active is True

    # Intento con token autorizado
    authorized = ks.reset(auth_token="secure_token_secret_2026", expected_token="secure_token_secret_2026")
    assert authorized is True
    assert ks.is_active is False
    assert ks.can_open_new_position() is True


def test_kill_switch_chaos_exception_resilience(tmp_path):
    """Inyecta un fallo simulado en el API de órdenes y verifica que el KillSwitch no aborte y registre el evento."""
    state_file = os.path.join(tmp_path, "kill_switch_state.json")
    ks = EmergencyKillSwitch(state_file=state_file)

    failing_exchange = MagicMock()
    failing_exchange.cancel_all_orders.side_effect = ConnectionResetError("Conexión abortada por exchange")
    failing_exchange.close_all_positions.return_value = ["POS_EMERGENCY"]

    res = ks.trigger(KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND, "Fallo de red en exchange", exchange_adapter=failing_exchange)
    assert res["success"] is True
    assert ks.is_active is True
    assert ks.current_level == KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND
