from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas_ta as ta
import json
from pathlib import Path

class MemeHunterV1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False
    
    # Minimal ROI
    minimal_roi = {
        "0": 100.0  # Require 10000% to let it run (essentially rely on stoploss/trailing)
    }

    # Stoploss
    stoploss = -0.10  # 10% stoploss
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.10
    trailing_only_offset_is_reached = True

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

        # Simple MACD for testing
        macd = ta.macd(dataframe['close'])
        if macd is not None:
            dataframe['macd'] = macd['MACD_12_26_9']
            dataframe['macdsignal'] = macd['MACDs_12_26_9']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['macd'] > dataframe['macdsignal']) &
                (dataframe['volume'] > 0) &
                (dataframe['in_universe'] == True)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1
        return dataframe
