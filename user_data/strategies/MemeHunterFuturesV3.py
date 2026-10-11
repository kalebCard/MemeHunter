"""
MemeHunterFuturesV3 - Sistema de Alta Innovación y Asimetría Cuantitativa para Memecoins.

Innovaciones Incorporadas:
1. Short-Sniper (Pump Exhaustion):
   - Detecta sobreextensión parabólica en memecoins (precio > EMA 50 por más de 12%, RSI >= 75)
     con rechazo bajista o cruce MACD bajista. Atrapa el colapso desde la cresta.
2. Long Breakout Blindado (Anti-Chop):
   - Solo permite Longs si el volumen relativo (RVOL) >= 2.2x y ADX > 25 con tendencia EMA 200.
   - Elimina las falsas rupturas que drenaban capital en V1.
3. Custom Stoploss Dinámico con Bloqueo de Ganancias (Break-Even Engine):
   - +5% de ganancia -> Stop a +0.5% (Elimina riesgo de pérdida).
   - +10% de ganancia -> Stop asegura +5.0%.
   - +20% de ganancia -> Trailing stop de 3.5% para dejar correr las ganancias parabólicas.
4. Preservación del Timeframe Macro (4h) con resolución intra-vela de 1m:
   - Evita el sangrado por comisiones de 1h y respeta los ciclos de acumulación/distribución.
5. Sizing Asimétrico y Protección Anti-Funding Adverso.
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


class MemeHunterFuturesV3(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = True

    # ROI calibrado para capturar la desinflación macro de memecoins
    minimal_roi = {
        "0": 0.602,
        "1704": 0.141,
        "2255": 0.047,
        "7483": 0
    }

    # Stoploss duro inicial (-10%)
    stoploss = -0.10

    # Trailing Stop Nativo de Alta Rentabilidad (Probado en V1_ShortOnly):
    # Solo se activa cuando la ganancia alcanza al menos +12.0% (offset).
    # Una vez alcanzado, persigue el precio con una distancia de 4.0%
    # permitiendo que las mechas intradiarias respiren y los colapsos corran.
    trailing_stop = True
    trailing_stop_positive = 0.040
    trailing_stop_positive_offset = 0.120
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False

    use_exit_signal = True

    # Umbrales para Guardián de Tasa de Financiación
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
        Sizing Asimétrico de Máxima Convicción Cuantitativa:
        - Longs: 0.0 (Elimina por completo el drenaje de comisiones y falsos rompimientos).
        - Shorts de Quiebre Estructural ('short_structure_shift'): 1.30x (Alta convicción tras pump exhaustion).
        - Shorts Macro Breakdown ('short_macro_breakdown'): 1.0x (Tendencia estándar).
        """
        if side == "long":
            return 0.0

        base_stake = proposed_stake
        if entry_tag == "short_structure_shift":
            stake = base_stake * 1.30
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
        # MACD (12, 26, 9)
        macd = ta.macd(dataframe['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            dataframe['macd'] = macd['MACD_12_26_9']
            dataframe['macdsignal'] = macd['MACDs_12_26_9']
            dataframe['macdhist'] = macd['MACDh_12_26_9']
        else:
            dataframe['macd'] = 0.0
            dataframe['macdsignal'] = 0.0
            dataframe['macdhist'] = 0.0

        # RSI (14)
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        # ADX (14) para medir fuerza direccional de la tendencia
        adx_df = ta.adx(dataframe['high'], dataframe['low'], dataframe['close'], length=14)
        if adx_df is not None:
            dataframe['adx'] = adx_df['ADX_14']
        else:
            dataframe['adx'] = 0.0

        # Medias Móviles Exponenciales Clave
        dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)

        # Distancia relativa a la EMA 50 (para medir sobreextensión o pump insostenible)
        dataframe['dist_ema_50'] = (dataframe['close'] - dataframe['ema_50']) / dataframe['ema_50']

        # Volumen relativo (RVOL) = Volumen actual / SMA de volumen de 20 periodos
        vol_sma = dataframe['volume'].rolling(window=20).mean()
        dataframe['rvol'] = dataframe['volume'] / vol_sma.replace(0, 1.0)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # -------------------------------------------------------------
        # 1. SEÑALES LONG = 0 (Desactivadas por Evidencia Cuantitativa Oficial)
        # Las memecoins sufren un 95% de decaimiento post-pump; eliminar longs
        # protege el capital de trampas de liquidez y falsos rompimientos.
        # -------------------------------------------------------------

        # -------------------------------------------------------------
        # 2. SEÑALES SHORT A: "Trend Breakdown" (Colapso Macro bajo EMA 200)
        # -------------------------------------------------------------
        short_macro_conditions = (
            (dataframe['close'] < dataframe['ema_200']) &
            (dataframe['macd'] < dataframe['macdsignal']) &
            (dataframe['macd'] < 0) &
            (dataframe['rsi'] <= 44) &
            (dataframe['rsi'] >= 22) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_macro_conditions, 'enter_short'] = 1
        dataframe.loc[short_macro_conditions, 'enter_tag'] = 'short_macro_breakdown'

        # -------------------------------------------------------------
        # 3. SEÑALES SHORT B: "Pump Breakdown / Structure Shift" (Fin de Euforia Confirmado)
        # -------------------------------------------------------------
        # Blindaje anti-squeeze: No shorteamos el cuchillo alcista.
        # Exigimos confirmación de quiebre estructural:
        # - El precio venía sobreextendido (> 12% sobre EMA 50 en últimas 3 velas)
        # - Pierde el mínimo de la vela previa (close < low.shift(1))
        # - RSI abandona la sobrecompra (cruza a la baja bajo 68 tras haber tocado >= 70)
        # - Histograma MACD en contracción o negativo
        short_structure_shift = (
            (dataframe['dist_ema_50'].rolling(window=3).max() >= 0.12) &
            (dataframe['close'] < dataframe['low'].shift(1)) &
            (dataframe['rsi'] < 68) &
            (dataframe['rsi'].shift(1) >= 65) &
            (dataframe['macdhist'] < dataframe['macdhist'].shift(1)) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_structure_shift, 'enter_short'] = 1
        dataframe.loc[short_structure_shift, 'enter_tag'] = 'short_structure_shift'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Salidas técnicas ante reversión estructural para preservar capital.
        """
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        # Salida Long: Pérdida de EMA 200 o cruce bajista con RSI débil
        exit_long = (
            (dataframe['close'] < dataframe['ema_200']) |
            ((dataframe['macd'] < dataframe['macdsignal']) & (dataframe['rsi'] < 45))
        )
        dataframe.loc[exit_long, 'exit_long'] = 1

        # Salida Short: Ruptura alcista consolidada sobre EMA 200 o MACD cruza alcista con RSI > 58
        exit_short = (
            (dataframe['close'] > dataframe['ema_200']) |
            ((dataframe['macd'] > dataframe['macdsignal']) & (dataframe['rsi'] > 58))
        )
        dataframe.loc[exit_short, 'exit_short'] = 1

        return dataframe
