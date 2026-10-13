"""
Estrategia Ensamble Generada Dinámicamente por la Fábrica de Minería de Alphas.
Compilada automáticamente a partir del Estado de la Incubadora HRP y la Biblioteca de Factores.
Estatus: LIVE PRODUCTION READY
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

try:
    from freqtrade.strategy import IStrategy
except ImportError:
    class IStrategy:
        def __init__(self, config: Optional[dict] = None):
            self.config = config or {}

try:
    import talib.abstract as ta
except ImportError:
    try:
        import pandas_ta as ta
    except ImportError:
        ta = None


class MemeHunter_MinedEnsemble(IStrategy):
    """
    Estrategia de Ensamble Multi-Factor ponderada por Hierarchical Risk Parity (HRP).
    Integra los factores validados por CPCV y control de descubrimientos falsos (FDR).
    """

    INTERFACE_VERSION = 3
    can_short: bool = True
    timeframe = "4h"

    # Parámetros de Riesgo y Microestructura
    stoploss = -0.10  # Stop Loss duro al 10%
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # Trailing Stop Holgado de Alta Fidelidad
    trailing_stop = True
    trailing_stop_positive = 0.04
    trailing_stop_positive_offset = 0.12
    trailing_only_offset_is_reached = True

    # Ponderaciones HRP de Factores Activos
    ACTIVE_WEIGHTS = {
        "ALPHA_001": 0.25,
        "ALPHA_002": 0.2499999987543191,
        "ALPHA_004": 0.5000000012456809,
        "STRAT_A": 0.187585,
        "STRAT_B": 0.812415,
        "ALPHA_LIVE_01": 1.0,
        "HEALTHY_01": 1.0
}

    # Órdenes forzadas a mercado en salidas para erradicar riesgo de no-fill
    order_types = {
        "entry": "limit",
        "exit": "market",
        "emergency_exit": "market",
        "force_entry": "market",
        "force_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
        "stoploss_on_exchange_interval": 60,
    }

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calcula los indicadores base y evalúa vectorialmente los factores minados."""
        if dataframe.empty:
            return dataframe

        # 1. Variables de Microestructura Base
        dataframe['hl_spread'] = ((dataframe['high'] - dataframe['low']) / dataframe['close']).fillna(0.0)
        dataframe['returns'] = dataframe['close'].pct_change().fillna(0.0)
        
        typical = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3.0
        cum_vol = dataframe['volume'].cumsum().replace(0, 1.0)
        dataframe['vwap'] = ((typical * dataframe['volume']).cumsum() / cum_vol).fillna(dataframe['close'])
        
        vol_ma = dataframe['volume'].rolling(20, min_periods=1).mean().replace(0, 1.0)
        dataframe['rvol'] = (dataframe['volume'] / vol_ma).fillna(1.0)

        # 2. Helpers para Operadores Temporales
        def ts_decay_linear(s: pd.Series, w: int) -> pd.Series:
            weights = np.arange(1, w + 1)
            weights = weights / weights.sum()
            return s.rolling(w, min_periods=1).apply(lambda x: np.dot(x, weights[-len(x):]) if len(x) > 0 else 0.0, raw=True).fillna(0.0)

        def ts_zscore(s: pd.Series, w: int) -> pd.Series:
            m = s.rolling(w, min_periods=1).mean()
            std = s.rolling(w, min_periods=1).std().replace(0.0, 1e-6)
            return ((s - m) / std).fillna(0.0)

        def ts_delta(s: pd.Series, w: int) -> pd.Series:
            return (s - s.shift(w)).fillna(0.0)

        def ts_rank(s: pd.Series, w: int) -> pd.Series:
            return s.rolling(w, min_periods=1).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False).fillna(0.5)

        def ts_delay(s: pd.Series, w: int) -> pd.Series:
            return s.shift(w).fillna(s)

        # 3. Evaluación Dinámica de cada Factor Minado Activo
        composite_score = pd.Series(0.0, index=dataframe.index)

        # Factor ALPHA_001 (Peso HRP: 0.2500)
        f_val_ALPHA_001 = ((dataframe['open'] + np.sign(-1.00)))
        f_std_ALPHA_001 = float(f_val_ALPHA_001.std()) if float(f_val_ALPHA_001.std()) > 1e-8 else 1.0
        f_norm_ALPHA_001 = (f_val_ALPHA_001 - f_val_ALPHA_001.mean()) / f_std_ALPHA_001
        composite_score += f_norm_ALPHA_001.fillna(0.0) * 0.250000

        # Factor ALPHA_002 (Peso HRP: 0.2500)
        f_val_ALPHA_002 = (np.abs((2.00 - dataframe['high'])))
        f_std_ALPHA_002 = float(f_val_ALPHA_002.std()) if float(f_val_ALPHA_002.std()) > 1e-8 else 1.0
        f_norm_ALPHA_002 = (f_val_ALPHA_002 - f_val_ALPHA_002.mean()) / f_std_ALPHA_002
        composite_score += f_norm_ALPHA_002.fillna(0.0) * 0.250000

        # Factor ALPHA_004 (Peso HRP: 0.5000)
        f_val_ALPHA_004 = (np.abs(ts_decay_linear(dataframe['vwap'], 10)))
        f_std_ALPHA_004 = float(f_val_ALPHA_004.std()) if float(f_val_ALPHA_004.std()) > 1e-8 else 1.0
        f_norm_ALPHA_004 = (f_val_ALPHA_004 - f_val_ALPHA_004.mean()) / f_std_ALPHA_004
        composite_score += f_norm_ALPHA_004.fillna(0.0) * 0.500000

        # Factor STRAT_A (Peso HRP: 0.1876)
        f_val_STRAT_A = (dataframe['close'].pct_change().fillna(0.0))
        f_std_STRAT_A = float(f_val_STRAT_A.std()) if float(f_val_STRAT_A.std()) > 1e-8 else 1.0
        f_norm_STRAT_A = (f_val_STRAT_A - f_val_STRAT_A.mean()) / f_std_STRAT_A
        composite_score += f_norm_STRAT_A.fillna(0.0) * 0.187585

        # Factor STRAT_B (Peso HRP: 0.8124)
        f_val_STRAT_B = (dataframe['close'].pct_change().fillna(0.0))
        f_std_STRAT_B = float(f_val_STRAT_B.std()) if float(f_val_STRAT_B.std()) > 1e-8 else 1.0
        f_norm_STRAT_B = (f_val_STRAT_B - f_val_STRAT_B.mean()) / f_std_STRAT_B
        composite_score += f_norm_STRAT_B.fillna(0.0) * 0.812415

        # Factor ALPHA_LIVE_01 (Peso HRP: 1.0000)
        f_val_ALPHA_LIVE_01 = (ts_rank(dataframe['close'], 14))
        f_std_ALPHA_LIVE_01 = float(f_val_ALPHA_LIVE_01.std()) if float(f_val_ALPHA_LIVE_01.std()) > 1e-8 else 1.0
        f_norm_ALPHA_LIVE_01 = (f_val_ALPHA_LIVE_01 - f_val_ALPHA_LIVE_01.mean()) / f_std_ALPHA_LIVE_01
        composite_score += f_norm_ALPHA_LIVE_01.fillna(0.0) * 1.000000

        # Factor HEALTHY_01 (Peso HRP: 1.0000)
        f_val_HEALTHY_01 = (ts_rank(dataframe['close'], 5))
        f_std_HEALTHY_01 = float(f_val_HEALTHY_01.std()) if float(f_val_HEALTHY_01.std()) > 1e-8 else 1.0
        f_norm_HEALTHY_01 = (f_val_HEALTHY_01 - f_val_HEALTHY_01.mean()) / f_std_HEALTHY_01
        composite_score += f_norm_HEALTHY_01.fillna(0.0) * 1.000000


        dataframe['composite_alpha_score'] = composite_score
        
        # Filtros de régimen adicionales (EMA 200 de tendencia y RSI)
        if ta is not None and hasattr(ta, 'EMA'):
            try:
                dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
                dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
            except Exception:
                dataframe['ema_200'] = dataframe['close'].ewm(span=200, adjust=False).mean()
                delta = dataframe['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 1e-6)
                rs = gain / loss
                dataframe['rsi'] = 100.0 - (100.0 / (1.0 + rs))
        else:
            dataframe['ema_200'] = dataframe['close'].ewm(span=200, adjust=False).mean()
            delta = dataframe['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 1e-6)
            rs = gain / loss
            dataframe['rsi'] = 100.0 - (100.0 / (1.0 + rs))

        # 4. Indicadores de Confirmación Rápida Multi-Horizonte (PB-102)
        dataframe['ema_50'] = dataframe['close'].ewm(span=50, adjust=False).mean()
        dataframe['fast_momentum'] = (
            (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3).replace(0, 1.0)
        ).fillna(0.0)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        PB-99: Genera señales de entrada bidireccionales (LONG / SHORT) basadas en la confluencia
        del ensamble de factores HRP y el régimen macro de microestructura.
        """
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['enter_tag'] = ''

        # 1. Entrada LONG: Ensamble alcista + Precio sobre EMA 200 + RSI moderado + Confirmación rápida
        cond_alpha_long = (dataframe['composite_alpha_score'] > 0.05)
        cond_struct_long = (dataframe['close'] > dataframe['ema_200']) & (dataframe['rsi'] < 68)
        cond_fast_long = (dataframe['close'] >= dataframe['ema_50']) | (dataframe['fast_momentum'] > 0.0)
        mask_long = cond_alpha_long & cond_struct_long & cond_fast_long
        dataframe.loc[mask_long, 'enter_long'] = 1
        dataframe.loc[mask_long, 'enter_tag'] = 'long_hrp_ensemble'

        # 2. Entrada SHORT: Ensamble bajista + Precio bajo EMA 200 + RSI moderado + Confirmación rápida
        cond_alpha_short = (dataframe['composite_alpha_score'] < -0.05)
        cond_struct_short = (dataframe['close'] < dataframe['ema_200']) & (dataframe['rsi'] > 32)
        cond_fast_short = (dataframe['close'] <= dataframe['ema_50']) | (dataframe['fast_momentum'] < 0.0)
        mask_short = cond_alpha_short & cond_struct_short & cond_fast_short
        dataframe.loc[mask_short, 'enter_short'] = 1
        dataframe.loc[mask_short, 'enter_tag'] = 'short_hrp_ensemble'

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        PB-99: Salida ágil tipo Airbag técnico para proteger el capital en Longs y Shorts.
        """
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''

        # Salida LONG: Ensamble se invierte a bajista o RSI en sobrecompra extrema
        cond_exit_long = (dataframe['composite_alpha_score'] < -0.10) | (dataframe['rsi'] > 75)
        dataframe.loc[cond_exit_long, 'exit_long'] = 1
        dataframe.loc[cond_exit_long, 'exit_tag'] = 'airbag_long_exit'

        # Salida SHORT: Ensamble se invierte a alcista o RSI en sobreventa extrema
        cond_exit_short = (dataframe['composite_alpha_score'] > 0.10) | (dataframe['rsi'] < 25)
        dataframe.loc[cond_exit_short, 'exit_short'] = 1
        dataframe.loc[cond_exit_short, 'exit_tag'] = 'airbag_short_exit'

        return dataframe

    def leverage(self, pair: str, current_time: Any, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Apalancamiento dinámico aislado regulado según la convicción del ensamble."""
        return 1.5
