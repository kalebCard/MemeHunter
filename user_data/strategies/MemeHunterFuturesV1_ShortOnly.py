"""
MemeHunterFuturesV1_ShortOnly - Versión Asimétrica Pura de MemeHunterFuturesV1.
Hipótesis Cuantitativa:
En MemeHunterFuturesV1 (4h):
- Shorts generaron +103.81 USDT de beneficio neto.
- Longs destruyeron -48.11 USDT.
Al eliminar las compras (Longs = 0) y concentrar el 100% del capital en la asimetría bajista
(Shorting el ciclo de sangrado de memecoins con margen 1.0x aislado),
el sistema elimina la fuga de capital y maximiza el retorno.
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
from pandas import DataFrame
import pandas_ta as ta

LOG = logging.getLogger(__name__)

KILL_SWITCH_DRAWDOWN = 0.25
KILL_SWITCH_FLAG = "KILL_SWITCH"
LIVE_RUNMODES = ('live', 'dry_run', 'runmode.live', 'runmode.dry_run')


def compute_drawdown(profits_abs, starting_balance: float, open_profit_abs: float = 0.0) -> float:
    equity = peak = starting_balance
    for p in profits_abs:
        equity += p
        peak = max(peak, equity)
    total_equity = equity + open_profit_abs
    peak = max(peak, total_equity)
    return (peak - total_equity) / peak if peak > 0 else 0.0


class MemeHunterFuturesV1_ShortOnly(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = True

    # ROI probado en V1
    minimal_roi = {
        "0": 0.602,
        "1704": 0.141,
        "2255": 0.047,
        "7483": 0
    }
    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.040
    trailing_stop_positive_offset = 0.120
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    use_exit_signal = True

    MAX_ADVERSE_FUNDING = -0.0005
    MAX_EUPHORIC_FUNDING = 0.0010

    startup_candle_count = 200

    protections = [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 2
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 6,
            "trade_limit": 3,
            "stop_duration_candles": 6,
            "only_per_pair": False
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 120,
            "trade_limit": 1,
            "stop_duration_candles": 24,
            "max_allowed_drawdown": 0.18
        }
    ]

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        return 1.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        if side == "long":
            return 0.0
        # Shorts con asignación plena 1.0x de slot
        stake = proposed_stake
        if min_stake is not None:
            stake = max(stake, min_stake)
        stake = max(stake, 5.0)
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

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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
        dataframe['atr'] = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # LONGS = 0 (Totalmente deshabilitados en memecoins)

        # SHORTS (Régimen bajista con confirmación macro)
        short_conditions = (
            (dataframe['close'] < dataframe['ema_200']) &
            (dataframe['macd'] < dataframe['macdsignal']) &
            (dataframe['macd'] < 0) &
            (dataframe['rsi'] <= 44) &
            (dataframe['rsi'] >= 24) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_conditions, 'enter_short'] = 1
        dataframe.loc[short_conditions, 'enter_tag'] = 'short_breakdown_ema200'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        # Salida Short: Ruptura alcista sobre EMA 200 o cruce alcista de MACD con RSI > 55
        exit_short = (
            (dataframe['close'] > dataframe['ema_200']) |
            ((dataframe['macd'] > dataframe['macdsignal']) & (dataframe['rsi'] > 55))
        )
        dataframe.loc[exit_short, 'exit_short'] = 1

        return dataframe
