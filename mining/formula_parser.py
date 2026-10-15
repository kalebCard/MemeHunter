"""
mining.formula_parser - Shim de Compatibilidad (Sprint 55: PB-210 & PB-211).
Re-exporta la implementación canónica unificada desde meme_hunter.alpha.parser.
"""

from meme_hunter.alpha.parser import FormulaASTParser

__all__ = ["FormulaASTParser"]
