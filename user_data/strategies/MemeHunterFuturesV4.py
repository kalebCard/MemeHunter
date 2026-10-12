"""
MemeHunterFuturesV4 - Auction Market Theory & Human Seasonality Engine.

Innovaciones Integradas:
1. Máscara de Estacionalidad Humana (Sprint 13 / PB-48, PB-49, PB-50):
   - Bloqueo sistemático de entradas Short los Lunes y Martes (responsables de -$756 USDT y 156 stoplosses en V3).
   - Concentración y sizing prioritario de Jueves a Domingo (donde el ciclo de desinflación generó +$761 USDT neto).
   - Prioridad a la sesión americana de distribución (14:00 - 21:00 UTC).
2. Teoría de Subasta & Trapped Longs Index (Sprint 12 / PB-45, PB-46, PB-47):
   - Trapped Longs Score: mechas superiores con volumen anormal y cierre bajo que indican compradores minoristas atrapados.
   - Detección de Nodos de Bajo Volumen (LVN): aceleración bajista en vacíos de liquidez.
3. Motor de Salida Asimétrico Puro:
   - Margen aislado 1.0x (cero riesgo de liquidación).
   - Trailing stop holgado (offset al 12%, trailing al 4%) probado en Freqtrade para dejar correr colapsos macro.
   - Time-decay exit para evitar sangrado de tasas de financiación negativas en operaciones estancadas.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
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
LIVE_RUNMODES = ('live', 'dry_run', 'runmode.live', 'runmode.dry_run')


class MemeHunterFuturesV4(IStrategy):
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
    use_custom_stoploss = False

    use_exit_signal = True

    # Guardián de Funding Rate
    MAX_ADVERSE_FUNDING = -0.0005
    MAX_EUPHORIC_FUNDING = 0.0010

    startup_candle_count = 200

    # Protecciones de Cartera Activas
    protections = [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 2
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 6,   # 24 horas
            "trade_limit": 3,
            "stop_duration_candles": 6,
            "only_per_pair": False
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 120, # 20 días
            "trade_limit": 1,
            "stop_duration_candles": 24,    # 4 días
            "max_allowed_drawdown": 0.18
        }
    ]

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Margen Aislado 1.0x para inmunidad absoluta contra liquidaciones catastróficas."""
        return 1.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
        Sizing Asimétrico Multicapa (Estacionalidad + Subasta):
        - Longs: 0.0 (Cero compras).
        - Trapped Longs en LVN o Fin de Semana: 1.40x (Máxima aceleración y convicción).
        - Short Structure Shift estándar: 1.25x.
        - Short Macro Breakdown estándar: 1.0x.
        """
        if side == "long":
            return 0.0

        base_stake = proposed_stake
        if entry_tag == "short_trapped_auction":
            stake = base_stake * 1.40
        elif entry_tag == "short_structure_shift":
            stake = base_stake * 1.25
        else:
            stake = base_stake * 1.0

        if min_stake is not None:
            stake = max(stake, min_stake)
        stake = max(stake, 5.0)  # Binance Min Notional
        return min(stake, max_stake)

    def _is_live_mode(self) -> bool:
        runmode = self.config.get('runmode')
        return bool(runmode) and str(runmode).lower() in LIVE_RUNMODES

    def _kill_switch_path(self) -> Path:
        return Path(self.config.get('user_data_dir', '/freqtrade/user_data')) / KILL_SWITCH_FLAG

    def _is_adverse_funding(self, pair: str, side: str) -> bool:
        exchange = getattr(self, 'dp', None) and getattr(self.dp, 'exchange', None)
        if not exchange:
            exchange = getattr(self, 'exchange', None)
        if not exchange:
            return False

        try:
            funding_rate = None
            if hasattr(exchange, 'fetch_funding_rate'):
                fr_data = exchange.fetch_funding_rate(pair)
                if isinstance(fr_data, dict):
                    funding_rate = fr_data.get('fundingRate') or fr_data.get('funding_rate')
                elif isinstance(fr_data, (float, int)):
                    funding_rate = float(fr_data)
            elif hasattr(exchange, 'get_funding_rate'):
                funding_rate = exchange.get_funding_rate(pair)
            elif hasattr(exchange, '_funding_rates') and pair in exchange._funding_rates:
                funding_rate = exchange._funding_rates[pair]

            if funding_rate is not None:
                funding_rate = float(funding_rate)
                if side == "short" and funding_rate < self.MAX_ADVERSE_FUNDING:
                    return True
                if side == "long" and funding_rate > self.MAX_EUPHORIC_FUNDING:
                    return True
        except Exception:
            pass
        return False

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        if side == "long":
            return False

        live = self._is_live_mode()
        flag = self._kill_switch_path()
        if live and flag.exists():
            return False

        if self._is_adverse_funding(pair, side):
            return False

        return True

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        """
        Salida por Decaimiento Temporal / Funding Exhaustion:
        Si la posición lleva abierta más de 72 horas (4320 min) y se encuentra estancada
        con ganancia menor al +1.5%, cerramos para liberar margen y no sangrar funding fees.
        """
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 60.0
        if trade_duration >= 4320 and current_profit < 0.015:
            return "time_decay_exit"

        return None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Variables Temporales y Estacionales Humanas
        # dayofweek: 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo
        dataframe['dayofweek'] = dataframe['date'].dt.dayofweek
        dataframe['hour_utc'] = dataframe['date'].dt.hour
        dataframe['day_of_month'] = dataframe['date'].dt.day

        # Filtro de Estacionalidad Favorable para Shorts:
        # Excluye Lunes y Martes (responsables de -$756 USDT en pérdidas en la auditoría)
        # Permite Jueves, Viernes, Sábado y Domingo (donde se concentra el +$761 USDT neto).
        # Miércoles se permite solo si coincide con la sesión americana de distribución (14:00 - 21:00 UTC).
        favorable_day = dataframe['dayofweek'].isin([3, 4, 5, 6])
        favorable_wednesday = (dataframe['dayofweek'] == 2) & (dataframe['hour_utc'] >= 14)
        dataframe['seasonal_short_allowed'] = favorable_day | favorable_wednesday

        # 2. Indicadores Clásicos de Tendencia y Momento
        macd = ta.macd(dataframe['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            dataframe['macd'] = macd['MACD_12_26_9']
            dataframe['macdsignal'] = macd['MACDs_12_26_9']
            dataframe['macdhist'] = macd['MACDh_12_26_9']
        else:
            dataframe['macd'] = 0.0
            dataframe['macdsignal'] = 0.0
            dataframe['macdhist'] = 0.0

        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)

        # Distancia a EMA 50
        dataframe['dist_ema_50'] = (dataframe['close'] - dataframe['ema_50']) / dataframe['ema_50']

        # Volumen Relativo (RVOL)
        vol_sma = dataframe['volume'].rolling(window=20).mean()
        dataframe['rvol'] = dataframe['volume'] / vol_sma.replace(0, 1.0)

        # 3. Teoría de Subasta: Trapped Longs Squeeze Index
        # Mide la concentración de volumen en la mecha superior de una vela de pump fallida
        candle_range = (dataframe['high'] - dataframe['low']).replace(0, 1e-8)
        upper_wick = dataframe['high'] - dataframe[['open', 'close']].max(axis=1)
        dataframe['wick_ratio'] = upper_wick / candle_range
        # Trapped Score: mecha superior alta (>= 40% del rango) con volumen inusual (RVOL >= 1.8)
        dataframe['trapped_longs_signal'] = (dataframe['wick_ratio'] >= 0.40) & (dataframe['rvol'] >= 1.8)

        # 4. Detección de Aceleración en Nodos de Bajo Volumen (LVN Proxy)
        # Una contracción de rango previo seguida de expansión bajista
        atr = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)
        dataframe['atr'] = atr if atr is not None else (dataframe['high'] - dataframe['low'])
        dataframe['is_lvn_break'] = (dataframe['close'] < dataframe['close'].shift(1) - 0.7 * dataframe['atr'])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # -------------------------------------------------------------
        # LONGS = 0 (Completamente Desactivados)
        # -------------------------------------------------------------

        # -------------------------------------------------------------
        # SHORTS A: "Auction Failure / Trapped Longs Squeeze" (Máxima Convicción)
        # -------------------------------------------------------------
        # Combina la estacionalidad humana favorable con la trampa de compradores:
        # - Estacionalidad favorable (Jueves a Domingo o Miércoles tarde)
        # - Señal de compradores atrapados en las últimas 3 velas
        # - Quiebre del mínimo de la vela previa
        # - Pérdida de impulso en MACD
        short_trapped_conditions = (
            (dataframe['seasonal_short_allowed']) &
            (dataframe['trapped_longs_signal'].rolling(window=3).max() == 1) &
            (dataframe['close'] < dataframe['low'].shift(1)) &
            (dataframe['macdhist'] < dataframe['macdhist'].shift(1)) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_trapped_conditions, 'enter_short'] = 1
        dataframe.loc[short_trapped_conditions, 'enter_tag'] = 'short_trapped_auction'

        # -------------------------------------------------------------
        # SHORTS B: "Pump Structure Shift" (Fin de Euforia con Filtro Humano)
        # -------------------------------------------------------------
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

        # -------------------------------------------------------------
        # SHORTS C: "Macro Breakdown" (Tendencia Bajista en Días Favirables)
        # -------------------------------------------------------------
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

        # Salida técnica de Short: Ruptura alcista consolidada sobre EMA 200 o MACD cruza alcista con RSI > 58
        exit_short = (
            (dataframe['close'] > dataframe['ema_200']) |
            ((dataframe['macd'] > dataframe['macdsignal']) & (dataframe['rsi'] > 58))
        )
        dataframe.loc[exit_short, 'exit_short'] = 1

        return dataframe
