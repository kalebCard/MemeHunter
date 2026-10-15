"""
meme_hunter.core - Kernel del sistema, configuración tipada, excepciones y tipos de dominio.
"""

from meme_hunter.core.config import AppSettings, get_settings
from meme_hunter.core.exceptions import (
    MemeHunterError,
    ConfigurationError,
    SecurityError,
    DatabaseError,
    DataFeedError,
    RiskGateError,
    KillSwitchActivatedError,
    ExecutionError,
)
from meme_hunter.core.types import (
    MarketRegime,
    StrategyStatus,
    HealthStatus,
    OrderSide,
    SignalAction,
    AgentSignalDTO,
    TradeOrderDTO,
)
from meme_hunter.core.logging import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    StructuredJsonFormatter,
    CorrelationIdAdapter,
    get_logger,
    configure_structured_logging,
)

__all__ = [
    "AppSettings",
    "get_settings",
    "MemeHunterError",
    "ConfigurationError",
    "SecurityError",
    "DatabaseError",
    "DataFeedError",
    "RiskGateError",
    "KillSwitchActivatedError",
    "ExecutionError",
    "MarketRegime",
    "StrategyStatus",
    "HealthStatus",
    "OrderSide",
    "SignalAction",
    "AgentSignalDTO",
    "TradeOrderDTO",
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
    "StructuredJsonFormatter",
    "CorrelationIdAdapter",
    "get_logger",
    "configure_structured_logging",
]
