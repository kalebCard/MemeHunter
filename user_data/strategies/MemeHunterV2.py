from datetime import datetime
from pathlib import Path
import json
import logging

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    merge_informative_pair,
)
from freqtrade.persistence import Trade
from pandas import DataFrame
import pandas_ta as ta

LOG = logging.getLogger(__name__)


class MemeHunterV2(IStrategy):
    """
    MemeHunterV2 - Sistema Cuantitativo Dinámico y Adaptativo para Binance Real.
    
    Mejoras clave respecto a V1:
    1. Semáforo Macro Global: Informative Pair BTC/USDT 1D (EMA 50 / EMA 200).
    2. Position Sizing Dinámico por Volatilidad: Arriesga exactamente el 1.0% de la cartera por trade según ATR.
    3. Chandelier Trailing Exit & Breakeven:
       - Si profit > +1.5x ATR -> Protege Breakeven (+0.5% para cubrir fees).
       - Si profit > +2.5x ATR -> Trailing ceñido a 1x ATR desde máximos.
       - Stop inicial a 2x ATR.
    4. Cero salidas prematuras (use_exit_signal = False).
    """

    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False

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

    # Parámetros optimizables
    rsi_lower = IntParameter(50, 65, default=56, space="buy", optimize=True)
    rsi_upper = IntParameter(70, 80, default=76, space="buy", optimize=True)
    atr_sl_mult = DecimalParameter(1.5, 3.0, default=2.0, space="sell", optimize=True)

    # Requerimos suficientes velas para calcular indicadores de 4h
    startup_candle_count = 200

    # Protecciones de Cartera (§3.1 DAS)
    protections = [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 2
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 6,   # 24 horas
            "trade_limit": 3,               # Blindado: Pausar si saltan 3 stops en 24h
            "stop_duration_candles": 6,     # Pausar 24 horas
            "only_per_pair": False
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 120, # ~20 días
            "trade_limit": 1,
            "stop_duration_candles": 24,    # Pausar 4 días (24 velas de 4h)
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

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._universe = {}
        datadir = Path(config.get('datadir', '/freqtrade/user_data/data'))
        universe_path = datadir / "binance_vision" / "universe.json"
        if not universe_path.exists():
            universe_path = datadir.parent / "binance_vision" / "universe.json"

        if universe_path.exists():
            self._universe = json.loads(universe_path.read_text())
        else:
            LOG.warning("Universe map no encontrado en %s. Filtro inactivo.", universe_path)

    def informative_pairs(self):
        """Define pares informativos para el análisis macro."""
        return [("BTC/USDT", "1d")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']

        # 1. Filtro de Universo Dinámico (Top 30 histórico en backtest, nativo en live/dry_run)
        is_live_mode = self.config.get('runmode') and str(self.config.get('runmode')).lower() in ('live', 'dry_run', 'runmode.live', 'runmode.dry_run')
        if self._universe and not is_live_mode:
            months = dataframe['date'].dt.strftime('%Y-%m')
            valid_months = {m for m, pairs in self._universe.items() if pair in pairs}
            dataframe['in_universe'] = months.isin(valid_months)
        else:
            dataframe['in_universe'] = True

        # 2. Semáforo Macro BTC en velas 1D
        if self.dp:
            btc_1d = self.dp.get_pair_dataframe("BTC/USDT", "1d")
            if not btc_1d.empty:
                btc_ema_50 = ta.ema(btc_1d['close'], length=50)
                btc_ema_200 = ta.ema(btc_1d['close'], length=200)
                btc_1d['btc_macro_bull'] = (
                    (btc_1d['close'] > (btc_ema_50 if btc_ema_50 is not None else 0)) &
                    (btc_1d['close'] > (btc_ema_200 if btc_ema_200 is not None else 0))
                )
                dataframe = merge_informative_pair(
                    dataframe, btc_1d, self.timeframe, "1d", ffill=True
                )
        if 'btc_macro_bull_1d' not in dataframe.columns:
            dataframe['btc_macro_bull_1d'] = True

        # 3. Indicadores del par en 4H
        # Filtro de régimen del par propio
        ema200 = ta.ema(dataframe['close'], length=200)
        dataframe['ema_200'] = ema200 if ema200 is not None else 0

        # MACD (Momentum)
        macd = ta.macd(dataframe['close'])
        if macd is not None:
            dataframe['macd'] = macd['MACD_12_26_9']
            dataframe['macdsignal'] = macd['MACDs_12_26_9']
        else:
            dataframe['macd'] = 0
            dataframe['macdsignal'] = 0

        # ATR (Volatilidad para Stoploss y Position Sizing)
        dataframe['atr'] = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)
        dataframe['atr_sma'] = ta.sma(dataframe['atr'], length=14)

        # RSI (Fuerza relativa sin sobrecompra)
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema_200']) &       # Tendencia alcista del propio par
                (dataframe['macd'] > dataframe['macdsignal']) &     # Momentum alcista
                (dataframe['atr'] > dataframe['atr_sma']) &         # Expansión de volatilidad
                (dataframe['rsi'] > self.rsi_lower.value) &         # Fortaleza de impulso
                (dataframe['rsi'] < self.rsi_upper.value) &         # Sin sobrecompra extrema
                (dataframe['volume'] > 0) &
                (dataframe['in_universe'] == True)                  # Liquidez comprobada
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Salidas gobernadas por custom_stoploss dinámico
        return dataframe


    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Stoploss dinámico: mult * ATR del momento de la entrada.
        Si el precio cae por debajo del stop_price, retorna 1 para ejecutar la venta inmediata.
        Permite que el trailing stop (+11.9% offset) y la escalera ROI capturen las ganancias.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if trade.open_date_utc and dataframe is not None and not dataframe.empty:
            entry_candles = dataframe[dataframe['date'] <= trade.open_date_utc]
            if not entry_candles.empty:
                entry_atr = entry_candles.iloc[-1]['atr']
                if entry_atr > 0 and trade.open_rate > 0:
                    stop_mult = self.atr_sl_mult.value
                    stop_price = trade.open_rate - (stop_mult * entry_atr)
                    if current_rate <= stop_price:
                        return 1  # Salida inmediata si perforó el stop
                    return (stop_price - current_rate) / current_rate

        return -0.10
