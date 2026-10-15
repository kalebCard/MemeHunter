"""
data_engine.slippage_engine - Shim de Compatibilidad (Sprint 55: PB-210 & PB-211).
Re-exporta la implementación canónica unificada desde meme_hunter.data.slippage_engine.
"""

from meme_hunter.data.slippage_engine import ExecutionResult, MicrostructureSlippageEngine

__all__ = ["ExecutionResult", "MicrostructureSlippageEngine"]
