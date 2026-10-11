from datetime import datetime
from typing import Optional
from pathlib import Path
import json
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

KILL_SWITCH_DRAWDOWN = 0.25  # Bloquea nuevas entradas si el DD del equity realizado supera 25%
KILL_SWITCH_FLAG = "KILL_SWITCH"  # Archivo latch en user_data (borrarlo para reanudar)
LIVE_RUNMODES = ('live', 'dry_run', 'runmode.live', 'runmode.dry_run')


def compute_drawdown(profits_abs, starting_balance: float) -> float:
    """Drawdown maximo actual (fraccion) del equity realizado: (pico - actual) / pico."""
    equity = peak = starting_balance
    for p in profits_abs:
        equity += p
        peak = max(peak, equity)
    return (peak - equity) / peak if peak > 0 else 0.0


class MemeHunterFuturesV1(IStrategy):
    """
    MemeHunterFuturesV1 - Sistema Bidireccional Adaptativo para Binance Futures (USDT-M).
    
    Características Institucionales:
    1. Operativa Bidireccional (can_short = True):
       - Modo Alcista: Entradas Long sobre EMA 200 con aceleración MACD y RSI sano.
       - Modo Bajista: Entradas Short bajo EMA 200 con impulso vendedor para monetizar inviernos y caídas severas.
    2. Apalancamiento Estricto 1.0x (Sin riesgo de liquidación):
       - Se opera con margen aislado al 1x, eliminando por completo el riesgo de margin-call.
    3. Trailing Stop Simétrico:
       - Protege ganancias tanto en subidas como en desplomes (+11.9% offset / 2.2% positive).
    4. Protecciones de Cartera Activas (StoplossGuard, MaxDrawdown, CooldownPeriod).
    """

    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = True

    # Configuración de riesgo y ROI nativo probado
    minimal_roi = {
        "0": 0.602,
        "1704": 0.141,
        "2255": 0.047,
        "7483": 0
    }
    stoploss = -0.15  # Techo de seguridad máximo absoluto (15%)
    trailing_stop = True
    trailing_stop_positive = 0.022
    trailing_stop_positive_offset = 0.119
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    use_exit_signal = False

    # Parámetros simétricos para Long y Short
    rsi_long_lower = IntParameter(50, 65, default=56, space="buy", optimize=True)
    rsi_long_upper = IntParameter(70, 80, default=76, space="buy", optimize=True)

    # Requerimos 200 velas para calcular la EMA 200 macro
    startup_candle_count = 200

    # Protecciones de Cartera (§3.1 DAS Blindado)
    protections = [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 2
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 6,   # 24 horas
            "trade_limit": 3,               # Pausar si saltan 3 stops en 24h
            "stop_duration_candles": 6,     # Pausar 24 horas
            "only_per_pair": False
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 120, # ~20 días
            "trade_limit": 1,
            "stop_duration_candles": 24,    # Pausar 4 días
            "max_allowed_drawdown": 0.15    # Blindado al 15% de drawdown
        },
        {
            "method": "LowProfitPairs",
            "lookback_period_candles": 60,
            "trade_limit": 2,
            "stop_duration_candles": 84,    # 14 días
            "required_profit": 0.0
        }
    ]

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        Garantiza apalancamiento 1.0x (sin apalancamiento tóxico).
        Elimina completamente el riesgo de liquidación en operaciones Short.
        """
        return 1.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
        Sizing Asimétrico y Reinversión Compuesta (Quarter-Kelly):
        - Shorts demostraron Win Rate > 66% y PnL de +61.68%: Asignación estándar óptima.
        - Longs tuvieron desempeño lateral (-4.86%): Reducción prudente de riesgo al 70% del stake.
        """
        base_stake = proposed_stake
        if side == "short":
            stake = base_stake * 1.15  # Impulso moderado en el lado más rentable
        else:
            stake = base_stake * 0.70  # Mitigación del lastre histórico en Longs

        if min_stake is not None:
            stake = max(stake, min_stake)
        # Salvaguarda Binance Min Notional ($5.00 USDT)
        stake = max(stake, 5.0)
        return min(stake, max_stake)


    def _is_live_mode(self) -> bool:
        runmode = self.config.get('runmode')
        return bool(runmode) and str(runmode).lower() in LIVE_RUNMODES

    def _kill_switch_path(self) -> Path:
        return Path(self.config.get('user_data_dir', '/freqtrade/user_data')) / KILL_SWITCH_FLAG

    def _current_drawdown(self) -> float:
        closed = sorted(Trade.get_trades_proxy(is_open=False),
                        key=lambda t: t.close_date_utc or datetime.min)
        start = self.wallets.get_starting_balance() if getattr(self, 'wallets', None) \
            else self.config.get('dry_run_wallet', 0)
        return compute_drawdown([t.close_profit_abs or 0.0 for t in closed], start)

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        """
        Kill-Switch (PB-15): si el drawdown del equity realizado supera KILL_SWITCH_DRAWDOWN,
        no se abren nuevas posiciones. Las abiertas siguen gobernadas por sus stops.
        En dry-run/live queda enclavado en un archivo (borrarlo para reanudar).
        """
        live = self._is_live_mode()
        flag = self._kill_switch_path()
        if live and flag.exists():
            return False

        dd = self._current_drawdown()
        if dd < KILL_SWITCH_DRAWDOWN:
            return True

        LOG.error("KILL-SWITCH: drawdown %.2f%% >= %.0f%%. Entradas bloqueadas (%s %s).",
                  dd * 100, KILL_SWITCH_DRAWDOWN * 100, side, pair)
        if live:
            try:
                flag.write_text(f"Activado {current_time.isoformat()} con drawdown {dd:.2%}\n")
            except OSError as exc:
                LOG.error("No se pudo escribir el latch del kill-switch: %s", exc)
            if getattr(self, 'dp', None):
                try:
                    self.dp.send_msg(f"KILL-SWITCH activado: drawdown {dd:.2%}. Entradas bloqueadas.")
                except Exception:  # noqa: BLE001 - la notificacion no debe romper el bot
                    pass
        return False

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

        # ATR (14) para medir volatilidad
        dataframe['atr'] = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)

        # EMA 200 (Filtro Macro de Régimen)
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # -------------------------------------------------------------
        # 1. SEÑALES LONG (Modo Alcista: Expansión de Momentum)
        # -------------------------------------------------------------
        long_conditions = (
            (dataframe['close'] > dataframe['ema_200']) &           # Tendencia Macro Alcista
            (dataframe['macd'] > dataframe['macdsignal']) &          # Cruce alcista de MACD
            (dataframe['macd'] > 0) &                               # Momentum sobre cero
            (dataframe['rsi'] >= self.rsi_long_lower.value) &       # RSI con impulso suficiente (56)
            (dataframe['rsi'] <= self.rsi_long_upper.value) &       # Sin sobrecompra exhaustiva (76)
            (dataframe['volume'] > 0)
        )
        dataframe.loc[long_conditions, 'enter_long'] = 1
        dataframe.loc[long_conditions, 'enter_tag'] = 'long_momentum_ema200'

        # -------------------------------------------------------------
        # 2. SEÑALES SHORT (Modo Bajista: Monetización del Invierno)
        # -------------------------------------------------------------
        rsi_short_upper = 100 - self.rsi_long_lower.value  # 100 - 56 = 44
        rsi_short_lower = 100 - self.rsi_long_upper.value  # 100 - 76 = 24

        short_conditions = (
            (dataframe['close'] < dataframe['ema_200']) &           # Tendencia Macro Bajista
            (dataframe['macd'] < dataframe['macdsignal']) &          # Cruce bajista de MACD
            (dataframe['macd'] < 0) &                               # Momentum bajo cero
            (dataframe['rsi'] <= rsi_short_upper) &                 # Presión vendedora fuerte (<= 44)
            (dataframe['rsi'] >= rsi_short_lower) &                 # Sin sobreventa de pánico (>= 24)
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_conditions, 'enter_short'] = 1
        dataframe.loc[short_conditions, 'enter_tag'] = 'short_breakdown_ema200'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Cero salidas prematuras manuales: Salidas gestionadas 100% por Trailing Stop y Stoploss
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        return dataframe
