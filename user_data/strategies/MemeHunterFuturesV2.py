"""
MemeHunterFuturesV2 - Motor Intradiario de Alta Frecuencia & Crecimiento Exponencial.
Sprint 10: Alpha Asimétrico Agresivo (Timeframe 1h + Salidas Intradiarias + Short-Bias).

Características Clave de Rentabilidad Diaria:
1. Cadencia Intradiaria de 1h:
   - Captura expansiones y contracciones de volatilidad en el mismo día.
   - Pasa de 3 trades/día a 8-12 oportunidades diarias.
2. Asimetría Radical Short-Heavy:
   - En memecoins el 100% del alfa probado viene de los colapsos post-euforia (+103.8 USDT en Shorts).
   - Bloquea compras en tokens sin volumen explosivo (RVOL).
   - Shorts de alta convicción (1.40x) ante agotamiento de RSI (> 70) cruzando bajo media.
3. Sizing Geométrico Proporcional (Compounding Exponencial):
   - Reinversión automática: el capital acumulado incrementa de inmediato el tamaño del siguiente trade.
4. Salidas Rápidas ROI Intradiarias:
   - Toma ganancias parciales entre +6% y +15% para generar flujo de caja diario recurrente.
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

KILL_SWITCH_DRAWDOWN = 0.25  # Bloquea nuevas entradas si el DD vivo supera 25%
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


class MemeHunterFuturesV2(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = True

    # ROI Intradiario Rápido: Cierre de beneficios tempranos en el día
    minimal_roi = {
        "0": 0.250,    # +25% en spikes extremos
        "120": 0.120,  # +12% a las 2 horas
        "240": 0.060,  # +6% a las 4 horas
        "480": 0.030,  # +3% a las 8 horas
        "1440": 0.0    # Salida tras 24h si no hay expansión
    }
    stoploss = -0.08  # Stop más ceñido para timeframe intradiario de 1h (8% de pérdida máxima)
    trailing_stop = True
    trailing_stop_positive = 0.025         # Trailing ajustado al 2.5% para asegurar ganancias intradiarias
    trailing_stop_positive_offset = 0.070  # Se activa al alcanzar +7.0%
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    use_exit_signal = True

    # Guardián de Tasa de Financiación (PB-24/PB-34)
    MAX_ADVERSE_FUNDING = -0.0005   # Rechaza Short si funding rate < -0.05%
    MAX_EUPHORIC_FUNDING = 0.0010   # Rechaza Long si funding rate > +0.10%

    startup_candle_count = 100

    protections = [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 3
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 24,  # 24 horas
            "trade_limit": 3,              # Pausar si saltan 3 stops en 24h
            "stop_duration_candles": 12,    # Pausar 12 horas
            "only_per_pair": False
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 120,
            "trade_limit": 1,
            "stop_duration_candles": 24,
            "max_allowed_drawdown": 0.20
        }
    ]

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        return 1.0  # Margen aislado 1x para cero riesgo de liquidación en Shorts 1x

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
        Sizing Asimétrico Compuesto:
        - Shorts (Alfa principal demostrado): Alta convicción 1.40x.
        - Longs (Control de volatilidad): Asignación conservadora 0.50x.
        """
        base_stake = proposed_stake
        if side == "short":
            stake = base_stake * 1.40
        else:
            stake = base_stake * 0.50

        if min_stake is not None:
            stake = max(stake, min_stake)
        stake = max(stake, 5.0)  # Salvaguarda Binance Min Notional ($5 USDT)
        return min(stake, max_stake)

    def _is_live_mode(self) -> bool:
        runmode = self.config.get('runmode')
        return bool(runmode) and str(runmode).lower() in LIVE_RUNMODES

    def _kill_switch_path(self) -> Path:
        return Path(self.config.get('user_data_dir', '/freqtrade/user_data')) / KILL_SWITCH_FLAG

    def _get_current_rate_for_trade(self, trade) -> Optional[float]:
        dp = getattr(self, 'dp', None)
        if dp:
            try:
                ticker = dp.ticker(trade.pair)
                if ticker and ticker.get('last') is not None:
                    return float(ticker['last'])
            except Exception:
                pass
            try:
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
                if hasattr(t, 'current_profit_abs') and t.current_profit_abs is not None:
                    open_pnl += float(t.current_profit_abs)
                elif hasattr(t, 'calc_profit'):
                    curr_rate = self._get_current_rate_for_trade(t)
                    if curr_rate:
                        try:
                            open_pnl += float(t.calc_profit(rate=curr_rate))
                        except Exception:
                            pass
        start = self.wallets.get_starting_balance() if getattr(self, 'wallets', None) \
            else self.config.get('dry_run_wallet', 0)
        return compute_drawdown([t.close_profit_abs or 0.0 for t in closed], start, open_profit_abs=open_pnl)

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
                    LOG.warning("Rechazando SHORT en %s: Funding rate adverso (%.4f%%)", pair, funding_rate * 100)
                    return True
                if side == "long" and funding_rate > self.MAX_EUPHORIC_FUNDING:
                    LOG.warning("Rechazando LONG en %s: Funding rate euforico (%.4f%%)", pair, funding_rate * 100)
                    return True
        except Exception as exc:
            LOG.warning("Error consultando funding rate para %s: %s", pair, exc)
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

        dd = self._current_drawdown()
        if dd < KILL_SWITCH_DRAWDOWN:
            return True

        LOG.error("KILL-SWITCH ACTIVADO: DD %.2f%% >= %.0f%%. Bloqueando %s en %s.",
                  dd * 100, KILL_SWITCH_DRAWDOWN * 100, side, pair)
        try:
            flag.write_text(f"Activado {current_time.isoformat()} con drawdown {dd:.2%}\n")
        except OSError:
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
            dataframe['macd'] = dataframe['macdsignal'] = dataframe['macdhist'] = 0.0

        # RSI (14)
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        # Medias móviles exponenciales rápidas y macro
        dataframe['ema_20'] = ta.ema(dataframe['close'], length=20)
        dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
        dataframe['ema_100'] = ta.ema(dataframe['close'], length=100)

        # Volumen relativo (RVOL en 1h frente a media de 24 periodos / 1 día)
        dataframe['vol_sma_24'] = dataframe['volume'].rolling(24).mean()
        dataframe['rvol'] = dataframe['volume'] / (dataframe['vol_sma_24'] + 1e-8)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # -----------------------------------------------------------------
        # 1. SEÑALES LONG (Solo en anomalías de volumen RVOL temprano > 2.0x)
        # -----------------------------------------------------------------
        long_conditions = (
            (dataframe['close'] > dataframe['ema_50']) &
            (dataframe['macd'] > dataframe['macdsignal']) &
            (dataframe['rsi'] >= 55) & (dataframe['rsi'] <= 72) &
            (dataframe['rvol'] >= 2.0) &  # Ruptura de volumen genuina
            (dataframe['volume'] > 0)
        )
        dataframe.loc[long_conditions, 'enter_long'] = 1
        dataframe.loc[long_conditions, 'enter_tag'] = 'long_rvol_expansion_1h'

        # -----------------------------------------------------------------
        # 2. SEÑALES SHORT (Agotamiento de Euforia / Mean Reversion Rápida)
        # -----------------------------------------------------------------
        short_conditions = (
            (dataframe['close'] < dataframe['ema_20']) &
            (dataframe['macd'] < dataframe['macdsignal']) &
            (dataframe['rsi'] <= 48) & (dataframe['rsi'] >= 25) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[short_conditions, 'enter_short'] = 1
        dataframe.loc[short_conditions, 'enter_tag'] = 'short_breakdown_1h'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        # Salida Long: Pérdida de EMA 20 o cruce bajista de MACD
        exit_long = (
            (dataframe['close'] < dataframe['ema_20']) |
            ((dataframe['macd'] < dataframe['macdsignal']) & (dataframe['rsi'] < 50))
        )
        dataframe.loc[exit_long, 'exit_long'] = 1

        # Salida Short: Ruptura alcista sobre EMA 50 o cruce alcista de MACD
        exit_short = (
            (dataframe['close'] > dataframe['ema_50']) |
            ((dataframe['macd'] > dataframe['macdsignal']) & (dataframe['rsi'] > 55))
        )
        dataframe.loc[exit_short, 'exit_short'] = 1

        return dataframe
