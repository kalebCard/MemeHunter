from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
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
        "0": 100.0  # Solo cerramos por señales o stop/trailing (optimizaremos esto con Freqtrade nativamente)
    }
    stoploss = -0.99  # Desactivar el estático; se usa custom_stoploss basado en ATR
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.10
    trailing_only_offset_is_reached = True

    # Parámetros de Optimización (Hyperopt - PB-10)
    # Rango del RSI para entrada
    rsi_lower = IntParameter(40, 60, default=50, space="buy", optimize=True)
    rsi_upper = IntParameter(60, 80, default=70, space="buy", optimize=True)
    
    # Multiplicador del ATR para el Stoploss dinámico
    atr_sl_mult = DecimalParameter(1.0, 4.0, default=2.0, space="sell", optimize=True)

    # Definimos que necesitamos al menos 30 velas para calcular las medias y el MACD
    startup_candle_count = 30

    # Protecciones de Cartera (DAS §3.1)
    protections = [
        {
            # Cooldown: Tras cerrar una operación, esperar 2 velas (8 horas) antes de volver a operar el mismo par.
            "method": "CooldownPeriod",
            "stop_duration_candles": 2
        },
        {
            # StoplossGuard: Si saltan 4 stoplosses en 24 horas, detener toda la operativa durante 1 día.
            # Nos protege de días catastróficos donde el mercado cambia de régimen bruscamente.
            "method": "StoplossGuard",
            "lookback_period_candles": 6,   # 6 velas de 4h = 24 horas
            "trade_limit": 4,
            "stop_duration_candles": 6,     # Pausar 24 horas
            "only_per_pair": False          # Evalúa a nivel global (toda la cartera)
        },
        {
            # MaxDrawdown: Si el saldo total baja un 20%, apagar el bot.
            "method": "MaxDrawdown",
            "lookback_period_candles": 120, # Mirar hacia atrás ~20 días
            "trade_limit": 1,               # Limitar a 1 trade perdedor del tamaño del max_allowed_drawdown
            "stop_duration_candles": 12,    # Detener por 2 días
            "max_allowed_drawdown": 0.20
        },
        {
            # LowProfitPairs: Si un par resulta ser un perdedor crónico (ej. -5% acumulado en las últimas 10 operaciones)
            # se prohíbe operar ese par durante 2 semanas.
            "method": "LowProfitPairs",
            "lookback_period_candles": 60,  # Últimos 10 días
            "trade_limit": 2,
            "stop_duration_candles": 84,    # 84 velas de 4h = 14 días
            "required_profit": 0.0
        }
    ]

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
                (dataframe['rsi'] > self.rsi_lower.value) &        # Tendencia sana (optimizada)
                (dataframe['rsi'] < self.rsi_upper.value) &        # NO sobrecomprado (optimizada)
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
                    # Riesgo = mult * ATR
                    stop_mult = self.atr_sl_mult.value
                    stop_price = trade.open_rate - (stop_mult * entry_atr)
                    if current_rate > stop_price:
                        return (stop_price - current_rate) / current_rate
        
        # Fallback
        return -0.10
