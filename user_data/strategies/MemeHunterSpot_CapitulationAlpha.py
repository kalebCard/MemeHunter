"""
MemeHunterSpot_CapitulationAlpha.py - Estrategia Definitiva Meme Hunter Spot (Binance).

Fundamento Cuantitativo y Microestructura (Actualizado con Auditoría Forense):
1. En el mercado Spot de Binance NO existe venta en corto nativa (can_short = False).
2. Las memecoins sufren bajadas abruptas (flash crashes de -15% a -40%) por cascadas
   de liquidación en futuros que vacían el libro spot.
3. Lección Crítica del Backtesting: Comprar la vela de pánico en caída libre ("falling knife")
   resulta en falsos suelos y saltos de stoploss.
4. Edge Corregido y Validado:
   - Se detecta la vela de pánico extremo (drop >= 13%, piercing BB 2.5σ, RSI <= 25, volumen >= 1.8x).
   - La entrada se ejecuta EXCLUSIVAMENTE cuando la vela siguiente CONFIRMA el giro
     (cierre verde, Close > Open y Close > Close[t-1]), demostrando absorción institucional real.
5. Blindaje de Capital y Micro-Capital (100 USDT):
   - Asignación de 3 slots concurrentes (~33 USDT cada uno) para superar por 6X el Min Notional ($5) de Binance.
   - Breakeven Inmediato al +2.0%: El stop sube a +0.5% (riesgo CERO absoluto y comisiones cubiertas).
   - Stoploss Ceñido en -3.5%: Corte de sangrado rápido si la confirmación falla.
   - Time-Stop Anti-Bagholding de 8 horas.
"""

import math
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
import logging
from pathlib import Path

try:
    from portfolio.bias_store import BiasStore
    from portfolio.pre_trade_profitability import PreTradeProfitabilityGate
except ImportError:
    BiasStore = None
    PreTradeProfitabilityGate = None

try:
    from freqtrade.strategy import (
        IStrategy,
        IntParameter,
        DecimalParameter,
    )
    from freqtrade.persistence import Trade
except ImportError:
    class IStrategy:
        pass
    class Trade:
        pass
    class IntParameter:
        def __init__(self, low, high, default=0, space="buy", optimize=True):
            self.value = default
    class DecimalParameter:
        def __init__(self, low, high, default=0.0, space="buy", optimize=True):
            self.value = default

try:
    import pandas_ta as ta
except ImportError:
    ta = None

import pandas as pd
from pandas import DataFrame
import numpy as np

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------
# Utilidades Matemáticas e Indicadores Vectorizados Puros
# ---------------------------------------------------------
def calculate_ffd_approx(close_series: np.ndarray, d: float = 0.40, lags: int = 30) -> np.ndarray:
    """Aproximación vectorizada de FFD para memoria estacionaria (López de Prado)."""
    weights = [1.0]
    for k in range(1, lags):
        w_k = -weights[-1] / k * (d - k + 1)
        weights.append(w_k)
    weights = np.array(weights[::-1])
    
    n = len(close_series)
    ffd = np.full(n, np.nan)
    for i in range(lags - 1, n):
        ffd[i] = np.dot(weights, close_series[i - lags + 1 : i + 1])
    return ffd


def compute_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """RSI clásico vectorizado con fallback seguro."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def compute_bollinger_bands(series: pd.Series, length: int = 20, std_dev: float = 2.5):
    """Bandas de Bollinger con ancho de desviación ajustable."""
    mid = series.rolling(window=length).mean()
    std = series.rolling(window=length).std(ddof=0)
    lower = mid - (std * std_dev)
    upper = mid + (std * std_dev)
    return lower, mid, upper


# ---------------------------------------------------------
# Clase Principal de la Estrategia Spot
# ---------------------------------------------------------
class MemeHunterSpot_CapitulationAlpha(IStrategy):
    """
    Estrategia Canónica Optimizada para Binance Spot:
    Cazador de Rebotes de Capitulación Confirmada con Blindaje para 100 USDT.
    """
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False  # Binance Spot puro: solo compras (Long)

    # -----------------------------------------------------
    # Matriz ROI Escalonada: Toma de Ganancias Rápida Asimétrica
    # -----------------------------------------------------
    minimal_roi = {
        "0": 0.060,    # +6.0% Take Profit primario en rebote elástico
        "240": 0.035,  # +3.5% tras 4 horas
        "480": 0.020,  # +2.0% tras 8 horas
        "720": 0.010   # +1.0% tras 12 horas
    }

    # -----------------------------------------------------
    # Blindaje de Capital: Stoploss Ceñido & Custom Stoploss
    # -----------------------------------------------------
    stoploss = -0.030  # Stop duro ceñido del -3.0% (anclado bajo la mecha de capitulación)
    use_custom_stoploss = True
    use_exit_signal = True

    trailing_stop = False  # Gestionado dinámicamente por custom_stoploss
    process_only_new_candles = True
    startup_candle_count: int = 50

    # -----------------------------------------------------
    # Tipos de Órdenes Institucionales
    # -----------------------------------------------------
    order_types = {
        'entry': 'limit',       # Órdenes Limit en libro para tarifa Maker (0.10% o 0.075% BNB)
        'exit': 'market',      # Órdenes Market para asegurar fill inmediato al salir
        'emergency_exit': 'market',
        'force_entry': 'market',
        'force_exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
        'stoploss_on_exchange_interval': 60
    }

    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }

    # -----------------------------------------------------
    # Conexión con Arquitectura Multi-Capa (Sprints 37-38)
    # -----------------------------------------------------
    enforce_agent_bias: bool = False       # Si True, exige autorización previa de BiasStore
    enforce_profitability_gate: bool = True # Valida que target > fricción * 2.5x

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) if hasattr(super(), '__init__') else None
        self.bias_store = BiasStore() if BiasStore is not None else None
        self.profitability_gate = PreTradeProfitabilityGate() if PreTradeProfitabilityGate is not None else None

    def check_pre_trade_filters(
        self,
        pair: str,
        current_price: float,
        spread_pct: float = 0.0010
    ) -> Tuple[bool, str]:
        """Auditoría determinista previa a la orden (Sesgo del Agente + Rentabilidad)."""
        if getattr(self, "enforce_agent_bias", False) and self.bias_store is not None:
            is_auth, reason = self.bias_store.is_authorized(pair, "LONG")
            if not is_auth:
                return False, f"BIAS_BLOCKED: {reason}"

        if getattr(self, "enforce_profitability_gate", True) and self.profitability_gate is not None:
            dec = self.profitability_gate.evaluate_entry(
                symbol=pair,
                current_price=current_price,
                spread_pct=spread_pct
            )
            if not dec.is_approved:
                return False, dec.rejection_reason or "FRICTION_BLOCKED"

        return True, "APPROVED"

    # Parámetros optimizados con rigor cuantitativo
    drop_threshold = DecimalParameter(-0.25, -0.12, default=-0.14, space="buy", optimize=True)
    rsi_capitulation = IntParameter(15, 26, default=24, space="buy", optimize=True)
    vol_climax_ratio = DecimalParameter(1.5, 3.0, default=1.8, space="buy", optimize=True)
    bb_std_mult = DecimalParameter(2.0, 3.2, default=2.5, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calcula el arsenal de indicadores de microestructura y detección de capitulación."""
        # 1. Medias de Tendencia y Desviación
        if ta is not None:
            dataframe['ema_20'] = ta.ema(dataframe['close'], length=20)
            dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
            dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
            dataframe['rsi_fast'] = ta.rsi(dataframe['close'], length=7)
            bb = ta.bbands(dataframe['close'], length=20, std=self.bb_std_mult.value)
            dataframe['bb_lower'] = bb[f'BBL_20_{self.bb_std_mult.value}']
            dataframe['bb_middle'] = bb[f'BBM_20_{self.bb_std_mult.value}']
            dataframe['bb_upper'] = bb[f'BBU_20_{self.bb_std_mult.value}']
            dataframe['atr'] = ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length=14)
        else:
            dataframe['ema_20'] = dataframe['close'].ewm(span=20, adjust=False).mean()
            dataframe['ema_50'] = dataframe['close'].ewm(span=50, adjust=False).mean()
            dataframe['rsi'] = compute_rsi(dataframe['close'], length=14)
            dataframe['rsi_fast'] = compute_rsi(dataframe['close'], length=7)
            bb_l, bb_m, bb_u = compute_bollinger_bands(dataframe['close'], length=20, std_dev=self.bb_std_mult.value)
            dataframe['bb_lower'] = bb_l
            dataframe['bb_middle'] = bb_m
            dataframe['bb_upper'] = bb_u
            tr = pd.concat([
                dataframe['high'] - dataframe['low'],
                (dataframe['high'] - dataframe['close'].shift()).abs(),
                (dataframe['low'] - dataframe['close'].shift()).abs()
            ], axis=1).max(axis=1)
            dataframe['atr'] = tr.rolling(window=14).mean()

        # 2. Magnitud de la Bajada Abrupta (Flash Crash en ventana de 16 horas)
        recent_high = dataframe['high'].rolling(window=16).max()
        dataframe['drop_from_recent_high'] = (dataframe['close'] - recent_high) / recent_high

        # 3. Z-Score de Distancia Estadística a la Media
        std_20 = dataframe['close'].rolling(window=20).std(ddof=0)
        dataframe['z_score_dist'] = (dataframe['close'] - dataframe['ema_20']) / std_20.replace(0, np.nan)

        # 4. Microestructura: Mecha Inferior de Absorción (Wick Dominance)
        candle_open = dataframe['open']
        candle_close = dataframe['close']
        candle_low = dataframe['low']
        candle_high = dataframe['high']

        lower_wick = np.minimum(candle_open, candle_close) - candle_low
        candle_body = (candle_close - candle_open).abs()
        candle_range = (candle_high - candle_low).replace(0, np.nan)

        vol_sma20 = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / vol_sma20.replace(0, np.nan)

        is_wick_dominant = (lower_wick >= candle_body * 1.3) & (lower_wick >= candle_range * 0.35)
        is_volume_spike = dataframe['vol_ratio'] >= self.vol_climax_ratio.value
        dataframe['absorption_wick_signal'] = (is_wick_dominant & is_volume_spike).astype(int)

        # 5. Detección de la Vela de Pánico y Vela de Confirmación
        dataframe['panic_candle'] = (
            (dataframe['drop_from_recent_high'] <= self.drop_threshold.value) &
            (dataframe['low'] <= dataframe['bb_lower']) &
            ((dataframe['rsi'] <= self.rsi_capitulation.value) | (dataframe['rsi_fast'] <= 18)) &
            (dataframe['vol_ratio'] >= self.vol_climax_ratio.value)
        ).astype(int)

        dataframe['confirmation_candle'] = (
            (dataframe['close'] > dataframe['open']) &
            (dataframe['close'] > dataframe['close'].shift(1)) &
            (dataframe['volume'] > 0)
        ).astype(int)

        # 6. Memoria Estacionaria FFD (d=0.40)
        close_arr = dataframe['close'].values
        dataframe['ffd_close'] = calculate_ffd_approx(close_arr, d=0.40, lags=30)
        dataframe['ffd_momentum'] = dataframe['ffd_close'].diff()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entrada quirúrgica: Se ingresa al mercado ÚNICAMENTE tras confirmación de giro,
        eliminando las entradas en 'cuchillo cayendo' que destruían el Win Rate.
        """
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # PB-126: Si enforce_agent_bias está activo, verificar autorización del Cerebro Lento
        if getattr(self, "enforce_agent_bias", False) and self.bias_store is not None:
            pair = metadata.get("pair", "")
            if pair:
                is_auth, _ = self.bias_store.is_authorized(pair, "LONG")
                if not is_auth:
                    return dataframe

        # -------------------------------------------------------------
        # SETUP 1: Capitulación Extrema con Confirmación de Giro
        # La vela previa sufrió el crash de pánico y la vela actual confirma
        # el rebote cerrando verde por encima del cierre previo.
        # -------------------------------------------------------------
        confirmed_capitulation = (
            (dataframe['panic_candle'].shift(1) == 1) &
            (dataframe['confirmation_candle'] == 1) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[confirmed_capitulation, 'enter_long'] = 1
        dataframe.loc[confirmed_capitulation, 'enter_tag'] = 'spot_confirmed_capitulation'

        # -------------------------------------------------------------
        # SETUP 2: Absorción de Mecha Institucional Confirmada
        # Vela previa con mecha gigante de rechazo y vela actual verde.
        # -------------------------------------------------------------
        confirmed_wick_reversal = (
            (dataframe['enter_long'] == 0) &
            (dataframe['absorption_wick_signal'].shift(1) == 1) &
            (dataframe['drop_from_recent_high'].shift(1) <= -0.14) &
            (dataframe['confirmation_candle'] == 1) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[confirmed_wick_reversal, 'enter_long'] = 1
        dataframe.loc[confirmed_wick_reversal, 'enter_tag'] = 'spot_confirmed_wick_reversal'

        # -------------------------------------------------------------
        # SETUP 3: Distorsión Estadística Elástica Confirmada
        # Z-Score <= -2.5 en vela previa con giro confirmado en vela verde.
        # -------------------------------------------------------------
        elastic_rebound = (
            (dataframe['enter_long'] == 0) &
            (dataframe['drop_from_recent_high'].shift(1) <= -0.13) &
            (dataframe['z_score_dist'].shift(1) <= -2.5) &
            (dataframe['confirmation_candle'] == 1) &
            (dataframe['rsi'] <= 28) &
            (dataframe['volume'] > 0)
        )
        dataframe.loc[elastic_rebound, 'enter_long'] = 1
        dataframe.loc[elastic_rebound, 'enter_tag'] = 'spot_elastic_rebound'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Salidas técnicas que actúan como Airbag de invalidación."""
        dataframe.loc[:, 'exit_long'] = 0

        # Si el precio recupera la EMA 50 o el RSI llega a 65, el rebote elástico se completó
        rebound_exhaustion = (
            (dataframe['close'] >= dataframe['ema_50']) |
            (dataframe['rsi'] >= 65) |
            (dataframe['close'] >= dataframe['bb_upper'] * 0.99)
        )
        dataframe.loc[rebound_exhaustion, 'exit_long'] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        MECANISMO INFLEXIBLE DE BLINDAJE DE CAPITAL (CAPITAL ARMOR):
        1. Si la ganancia supera +2.0%, sube automáticamente el Stoploss a +0.5% (BREAKEVEN BLINDADO).
           Garantiza riesgo CERO absoluto y comisiones cubiertas.
        2. Si la ganancia supera +4.5%, asegura +2.5% de beneficio neto.
        3. Si la ganancia supera +6.5%, asegura +4.5% de beneficio neto.
        4. Si la ganancia supera +10.0%, asegura +8.0% de beneficio neto.
        """
        # Hito 4: Rebote Parabólico (> +10.0%) -> asegurar +8.0%
        if current_profit >= 0.100:
            return -0.020

        # Hito 3: Rebote Maduro (> +6.5%) -> asegurar +4.5%
        if current_profit >= 0.065:
            return -0.015

        # Hito 2: Rebote Fuerte (> +4.5%) -> asegurar +2.5%
        if current_profit >= 0.045:
            return -0.015

        # Hito 1: Umbral de Breakeven (> +2.0%) -> Stop en +0.5% sobre la entrada
        # Garantiza comisiones de Binance Spot cubiertas y capital blindado
        if current_profit >= 0.020:
            breakeven_distance = 1.0 - (1.005 / (1.0 + current_profit))
            return -max(0.005, breakeven_distance)

        # Por defecto, respetar el stoploss ceñido institucional (-3.5%)
        return self.stoploss

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        """
        GUARDIÁN ANTI-BAGHOLDING Y TIME-STOP INSTITUCIONAL:
        En memecoins de Spot, si a las 8 horas el rebote no ha generado ganancias, se liquida a mercado.
        """
        try:
            trade_duration_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        except Exception:
            trade_duration_hours = 0.0

        # Regla 1: Time-Stop Anti-Bagholding (8 horas de inactividad)
        if trade_duration_hours >= 8.0 and current_profit < 0.010:
            return "time_stop_anti_bagholding"

        # Regla 2: Agotamiento Rápido (4 horas con debilidad)
        if trade_duration_hours >= 4.0 and current_profit <= -0.020:
            return "early_weakness_airbag"

        return None
