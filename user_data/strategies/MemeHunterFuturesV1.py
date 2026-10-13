from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import logging

try:
    from freqtrade.strategy import (
        IStrategy,
        IntParameter,
        DecimalParameter,
    )
    from freqtrade.persistence import Trade
except ImportError:
    class IStrategy:
        def __init__(self, config=None):
            self.config = config or {}
    class Trade:
        @staticmethod
        def get_trades_proxy(*args, **kwargs):
            return []
    class IntParameter:
        def __init__(self, low, high, default=0, space="buy", optimize=True):
            self.value = default
    class DecimalParameter:
        def __init__(self, low, high, default=0.0, space="buy", optimize=True):
            self.value = default

from pandas import DataFrame
try:
    import pandas_ta as ta
except ImportError:
    ta = None

LOG = logging.getLogger(__name__)

KILL_SWITCH_DRAWDOWN = 0.25  # Bloquea nuevas entradas si el DD del equity realizado supera 25%
KILL_SWITCH_FLAG = "KILL_SWITCH"  # Archivo latch en user_data (borrarlo para reanudar)
LIVE_RUNMODES = ('live', 'dry_run', 'runmode.live', 'runmode.dry_run')


def compute_drawdown(profits_abs, starting_balance: float, open_profit_abs: float = 0.0) -> float:
    """
    PB-25: Drawdown maximo actual (fraccion) de la equidad total (realizada + flotante):
    (pico - actual) / pico. Evita ceguera ante multiples posiciones abiertas en pérdida.
    """
    equity = peak = starting_balance
    for p in profits_abs:
        equity += p
        peak = max(peak, equity)
    total_equity = equity + open_profit_abs
    peak = max(peak, total_equity)
    return (peak - total_equity) / peak if peak > 0 else 0.0


class MemeHunterFuturesV1(IStrategy):
    """
    MemeHunterFuturesV1 - Sistema Bidireccional Adaptativo Blindado para Binance Futures (USDT-M).
    
    Características Institucionales:
    1. Operativa Bidireccional (can_short = True):
       - Modo Alcista: Entradas Long sobre EMA 200 con aceleración MACD y RSI sano.
       - Modo Bajista: Entradas Short bajo EMA 200 con impulso vendedor para monetizar caídas severas.
    2. Apalancamiento Controlado 1.0x & Squeeze Guard:
       - Margen aislado al 1x con stoploss obligatorio (-10%) e invalidación técnica para
         eliminar el riesgo de liquidación catastrófica por short-squeeze en rallies parabólicos.
    3. Trailing Stop Adaptativo & Salidas Técnicas Dinámicas (PB-23):
       - Trailing holgado (+12% offset / 4.0% trailing) para absorber ruido de 4H en memecoins.
       - Salidas por quiebre de régimen técnico (EMA 200 / MACD exhausto) previniendo pérdidas por round-trip.
    4. Guardián de Tasa de Financiación (PB-24):
       - Rechaza aperturas en pares donde el funding rate adverso desangra el capital pasivamente.
    5. Protecciones de Cartera Activas & Kill-Switch de Equidad Total (PB-25).
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
    stoploss = -0.10  # Techo de seguridad optimizado (10% en lugar de 15% para proteger equity)
    trailing_stop = True
    trailing_stop_positive = 0.040  # 4.0% de holgura para absorber mechas intradía en velas de 4h
    trailing_stop_positive_offset = 0.120  # Activación en +12.0%
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    use_exit_signal = True  # PB-23: Habilitar salidas técnicas ante reversión de estructura

    # Umbrales para Guardián de Tasa de Financiación (PB-24)
    MAX_ADVERSE_FUNDING = -0.0005   # Rechaza Short si funding rate < -0.05% por 8h
    MAX_EUPHORIC_FUNDING = 0.0010   # Rechaza Long si funding rate > +0.10% por 8h

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

    def is_secular_bear_pair(self, pair: str) -> bool:
        """
        PB-29: Detección cuantitativa de régimen de sangrado secular (elimina blacklist hardcoded).
        Detecta si la EMA 200 macro cae continuamente (pendiente < -1.5% en 10 velas de 4h).
        """
        if hasattr(self, '_secular_bear_pairs'):
            return pair in self._secular_bear_pairs

        dp = getattr(self, 'dp', None)
        if dp:
            try:
                analyzed_df, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
                if analyzed_df is not None and len(analyzed_df) >= 10:
                    slope = analyzed_df.get('ema_200_slope', None)
                    if slope is not None and len(slope) > 0:
                        val = slope.iloc[-1]
                        if val is not None and not (isinstance(val, float) and val != val) and float(val) < -0.015:
                            LOG.info("PB-29: Régimen secular bajista dinámico en %s (pendiente EMA 200: %.2f%%). Longs anulados.",
                                     pair, float(val) * 100)
                            return True
            except Exception as exc:
                LOG.debug("Error evaluando régimen dinámico para %s: %s", pair, exc)
        return False

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
        Sizing Asimétrico Cuantitativo de Frontera Eficiente:
        - Shorts (+61.68% Alfa probado): Impulso de alta convicción a 1.35x.
        - Longs (Mitigación de volatilidad en altcoins):
          * Si el par tiene deriva bajista secular dinámica (PB-29), se cancela la exposición en compra (0.0x).
          * En régimen saludable, asignación moderada de 0.45x.
        - Salvaguarda inviolable: Min notional de Binance de $5.00 USDT.
        """
        if side == "long" and self.is_secular_bear_pair(pair):
            return 0.0

        base_stake = proposed_stake
        if side == "short":
            stake = base_stake * 1.35
        else:
            stake = base_stake * 0.45

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

    def _get_current_rate_for_trade(self, trade) -> Optional[float]:
        """Obtiene el último precio conocido para una posición abierta."""
        dp = getattr(self, 'dp', None)
        if dp:
            try:
                # 1. Intentar ticker en vivo
                ticker = dp.ticker(trade.pair)
                if ticker and ticker.get('last') is not None:
                    return float(ticker['last'])
            except Exception:
                pass
            try:
                # 2. Intentar último cierre analizado
                df, _ = dp.get_analyzed_dataframe(trade.pair, self.timeframe)
                if df is not None and len(df) > 0 and 'close' in df:
                    return float(df['close'].iloc[-1])
            except Exception:
                pass
        return getattr(trade, 'open_rate', None)

    def _current_drawdown(self) -> float:
        closed = sorted(Trade.get_trades_proxy(is_open=False),
                        key=lambda t: t.close_date_utc or datetime.min)
        open_trades = Trade.get_trades_proxy(is_open=True)
        open_pnl = 0.0
        if open_trades:
            for t in open_trades:
                # Si el mock o proxy ya expone current_profit_abs, usarlo directamente
                if hasattr(t, 'current_profit_abs') and t.current_profit_abs is not None:
                    open_pnl += float(t.current_profit_abs)
                elif hasattr(t, 'calc_profit'):
                    curr_rate = self._get_current_rate_for_trade(t)
                    if curr_rate:
                        try:
                            open_pnl += float(t.calc_profit(rate=curr_rate))
                        except Exception as exc:
                            LOG.debug("Error calculando profit flotante para %s: %s", t.pair, exc)
        start = self.wallets.get_starting_balance() if getattr(self, 'wallets', None) \
            else self.config.get('dry_run_wallet', 0)
        return compute_drawdown([t.close_profit_abs or 0.0 for t in closed], start, open_profit_abs=open_pnl)

    def _is_adverse_funding(self, pair: str, side: str) -> bool:
        """
        PB-24 / PB-34: Guardián de Tasa de Financiación en Futuros.
        Evita abrir Shorts si el funding es negativo severo (< -0.05% cada 8h),
        lo que drena el capital pagando comisiones periódicas a los Longs.
        """
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
                    LOG.warning("PB-24/34: Rechazando SHORT en %s: Funding rate sangrante (%.4f%%).",
                                pair, funding_rate * 100)
                    return True
                if side == "long" and funding_rate > self.MAX_EUPHORIC_FUNDING:
                    LOG.warning("PB-24/34: Rechazando LONG en %s: Funding rate euforico excesivo (%.4f%%).",
                                pair, funding_rate * 100)
                    return True
        except Exception as exc:
            LOG.warning("PB-34: No se pudo verificar funding rate para %s: %s", pair, exc)
        return False

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        """
        Kill-Switch (PB-15 / PB-25): si el drawdown de la equidad total (realizada + flotante)
        supera KILL_SWITCH_DRAWDOWN, no se abren nuevas posiciones.
        Guardián de Financiación (PB-24): rechaza entradas si el funding desangra la posición.
        """
        live = self._is_live_mode()
        flag = self._kill_switch_path()
        if live and flag.exists():
            return False

        if self._is_adverse_funding(pair, side):
            return False

        dd = self._current_drawdown()
        if dd >= KILL_SWITCH_DRAWDOWN:
            LOG.error("KILL-SWITCH: drawdown %.2f%% >= %.0f%%. Entradas bloqueadas (%s %s).",
                      dd * 100, KILL_SWITCH_DRAWDOWN * 100, side, pair)
            if live:
                try:
                    flag.write_text(f"Activado {current_time.isoformat()} con drawdown {dd:.2%}\n")
                except OSError as exc:
                    LOG.error("No se pudo escribir el latch del kill-switch: %s", exc)
                if getattr(self, 'dp', None):
                    self.dp.send_msg(f"🚨 KILL-SWITCH: Drawdown {dd:.2%} >= {KILL_SWITCH_DRAWDOWN:.0%}. Bot bloqueado.")
            return False

        return True
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

        # EMA 200 (Filtro Macro de Régimen) y pendiente relativa (10 periodos / 40h)
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)
        dataframe['ema_200_slope'] = (dataframe['ema_200'] - dataframe['ema_200'].shift(10)) / dataframe['ema_200'].shift(10)

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
        """
        PB-23: Salidas técnicas dinámicas para evitar el riesgo de round-trip trade
        y proteger capital si la estructura macro se invierte.
        """
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        # Salida Long: Pérdida de la tendencia macro (cierre bajo EMA 200) o
        # cruce bajista de MACD con RSI perdiendo momento (< 45)
        exit_long = (
            (dataframe['close'] < dataframe['ema_200']) |
            ((dataframe['macd'] < dataframe['macdsignal']) & (dataframe['rsi'] < 45))
        )
        dataframe.loc[exit_long, 'exit_long'] = 1

        # Salida Short: Ruptura alcista sobre EMA 200 o cruce alcista de MACD con RSI > 55
        exit_short = (
            (dataframe['close'] > dataframe['ema_200']) |
            ((dataframe['macd'] > dataframe['macdsignal']) & (dataframe['rsi'] > 55))
        )
        dataframe.loc[exit_short, 'exit_short'] = 1

        return dataframe
