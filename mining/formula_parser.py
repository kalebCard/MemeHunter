"""
Módulo de Compilación, Sanitización y Parseo AST de Fórmulas Generadas por LLMs.
Sprint 2: Motor de Investigación Cuantitativa Aumentado por IA (US-2.2).

Convierte expresiones simbólicas matemáticas (generadas por OpenRouter / LLMs)
en árboles de ejecución `ASTNode` de `AlphaGrammar` de forma 100% segura y aislada (Zero eval).
"""

import ast
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from mining.alpha_grammar import (
    ASTNode,
    FeatureNode,
    ConstantNode,
    UnaryOpNode,
    BinaryOpNode,
    TimeSeriesOpNode,
    AlphaGrammar
)


class FormulaASTParser:
    """
    Parser sintáctico recursivo seguro que traduce cadenas de texto a árboles ASTNode de AlphaGrammar.
    """

    ALLOWED_FEATURES = set(AlphaGrammar.FEATURES) | {'volume_delta'}
    ALLOWED_UNARY = set(AlphaGrammar.UNARY_OPS)
    ALLOWED_TS = set(AlphaGrammar.TS_OPS)
    BINARY_FUNCTION_MAP = {
        'add': '+',
        'sub': '-',
        'mul': '*',
        'div': '/'
    }

    @classmethod
    def parse(cls, formula_str: str) -> ASTNode:
        """
        Parsea y sanitiza una fórmula simbólica de forma segura.
        Lanza ValueError si la expresión contiene llamadas prohibidas o sintaxis inválida.
        """
        clean_formula = formula_str.strip()
        if not clean_formula:
            raise ValueError("Fórmula vacía no permitida.")

        try:
            tree = ast.parse(clean_formula, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Error de sintaxis al parsear fórmula '{formula_str}': {e}")

        return cls._visit_node(tree.body)

    @classmethod
    def _visit_node(cls, node: ast.AST) -> ASTNode:
        # 1. Variables / Features
        if isinstance(node, ast.Name):
            feat_name = node.id.lower()
            if feat_name in cls.ALLOWED_FEATURES:
                return FeatureNode(feat_name)
            raise ValueError(f"Feature no reconocida o no permitida: '{node.id}'")

        # 2. Constantes numéricas
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return ConstantNode(float(node.value))
            raise ValueError(f"Tipo de constante no numérico: '{type(node.value)}'")

        # Compatibilidad con Python < 3.8
        elif isinstance(node, ast.Num):
            return ConstantNode(float(node.n))

        # 3. Operadores Binarios Estándar (+, -, *, /)
        elif isinstance(node, ast.BinOp):
            left = cls._visit_node(node.left)
            right = cls._visit_node(node.right)

            if isinstance(node.op, ast.Add):
                op_str = '+'
            elif isinstance(node.op, ast.Sub):
                op_str = '-'
            elif isinstance(node.op, ast.Mult):
                op_str = '*'
            elif isinstance(node.op, ast.Div):
                op_str = '/'
            else:
                raise ValueError(f"Operador binario no admitido: {type(node.op)}")

            return BinaryOpNode(op_str, left, right)

        # 4. Operadores Unarios (-x)
        elif isinstance(node, ast.UnaryOp):
            child = cls._visit_node(node.operand)
            if isinstance(node.op, ast.USub):
                return UnaryOpNode('neg', child)
            elif isinstance(node.op, ast.UAdd):
                return child
            else:
                raise ValueError(f"Operador unario no admitido: {type(node.op)}")

        # 5. Funciones (ts_rank, ts_zscore, log, abs, add, div, etc.)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Llamada de función dinámica no autorizada.")

            func_name = node.func.id.lower()

            # Operadores de Series de Tiempo (ej. ts_rank(child, window))
            if func_name in cls.ALLOWED_TS:
                if len(node.args) != 2:
                    raise ValueError(f"Función temporal '{func_name}' requiere exactamente 2 argumentos (expresión, ventana).")
                child = cls._visit_node(node.args[0])
                window_node = node.args[1]
                if isinstance(window_node, ast.Constant) and isinstance(window_node.value, (int, float)):
                    window = int(window_node.value)
                elif isinstance(window_node, ast.Num):
                    window = int(window_node.n)
                else:
                    raise ValueError(f"El argumento de ventana para '{func_name}' debe ser un entero constante.")
                return TimeSeriesOpNode(func_name, child, window)

            # Operadores Unarios (ej. abs(x), log(x))
            elif func_name in cls.ALLOWED_UNARY:
                if len(node.args) != 1:
                    raise ValueError(f"Función unaria '{func_name}' requiere 1 argumento.")
                child = cls._visit_node(node.args[0])
                return UnaryOpNode(func_name, child)

            # Operadores Binarios en formato de función (ej. add(x, y), div(x, y))
            elif func_name in cls.BINARY_FUNCTION_MAP:
                if len(node.args) != 2:
                    raise ValueError(f"Función '{func_name}' requiere 2 argumentos.")
                left = cls._visit_node(node.args[0])
                right = cls._visit_node(node.args[1])
                return BinaryOpNode(cls.BINARY_FUNCTION_MAP[func_name], left, right)

            else:
                raise ValueError(f"Función desconocida o no autorizada en la gramática: '{func_name}'")

        else:
            raise ValueError(f"Elemento sintáctico bloqueado por seguridad: {type(node).__name__}")
