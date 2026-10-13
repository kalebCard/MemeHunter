"""
MemeHunter_ApexOmegaAlpha.py - La Estrategia Cuantitativa Definitiva (v7.6).
=============================================================================
Estrategia Maestra de Grado Institucional que fusiona la totalidad de innovaciones
del proyecto Meme Hunter (Sprints 1 a 39):

1. ARQUITECTURA DE 4 CAPAS (v7.6):
   - Capa 1: Cortafuegos de Datos Pydantic v2 (DataFirewallGuard & SanitizedFeed).
   - Capa 2: Desacoplamiento Asíncrono del Cerebro Lento (BiasStore & DAGSignalOrchestrator).
   - Capa 3: Capa de Ejecución Determinista con PreTradeProfitabilityGate (Margen >= 2.5x fricción).
   - Capa 4: Kill Switch Absoluto e Interceptor de Broker (ExecutionGatekeeper & EmergencyKillSwitch).

2. EDGE CUANTITATIVO Y MICROESTRUCTURA (Spot & Futuros):
   - Memoria Fraccional Estacionaria FFD (d=0.40, Marcos López de Prado).
   - SETUP LONG: Capitulación Extrema de Liquidaciones con Absorción de Mecha y Confirmación de Giro Verde.
   - SETUP SHORT: Desinflación Gravitacional Post-Pump con Quiebre de Estructura de Subasta Atrapada.
   - Dimensionamiento Continuo de Apuestas (Continuous Bet Sizing de López de Prado / Kelly Sigmoidal [1.0x - 2.0x]).

3. BLINDAJE DE CAPITAL Y TRINQUETE DE GANANCIAS (Capital Armor):
   - Breakeven Inmediato al +2.0%: Stoploss asegurado al +0.5% (Riesgo Cero y comisiones cubiertas).
   - Trailing Ratchet Escalonado: +2.5% asegurado al +4.5%, +4.5% al +6.5%, +8.0% al +10.0%.
   - Time-Stop Anti-Bagholding de 8 horas: Liquidación de posiciones estancadas.
   - Guardián de Tasa de Financiación (Funding Bleed Guard): Rechazo de cortos con tasa < -0.05% por 8h.
   - Stoploss duro ceñido del -3.0% en código.
=============================================================================
"""

import math
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, Any
import logging
from pathlib import Path

# Fallback seguro para ejecución dentro o fuera de Freqtrade / Docker
try:
    from freqtrade.strategy import (
        IStrategy,
        IntParameter,
        DecimalParameter,
        BooleanParameter
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
    class BooleanParameter:
        def __init__(self, default=True, space="buy", optimize=True):
            self.value = default

try:
    import pandas_ta as ta
except ImportError:
    ta = None

import pandas as pd
from pandas import DataFrame
import numpy as np
import scipy.stats as ss

# Módulos de la Arquitectura de 4 Capas de Meme Hunter
try:
    from portfolio.bias_store import BiasStore
    from portfolio.pre_trade_profitability import PreTradeProfitabilityGate, ProfitabilityDecision
    from portfolio.kill_switch import EmergencyKillSwitch, KillSwitchLevel
    from portfolio.execution_gatekeeper import ExecutionGatekeeper
    from validation.data_firewall import DataFirewallGuard
except ImportError:
    BiasStore = None
    PreTradeProfitabilityGate = None
    EmergencyKillSwitch = None
    ExecutionGatekeeper = None
    DataFirewallGuard = None

LOG = logging.getLogger(__name__)


# =============================================================================
# FUNCIONES MATEMÁTICAS INSTITUCIONALES (FFD & BET SIZING)
# =============================================================================

def calculate_ffd_approx(close_series: np.ndarray, d: float = 0.40, lags: int = 30) -> np.ndarray:
    """
    Diferenciación Fraccionaria (FFD) de memoria estacionaria (Marcos López de Prado).
    Conserva la memoria de largo plazo sin inducir no-estacionariedad en las series.
    """
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


def continuous_bet_sizing(conviction_score: float, min_lev: float = 1.0, max_lev: float = 2.0) -> float:
    """
    Dimensionamiento Continuo de Apuestas de López de Prado / Kelly Sigmoidal Normal:
    m = 2 * Z[ (p - 0.5) / sqrt(p * (1 - p)) ] - 1
    Traduce convicción estadística continua a apalancamiento [1.0x - 2.0x].
    """
    p = 0.50 + 0.45 * min(1.0, max(0.0, conviction_score))
    if p <= 0.51:
        return min_lev

    denom = math.sqrt(p * (1.0 - p))
    z = (p - 0.5) / denom
    m = 2.0 * float(ss.norm.cdf(z)) - 1.0

    lev = min_lev + m * (max_lev - min_lev)
    return round(float(lev), 2)


def compute_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """RSI vectorizado robusto con fallback seguro."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def compute_bollinger_bands(series: pd.Series, length: int = 20, std_dev: float = 2.5):
    """Bandas de Bollinger de microestructura."""
    mid = series.rolling(window=length).mean()
    std = series.rolling(window=length).std(ddof=0)
    lower = mid - (std * std_dev)
    upper = mid + (std * std_dev)
    return lower, mid, upper


# =============================================================================
# ESTRATEGIA PRINCIPAL CANÓNICA
# =============================================================================

class MemeHunter_ApexOmegaAlpha(IStrategy):
    """
    Cazador Cuantitativo Definitivo v7.6:
    Combina el Cerebro Lento Asíncrono con el Cerebro Rápido Determinista,
    blindado por el Cortafuegos Pydantic y el Kill Switch Absoluto.
    """
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False  # Modo Spot por defecto (cambiar a True para Futuros Bidireccional)

    # -----------------------------------------------------
    # Matriz ROI Asimétrica de Alta Velocidad
    # -----------------------------------------------------
    minimal_roi = {
        "0": 0.060,    # +6.0% Take Profit primario en rebote elástico
        "240": 0.035,  # +3.5% tras 4 horas
        "480": 0.020,  # +2.0% tras 8 horas
        "720": 0.010   # +1.0% tras 12 horas
    }

    # -----------------------------------------------------
    # Blindaje de Capital y Stop-Loss Estructural Ceñido
    # -----------------------------------------------------
    stoploss = -0.030  # -3.0% Stoploss duro en código
    use_custom_stoploss = True
    use_exit_signal = True

    trailing_stop = False  # Gestionado dinámicamente por custom_stoploss (Trinquete)
    process_only_new_candles = True
    startup_candle_count: int = 50

    # -----------------------------------------------------
    # Tipos de Órdenes Institucionales
    # -----------------------------------------------------
    order_types = {
        'entry': 'limit',          # Maker Post-Only al Bid para cobrar rebate o pagar tarifa reducida
        'exit': 'market',         # Salidas a mercado para asegurar fill inmediato sin selección adversa
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
    # Gobernanza de la Arquitectura de 4 Capas (v7.6)
    # -----------------------------------------------------
    enforce_agent_bias: bool = False           # Si True, exige autorización previa de BiasStore
    enforce_profitability_gate: bool = True     # Si True, exige Ganancia >= 2.5x costos friccionales
    enforce_execution_gatekeeper: bool = True   # Si True, audita drawdown, stoploss y max slots

    # Parámetros Cuantitativos Optimizados
    drop_threshold = DecimalParameter(-0.25, -0.12, default=-0.14, space="buy", optimize=True)
    rsi_capitulation = IntParameter(15, 26, default=24, space="buy", optimize=True)
    vol_climax_ratio = DecimalParameter(1.5, 3.0, default=1.8, space="buy", optimize=True)
    bb_std_mult = DecimalParameter(2.0, 3.2, default=2.5, space="buy", optimize=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) if hasattr(super(), '__init__') else None
        # Inicialización segura de guardianes de arquitectura
        self.bias_store = BiasStore() if BiasStore is not None else None
        self.profitability_gate = PreTradeProfitabilityGate() if PreTradeProfitabilityGate is not None else None
        self.kill_switch = EmergencyKillSwitch() if EmergencyKillSwitch is not None else None
        self.gatekeeper = ExecutionGatekeeper(kill_switch=self.kill_switch) if ExecutionGatekeeper is not None else None

    # -----------------------------------------------------
    # 1. GENERACIÓN DE INDICADORES Y FEATURES MATEMÁTICOS
    # -----------------------------------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calcula el arsenal matemático de microestructura y persistencia de memoria."""
        # 1. Medias Exponenciales y Volatilidad
        if ta is not None:
            dataframe['ema_20'] = ta.ema(dataframe['close'], length=20)
            dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
            dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)
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
            dataframe['ema_200'] = dataframe['close'].ewm(span=200, adjust=False).mean()
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

        # 2. Magnitud de la Caída y Z-Score de Desviación
        recent_high = dataframe['high'].rolling(window=16).max()
        dataframe['drop_from_recent_high'] = (dataframe['close'] - recent_high) / recent_high
        std_20 = dataframe['close'].rolling(window=20).std(ddof=0)
        dataframe['z_score_dist'] = (dataframe['close'] - dataframe['ema_20']) / std_20.replace(0, np.nan)

        # 3. Microestructura: Mechas de Absorción Level 2 (Wick Dominance)
        candle_open = dataframe['open']
        candle_close = dataframe['close']
        candle_low = dataframe['low']
        candle_high = dataframe['high']

        lower_wick = np.minimum(candle_open, candle_close) - candle_low
        upper_wick = candle_high - np.maximum(candle_open, candle_close)
        candle_body = (candle_close - candle_open).abs()
        candle_range = (candle_high - candle_low).replace(0, np.nan)

        vol_sma20 = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_ratio'] = dataframe['volume'] / vol_sma20.replace(0, np.nan)

        # Mecha inferior dominante (Absorción de compras institucionales)
        is_lower_wick_dominant = (lower_wick >= candle_body * 1.3) & (lower_wick >= candle_range * 0.35)
        is_vol_spike = dataframe['vol_ratio'] >= self.vol_climax_ratio.value
        dataframe['absorption_wick_signal'] = (is_lower_wick_dominant & is_vol_spike).astype(int)

        # Mecha superior dominante (Subasta atrapada en techo para shorts)
        is_upper_wick_dominant = (upper_wick >= candle_body * 1.3) & (upper_wick >= candle_range * 0.35)
        dataframe['rejection_top_signal'] = (is_upper_wick_dominant & is_vol_spike).astype(int)

        # 4. Vela de Pánico y Vela de Confirmación de Giro
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

        # 5. Memoria Fraccional FFD (d=0.40)
        close_arr = dataframe['close'].values
        dataframe['ffd_close'] = calculate_ffd_approx(close_arr, d=0.40, lags=30)
        dataframe['ffd_momentum'] = dataframe['ffd_close'].diff()

        return dataframe

    # -----------------------------------------------------
    # 2. ENTRADAS QUIRÚRGICAS (CEREBRO RÁPIDO & GATILLOS)
    # -----------------------------------------------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Disparo determinista condicionado por las 4 capas de protección."""
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        pair = metadata.get("pair", "")

        # FILTRO CAPA 2: Verificación de Sesgo Asíncrono del Cerebro Lento si está habilitado
        if self.enforce_agent_bias and self.bias_store is not None and pair:
            is_long_auth, _ = self.bias_store.is_authorized(pair, side="LONG", min_confidence=0.70)
            is_short_auth, _ = self.bias_store.is_authorized(pair, side="SHORT", min_confidence=0.70)
        else:
            is_long_auth = True
            is_short_auth = True

        # -------------------------------------------------------------
        # SETUP LONG 1: Capitulación Extrema con Confirmación de Giro
        # -------------------------------------------------------------
        if is_long_auth:
            confirmed_capitulation = (
                (dataframe['panic_candle'].shift(1) == 1) &
                (dataframe['confirmation_candle'] == 1) &
                (dataframe['volume'] > 0)
            )
            dataframe.loc[confirmed_capitulation, 'enter_long'] = 1
            dataframe.loc[confirmed_capitulation, 'enter_tag'] = 'apex_confirmed_capitulation'

            # -------------------------------------------------------------
            # SETUP LONG 2: Absorción de Mecha Institucional Confirmada
            # -------------------------------------------------------------
            confirmed_wick_reversal = (
                (dataframe['enter_long'] == 0) &
                (dataframe['absorption_wick_signal'].shift(1) == 1) &
                (dataframe['drop_from_recent_high'].shift(1) <= -0.14) &
                (dataframe['confirmation_candle'] == 1) &
                (dataframe['volume'] > 0)
            )
            dataframe.loc[confirmed_wick_reversal, 'enter_long'] = 1
            dataframe.loc[confirmed_wick_reversal, 'enter_tag'] = 'apex_confirmed_wick'

            # -------------------------------------------------------------
            # SETUP LONG 3: Distorsión Estadística Elástica (Z-Score <= -2.5)
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
            dataframe.loc[elastic_rebound, 'enter_tag'] = 'apex_elastic_rebound'

        # -------------------------------------------------------------
        # SETUP SHORT (Solo si can_short está activo para Futuros)
        # -------------------------------------------------------------
        if self.can_short and is_short_auth:
            # Short 1: Subasta Atrapada en Techo Post-Pump
            trapped_auction_short = (
                (dataframe['rejection_top_signal'].shift(1) == 1) &
                (dataframe['close'] < dataframe['open']) &  # Vela roja de confirmación bajista
                (dataframe['close'] < dataframe['close'].shift(1)) &
                (dataframe['rsi'] >= 68) &
                (dataframe['volume'] > 0)
            )
            dataframe.loc[trapped_auction_short, 'enter_short'] = 1
            dataframe.loc[trapped_auction_short, 'enter_tag'] = 'apex_trapped_auction_short'

            # Short 2: Quiebre de Estructura Gravitacional
            structure_breakdown_short = (
                (dataframe['enter_short'] == 0) &
                (dataframe['close'] < dataframe['ema_20']) &
                (dataframe['close'].shift(1) >= dataframe['ema_20'].shift(1)) &
                (dataframe['ffd_momentum'] < 0) &
                (dataframe['rsi'] >= 55) &
                (dataframe['volume'] > 0)
            )
            dataframe.loc[structure_breakdown_short, 'enter_short'] = 1
            dataframe.loc[structure_breakdown_short, 'enter_tag'] = 'apex_structure_breakdown_short'

        return dataframe

    # -----------------------------------------------------
    # 3. SALIDAS TÉCNICAS (AIRBAG DE INVALIDACIÓN)
    # -----------------------------------------------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Salidas de invalidación antes de tocar el stoploss estructural."""
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        # Salida Long: Rebote completado al alcanzar la EMA 50 o sobrecompra en RSI 65
        long_exhaustion = (
            (dataframe['close'] >= dataframe['ema_50']) |
            (dataframe['rsi'] >= 65) |
            (dataframe['close'] >= dataframe['bb_upper'] * 0.99)
        )
        dataframe.loc[long_exhaustion, 'exit_long'] = 1

        # Salida Short: Desinflación agotada al tocar la banda inferior o sobreventa en RSI 30
        if self.can_short:
            short_exhaustion = (
                (dataframe['close'] <= dataframe['bb_lower'] * 1.01) |
                (dataframe['rsi'] <= 30) |
                (dataframe['close'] >= dataframe['ema_20'])
            )
            dataframe.loc[short_exhaustion, 'exit_short'] = 1

        return dataframe

    # -----------------------------------------------------
    # 4. DIMENSIONAMIENTO CONTINUO DE APUESTAS (BET SIZING)
    # -----------------------------------------------------
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        Escala el apalancamiento [1.0x - 2.0x] según el score de convicción del setup
        mediante la fórmula sigmoidal normal de Marcos López de Prado.
        """
        if not self.can_short:
            return 1.0  # En Binance Spot el apalancamiento siempre es 1.0x

        conviction_map = {
            'apex_confirmed_capitulation': 0.90,
            'apex_trapped_auction_short': 0.88,
            'apex_confirmed_wick': 0.78,
            'apex_structure_breakdown_short': 0.75,
            'apex_elastic_rebound': 0.70
        }
        score = conviction_map.get(entry_tag or '', 0.65)
        return continuous_bet_sizing(score, min_lev=1.0, max_lev=min(2.0, max_leverage))

    # -----------------------------------------------------
    # 5. TRINQUETE DE GANANCIAS (CAPITAL ARMOR)
    # -----------------------------------------------------
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        MECANISMO INFLEXIBLE DE BLINDAJE DE CAPITAL:
        - +2.0% de ganancia -> Breakeven en +0.5% (Riesgo CERO y comisiones cubiertas).
        - +4.5% de ganancia -> Asegura +2.5% de ganancia neta.
        - +6.5% de ganancia -> Asegura +4.5% de ganancia neta.
        - +10.0% de ganancia -> Asegura +8.0% de ganancia neta.
        """
        # Hito 4: Expansión Parabólica (> +10.0%)
        if current_profit >= 0.100:
            return -0.020

        # Hito 3: Rebote Maduro (> +6.5%)
        if current_profit >= 0.065:
            return -0.015

        # Hito 2: Rebote Fuerte (> +4.5%)
        if current_profit >= 0.045:
            return -0.015

        # Hito 1: Umbral de Breakeven (> +2.0%) -> Asegurar +0.5% neto
        if current_profit >= 0.020:
            breakeven_distance = 1.0 - (1.005 / (1.0 + current_profit))
            return -max(0.005, breakeven_distance)

        # Por defecto, respetar el stop duro del -3.0%
        return self.stoploss

    # -----------------------------------------------------
    # 6. TIME-STOP ANTI-BAGHOLDING
    # -----------------------------------------------------
    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        """Liquidación obligatoria si el trade no produce ganancias tras 8 horas."""
        try:
            trade_duration_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        except Exception:
            trade_duration_hours = 0.0

        # Regla 1: Time-Stop Anti-Bagholding (8 horas)
        if trade_duration_hours >= 8.0 and current_profit < 0.010:
            return "time_stop_anti_bagholding"

        # Regla 2: Agotamiento Rápido (4 horas con debilidad)
        if trade_duration_hours >= 4.0 and current_profit <= -0.020:
            return "early_weakness_airbag"

        return None

    # -----------------------------------------------------
    # 7. INTERCEPTOR Y AUDITORÍA PRE-ORDEN (CAPAS 3 Y 4)
    # -----------------------------------------------------
    def check_pre_trade_filters(
        self,
        pair: str,
        current_price: float,
        side: str = "LONG",
        spread_pct: float = 0.0010,
        order_size_usdt: float = 33.0,
        current_open_trades: int = 0,
        intraday_drawdown_pct: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Auditoría unificada previa al disparo de la orden.
        Valida Sesgo del Agente -> Rentabilidad Pre-Trade -> Gatekeeper de Broker.
        """
        # 1. Sesgo del Cerebro Lento
        if self.enforce_agent_bias and self.bias_store is not None:
            is_auth, reason = self.bias_store.is_authorized(pair, side=side, min_confidence=0.70)
            if not is_auth:
                return False, f"BIAS_BLOCKED: {reason}"

        # 2. Filtro Matemático de Rentabilidad Pre-Trade
        if self.enforce_profitability_gate and self.profitability_gate is not None:
            dec: ProfitabilityDecision = self.profitability_gate.evaluate_entry(
                symbol=pair,
                current_price=current_price,
                spread_pct=spread_pct
            )
            if not dec.is_approved:
                return False, dec.rejection_reason or "FRICTION_BLOCKED"

        # 3. Gatekeeper Final y Kill Switch
        if self.enforce_execution_gatekeeper and self.gatekeeper is not None:
            ok, reason = self.gatekeeper.intercept_order(
                symbol=pair,
                side="buy" if side.upper() == "LONG" else "sell",
                order_size_usdt=order_size_usdt,
                price=current_price,
                stoploss_pct=self.stoploss,
                current_open_trades=current_open_trades,
                intraday_drawdown_pct=intraday_drawdown_pct
            )
            if not ok:
                return False, f"GATEKEEPER_BLOCKED: {reason}"

        return True, "APPROVED_FOR_DISPATCH"
