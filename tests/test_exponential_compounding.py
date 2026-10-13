"""
tests/test_exponential_compounding.py - Suite de Certificación para el Motor de Crecimiento Exponencial.
Valida:
1. Precisión matemática del Criterio de Half-Kelly.
2. Transición determinista entre Fases de Escalado (Fase 1 Semilla a Fase 4 Barbell).
3. Cumplimiento estricto del Min Notional de Binance ($5 USDT).
4. Válvula de Trinquete Asimétrico (Profit Ratchet) hacia la Bóveda Cash & Carry.
5. Integración con el callback custom_stake_amount de MemeHunter_ApexOmegaAlpha.
"""

import pytest
from datetime import datetime, timezone

from portfolio.exponential_compounding_engine import (
    ExponentialCompoundingManager,
    CompoundingPhase
)
from user_data.strategies.MemeHunter_ApexOmegaAlpha import MemeHunter_ApexOmegaAlpha


def test_kelly_formula_theoretical():
    manager = ExponentialCompoundingManager(
        base_win_rate=0.48,
        base_payoff_ratio=2.20,
        kelly_fraction=0.40
    )
    # p = 0.48, b = 2.20, q = 0.52
    # Edge = (0.48 * 2.20) - 0.52 = 1.056 - 0.52 = 0.536
    # Raw Kelly = 0.536 / 2.20 ~= 0.243636
    # Half-Kelly (gamma=0.40) = 0.243636 * 0.40 ~= 0.0975
    f_star = manager.calculate_optimal_kelly_fraction()
    assert 0.09 <= f_star <= 0.11

    # Edge nulo o negativo debe devolver 0.0
    zero_edge = manager.calculate_optimal_kelly_fraction(win_rate=0.20, payoff_ratio=1.0)
    assert zero_edge == 0.0


def test_phase_transitions():
    manager = ExponentialCompoundingManager()

    # Fase 1: Semilla ($10 a $250)
    p1 = manager.get_current_phase(100.0)
    assert p1.phase_id == 1
    assert p1.max_slots == 3
    assert p1.name == "FASE_1_SEMILLA_BLINDADA"

    # Fase 2: Expansión ($250 a $1,000)
    p2 = manager.get_current_phase(400.0)
    assert p2.phase_id == 2
    assert p2.max_slots == 4
    assert p2.name == "FASE_2_EXPANSION_GEOMETRICA"

    # Fase 3: Aceleración ($1,000 a $5,000)
    p3 = manager.get_current_phase(2500.0)
    assert p3.phase_id == 3
    assert p3.max_slots == 5
    assert p3.name == "FASE_3_ACELERACION_PARABOLICA"

    # Fase 4: Barbell Institucional (>$5,000)
    p4 = manager.get_current_phase(10000.0)
    assert p4.phase_id == 4
    assert p4.max_slots == 6
    assert p4.name == "FASE_4_BARBELL_INSTITUCIONAL"


def test_compute_stake_amount_micro_capital():
    manager = ExponentialCompoundingManager(min_notional_usdt=5.0)

    # 1. Saldo de $100 USDT con 0 trades abiertos -> Asignación de ~33 USDT (supera por >6x el mínimo de Binance)
    stake_100 = manager.compute_stake_amount(current_wallet=100.0, open_trades_count=0)
    assert stake_100 >= 5.0
    assert stake_100 <= 100.0 / 3.0 + 1.0

    # 2. Saldo insuficiente (< $5 USDT) -> 0.0
    stake_under = manager.compute_stake_amount(current_wallet=4.5, open_trades_count=0)
    assert stake_under == 0.0

    # 3. Slots llenos (Fase 1 max 3 slots, open_trades=3) -> 0.0
    stake_full = manager.compute_stake_amount(current_wallet=100.0, open_trades_count=3)
    assert stake_full == 0.0

    # 4. Modulador de convicción: Mayor convicción incrementa el stake respetando el tope de slot
    stake_high_conviction = manager.compute_stake_amount(current_wallet=100.0, open_trades_count=0, conviction_score=0.95)
    stake_low_conviction = manager.compute_stake_amount(current_wallet=100.0, open_trades_count=0, conviction_score=0.10)
    assert stake_high_conviction >= stake_low_conviction


def test_profit_ratchet_vault_extraction():
    manager = ExponentialCompoundingManager(ratchet_extraction_pct=0.35)
    manager.last_ratchet_peak = 100.0

    # Subida normal de $100 a $150 -> No activa trinquete
    triggered, amount, msg = manager.check_and_execute_profit_ratchet(150.0)
    assert not triggered
    assert amount == 0.0

    # Hito 1: La cuenta se duplica a $200 USDT -> Activa Trinquete
    # Ganancia = $100. Cosecha del 35% = $35 USDT hacia la Bóveda Delta-Neutral.
    # Nuevo pico = $200 - $35 = $165.
    triggered, amount, msg = manager.check_and_execute_profit_ratchet(200.0)
    assert triggered
    assert amount == 35.0
    assert manager.total_harvested_to_vault_usdt == 35.0
    assert manager.last_ratchet_peak == 165.0
    assert "HITO DE DUPLICACIÓN ALCANZADO" in msg

    # Próximo hito es 165 * 2 = $330 USDT
    triggered2, amount2, _ = manager.check_and_execute_profit_ratchet(300.0)
    assert not triggered2

    # Alcanza $330 USDT -> Segunda duplicación
    triggered3, amount3, _ = manager.check_and_execute_profit_ratchet(330.0)
    assert triggered3
    assert amount3 > 0.0
    assert manager.total_harvested_to_vault_usdt == 35.0 + amount3


def test_strategy_integration_custom_stake_amount():
    strat = MemeHunter_ApexOmegaAlpha()
    now = datetime.now(timezone.utc)

    # 1. Con Exponential Compounding activo
    stake = strat.custom_stake_amount(
        pair="PEPE/USDT",
        current_time=now,
        current_rate=0.00001,
        proposed_stake=30.0,
        min_stake=5.0,
        max_stake=100.0,
        leverage=1.5,
        entry_tag="apex_confirmed_capitulation",
        side="long",
        wallet=100.0,
        open_trades=0
    )
    assert stake >= 5.0
    assert stake <= 40.0

    # 2. Desactivado explícitamente -> Retorna el proposed_stake original
    strat.enable_exponential_compounding = False
    stake_disabled = strat.custom_stake_amount(
        pair="PEPE/USDT",
        current_time=now,
        current_rate=0.00001,
        proposed_stake=25.0,
        min_stake=5.0,
        max_stake=100.0,
        leverage=1.5,
        entry_tag="apex_confirmed_capitulation",
        side="long",
        wallet=100.0,
        open_trades=0
    )
    assert stake_disabled == 25.0


def test_status_report():
    manager = ExponentialCompoundingManager()
    report = manager.get_status_report(current_equity=500.0)

    assert report["current_equity_usdt"] == 500.0
    assert report["phase_id"] == 2
    assert report["phase_name"] == "FASE_2_EXPANSION_GEOMETRICA"
    assert report["max_slots"] == 4
    assert "optimal_kelly_pct" in report
    assert report["recommended_leverage"] == 1.75
    assert report["next_double_target_usdt"] == 200.0
