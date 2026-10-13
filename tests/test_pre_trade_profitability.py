"""
Pruebas Unitarias para PreTradeProfitabilityGate e Integración en Estrategia (Sprint 38: PB-126 / PB-127).
"""

import pytest
from portfolio.pre_trade_profitability import PreTradeProfitabilityGate
from user_data.strategies.MemeHunterSpot_CapitulationAlpha import MemeHunterSpot_CapitulationAlpha
from portfolio.bias_store import BiasStore
from validation.schemas import MarketBiasSchema, MarketBiasPosture
from datetime import datetime, timezone, timedelta


def test_profitability_gate_healthy_trade():
    gate = PreTradeProfitabilityGate(default_safety_multiplier=2.5)

    # Caso saludable: Ganancia proyectada +4.5% con spread normal (0.10%)
    decision = gate.evaluate_entry(
        symbol="DOGE/USDT",
        current_price=0.15,
        target_price=0.15675,  # +4.5%
        spread_pct=0.0010,     # 0.10%
        is_entry_maker=True,   # 0.075%
        is_exit_maker=False,   # 0.10%
        estimated_slippage_bps=5.0 # 0.05%
    )

    # Costo friccional total: 0.075% + 0.10% + 0.10% + 0.05% = 0.325%
    # Margen requerido: 0.325% * 2.5 = 0.8125%
    # Ganancia proyectada: 4.5% > 0.8125% -> Aprobado!
    assert decision.is_approved is True
    assert decision.net_projected_gain_pct > 0.04
    assert gate.approved_orders_count >= 1


def test_profitability_gate_toxic_spread_rejection():
    gate = PreTradeProfitabilityGate(default_safety_multiplier=2.5)

    # Caso tóxico: Rebote pequeño (+1.0%) con spread muy abierto (0.60%)
    decision = gate.evaluate_entry(
        symbol="SHIB/USDT",
        current_price=0.00002,
        custom_target_pct=0.010, # +1.0%
        spread_pct=0.0060,       # 0.60% spread tóxico!
        is_entry_maker=False,    # Taker 0.10%
        is_exit_maker=False,     # Taker 0.10%
        estimated_slippage_bps=15.0 # 0.15%
    )

    # Costo friccional: 0.10% + 0.10% + 0.60% + 0.15% = 0.95%
    # Umbral de seguridad requerido: 0.95% * 2.5 = 2.375%
    # Ganancia proyectada: 1.0% < 2.375% -> Rechazo silencioso
    assert decision.is_approved is False
    assert "FRICCION_EXCESIVA" in decision.rejection_reason
    assert gate.discarded_orders_count >= 1


def test_strategy_pre_trade_filter_integration(tmp_path):
    strat = MemeHunterSpot_CapitulationAlpha()
    strat.bias_store = BiasStore(filepath=str(tmp_path / "strat_bias.json"))

    # 1. Sin activar enforce_agent_bias, el chequeo pasa si la rentabilidad es buena
    ok, reason = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        spread_pct=0.0010
    )
    assert ok is True
    assert reason == "APPROVED"

    # 2. Si el spread es tóxico (ej. 1.8%), el filtro matemático pre-trade bloquea la orden
    ok_fric, reason_fric = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        spread_pct=0.0180
    )
    assert ok_fric is False
    assert "FRICCION_EXCESIVA" in reason_fric

    # 3. Activando enforce_agent_bias sin autorización en el BiasStore
    strat.enforce_agent_bias = True
    ok_bias, reason_bias = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        spread_pct=0.0010
    )
    assert ok_bias is False
    assert "BIAS_BLOCKED" in reason_bias

    # 4. Inyectando autorización válida al BiasStore
    future = datetime.now(timezone.utc) + timedelta(hours=4)
    strat.bias_store.save_bias(MarketBiasSchema(
        symbol="DOGE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.85,
        consensus_score=0.90,
        valid_until_utc=future.isoformat()
    ))

    ok_auth, reason_auth = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        spread_pct=0.0010
    )
    assert ok_auth is True
    assert reason_auth == "APPROVED"
