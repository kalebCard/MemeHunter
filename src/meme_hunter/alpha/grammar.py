"""
meme_hunter.alpha.grammar - Módulo Canónico de Gramática Simbólica para Minería de Alpha Factors.
Inspirado en la taxonomía WorldQuant Alpha 101 y operadores cuantitativos de López de Prado.

Provee:
- Nodos AST (Expression Tree) evaluables vectorialmente sobre DataFrames OHLCV.
- Operadores temporales: ts_rank, ts_corr, ts_delay, ts_delta, ts_std, ts_decay_linear, ts_zscore.
- Operadores matemáticos: abs, sign, log, power, add, sub, mul, div.
- Operadores de microestructura: rvol, vwap_diff, spread_proxy.
- Generador de fórmulas aleatorias para algoritmos genéticos.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd


class ASTNode(ABC):
    """Nodo base abstracto del árbol sintáctico del factor."""
    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> pd.Series:
        pass

    @abstractmethod
    def to_formula(self) -> str:
        pass

    @abstractmethod
    def get_depth(self) -> int:
        pass

    @abstractmethod
    def get_nodes(self) -> List['ASTNode']:
        pass


class FeatureNode(ASTNode):
    """Nodo hoja que representa una columna de datos del mercado."""
    def __init__(self, column_name: str):
        self.column = column_name

    def evaluate(self, df: pd.DataFrame) -> pd.Series:
        if self.column in df.columns:
            return df[self.column].astype(float)
        # Proxies computados al vuelo si no están presentes
        if self.column == 'returns':
            return df['close'].pct_change().fillna(0.0)
        elif self.column == 'hl_spread':
            return ((df['high'] - df['low']) / df['close'].replace(0, 1.0)).fillna(0.0)
        elif self.column == 'vwap':
            typical = (df['high'] + df['low'] + df['close']) / 3.0
            cum_vol = df['volume'].cumsum().replace(0, 1.0)
            return ((typical * df['volume']).cumsum() / cum_vol).fillna(df['close'])
        elif self.column == 'rvol':
            vol_ma = df['volume'].rolling(20, min_periods=1).mean()
            return (df['volume'] / vol_ma.replace(0, 1.0)).fillna(1.0)
        return pd.Series(0.0, index=df.index)

    def to_formula(self) -> str:
        return self.column

    def get_depth(self) -> int:
        return 1

    def get_nodes(self) -> List[ASTNode]:
        return [self]


class ConstantNode(ASTNode):
    """Nodo hoja que representa una constante escalar."""
    def __init__(self, value: float):
        self.value = float(value)

    def evaluate(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(self.value, index=df.index)

    def to_formula(self) -> str:
        return f"{self.value:.2f}"

    def get_depth(self) -> int:
        return 1

    def get_nodes(self) -> List[ASTNode]:
        return [self]


class UnaryOpNode(ASTNode):
    """Operador unario matemático sobre una serie."""
    def __init__(self, op: str, child: ASTNode):
        self.op = op
        self.child = child

    def evaluate(self, df: pd.DataFrame) -> pd.Series:
        val = self.child.evaluate(df)
        if self.op == 'abs':
            return val.abs()
        elif self.op == 'sign':
            return np.sign(val)
        elif self.op == 'log':
            return np.log(val.abs() + 1e-6)
        elif self.op == 'neg':
            return -val
        return val

    def to_formula(self) -> str:
        return f"{self.op}({self.child.to_formula()})"

    def get_depth(self) -> int:
        return 1 + self.child.get_depth()

    def get_nodes(self) -> List[ASTNode]:
        return [self] + self.child.get_nodes()


class BinaryOpNode(ASTNode):
    """Operador binario entre dos expresiones (+, -, *, /)."""
    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, df: pd.DataFrame) -> pd.Series:
        l_val = self.left.evaluate(df)
        r_val = self.right.evaluate(df)
        if self.op == '+':
            return l_val + r_val
        elif self.op == '-':
            return l_val - r_val
        elif self.op == '*':
            return l_val * r_val
        elif self.op == '/':
            # División protegida para evitar división por cero
            denom = r_val.replace(0.0, 1e-6)
            return (l_val / denom).replace([np.inf, -np.inf], 0.0)
        return l_val

    def to_formula(self) -> str:
        return f"({self.left.to_formula()} {self.op} {self.right.to_formula()})"

    def get_depth(self) -> int:
        return 1 + max(self.left.get_depth(), self.right.get_depth())

    def get_nodes(self) -> List[ASTNode]:
        return [self] + self.left.get_nodes() + self.right.get_nodes()


class TimeSeriesOpNode(ASTNode):
    """Operador temporal de series de tiempo (rolling window)."""
    def __init__(self, op: str, child: ASTNode, window: int):
        self.op = op
        self.child = child
        self.window = max(2, int(window))

    def evaluate(self, df: pd.DataFrame) -> pd.Series:
        s = self.child.evaluate(df)
        w = self.window
        
        if self.op == 'ts_delay':
            return s.shift(w).fillna(0.0)
        elif self.op == 'ts_delta':
            return (s - s.shift(w)).fillna(0.0)
        elif self.op == 'ts_std':
            return s.rolling(w, min_periods=1).std().fillna(0.0)
        elif self.op == 'ts_zscore':
            mean = s.rolling(w, min_periods=1).mean()
            std = s.rolling(w, min_periods=1).std().replace(0.0, 1e-6)
            return ((s - mean) / std).fillna(0.0)
        elif self.op == 'ts_decay_linear':
            # Ponderación lineal decreciente hacia el pasado
            weights = np.arange(1, w + 1)
            weights = weights / weights.sum()
            return s.rolling(w, min_periods=1).apply(lambda x: np.dot(x, weights[-len(x):]) if len(x) > 0 else 0.0, raw=True).fillna(0.0)
        elif self.op == 'ts_rank':
            # Rango percentil dentro de la ventana móvil
            return s.rolling(w, min_periods=1).apply(lambda x: float(pd.Series(x).rank().iloc[-1] / len(x)), raw=False).fillna(0.5)
        return s

    def to_formula(self) -> str:
        return f"{self.op}({self.child.to_formula()}, {self.window})"

    def get_depth(self) -> int:
        return 1 + self.child.get_depth()

    def get_nodes(self) -> List[ASTNode]:
        return [self] + self.child.get_nodes()


class AlphaGrammar:
    """Fábrica y generador de expresiones aleatorias y mutaciones genéticas."""
    FEATURES = ['open', 'high', 'low', 'close', 'volume', 'returns', 'hl_spread', 'vwap', 'rvol']
    UNARY_OPS = ['abs', 'sign', 'log', 'neg']
    BINARY_OPS = ['+', '-', '*', '/']
    TS_OPS = ['ts_delay', 'ts_delta', 'ts_std', 'ts_zscore', 'ts_decay_linear', 'ts_rank']
    WINDOWS = [3, 5, 10, 14, 20, 30]

    @classmethod
    def random_terminal(cls) -> ASTNode:
        """Crea un nodo hoja terminal (Feature o Constante)."""
        if np.random.rand() < 0.8:
            return FeatureNode(np.random.choice(cls.FEATURES))
        else:
            return ConstantNode(np.random.choice([0.5, 1.0, 2.0, -1.0]))

    @classmethod
    def random_expression(cls, max_depth: int = 3, current_depth: int = 1) -> ASTNode:
        """Genera un árbol sintáctico aleatorio recursivo."""
        if current_depth >= max_depth or (current_depth > 1 and np.random.rand() < 0.3):
            return cls.random_terminal()

        choice = np.random.choice(['unary', 'binary', 'ts'])
        if choice == 'unary':
            op = np.random.choice(cls.UNARY_OPS)
            child = cls.random_expression(max_depth, current_depth + 1)
            return UnaryOpNode(op, child)
        elif choice == 'binary':
            op = np.random.choice(cls.BINARY_OPS)
            left = cls.random_expression(max_depth, current_depth + 1)
            right = cls.random_expression(max_depth, current_depth + 1)
            return BinaryOpNode(op, left, right)
        else:  # ts
            op = np.random.choice(cls.TS_OPS)
            window = np.random.choice(cls.WINDOWS)
            child = cls.random_expression(max_depth, current_depth + 1)
            return TimeSeriesOpNode(op, child, window)


__all__ = [
    "ASTNode",
    "FeatureNode",
    "ConstantNode",
    "UnaryOpNode",
    "BinaryOpNode",
    "TimeSeriesOpNode",
    "AlphaGrammar",
]
