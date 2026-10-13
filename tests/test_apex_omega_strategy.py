"""
tests/test_apex_omega_strategy.py - Suite de Certificación para MemeHunter_ApexOmegaAlpha (v7.6).
Verifica:
1. Cálculo de indicadores (FFD d=0.40, Absorción de Mecha L2, Z-Score, Bandas BB).
2. Generación de entradas deterministas Long (Capitulación) y Short (Desinflación).
3. Dimensionamiento Continuo de Apuestas (Bet Sizing de López de Prado).
4. Trinquete de Ganancias (Breakeven Ratchet) y Time-Stop Anti-Bagholding.
5. Auditoría unificada de las 4 capas (BiasStore -> ProfitabilityGate -> ExecutionGatekeeper).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from user_data.strategies.MemeHunter_ApexOmegaAlpha import (
    MemeHunter_ApexOmegaAlpha,
    continuous_bet_sizing,
    calculate_ffd_approx
)
from portfolio.bias_store import BiasStore
from validation.schemas import MarketBiasSchema, MarketBiasPosture
from portfolio.kill_switch import KillSwitchLevel, EmergencyKillSwitch


def test_apex_omega_indicators_and_ffd():
    strat = MemeHunter_ApexOmegaAlpha()
    n = 100
    prices = [100.0 * (1.0 + 0.005 * i + 0.01 * np.sin(i)) for i in range(n)]

    df = pd.DataFrame({
        "open": prices,
        "high": [p * 1.02 for p in prices],
        "low": [p * 0.98 for p in prices],
        "close": prices,
        "volume": [1000.0] * n
    })

    df = strat.populate_indicators(df, metadata={"pair": "DOGE/USDT"})

    assert "ffd_close" in df.columns
    assert "ffd_momentum" in df.columns
    assert "absorption_wick_signal" in df.columns
    assert "panic_candle" in df.columns
    assert "confirmation_candle" in df.columns
    assert "z_score_dist" in df.columns
    assert not df["ffd_close"].iloc[35:].isna().all()


def test_apex_omega_confirmed_capitulation_entry():
    strat = MemeHunter_ApexOmegaAlpha()
    n = 60

    # Crear serie con crash de capitulación en vela 40 y confirmación en vela 41
    df = pd.DataFrame({
        "open": [100.0] * n,
        "high": [105.0] * n,
        "low": [95.0] * n,
        "close": [100.0] * n,
        "volume": [1000.0] * n
    })

    df = strat.populate_indicators(df, metadata={"pair": "PEPE/USDT"})

    # Inyectar pánico en t-1 y confirmación verde en t
    df.loc[40, 'panic_candle'] = 1
    df.loc[41, 'confirmation_candle'] = 1
    df.loc[41, 'volume'] = 5000.0

    df = strat.populate_entry_trend(df, metadata={"pair": "PEPE/USDT"})

    assert df.loc[41, 'enter_long'] == 1
    assert df.loc[41, 'enter_tag'] == 'apex_confirmed_capitulation'


def test_apex_omega_continuous_bet_sizing():
    # Convicción nula -> 1.0x
    lev_zero = continuous_bet_sizing(0.0, min_lev=1.0, max_lev=2.0)
    assert lev_zero == 1.0

    # Baja convicción (0.10) -> ~1.05x - 1.15x
    lev_low = continuous_bet_sizing(0.10, min_lev=1.0, max_lev=2.0)
    assert 1.05 <= lev_low <= 1.15

    # Convicción media -> ~1.4x - 1.6x
    lev_mid = continuous_bet_sizing(0.70, min_lev=1.0, max_lev=2.0)
    assert 1.30 <= lev_mid <= 1.70

    # Convicción máxima -> 1.9x - 2.0x
    lev_max = continuous_bet_sizing(0.95, min_lev=1.0, max_lev=2.0)
    assert lev_max >= 1.90


def test_apex_omega_capital_armor_ratchet():
    strat = MemeHunter_ApexOmegaAlpha()
    trade = SimpleNamespace(open_date_utc=datetime.now(timezone.utc))

    # 1. Ganancia normal bajo +2.0% -> Respetar stop duro (-3.0%)
    sl_base = strat.custom_stoploss("DOGE/USDT", trade, datetime.now(timezone.utc), 0.15, current_profit=0.012)
    assert sl_base == -0.030

    # 2. Hito 1: Ganancia toca +2.5% -> Breakeven asegurando +0.5% neto
    sl_be = strat.custom_stoploss("DOGE/USDT", trade, datetime.now(timezone.utc), 0.15, current_profit=0.025)
    assert sl_be < 0.0
    # La distancia de stoploss calculada protege el capital

    # 3. Hito 2: Ganancia fuerte (+5.0%) -> Asegurar +2.5% neto
    sl_lock = strat.custom_stoploss("DOGE/USDT", trade, datetime.now(timezone.utc), 0.15, current_profit=0.050)
    assert sl_lock == -0.015


def test_apex_omega_time_stop_anti_bagholding():
    strat = MemeHunter_ApexOmegaAlpha()
    now = datetime.now(timezone.utc)
    ten_hours_ago = now - timedelta(hours=10)
    stagnant_trade = SimpleNamespace(open_date_utc=ten_hours_ago)

    # 10 horas de trade y apenas 0.4% de ganancia -> Disparar liquidación anti-bagholding
    exit_reason = strat.custom_exit("DOGE/USDT", stagnant_trade, now, 0.15, current_profit=0.004)
    assert exit_reason == "time_stop_anti_bagholding"


def test_apex_omega_four_tier_unified_filter(tmp_path):
    strat = MemeHunter_ApexOmegaAlpha()
    strat.bias_store = BiasStore(filepath=str(tmp_path / "apex_bias.json"))
    strat.kill_switch = EmergencyKillSwitch(state_file=str(tmp_path / "apex_ks.json"))
    strat.gatekeeper.kill_switch = strat.kill_switch

    # 1. Caso saludable y rentable
    ok, reason = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        side="LONG",
        spread_pct=0.0010
    )
    assert ok is True
    assert reason == "APPROVED_FOR_DISPATCH"

    # 2. Caso de spread tóxico devorando el edge
    ok_fric, reason_fric = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        side="LONG",
        spread_pct=0.0190 # Spread tóxico del 1.9%!
    )
    assert ok_fric is False
    assert "FRICCION_EXCESIVA" in reason_fric

    # 3. Caso con Sesgo Directivo obligatorio activado
    strat.enforce_agent_bias = True
    ok_no_bias, reason_no_bias = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        side="LONG"
    )
    assert ok_no_bias is False
    assert "BIAS_BLOCKED" in reason_no_bias

    # 4. Autorizando el par con BiasStore
    future = datetime.now(timezone.utc) + timedelta(hours=4)
    strat.bias_store.save_bias(MarketBiasSchema(
        symbol="DOGE/USDT",
        posture=MarketBiasPosture.ALLOW_LONG,
        confidence=0.88,
        consensus_score=0.92,
        valid_until_utc=future.isoformat()
    ))

    ok_auth, reason_auth = strat.check_pre_trade_filters(
        pair="DOGE/USDT",
        current_price=0.15,
        side="LONG"
    )
    assert ok_auth is True
    assert reason_auth == "APPROVED_FOR_DISPATCH"


def test_apex_omega_confirm_trade_entry_lifecycle(tmp_path):
    """PB-132: Valida que confirm_trade_entry ejecute el pipeline de compuertas en runtime."""
    strat = MemeHunter_ApexOmegaAlpha()
    strat.bias_store = BiasStore(filepath=str(tmp_path / "lifecycle_bias.json"))
    strat.kill_switch = EmergencyKillSwitch(state_file=str(tmp_path / "lifecycle_ks.json"))
    strat.gatekeeper.kill_switch = strat.kill_switch

    now = datetime.now(timezone.utc)

    # 1. Entrada válida aprobada
    approved = strat.confirm_trade_entry(
        pair="DOGE/USDT",
        order_type="limit",
        amount=100.0,
        rate=0.15,
        time_in_force="GTC",
        current_time=now,
        entry_tag="apex_confirmed_capitulation",
        side="buy"
    )
    assert approved is True

    # 2. Entrada bloqueada si el sesgo del agente está habilitado pero no autorizado
    strat.enforce_agent_bias = True
    blocked_bias = strat.confirm_trade_entry(
        pair="DOGE/USDT",
        order_type="limit",
        amount=100.0,
        rate=0.15,
        time_in_force="GTC",
        current_time=now,
        entry_tag="apex_confirmed_capitulation",
        side="buy"
    )
    assert blocked_bias is False

    # 3. Entrada bloqueada si el Kill Switch está en emergencia
    strat.enforce_agent_bias = False
    strat.kill_switch.trigger(
        target_level=KillSwitchLevel.LEVEL_1_SOFT_LOCK,
        reason="Drawdown intradia excedido 5.0%"
    )
    blocked_ks = strat.confirm_trade_entry(
        pair="DOGE/USDT",
        order_type="limit",
        amount=100.0,
        rate=0.15,
        time_in_force="GTC",
        current_time=now,
        entry_tag="apex_confirmed_capitulation",
        side="buy"
    )
    assert blocked_ks is False
