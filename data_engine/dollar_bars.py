"""
Módulo de Generación de Barras de Información (Information-Driven Bars).
Implementación basada en 'Advances in Financial Machine Learning' (Marcos López de Prado).

Provee generadores para:
1. Volume Bars: Muestreo cada V contratos negociados.
2. Dollar / Notional Bars: Muestreo cada $M notional negociado en futuros.
3. Tick Imbalance Bars (TIB): Muestreo dinámico basado en desbalances acumulados de compradores vs vendedores.
"""

from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, Dict, Any
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


class InformationBarsGenerator:
    """
    Generador industrial de barras de información a partir de velas de alta frecuencia (1m)
    o secuencias de ticks (trades).
    """

    def __init__(self, notional_threshold: float = 1_000_000.0, volume_threshold: float = 100_000.0):
        """
        :param notional_threshold: Umbral en dólares/USDT para cerrar una Dollar Bar.
        :param volume_threshold: Umbral en tokens/contratos para cerrar una Volume Bar.
        """
        self.notional_threshold = float(notional_threshold)
        self.volume_threshold = float(volume_threshold)

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

    def generate_dollar_bars(self, df: pd.DataFrame, threshold: Optional[float] = None) -> pd.DataFrame:
        """
        Genera Dollar Bars (barras muestreadas por valor notional acumulado).
        df debe contener columnas: ['date' o 'timestamp', 'open', 'high', 'low', 'close', 'volume'].
        Si no existe columna 'notional', se aproxima con volume * vwap o volume * close.
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

        # Si quedaron datos remanentes significativos (> 50% del umbral), generar última barra
        if cum_notional >= (thresh * 0.5):
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
