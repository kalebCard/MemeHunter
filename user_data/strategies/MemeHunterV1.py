from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas_ta as ta
import json
from pathlib import Path

class MemeHunterV1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False
    
    # Configuración de riesgo y ROI
    minimal_roi = {
        "0": 100.0  # Solo cerramos por señales o stop/trailing
    }
    stoploss = -0.99  # Desactivar el estático; se usa custom_stoploss basado en ATR
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.10
    trailing_only_offset_is_reached = True

    # Definimos que necesitamos al menos 30 velas para calcular las medias y el MACD
    startup_candle_count = 30

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._universe = {}
        universe_path = Path(config['datadir']) / "binance_vision" / "universe.json"
        if universe_path.exists():
            self._universe = json.loads(universe_path.read_text())
        else:
            print(f"Warning: {universe_path} no encontrado. Filtro de universo inactivo.")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        
        # Filtro de Universo Dinámico (Top N histórico mensual)
        # Permite operar solo en los meses donde el par era válido.
        if self._universe:
            # Convertimos la fecha a YYYY-MM para vectorizar
            months = dataframe['date'].dt.strftime('%Y-%m')
            
            # Lista de meses válidos para este par
            valid_months = {m for m, pairs in self._universe.items() if pair in pairs}
            
            # Máscara: True si el mes estaba en el universo de ese par
            dataframe['in_universe'] = months.isin(valid_months)
        else:
            dataframe['in_universe'] = True

        # Indicadores: MACD
        macd = ta.macd(dataframe['close'])
        if macd is not None:
            dataframe['macd'] = macd['MACD_12_26_9']
            dataframe['macdsignal'] = macd['MACDs_12_26_9']
        else:
            dataframe['macd'] = 0
            dataframe['macdsignal'] = 0

        # Indicadores: ATR para volatilidad
        dataframe['atr'] = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)
        dataframe['atr_sma'] = ta.sma(dataframe['atr'], length=14)

        # Indicadores: RSI para evitar sobrecompra
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['macd'] > dataframe['macdsignal']) &    # Momentum alcista
                (dataframe['atr'] > dataframe['atr_sma']) &        # Expansión de volatilidad
                (dataframe['rsi'] > 50) &                          # Tendencia sana
                (dataframe['rsi'] < 70) &                          # NO sobrecomprado
                (dataframe['volume'] > 0) &
                (dataframe['in_universe'] == True)                 # Filtro de sesgo
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['macd'] < dataframe['macdsignal']) &    # Pérdida de momentum
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: 'datetime',
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Stoploss dinámico: 2x ATR del momento de la entrada.
        Si la vela de entrada no tiene ATR, fallback al 10%.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Si el trade acaba de abrirse, miramos el ATR en ese momento
        if trade.open_date_utc:
            # Buscar la vela de entrada (o la anterior)
            entry_candles = dataframe[dataframe['date'] <= trade.open_date_utc]
            if not entry_candles.empty:
                entry_atr = entry_candles.iloc[-1]['atr']
                if entry_atr > 0 and trade.open_rate > 0:
                    # Riesgo = 2 * ATR
                    risk_ratio = (2 * entry_atr) / trade.open_rate
                    # Freqtrade stoploss is relative to current_rate if current_profit > 0? No,
                    # return relative percentage from current_rate that would hit stoploss, 
                    # but it's simpler to just return a hard relative stop from entry rate initially.
                    # El stop_loss devuelto aquí es % desde el current_rate hacia abajo.
                    # Para mantenerlo atado a la entrada:
                    stop_price = trade.open_rate - (2 * entry_atr)
                    if current_rate > stop_price:
                        return (stop_price - current_rate) / current_rate
        
        # Fallback
        return -0.10
