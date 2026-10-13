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
]
