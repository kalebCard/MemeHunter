"""Tests para las protecciones de producción real del Sprint 8 (PB-23, PB-24, PB-25, PB-26, PB-27)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "user_data" / "strategies"))
import MemeHunterFuturesV1 as mod

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)
PROJ_ROOT = Path(__file__).resolve().parents[1]


def make_strat(tmp_path=None, runmode="dry_run", wallet=1000):
    user_data = str(tmp_path) if tmp_path else str(PROJ_ROOT / "user_data")
    return mod.MemeHunterFuturesV1({
        "runmode": runmode,
        "dry_run_wallet": wallet,
        "user_data_dir": user_data,
        "stake_currency": "USDT",
    })


def make_ohlcv_frame(**kwargs):
    row = {
        "close": 100.0,
        "high": 105.0,
        "low": 95.0,
        "ema_200": 100.0,
        "macd": 0.0,
        "macdsignal": 0.0,
        "rsi": 50.0,
        "volume": 1000.0,
    }
    row.update(kwargs)
    return pd.DataFrame([row])


# =====================================================================
# PB-24: Guardián de Funding Rate
# =====================================================================

def test_funding_rate_guard_boundaries():
    s = make_strat()
    # Simular exchange con diferentes funding rates
    class MockExchange:
        def __init__(self, rate):
            self.rate = rate
        def get_funding_rate(self, pair):
            return self.rate

    # Caso 1: Funding neutro (0.01% por 8h) -> Ambos permitidos
    s.exchange = MockExchange(0.0001)
    assert s._is_adverse_funding("PEPE/USDT:USDT", "short") is False
    assert s._is_adverse_funding("PEPE/USDT:USDT", "long") is False

    # Caso 2: Funding muy adverso para short (-0.06% < -0.05%) -> Short rechazado
    s.exchange = MockExchange(-0.0006)
    assert s._is_adverse_funding("PEPE/USDT:USDT", "short") is True
    assert s._is_adverse_funding("PEPE/USDT:USDT", "long") is False

    # Caso 3: Funding eufórico excesivo para long (+0.12% > +0.10%) -> Long rechazado
    s.exchange = MockExchange(0.0012)
    assert s._is_adverse_funding("PEPE/USDT:USDT", "short") is False
    assert s._is_adverse_funding("PEPE/USDT:USDT", "long") is True

    # Caso 4: Excepción o None en exchange se gestiona de forma segura sin romper
    class FailingExchange:
        def get_funding_rate(self, pair):
            raise RuntimeError("API timeout")
    s.exchange = FailingExchange()
    assert s._is_adverse_funding("PEPE/USDT:USDT", "short") is False


# =====================================================================
# PB-23: Matriz de Salidas Técnicas Dinámicas
# =====================================================================

def test_exit_matrix_long():
    s = make_strat()
    metadata = {"pair": "DOGE/USDT:USDT"}

    # Caso Long en tendencia: close > ema_200, MACD alcista, RSI 60 -> exit_long = 0
    df_hold = s.populate_exit_trend(
        make_ohlcv_frame(close=120.0, ema_200=100.0, macd=1.5, macdsignal=1.0, rsi=60.0),
        metadata
    )
    assert df_hold["exit_long"].iloc[0] == 0

    # Infracción 1: Caída bajo EMA 200 -> exit_long = 1
    df_break = s.populate_exit_trend(
        make_ohlcv_frame(close=98.0, ema_200=100.0, macd=1.5, macdsignal=1.0, rsi=60.0),
        metadata
    )
    assert df_break["exit_long"].iloc[0] == 1

    # Infracción 2: Cruce bajista de MACD con RSI exhausto (< 45) -> exit_long = 1
    df_momentum_loss = s.populate_exit_trend(
        make_ohlcv_frame(close=105.0, ema_200=100.0, macd=0.2, macdsignal=0.5, rsi=42.0),
        metadata
    )
    assert df_momentum_loss["exit_long"].iloc[0] == 1


def test_exit_matrix_short():
    s = make_strat()
    metadata = {"pair": "DOGE/USDT:USDT"}

    # Caso Short en tendencia: close < ema_200, MACD bajista, RSI 35 -> exit_short = 0
    df_hold = s.populate_exit_trend(
        make_ohlcv_frame(close=80.0, ema_200=100.0, macd=-1.5, macdsignal=-1.0, rsi=35.0),
        metadata
    )
    assert df_hold["exit_short"].iloc[0] == 0

    # Infracción 1: Ruptura alcista sobre EMA 200 -> exit_short = 1
    df_break = s.populate_exit_trend(
        make_ohlcv_frame(close=102.0, ema_200=100.0, macd=-1.5, macdsignal=-1.0, rsi=35.0),
        metadata
    )
    assert df_break["exit_short"].iloc[0] == 1

    # Infracción 2: Cruce alcista de MACD con RSI recuperando (> 55) -> exit_short = 1
    df_squeeze = s.populate_exit_trend(
        make_ohlcv_frame(close=90.0, ema_200=100.0, macd=-0.2, macdsignal=-0.6, rsi=58.0),
        metadata
    )
    assert df_squeeze["exit_short"].iloc[0] == 1


# =====================================================================
# PB-25: Kill-Switch y Combinación de PnL Realizado + Flotante
# =====================================================================

def test_drawdown_unrealized_peak_tracking():
    # Capital inicial 1000 USDT.
    # 1. Ganancia realizada +200 -> pico sube a 1200.
    # 2. Posiciones abiertas acumulan -400 flotante -> equity viva = 800.
    # Drawdown actual = (1200 - 800) / 1200 = 33.33% (supera 25% Kill-Switch)
    dd = mod.compute_drawdown([200], 1000, open_profit_abs=-400)
    assert dd == pytest.approx(400 / 1200)
    assert dd >= mod.KILL_SWITCH_DRAWDOWN

    # 3. Posiciones abiertas con beneficio flotante compensan pérdida cerrada:
    # Pérdida cerrada -100 (equity = 900), pero flotante +250 (equity viva = 1150 -> nuevo pico).
    # Drawdown actual = 0.0
    dd_rebound = mod.compute_drawdown([-100], 1000, open_profit_abs=250)
    assert dd_rebound == pytest.approx(0.0)


# =====================================================================
# PB-26 & PB-27: Consistencia de Configuración y Tipos de Orden
# =====================================================================

def test_config_consistency():
    config_paths = [
        PROJ_ROOT / "user_data" / "config_futures.example.json",
        PROJ_ROOT / "user_data" / "config_futures_backtest_memes.json",
    ]
    real_config = PROJ_ROOT / "user_data" / "config_futures.json"
    if real_config.exists():
        config_paths.append(real_config)

    for cfg_path in config_paths:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert cfg["trading_mode"] == "futures"
        assert cfg["margin_mode"] == "isolated"
        assert cfg["timeframe"] == "4h"
        # Stoploss alineado al -10% optimizado
        assert cfg["stoploss"] == -0.10

        # PB-26: Tipos de orden protegidos ante iliquidez en memecoins
        order_types = cfg.get("order_types", {})
        assert order_types.get("stoploss") == "market"
        assert order_types.get("emergency_exit") == "market"
