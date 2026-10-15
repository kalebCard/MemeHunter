"""
portfolio.order_router - Shim de Compatibilidad (Sprint 55: PB-210 & PB-211).
Re-exporta la implementación canónica unificada desde meme_hunter.portfolio.order_router.
"""

from meme_hunter.portfolio.order_router import (
    ExitUrgency,
    OrderExecutionStage,
    SmartExitOrder,
    SmartExitRouter,
)

__all__ = [
    "ExitUrgency",
    "OrderExecutionStage",
    "SmartExitOrder",
    "SmartExitRouter",
]
