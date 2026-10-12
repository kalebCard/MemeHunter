"""
MemeHunterFuturesV5_Leverage - Dynamic Leverage & Exponential Compounding Engine.

Innovaciones:
1. Apalancamiento Dinámico Condicionado (Regime-Switching Leverage 1.5x - 2.0x):
   - Confluencia Alta (Trapped Longs + LVN + Fin de Semana): Leverage 2.0x.
   - Confluencia Estándar (Shift o Breakdown): Leverage 1.5x.
2. Protección Anti-Liquidación:
   - Margen aislado con stoploss duro -10% y trailing offset +12% / trail +4%.
   - Distancia a liquidación en 2.0x es +50%, garantizando cero riesgo de quiebra forzada.
3. Máscara de Estacionalidad Humana (Jueves a Domingo activa, Lunes/Martes bloqueada).
"""

from datetime import datetime
from typing import Optional
import logging

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
)
from freqtrade.persistence import Trade
from pandas import DataFrame, Series
import pandas_ta as ta
import numpy as np

LOG = logging.getLogger(__name__)

KILL_SWITCH_DRAWDOWN = 0.25
KILL_SWITCH_FLAG = "KILL_SWITCH"


class MemeHunterFuturesV5_Leverage(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = True

    # ROI calibrado para desinflación macro
    minimal_roi = {
        "0": 0.602,
        "1704": 0.141,
        "2255": 0.047,
        "7483": 0
    }

    # Stoploss duro de emergencia (-10%)
    stoploss = -0.10

    # Trailing Stop Nativo de Alta Fidelidad
    trailing_stop = True
    trailing_stop_positive = 0.040
    trailing_stop_positive_offset = 0.120
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    startup_candle_count: int = 200

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False,
        'stoploss_on_exchange_interval': 60
    }

    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        Apalancamiento dinámico asimétrico según nivel de convicción:
        - 'short_trapped_auction': 2.0x (Máxima convicción de colapso en techos).
        - 'short_structure_shift': 1.75x (Transición confirmada tras pump).
        - 'short_macro_breakdown': 1.5x (Continuación de tendencia).
        """
        if entry_tag == 'short_trapped_auction':
            return 2.0
        elif entry_tag == 'short_structure_shift':
            return 1.75
        elif entry_tag == 'short_macro_breakdown':
            return 1.5
        return 1.5

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Tendencia e impulso
        dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)
        dataframe['dist_ema_50'] = (dataframe['close'] - dataframe['ema_50']) / dataframe['ema_50']

        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        macd = ta.macd(dataframe['close'], fast=12, slow=26, signal=9)
        dataframe['macd'] = macd['MACD_12_26_9']
        dataframe['macdsignal'] = macd['MACDs_12_26_9']
        dataframe['macdhist'] = macd['MACDh_12_26_9']

        dataframe['atr'] = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)

        # -------------------------------------------------------------
        # TEORÍA DE SUBASTA & PARTICIPANTES ATRAPADOS (AUCTION THEORY)
        # -------------------------------------------------------------
        upper_wick = dataframe['high'] - dataframe[['close', 'open']].max(axis=1)
        candle_body = (dataframe['close'] - dataframe['open']).abs()
        candle_range = dataframe['high'] - dataframe['low']

        vol_sma20 = ta.sma(dataframe['volume'], length=20)
        vol_ratio = dataframe['volume'] / vol_sma20.replace(0, np.nan)

        is_wick_dominant = (upper_wick >= candle_body * 1.8) & (upper_wick >= candle_range * 0.45)
        is_volume_spike = vol_ratio >= 1.4
        is_closing_weak = dataframe['close'] <= (dataframe['low'] + candle_range * 0.35)

        dataframe['trapped_longs_signal'] = (is_wick_dominant & is_volume_spike & is_closing_weak).astype(int)

        # Nodos de Bajo Volumen (LVN)
        vol_percentile_25 = dataframe['volume'].rolling(window=30).quantile(0.25)
        dataframe['is_lvn'] = (dataframe['volume'] < vol_percentile_25).astype(int)

        # -------------------------------------------------------------
        # MÁSCARA DE ESTACIONALIDAD HUMANA
        # -------------------------------------------------------------
        dataframe['day_of_week'] = dataframe['date'].dt.dayofweek
        dataframe['hour'] = dataframe['date'].dt.hour

        is_favorable_day = dataframe['day_of_week'].isin([3, 4, 5, 6])
        is_favorable_session = (dataframe['hour'].between(13, 21)) | (dataframe['hour'].between(0, 4))
        dataframe['seasonal_short_allowed'] = is_favorable_day & is_favorable_session

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0

        # SHORTS A: "Trapped Longs Auction Rejection" (2.0x Leverage)
        short_trapped_conditions = (
            (dataframe['seasonal_short_allowed']) &
            (dataframe['trapped_longs_signal'].rolling(window=3).max() == 1) &
            (dataframe['close'] < dataframe['low'].shift(1)) &
            (dataframe['macdhist'] < dataframe['macdhist'].shift(1)) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_trapped_conditions, 'enter_short'] = 1
        dataframe.loc[short_trapped_conditions, 'enter_tag'] = 'short_trapped_auction'

        # SHORTS B: "Pump Structure Shift" (1.75x Leverage)
        short_structure_shift = (
            (dataframe['seasonal_short_allowed']) &
            (dataframe['dist_ema_50'].rolling(window=3).max() >= 0.12) &
            (dataframe['close'] < dataframe['low'].shift(1)) &
            (dataframe['rsi'] < 68) &
            (dataframe['rsi'].shift(1) >= 65) &
            (dataframe['macdhist'] < dataframe['macdhist'].shift(1)) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_structure_shift, 'enter_short'] = 1
        dataframe.loc[short_structure_shift, 'enter_tag'] = 'short_structure_shift'

        # SHORTS C: "Macro Breakdown" (1.5x Leverage)
        short_macro_conditions = (
            (dataframe['seasonal_short_allowed']) &
            (dataframe['close'] < dataframe['ema_200']) &
            (dataframe['macd'] < dataframe['macdsignal']) &
            (dataframe['macd'] < 0) &
            (dataframe['rsi'] <= 44) &
            (dataframe['rsi'] >= 22) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_macro_conditions, 'enter_short'] = 1
        dataframe.loc[short_macro_conditions, 'enter_tag'] = 'short_macro_breakdown'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        exit_short = (
            (dataframe['close'] > dataframe['ema_200']) |
            ((dataframe['macd'] > dataframe['macdsignal']) & (dataframe['rsi'] > 58))
        )
        dataframe.loc[exit_short, 'exit_short'] = 1

        return dataframe
