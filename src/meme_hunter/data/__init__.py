"""
meme_hunter.data - Motor de Ingesta, Feeds de Mercado Continuos y Microestructura (Dollar Bars, OFI).
"""

from meme_hunter.data.paths import get_base_data_dir, get_futures_data_dir
from meme_hunter.data.slippage_engine import ExecutionResult, MicrostructureSlippageEngine

__all__ = [
    "get_base_data_dir",
    "get_futures_data_dir",
    "ExecutionResult",
    "MicrostructureSlippageEngine",
]
