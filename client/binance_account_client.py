"""
client.binance_account_client - Shim de Compatibilidad (Sprint 55: PB-210 & PB-211).
Re-exporta la implementación canónica unificada desde meme_hunter.execution.binance_account_client.
"""

from meme_hunter.execution.binance_account_client import BinanceAccountClient

__all__ = ["BinanceAccountClient"]
