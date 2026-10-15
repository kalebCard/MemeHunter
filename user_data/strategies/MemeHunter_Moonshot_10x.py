"""
MemeHunter_Moonshot_10x - High-Volatility Exponential Compounding Strategy (10x Challenge).
Diseñada específicamente para el experimento de estrés:
- Capital inicial: 10 USDT (Simulado o Aislado).
- Meta cuantitativa: 100 USDT en 7 días (+900% ROI).
- Perfil de riesgo: Ultra-Agresivo (100% Drawdown tolerado por el operador).
- Apalancamiento: 10.0x aislado.
- Timeframe: 15 minutos (Alta frecuencia intradiaria).
"""

from datetime import datetime
from typing import Optional, Dict
import logging

from freqtrade.strategy import IStrategy
from pandas import DataFrame, Series
import pandas_ta as ta
import numpy as np

LOG = logging.getLogger("Moonshot10x")


class MemeHunter_Moonshot_10x(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = True

    # Take Profit Escalonado de Alta Frecuencia (en términos de ROI de posición)
    # A 10x de apalancamiento, 0.10 significa +1% de movimiento en el precio subyacente.
    minimal_roi = {
        "0": 0.25,     # +25% de ROI inmediato (+2.5% precio)
        "15": 0.12,    # +12% si se mantiene 15 min
        "45": 0.06,    # +6% si se mantiene 45 min
        "120": 0.02
    }

    # Stoploss duro preventivo (-4.5% del precio = -45% de margen, evita liquidación en 10x)
    stoploss = -0.045

    # Trailing Stop Dinámico Ultra-Apretado
    trailing_stop = True
    trailing_stop_positive = 0.020           # 2% de retroceso permitido una vez activado
    trailing_stop_positive_offset = 0.050    # Se activa al alcanzar +5% de ganancia en el trade
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    startup_candle_count: int = 60

    order_types = {
        "entry": "market",
        "exit": "market",
        "emergency_exit": "market",
        "force_entry": "market",
        "force_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False
    }

    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC"
    }

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Apalancamiento agresivo fijo 10.0x para el experimento de aceleración exponencial."""
        return 10.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Cálculo de momentum, volumen relativo y volatilidad en 15m."""
        if dataframe.empty:
            return dataframe

        # 1. EMAs de Momentum Rápido
        dataframe["ema_8"] = ta.ema(dataframe["close"], length=8)
        dataframe["ema_21"] = ta.ema(dataframe["close"], length=21)
        dataframe["ema_55"] = ta.ema(dataframe["close"], length=55)

        # 2. RSI Rápido
        dataframe["rsi"] = ta.rsi(dataframe["close"], length=14)

        # 3. Bandas de Bollinger para atrapar expansiones de volatilidad
        bb = ta.bbands(dataframe["close"], length=20, std=2.0)
        if bb is not None and not bb.empty:
            dataframe["bb_lower"] = bb.iloc[:, 0]
            dataframe["bb_middle"] = bb.iloc[:, 1]
            dataframe["bb_upper"] = bb.iloc[:, 2]
        else:
            dataframe["bb_lower"] = dataframe["close"] * 0.95
            dataframe["bb_upper"] = dataframe["close"] * 1.05

        # 4. Volumen Relativo (RVOL)
        vol_ma = dataframe["volume"].rolling(20, min_periods=1).mean().replace(0, 1.0)
        dataframe["rvol"] = dataframe["volume"] / vol_ma

        # 5. VWAP Intradiario
        typical = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3.0
        cum_vol = dataframe["volume"].cumsum().replace(0, 1.0)
        dataframe["vwap"] = (typical * dataframe["volume"]).cumsum() / cum_vol

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Gatillos de entrada explosivos en Long y Short."""
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # GATILLO LONG (Breakout de Momentum con Volumen Anómalo)
        long_cond = (
            (dataframe["close"] > dataframe["vwap"]) &
            (dataframe["ema_8"] > dataframe["ema_21"]) &
            (dataframe["close"] > dataframe["ema_8"]) &
            (dataframe["rvol"] > 1.8) &
            (dataframe["rsi"] > 52) &
            (dataframe["rsi"] < 75)
        )
        dataframe.loc[long_cond, "enter_long"] = 1
        dataframe.loc[long_cond, "enter_tag"] = "moonshot_long_breakout"

        # GATILLO SHORT (Desinflado Rápido post-pump / Caída con volumen)
        short_cond = (
            (dataframe["close"] < dataframe["vwap"]) &
            (dataframe["ema_8"] < dataframe["ema_21"]) &
            (dataframe["close"] < dataframe["ema_8"]) &
            (dataframe["rvol"] > 1.6) &
            (dataframe["rsi"] < 48) &
            (dataframe["rsi"] > 22)
        )
        dataframe.loc[short_cond, "enter_short"] = 1
        dataframe.loc[short_cond, "enter_tag"] = "moonshot_short_exhaustion"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Las salidas principales son gestionadas por Trailing Stop y ROI dinámico."""
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
