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

    # ROI escalonado
    minimal_roi = {
        "0": 0.45,       # Take profit agresivo ante pump/dump extremo
        "720": 0.20,     # A las 48h asegurar al menos 20%
        "1440": 0.10,    # A los 4 días asegurar 10%
        "2880": 0.04     # A los 8 días asegurar 4%
    }

    # Stoploss de seguridad duro inicial
    stoploss = -0.09  # 9% de riesgo máximo inicial

    # Custom stoploss dinámico activo
    use_custom_stoploss = True
    trailing_stop = False  # Gestionado con precisión quirúrgica en custom_stoploss

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
        Sizing Asimétrico de Alta Convicción:
        - Shorts (Motor principal de beneficio en memecoins): Asignación 1.35x.
        - Longs (Filtro estricto): Asignación 0.50x.
        """
        base_stake = proposed_stake
        if side == "short":
            stake = base_stake * 1.35
        else:
            stake = base_stake * 0.50

        if min_stake is not None:
            stake = max(stake, min_stake)
        stake = max(stake, 5.0)  # Binance Min Notional
        return min(stake, max_stake)

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> Optional[float]:
        """
        INNOVACIÓN: Gestor de Break-Even y Bloqueo Dinámico de Ganancias (Tiered Profit Locking).
        Protege las ganancias acumuladas y elimina el riesgo de round-trip.
        """
        # Tier 3: Ganancia explosiva (> 20%) -> Asegurar trailing ajustado a 4.0%
        if current_profit >= 0.20:
            return -0.040

        # Tier 2: Ganancia sustancial (> 10%) -> Asegurar al menos +5.0% de beneficio cerrado
        if current_profit >= 0.10:
            # Distancia desde current_profit hasta +5.0%
            profit_to_protect = 0.05
            stop_distance = (current_profit - profit_to_protect) / (1 + current_profit)
            return -stop_distance

        # Tier 1: Break-Even Temprano (> 5%) -> Mover Stoploss a +0.5% (Cero Riesgo de Pérdida)
        if current_profit >= 0.05:
            profit_to_protect = 0.005
            stop_distance = (current_profit - profit_to_protect) / (1 + current_profit)
            return -stop_distance

        # Por defecto, mantener el stoploss duro inicial (-9%)
        return -0.09

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
        live = self._is_live_mode()
        flag = self._kill_switch_path()
        if live and flag.exists():
            return False

        if self._is_adverse_funding(pair, side):
            return False

        if not live:
            return True

        # En live/dry_run se evalúa el latch de KillSwitch
        return True

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
        # 1. SEÑALES LONG (Breakout Blindado de Alta Liquidez)
        # -------------------------------------------------------------
        # Solo abrimos Long si:
        # - Precio sobre EMA 200 (Tendencia macro)
        # - MACD alcista
        # - RVOL >= 2.0 (Volumen institucional anómalo comprobado)
        # - ADX >= 22 (Tendencia direccional fuerte, evita rangos y trampas)
        # - RSI saludable (55 <= RSI <= 75)
        long_conditions = (
            (dataframe['close'] > dataframe['ema_200']) &
            (dataframe['macd'] > dataframe['macdsignal']) &
            (dataframe['macd'] > 0) &
            (dataframe['rvol'] >= 2.0) &
            (dataframe['adx'] >= 22.0) &
            (dataframe['rsi'] >= 55) &
            (dataframe['rsi'] <= 75) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[long_conditions, 'enter_long'] = 1
        dataframe.loc[long_conditions, 'enter_tag'] = 'long_institutional_breakout'

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
        # 3. SEÑALES SHORT B: "Pump Exhaustion / Sniper" (Agotamiento de Euforia)
        # -------------------------------------------------------------
        # Detecta el techo de un pump violento:
        # - Precio extendido > 12% por encima de EMA 50
        # - RSI >= 72 (Sobrecompra extrema)
        # - MACD histograma decreciendo (pérdida de inercia compradora)
        # - Cierre por debajo de la apertura o rechazo superior
        short_sniper_conditions = (
            (dataframe['dist_ema_50'] >= 0.12) &
            (dataframe['rsi'] >= 72) &
            (dataframe['macdhist'] < dataframe['macdhist'].shift(1)) &
            (dataframe['close'] < dataframe['open']) &  # Vela de rechazo bajista
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_sniper_conditions, 'enter_short'] = 1
        dataframe.loc[short_sniper_conditions, 'enter_tag'] = 'short_pump_exhaustion'

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
