"""
meme_hunter.core.types - Enums Canónicos y DTOs Tipados del Dominio (Pydantic v2).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class MarketRegime(str, Enum):
    """Regímenes de mercado detectados por el modelo HMM y reglas heurísticas."""
    BULL_MOMENTUM = "BULL_MOMENTUM"
    BEAR_BLEED = "BEAR_BLEED"
    CHOPPY_RANGE = "CHOPPY_RANGE"
    CRITICAL_BREAK = "CRITICAL_BREAK"


class StrategyStatus(str, Enum):
    """Ciclo de vida institucional de estrategias en la incubadora de alfas."""
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"
    ALPHA_DECAY = "ALPHA_DECAY"
    RETIRED = "RETIRED"


class HealthStatus(str, Enum):
    """Diagnóstico de degradación de alfas mediante Rolling IC, CUSUM y KS-Test."""
    HEALTHY = "HEALTHY"
    WARNING_DECAY = "WARNING_DECAY"
    CRITICAL_BREAK = "CRITICAL_BREAK"
    REGIME_SHIFT = "REGIME_SHIFT"


class OrderSide(str, Enum):
    """Dirección de la operación en derivados o spot."""
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(str, Enum):
    """Tipo de orden a despachar al broker."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class SignalAction(str, Enum):
    """Acción directiva emitida por el motor multi-agente."""
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    HOLD = "HOLD"


class ImmutableDTO(BaseModel):
    """Base para contratos de datos inmutables y estrictos."""
    model_config = ConfigDict(frozen=True, extra="forbid")


class AgentSignalDTO(ImmutableDTO):
    """Señal emitida por un agente especializado o nodo del DAG."""
    symbol: str
    signal_value: float = Field(..., ge=-1.0, le=1.0, description="Fuerza direccional [-1.0 = Short, +1.0 = Long]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Nivel de certeza estadística [0.0 a 1.0]")
    regime: MarketRegime = Field(..., description="Régimen de mercado clasificado")
    action: SignalAction = Field(default=SignalAction.HOLD, description="Acción sugerida")
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TradeOrderDTO(ImmutableDTO):
    """Especificación completa de una orden validada para despacho en broker."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: float = Field(..., gt=0.0)
    price: Optional[float] = Field(default=None, gt=0.0)
    stoploss_price: Optional[float] = Field(default=None, gt=0.0)
    leverage: float = Field(default=1.0, ge=1.0, le=5.0)
    entry_tag: Optional[str] = None
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthMetricDTO(ImmutableDTO):
    """Instantánea de salud estadística y drift de un factor de alfa."""
    factor_id: str
    rolling_ic: float
    ic_ir: float
    p_value: float = Field(..., ge=0.0, le=1.0)
    cusum_stat: float
    ks_drift_stat: float
    status: HealthStatus
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioWeightDTO(ImmutableDTO):
    """Ponderación óptima de capital calculada por HRP / Riskfolio."""
    strategy_id: str
    target_weight: float = Field(..., ge=0.0, le=1.0)
    allocated_usd: float = Field(default=0.0, ge=0.0)
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
