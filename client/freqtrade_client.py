"""
client.freqtrade_client - Shim de Compatibilidad (Sprint 55: PB-210 & PB-211).
Re-exporta la implementación canónica unificada desde meme_hunter.execution.freqtrade_client.
"""

from meme_hunter.execution.freqtrade_client import FreqtradeRestClient

__all__ = ["FreqtradeRestClient"]
