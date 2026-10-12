"""
Módulo de Generación de Barras de Información (Information-Driven Bars).
Implementación basada en 'Advances in Financial Machine Learning' (Marcos López de Prado).

Provee generadores para:
1. Volume Bars: Muestreo cada V contratos negociados.
2. Dollar / Notional Bars: Muestreo cada $M notional negociado en futuros.
3. Tick Imbalance Bars (TIB): Muestreo dinámico basado en desbalances acumulados de compradores vs vendedores.
"""

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Tuple, Dict, Any, Callable, Union
import numpy as np
import pandas as pd


@dataclass
class BarStats:
    """Métricas estadísticas comparativas entre barras de tiempo y de información."""
    sample_size: int
    mean_return: float
    std_return: float
    skewness: float
    kurtosis: float
    jarque_bera_stat: float
    jarque_bera_pvalue: float


@dataclass
class AccumulatorState:
    """Estado acumulado en memoria de una Dollar Bar en formación (Sprint 2: US-2.3)."""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    cum_notional: float = 0.0
    vwap_num: float = 0.0
    start_time: Any = None
    end_time: Any = None
    ticks_count: int = 0
    is_active: bool = False

    def reset(self):
        self.open = 0.0
        self.high = 0.0
        self.low = 0.0
        self.close = 0.0
        self.volume = 0.0
        self.cum_notional = 0.0
        self.vwap_num = 0.0
        self.start_time = None
        self.end_time = None
        self.ticks_count = 0
        self.is_active = False


class StreamingDollarBarAggregator:
    """
    Agregador incremental O(1) de Dollar Bars para entornos de streaming de alta frecuencia (Sprint 2: US-2.3).
    Mantiene el estado continuo sin reprocesar el histórico y emite barras única y exclusivamente
    cuando cum_notional >= threshold.
    """

    def __init__(
        self,
        default_threshold: float = 1_000_000.0,
        symbol_thresholds: Optional[Dict[str, float]] = None
    ):
        self.default_threshold = float(default_threshold)
        self.symbol_thresholds: Dict[str, float] = symbol_thresholds or {}
        self._states: Dict[str, AccumulatorState] = {}

    def get_threshold(self, symbol: str) -> float:
        """Obtiene el umbral notional vigente para un símbolo."""
        return self.symbol_thresholds.get(symbol, self.default_threshold)

    def set_threshold(self, symbol: str, threshold: float) -> None:
        """Establece o calibra el umbral para un símbolo específico."""
        self.symbol_thresholds[symbol] = float(threshold)

    def get_state(self, symbol: str) -> AccumulatorState:
        """Obtiene o inicializa el estado acumulador para un símbolo."""
        if symbol not in self._states:
            self._states[symbol] = AccumulatorState()
        return self._states[symbol]

    def add_tick(
        self,
        symbol: str,
        price: float,
        volume: float,
        timestamp: Any = None
    ) -> Optional[Dict[str, Any]]:
        """
        Incorpora un trade individual en complejidad O(1).
        Si cum_notional alcanza o supera el umbral, cierra y retorna la barra.
        En caso contrario, retorna None.
        """
        price = float(price)
        volume = float(volume)
        if price <= 0.0 or volume <= 0.0:
            return None

        state = self.get_state(symbol)
        trade_notional = price * volume

        if not state.is_active:
            state.open = price
            state.high = price
            state.low = price
            state.close = price
            state.volume = volume
            state.cum_notional = trade_notional
            state.vwap_num = price * volume
            state.start_time = timestamp
            state.end_time = timestamp
            state.ticks_count = 1
            state.is_active = True
        else:
            if price > state.high:
                state.high = price
            if price < state.low:
                state.low = price
            state.close = price
            state.volume += volume
            state.cum_notional += trade_notional
            state.vwap_num += (price * volume)
            state.end_time = timestamp
            state.ticks_count += 1

        thresh = self.get_threshold(symbol)
        if state.cum_notional >= thresh:
            vwap = state.vwap_num / state.volume if state.volume > 0.0 else state.close
            closed_bar = {
                'timestamp': state.end_time or timestamp,
                'open': state.open,
                'high': state.high,
                'low': state.low,
                'close': state.close,
                'volume': state.volume,
                'notional': state.cum_notional,
                'vwap': vwap,
                'duration_ticks': state.ticks_count
            }
            state.reset()
            return closed_bar

        return None

    def add_candle_1m(
        self,
        symbol: str,
        candle: Union[Dict[str, Any], pd.Series]
    ) -> List[Dict[str, Any]]:
        """
        Incorpora una vela de 1 minuto en streaming O(1).
        Puede emitir 0, 1 o múltiples Dollar Bars si el volumen de la vela supera múltiplos del umbral.
        """
        open_p = float(candle.get('open', 0.0))
        high_p = float(candle.get('high', 0.0))
        low_p = float(candle.get('low', 0.0))
        close_p = float(candle.get('close', 0.0))
        vol = float(candle.get('volume', 0.0))
        ts = candle.get('timestamp', candle.get('date', None))

        if vol <= 0.0 or close_p <= 0.0:
            return []

        typical_p = (high_p + low_p + close_p) / 3.0
        candle_notional = float(candle.get('notional', vol * typical_p))

        state = self.get_state(symbol)
        thresh = self.get_threshold(symbol)

        if not state.is_active:
            state.open = open_p
            state.high = high_p
            state.low = low_p
            state.close = close_p
            state.volume = vol
            state.cum_notional = candle_notional
            state.vwap_num = typical_p * vol
            state.start_time = ts
            state.end_time = ts
            state.ticks_count = 1
            state.is_active = True
        else:
            if high_p > state.high:
                state.high = high_p
            if low_p < state.low:
                state.low = low_p
            state.close = close_p
            state.volume += vol
            state.cum_notional += candle_notional
            state.vwap_num += (typical_p * vol)
            state.end_time = ts
            state.ticks_count += 1

        closed_bars = []
        if state.cum_notional >= thresh:
            vwap = state.vwap_num / state.volume if state.volume > 0.0 else state.close
            closed_bar = {
                'timestamp': state.end_time or ts,
                'open': state.open,
                'high': state.high,
                'low': state.low,
                'close': state.close,
                'volume': state.volume,
                'notional': state.cum_notional,
                'vwap': vwap,
                'duration_ticks': state.ticks_count
            }
            closed_bars.append(closed_bar)
            state.reset()

        return closed_bars

    def get_in_progress_bar(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retorna una instantánea de la barra actualmente en acumulación sin cerrarla."""
        state = self.get_state(symbol)
        if not state.is_active:
            return None
        vwap = state.vwap_num / state.volume if state.volume > 0.0 else state.close
        thresh = max(self.get_threshold(symbol), 1.0)
        return {
            'timestamp': state.end_time,
            'open': state.open,
            'high': state.high,
            'low': state.low,
            'close': state.close,
            'volume': state.volume,
            'notional': state.cum_notional,
            'cum_notional': state.cum_notional,
            'vwap': vwap,
            'duration_ticks': state.ticks_count,
            'progress_pct': min(1.0, state.cum_notional / thresh)
        }


class InformationBarsGenerator:
    """
    Generador industrial de barras de información a partir de velas de alta frecuencia (1m)
    o secuencias de ticks (trades).
    """

    def __init__(
        self,
        notional_threshold: float = 1_000_000.0,
        volume_threshold: float = 100_000.0,
        symbol_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        :param notional_threshold: Umbral estándar en dólares/USDT para cerrar una Dollar Bar.
        :param volume_threshold: Umbral en tokens/contratos para cerrar una Volume Bar.
        :param symbol_thresholds: Diccionario opcional de umbrales específicos por símbolo.
        """
        self.notional_threshold = float(notional_threshold)
        self.volume_threshold = float(volume_threshold)
        self.symbol_thresholds: Dict[str, float] = symbol_thresholds or {}

    def get_threshold_for_symbol(self, symbol: str) -> float:
        """Retorna el umbral asignado a un símbolo o el umbral global por defecto."""
        return self.symbol_thresholds.get(symbol, self.notional_threshold)

    def set_threshold_for_symbol(self, symbol: str, threshold: float) -> None:
        """Asigna un umbral notional específico a un símbolo."""
        self.symbol_thresholds[symbol] = float(threshold)

    def calibrate_threshold_from_history(
        self,
        df: pd.DataFrame,
        target_bars_per_day: float = 50.0,
        min_threshold: float = 10_000.0,
        max_threshold: float = 50_000_000.0
    ) -> float:
        """
        Calibra dinámicamente el umbral notional a partir de una serie histórica (Sprint 2: US-2.2).
        Calcula el volumen en dólares promedio diario (ADV) y deriva el umbral para obtener
        aproximadamente 'target_bars_per_day' barras diarias.
        """
        if df.empty:
            return self.notional_threshold

        typical = (df['high'] + df['low'] + df['close']) / 3.0
        notional_series = df['notional'] if 'notional' in df.columns else (df['volume'] * typical)
        total_notional = float(notional_series.sum())

        days = 1.0
        ts_col = 'date' if 'date' in df.columns else ('timestamp' if 'timestamp' in df.columns else None)
        if ts_col is not None:
            try:
                times = pd.to_datetime(df[ts_col])
                delta_days = (times.max() - times.min()).total_seconds() / 86400.0
                if delta_days > 0.05:
                    days = delta_days
            except Exception:
                days = max(1.0, len(df) / 1440.0)
        else:
            days = max(1.0, len(df) / 1440.0)

        daily_adv = total_notional / max(days, 0.05)
        calibrated = daily_adv / max(float(target_bars_per_day), 1.0)
        clamped = float(np.clip(calibrated, min_threshold, max_threshold))
        return clamped

    def update_symbol_threshold_rolling(
        self,
        symbol: str,
        new_threshold: float,
        smoothing_alpha: float = 0.2
    ) -> float:
        """
        Actualiza el umbral rodante de un símbolo con filtro exponencial (EMA).
        Evita discontinuidades bruscas en el muestreo de barras.
        """
        current = self.get_threshold_for_symbol(symbol)
        smoothed = (1.0 - smoothing_alpha) * current + smoothing_alpha * float(new_threshold)
        self.symbol_thresholds[symbol] = float(smoothed)
        return smoothed

    @staticmethod
    def _compute_tick_rule(prices: np.ndarray) -> np.ndarray:
        """
        Aplica la regla de tick de Lee & Ready para clasificar si un trade fue iniciado
        por el comprador (b_t = +1) o por el vendedor (b_t = -1).
        """
        n = len(prices)
        if n == 0:
            return np.array([])
        
        diff = np.diff(prices, prepend=prices[0])
        b = np.zeros(n)
        last_b = 1.0  # Default comprador si no hay cambio inicial
        
        for i in range(n):
            if diff[i] > 0:
                b[i] = 1.0
                last_b = 1.0
            elif diff[i] < 0:
                b[i] = -1.0
                last_b = -1.0
            else:
                b[i] = last_b
        return b

    def generate_dollar_bars(
        self,
        df: pd.DataFrame,
        threshold: Optional[float] = None,
        in_streaming: bool = False
    ) -> pd.DataFrame:
        """
        Genera Dollar Bars (barras muestreadas por valor notional acumulado).
        df debe contener columnas: ['date' o 'timestamp', 'open', 'high', 'low', 'close', 'volume'].
        Si no existe columna 'notional', se aproxima con volume * vwap o volume * close.
        :param in_streaming: Si es True, no añade la barra residual parcial al final.
        """
        thresh = threshold or self.notional_threshold
        if df.empty:
            return pd.DataFrame()

        df_sorted = df.copy()
        if 'date' in df_sorted.columns:
            df_sorted['timestamp'] = pd.to_datetime(df_sorted['date'])
        elif 'timestamp' in df_sorted.columns:
            df_sorted['timestamp'] = pd.to_datetime(df_sorted['timestamp'])
        else:
            df_sorted['timestamp'] = pd.RangeIndex(len(df_sorted))

        # Aproximar precio típico para el cálculo notional
        typical_price = (df_sorted['high'] + df_sorted['low'] + df_sorted['close']) / 3.0
        if 'notional' in df_sorted.columns:
            notionals = df_sorted['notional'].to_numpy(dtype=float)
        else:
            notionals = (df_sorted['volume'] * typical_price).to_numpy(dtype=float)

        dates = df_sorted['timestamp'].to_numpy()
        opens = df_sorted['open'].to_numpy(dtype=float)
        highs = df_sorted['high'].to_numpy(dtype=float)
        lows = df_sorted['low'].to_numpy(dtype=float)
        closes = df_sorted['close'].to_numpy(dtype=float)
        volumes = df_sorted['volume'].to_numpy(dtype=float)

        bars = []
        cum_notional = 0.0
        cum_vol = 0.0
        bar_open = opens[0]
        bar_high = highs[0]
        bar_low = lows[0]
        bar_date = dates[0]

        n = len(df_sorted)
        for i in range(n):
            curr_notional = notionals[i]
            curr_vol = volumes[i]
            
            if cum_notional == 0.0:
                bar_open = opens[i]
                bar_high = highs[i]
                bar_low = lows[i]
                bar_date = dates[i]
            else:
                if highs[i] > bar_high:
                    bar_high = highs[i]
                if lows[i] < bar_low:
                    bar_low = lows[i]

            cum_notional += curr_notional
            cum_vol += curr_vol

            if cum_notional >= thresh:
                bars.append({
                    'timestamp': dates[i],
                    'open': bar_open,
                    'high': bar_high,
                    'low': bar_low,
                    'close': closes[i],
                    'volume': cum_vol,
                    'notional': cum_notional,
                    'duration_ticks': i + 1
                })
                cum_notional = 0.0
                cum_vol = 0.0

        # Si quedaron datos remanentes significativos (> 50% del umbral), generar última barra solo en backtesting
        if not in_streaming and cum_notional >= (thresh * 0.5):
            bars.append({
                'timestamp': dates[-1],
                'open': bar_open,
                'high': bar_high,
                'low': bar_low,
                'close': closes[-1],
                'volume': cum_vol,
                'notional': cum_notional,
                'duration_ticks': n
            })

        out = pd.DataFrame(bars)
        if not out.empty:
            out['returns'] = out['close'].pct_change().fillna(0.0)
        return out

    def generate_volume_bars(self, df: pd.DataFrame, threshold: Optional[float] = None) -> pd.DataFrame:
        """
        Genera Volume Bars (barras cerradas cada V contratos negociados).
        """
        thresh = threshold or self.volume_threshold
        if df.empty:
            return pd.DataFrame()

        df_sorted = df.copy()
        dates = df_sorted['date'].to_numpy() if 'date' in df_sorted.columns else df_sorted.index.to_numpy()
        opens = df_sorted['open'].to_numpy(dtype=float)
        highs = df_sorted['high'].to_numpy(dtype=float)
        lows = df_sorted['low'].to_numpy(dtype=float)
        closes = df_sorted['close'].to_numpy(dtype=float)
        volumes = df_sorted['volume'].to_numpy(dtype=float)

        bars = []
        cum_vol = 0.0
        bar_open = opens[0]
        bar_high = highs[0]
        bar_low = lows[0]

        for i in range(len(df_sorted)):
            if cum_vol == 0.0:
                bar_open = opens[i]
                bar_high = highs[i]
                bar_low = lows[i]
            else:
                if highs[i] > bar_high:
                    bar_high = highs[i]
                if lows[i] < bar_low:
                    bar_low = lows[i]

            cum_vol += volumes[i]

            if cum_vol >= thresh:
                bars.append({
                    'timestamp': dates[i],
                    'open': bar_open,
                    'high': bar_high,
                    'low': bar_low,
                    'close': closes[i],
                    'volume': cum_vol
                })
                cum_vol = 0.0

        out = pd.DataFrame(bars)
        if not out.empty:
            out['returns'] = out['close'].pct_change().fillna(0.0)
        return out

    def generate_tick_imbalance_bars(
        self,
        df: pd.DataFrame,
        expected_imbalance_window: int = 50,
        warmup_ticks: int = 100
    ) -> pd.DataFrame:
        """
        Genera Tick Imbalance Bars (TIB).
        Las barras se cierran cuando el desbalance acumulado theta_t excede la expectativa de desbalance:
        |theta_t| >= E_T * |2*P[b=1] - 1|
        """
        if len(df) < warmup_ticks:
            return pd.DataFrame()

        prices = df['close'].to_numpy(dtype=float)
        volumes = df['volume'].to_numpy(dtype=float)
        dates = df['date'].to_numpy() if 'date' in df.columns else df.index.to_numpy()
        opens = df['open'].to_numpy(dtype=float)
        highs = df['high'].to_numpy(dtype=float)
        lows = df['low'].to_numpy(dtype=float)

        b = self._compute_tick_rule(prices)
        n = len(df)

        bars = []
        theta_t = 0.0
        cum_vol = 0.0
        bar_open = opens[0]
        bar_high = highs[0]
        bar_low = lows[0]
        t_count = 0

        # Calibración inicial de la probabilidad de tick alcista
        prob_buy = np.mean(b[:warmup_ticks] == 1.0)
        prob_buy = np.clip(prob_buy, 0.1, 0.9)
        expected_imbalance = expected_imbalance_window * abs(2.0 * prob_buy - 1.0)
        if expected_imbalance < 2.0:
            expected_imbalance = 5.0  # Límite inferior preventivo

        for i in range(n):
            if t_count == 0:
                bar_open = opens[i]
                bar_high = highs[i]
                bar_low = lows[i]
            else:
                if highs[i] > bar_high:
                    bar_high = highs[i]
                if lows[i] < bar_low:
                    bar_low = lows[i]

            theta_t += b[i]
            cum_vol += volumes[i]
            t_count += 1

            if abs(theta_t) >= expected_imbalance:
                bars.append({
                    'timestamp': dates[i],
                    'open': bar_open,
                    'high': bar_high,
                    'low': bar_low,
                    'close': prices[i],
                    'volume': cum_vol,
                    'imbalance': theta_t,
                    'ticks_count': t_count
                })
                # Reset
                theta_t = 0.0
                cum_vol = 0.0
                t_count = 0

        out = pd.DataFrame(bars)
        if not out.empty:
            out['returns'] = out['close'].pct_change().fillna(0.0)
        return out

    @staticmethod
    def evaluate_normality_and_properties(returns: np.ndarray) -> BarStats:
        """
        Calcula asimetría, curtosis y test de Jarque-Bera de normalidad sobre los retornos.
        """
        clean = returns[np.isfinite(returns)]
        clean = clean[clean != 0.0]
        n = len(clean)
        if n < 8:
            return BarStats(n, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)

        mean_val = float(np.mean(clean))
        std_val = float(np.std(clean, ddof=1)) if n > 1 else 1.0
        if std_val == 0.0:
            std_val = 1e-9

        z = (clean - mean_val) / std_val
        skew = float(np.mean(z**3))
        kurt = float(np.mean(z**4))  # Curtosis total (Normal = 3)

        # Test Jarque-Bera: JB = (n/6) * (S^2 + ((K-3)^2)/4)
        jb_stat = (n / 6.0) * (skew**2 + ((kurt - 3.0)**2) / 4.0)
        # Aproximación p-value de chi-cuadrado con 2 grados de libertad
        jb_pvalue = float(np.exp(-0.5 * jb_stat))

        return BarStats(
            sample_size=n,
            mean_return=mean_val,
            std_return=std_val,
            skewness=skew,
            kurtosis=kurt,
            jarque_bera_stat=jb_stat,
            jarque_bera_pvalue=jb_pvalue
        )
