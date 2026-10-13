"""
Pruebas Unitarias para ExecutionGatekeeper (Sprint 39: PB-130).
"""

import os
import pytest
from portfolio.kill_switch import EmergencyKillSwitch, KillSwitchLevel
from portfolio.execution_gatekeeper import ExecutionGatekeeper


@pytest.fixture
def gatekeeper_setup(tmp_path):
    ks_file = tmp_path / "test_ks_state.json"
    ks = EmergencyKillSwitch(
        max_intraday_drawdown_pct=3.5,
        max_1h_loss_pct=1.5,
        state_file=str(ks_file)
    )
    gk = ExecutionGatekeeper(
        kill_switch=ks,
        max_concurrent_slots=3,
        min_notional_usdt=5.0,
        max_stoploss_pct=-0.010,
        min_stoploss_pct=-0.100
    )
    yield gk, ks
    if os.path.exists(str(ks_file)):
        os.remove(str(ks_file))


def test_gatekeeper_approve_valid_order(gatekeeper_setup):
    gk, ks = gatekeeper_setup

    ok, reason = gk.intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.155,
        stoploss_pct=-0.030, # -3.0%
        current_open_trades=1,
        intraday_drawdown_pct=0.5
    )

    assert ok is True
    assert reason == "APPROVED_FOR_DISPATCH"
    assert gk.approved_orders_count == 1


def test_gatekeeper_reject_missing_stoploss(gatekeeper_setup):
    gk, ks = gatekeeper_setup

    # Orden sin stoploss
    ok, reason = gk.intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.155,
        stoploss_pct=None, # Missing!
        current_open_trades=1
    )

    assert ok is False
    assert "MANDATORY_STOPLOSS_MISSING" in reason
    assert gk.rejected_orders_count == 1


def test_gatekeeper_reject_positive_or_out_of_bounds_stoploss(gatekeeper_setup):
    gk, ks = gatekeeper_setup

    # Stoploss positivo
    ok_pos, reason_pos = gk.intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.155,
        stoploss_pct=0.05
    )
    assert ok_pos is False
    assert "INVALID_STOPLOSS" in reason_pos

    # Stoploss desproporcionado (-25%, viola rango permitido de [-10%, -1%])
    ok_deep, reason_deep = gk.intercept_order(
        symbol="DOGE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.155,
        stoploss_pct=-0.250
    )
    assert ok_deep is False
    assert "STOPLOSS_OUT_OF_BOUNDS" in reason_deep


def test_gatekeeper_reject_max_slots(gatekeeper_setup):
    gk, ks = gatekeeper_setup

    # Hay 3 slots ocupados de un máximo de 3
    ok, reason = gk.intercept_order(
        symbol="PEPE/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.00001,
        stoploss_pct=-0.030,
        current_open_trades=3
    )

    assert ok is False
    assert "MAX_SLOTS_REACHED" in reason


def test_gatekeeper_reject_kill_switch_trigger(gatekeeper_setup):
    gk, ks = gatekeeper_setup

    # Drawdown intradía severo del 4.2% (debe activar Unwind/bloqueo de entradas)
    ok, reason = gk.intercept_order(
        symbol="BONK/USDT",
        side="buy",
        order_size_usdt=33.0,
        price=0.00002,
        stoploss_pct=-0.030,
        current_open_trades=0,
        intraday_drawdown_pct=4.20
    )

    assert ok is False
    assert "KILL_SWITCH_ACTIVE" in reason
    assert ks.current_level >= KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND
