"""
meme_hunter.alpha - Síntesis Cognitiva, Gramática Formal, Compilador AST Zero-Eval y Backtesting Vectorial.
"""

from meme_hunter.alpha.grammar import (
    ASTNode,
    FeatureNode,
    ConstantNode,
    UnaryOpNode,
    BinaryOpNode,
    TimeSeriesOpNode,
    AlphaGrammar,
)
from meme_hunter.alpha.parser import FormulaASTParser
from meme_hunter.alpha.tester import validate_formula_ast, run_strategy_backtest

__all__ = [
    "ASTNode",
    "FeatureNode",
    "ConstantNode",
    "UnaryOpNode",
    "BinaryOpNode",
    "TimeSeriesOpNode",
    "AlphaGrammar",
    "FormulaASTParser",
    "validate_formula_ast",
    "run_strategy_backtest",
]
