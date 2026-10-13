"""
validation/schemas.py - Modelos de Esquemas Inmutables con Pydantic v2 (Sprint 36 & 37: PB-120 / PB-124).
Define contratos de datos estrictos para el Cortafuegos de Entrada, Sesgo del Cerebro Lento
y el Guardián de Salida de la IA.
"""

from enum import Enum
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# =============================================================================
# ENUMS CANÓNICOS
# =============================================================================

class MarketBiasPosture(str, Enum):
    """Postura directiva estructurada emitida por el Cerebro Lento."""
    ALLOW_LONG = "ALLOW_LONG"
    ALLOW_SHORT = "ALLOW_SHORT"
    NEUTRAL_HOLD = "NEUTRAL_HOLD"
    STRICT_VETO = "STRICT_VETO"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


# =============================================================================
# 1. CORTAFUEGOS DE ENTRADA (MERCADO & SERIES TEMPORALES)
# =============================================================================

class MarketTickSchema(BaseModel):
    """Esquema de validación para un tick individual de intercambio."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(..., min_length=3, description="Par negociado (ej. DOGE/USDT)")
    price: float = Field(..., gt=0.0, description="Precio de ejecución strictly positive")
    qty: float = Field(..., gt=0.0, description="Cantidad negociada strictly positive")
    side: OrderSide = Field(..., description="Lado de la transacción (buy/sell)")
    timestamp_ms: int = Field(..., gt=0, description="Timestamp en milisegundos UTC")


class MarketCandleSchema(BaseModel):
    """
    Esquema inmutable para una vela OHLCV.
    Impone relaciones matemáticas estrictas de microestructura: High >= Low, Close > 0, etc.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp_ms: int = Field(..., gt=0, description="Timestamp de apertura en ms")
    open: float = Field(..., gt=0.0, description="Precio de apertura")
    high: float = Field(..., gt=0.0, description="Precio máximo")
    low: float = Field(..., gt=0.0, description="Precio mínimo")
    close: float = Field(..., gt=0.0, description="Precio de cierre")
    volume: float = Field(..., ge=0.0, description="Volumen negociado")

    @model_validator(mode="after")
    def validate_candle_geometry(self) -> "MarketCandleSchema":
        """Valida que la geometría de la vela sea matemáticamente consistente."""
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) no puede ser menor que Low ({self.low})")
        if self.high < max(self.open, self.close):
            raise ValueError(f"High ({self.high}) debe ser >= max(Open, Close) ({max(self.open, self.close)})")
        if self.low > min(self.open, self.close):
            raise ValueError(f"Low ({self.low}) debe ser <= min(Open, Close) ({min(self.open, self.close)})")
        return self


class OrderBookL2Schema(BaseModel):
    """
    Esquema de validación de profundidad de libro Level 2.
    Certifica que el libro no esté cruzado (Best Bid < Best Ask) y tenga liquidez positiva.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(..., min_length=3)
    timestamp_ms: int = Field(..., gt=0)
    bids: List[Tuple[float, float]] = Field(..., min_length=1, description="Lista de [precio, cantidad]")
    asks: List[Tuple[float, float]] = Field(..., min_length=1, description="Lista de [precio, cantidad]")

    @model_validator(mode="after")
    def validate_book_integrity(self) -> "OrderBookL2Schema":
        best_bid = self.bids[0][0]
        best_ask = self.asks[0][0]

        if best_bid <= 0.0 or best_ask <= 0.0:
            raise ValueError("Precios en el libro L2 deben ser estrictamente positivos")

        if best_bid >= best_ask:
            raise ValueError(
                f"Libro L2 cruzado o invertido: Best Bid ({best_bid}) >= Best Ask ({best_ask})"
            )

        # Validar que no existan cantidades nulas o negativas
        for p, q in self.bids:
            if p <= 0 or q < 0:
                raise ValueError(f"Nivel de Bid inválido: price={p}, qty={q}")
        for p, q in self.asks:
            if p <= 0 or q < 0:
                raise ValueError(f"Nivel de Ask inválido: price={p}, qty={q}")

        return self


class MarketSeriesInput(BaseModel):
    """Colección ordenada de velas para ingesta en modelos y agentes."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(..., min_length=3)
    timeframe: str = Field(..., description="Intervalo de la serie ('1h', '4h', '1d')")
    candles: List[MarketCandleSchema] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_time_order(self) -> "MarketSeriesInput":
        """Verifica que las velas estén en orden estrictamente creciente."""
        prev_ts = -1
        for i, c in enumerate(self.candles):
            if c.timestamp_ms <= prev_ts:
                raise ValueError(
                    f"Inversión o duplicación temporal en vela {i}: ts {c.timestamp_ms} <= previo {prev_ts}"
                )
            prev_ts = c.timestamp_ms
        return self


# =============================================================================
# 2. ESQUEMA DE SESGO DEL CEREBRO LENTO (PB-124)
# =============================================================================

class MarketBiasSchema(BaseModel):
    """
    Estado estructurado de autorización y postura directiva emitida por el Cerebro Lento.
    El agente NUNCA emite órdenes de mercado; solo emite este contrato de sesgo.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(..., min_length=3, description="Símbolo del par (ej. DOGE/USDT)")
    posture: MarketBiasPosture = Field(..., description="Postura autorizada (ALLOW_LONG, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Nivel de convicción estadística [0, 1]")
    consensus_score: float = Field(..., ge=0.0, le=1.0, description="Grado de acuerdo entre agentes [0, 1]")
    regime_detected: str = Field("UNKNOWN", description="Régimen de mercado detectado (ej. BULL_MOMENTUM)")
    valid_until_utc: str = Field(..., description="Timestamp ISO-8601 tras el cual el sesgo expira")
    max_leverage: float = Field(default=1.0, ge=1.0, le=3.0, description="Apalancamiento máximo tolerable")
    allowed_setups: List[str] = Field(default_factory=list, description="Lista blanca de setups autorizados")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos auditables de la inferencia")
    generated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp de emisión"
    )

    @field_validator("valid_until_utc")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            # Debe ser parseable como ISO-8601
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"valid_until_utc debe ser un ISO-8601 válido: {e}")
        return v


# =============================================================================
# 3. ESQUEMA DE VALIDACIÓN DE SALIDA DE IA / GUARD (PB-129)
# =============================================================================

class AISentimentOutputSchema(BaseModel):
    """
    Validación de salida para modelos LLM cualitativos.
    Cualquier texto adicional o campo ajeno es rechazado por `extra='forbid'`.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    sentiment: float = Field(..., ge=-1.0, le=1.0, description="Score continuo [-1.0, 1.0]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza en la evaluación [0.0, 1.0]")
    key_catalyst: Optional[str] = Field(default=None, max_length=120, description="Catalizador clave detectado")


class AIOrderAuthorizationOutputSchema(BaseModel):
    """
    Validación estricta de autorización si un agente propone una directiva.
    Garantiza que la IA no intente especificar órdenes de mercado directas.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: MarketBiasPosture = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str = Field(..., max_length=200)
