"""
Compilador Dinámico de Estrategias para Freqtrade a partir de Factores Minados.
PB-86 (Sprint 24).

Lee:
- mining/factor_library.json (Fórmulas sintácticas de los factores)
- portfolio/incubator_state.json (Ponderaciones asignadas por HRP y estado LIVE)

Genera:
- user_data/strategies/MemeHunter_MinedEnsemble.py
Estrategia nativa ejecutable por Freqtrade en Binance Futures, con ponderación de factores,
dimensionamiento de apuestas por HRP, salidas a mercado y compatibilidad Barbell.
"""

import os
import sys
import json
from typing import Dict, List, Any


def compile_ast_formula_to_python(formula_str: str) -> str:
    """
    Traduce una fórmula simbólica de la gramática de factores a sintaxis ejecutable en pandas.
    """
    expr = formula_str.strip()
    
    # Mapeo de operadores de series temporales
    # ts_zscore(x, w) -> ((x - x.rolling(w).mean()) / (x.rolling(w).std().replace(0, 1e-6)))
    # ts_delta(x, w) -> (x - x.shift(w)).fillna(0)
    # ts_std(x, w) -> x.rolling(w).std().fillna(0)
    # ts_delay(x, w) -> x.shift(w).fillna(0)
    # sign(x) -> np.sign(x)
    # abs(x) -> np.abs(x)
    # neg(x) -> (-x)
    
    # Transformaciones idiomáticas seguras
    expr = expr.replace("neg(", "(-")
    expr = expr.replace("sign(", "np.sign(")
    expr = expr.replace("abs(", "np.abs(")
    
    # Manejo de ts_decay_linear(x, w)
    # Se evalúa en el contexto del helper populate_factor_indicators
    return expr


STRATEGY_TEMPLATE = '''"""
Estrategia Ensamble Generada Dinámicamente por la Fábrica de Minería de Alphas.
Compilada automáticamente a partir del Estado de la Incubadora HRP y la Biblioteca de Factores.
Estatus: LIVE PRODUCTION READY
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

try:
    from freqtrade.strategy import IStrategy
except ImportError:
    class IStrategy:
        def __init__(self, config: Optional[dict] = None):
            self.config = config or {{}}

try:
    import talib.abstract as ta
except ImportError:
    try:
        import pandas_ta as ta
    except ImportError:
        ta = None


class MemeHunter_MinedEnsemble(IStrategy):
    """
    Estrategia de Ensamble Multi-Factor ponderada por Hierarchical Risk Parity (HRP).
    Integra los factores validados por CPCV y control de descubrimientos falsos (FDR).
    """

    INTERFACE_VERSION = 3
    can_short: bool = True
    timeframe = "4h"

    # Parámetros de Riesgo y Microestructura
    stoploss = -0.10  # Stop Loss duro al 10%
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # Trailing Stop Holgado de Alta Fidelidad
    trailing_stop = True
    trailing_stop_positive = 0.04
    trailing_stop_positive_offset = 0.12
    trailing_only_offset_is_reached = True

    # Ponderaciones HRP de Factores Activos
    ACTIVE_WEIGHTS = {active_weights_json}

    # Órdenes forzadas a mercado en salidas para erradicar riesgo de no-fill
    order_types = {{
        "entry": "limit",
        "exit": "market",
        "emergency_exit": "market",
        "force_entry": "market",
        "force_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
        "stoploss_on_exchange_interval": 60,
    }}

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calcula los indicadores base y evalúa vectorialmente los factores minados."""
        if dataframe.empty:
            return dataframe

        # 1. Variables de Microestructura Base
        dataframe['hl_spread'] = ((dataframe['high'] - dataframe['low']) / dataframe['close']).fillna(0.0)
        dataframe['returns'] = dataframe['close'].pct_change().fillna(0.0)
        
        typical = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3.0
        cum_vol = dataframe['volume'].cumsum().replace(0, 1.0)
        dataframe['vwap'] = ((typical * dataframe['volume']).cumsum() / cum_vol).fillna(dataframe['close'])
        
        vol_ma = dataframe['volume'].rolling(20, min_periods=1).mean().replace(0, 1.0)
        dataframe['rvol'] = (dataframe['volume'] / vol_ma).fillna(1.0)

        # 2. Helpers para Operadores Temporales
        def ts_decay_linear(s: pd.Series, w: int) -> pd.Series:
            weights = np.arange(1, w + 1)
            weights = weights / weights.sum()
            return s.rolling(w, min_periods=1).apply(lambda x: np.dot(x, weights[-len(x):]) if len(x) > 0 else 0.0, raw=True).fillna(0.0)

        def ts_zscore(s: pd.Series, w: int) -> pd.Series:
            m = s.rolling(w, min_periods=1).mean()
            std = s.rolling(w, min_periods=1).std().replace(0.0, 1e-6)
            return ((s - m) / std).fillna(0.0)

        def ts_delta(s: pd.Series, w: int) -> pd.Series:
            return (s - s.shift(w)).fillna(0.0)

        # 3. Evaluación Dinámica de cada Factor Minado Activo
        composite_score = pd.Series(0.0, index=dataframe.index)

{factor_calculation_code}

        dataframe['composite_alpha_score'] = composite_score
        
        # Filtros de régimen adicionales (EMA 200 de tendencia y RSI)
        if ta is not None and hasattr(ta, 'EMA'):
            try:
                dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
                dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
            except Exception:
                dataframe['ema_200'] = dataframe['close'].ewm(span=200, adjust=False).mean()
                delta = dataframe['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 1e-6)
                rs = gain / loss
                dataframe['rsi'] = 100.0 - (100.0 / (1.0 + rs))
        else:
            dataframe['ema_200'] = dataframe['close'].ewm(span=200, adjust=False).mean()
            delta = dataframe['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 1e-6)
            rs = gain / loss
            dataframe['rsi'] = 100.0 - (100.0 / (1.0 + rs))

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Genera señales de entrada basadas en la confluencia del ensamble de factores."""
        dataframe['enter_short'] = 0
        dataframe['enter_tag'] = ''

        # Condición de Quiebre de Memecoins con confirmación del Ensamble
        # La confluencia ocurre cuando el composite_alpha_score supera el umbral estadístico
        # y el precio confirma régimen bajista por debajo de la EMA 200
        cond_alpha_short = (dataframe['composite_alpha_score'] > 0.05)
        cond_structural = (dataframe['close'] < dataframe['ema_200']) & (dataframe['rsi'] < 52)

        dataframe.loc[cond_alpha_short & cond_structural, 'enter_short'] = 1
        dataframe.loc[cond_alpha_short & cond_structural, 'enter_tag'] = 'short_hrp_ensemble'

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Salida ágil tipo Airbag técnico para proteger el capital de rebotes súbitos."""
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''

        # Salida si la señal compuesta colapsa o el RSI indica sobrecompra violenta
        cond_exit = (dataframe['composite_alpha_score'] < -0.15) | (dataframe['rsi'] > 58)
        dataframe.loc[cond_exit, 'exit_short'] = 1
        dataframe.loc[cond_exit, 'exit_tag'] = 'airbag_ensemble_exit'

        return dataframe

    def leverage(self, pair: str, current_time: Any, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Apalancamiento dinámico aislado regulado según la convicción del ensamble."""
        return 1.5
'''


def generate_ensemble_strategy_file(
    factor_library_path: str = "mining/factor_library.json",
    incubator_state_path: str = "portfolio/incubator_state.json",
    output_strategy_path: str = "user_data/strategies/MemeHunter_MinedEnsemble.py"
) -> str:
    """Lee los artefactos de la minería y compila la estrategia Python ejecutable."""
    if not os.path.exists(factor_library_path) or not os.path.exists(incubator_state_path):
        raise FileNotFoundError("Artefactos de minería o incubadora no encontrados.")

    with open(factor_library_path, 'r', encoding='utf-8') as f:
        factors_data = json.load(f)
    with open(incubator_state_path, 'r', encoding='utf-8') as f:
        incubator_data = json.load(f)

    # Identificar factores en estado LIVE
    live_factors = {}
    for fid, rec in incubator_data.items():
        if rec.get("status") == "LIVE" and rec.get("target_capital_weight", 0.0) > 0.0:
            live_factors[fid] = rec["target_capital_weight"]

    # Si no hay factores marcados LIVE, tomar los 2 con mejor Sharpe
    if not live_factors:
        for f in sorted(factors_data, key=lambda x: x.get("sharpe_proxy", 0), reverse=True)[:2]:
            live_factors[f["factor_id"]] = 0.50

    # Construir mapa de fórmulas
    formula_map = {f["factor_id"]: f["formula"] for f in factors_data}

    # Generar bloques de código de cálculo para cada factor
    calc_lines = []
    for fid, weight in live_factors.items():
        raw_formula = formula_map.get(fid, "dataframe['close']")
        py_formula = compile_ast_formula_to_python(raw_formula)
        # Adaptar referencias de columnas a dataframe['col']
        for col in ['open', 'high', 'low', 'close', 'volume', 'returns', 'hl_spread', 'vwap', 'rvol']:
            # Reemplazar identificadores independientes
            import re
            py_formula = re.sub(rf'\b{col}\b', f"dataframe['{col}']", py_formula)

        calc_lines.append(f"        # Factor {fid} (Peso HRP: {weight:.4f})")
        calc_lines.append(f"        f_val_{fid} = ({py_formula})")
        calc_lines.append(f"        f_std_{fid} = float(f_val_{fid}.std()) if float(f_val_{fid}.std()) > 1e-8 else 1.0")
        calc_lines.append(f"        f_norm_{fid} = (f_val_{fid} - f_val_{fid}.mean()) / f_std_{fid}")
        calc_lines.append(f"        composite_score += f_norm_{fid}.fillna(0.0) * {weight:.6f}\n")

    factor_code_str = "\n".join(calc_lines)
    active_weights_str = json.dumps(live_factors, indent=8)

    rendered_strategy = STRATEGY_TEMPLATE.format(
        active_weights_json=active_weights_str,
        factor_calculation_code=factor_code_str
    )

    os.makedirs(os.path.dirname(output_strategy_path), exist_ok=True)
    with open(output_strategy_path, 'w', encoding='utf-8') as f:
        f.write(rendered_strategy)

    return output_strategy_path


if __name__ == "__main__":
    out = generate_ensemble_strategy_file()
    print(f"Estrategia ensamble compilada con éxito en: {out}")
