"""
client.multi_bot_orchestrator - Shim de Compatibilidad (Sprint 55: PB-210 & PB-211).
Re-exporta la implementación canónica unificada desde meme_hunter.execution.multi_bot_orchestrator.
"""

from meme_hunter.execution.multi_bot_orchestrator import MultiBotOrchestratorClient

__all__ = ["MultiBotOrchestratorClient"]
