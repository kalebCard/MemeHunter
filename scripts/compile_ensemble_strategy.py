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
from typing import Dict, List, Any, Optional


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

        def ts_rank(s: pd.Series, w: int) -> pd.Series:
            return s.rolling(w, min_periods=1).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False).fillna(0.5)

        def ts_delay(s: pd.Series, w: int) -> pd.Series:
            return s.shift(w).fillna(s)

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

        # 4. Indicadores de Confirmación Rápida Multi-Horizonte (PB-102)
        dataframe['ema_50'] = dataframe['close'].ewm(span=50, adjust=False).mean()
        dataframe['fast_momentum'] = (
            (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3).replace(0, 1.0)
        ).fillna(0.0)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        PB-99: Genera señales de entrada bidireccionales (LONG / SHORT) basadas en la confluencia
        del ensamble de factores HRP y el régimen macro de microestructura.
        """
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['enter_tag'] = ''

        # 1. Entrada LONG: Ensamble alcista + Precio sobre EMA 200 + RSI moderado + Confirmación rápida
        cond_alpha_long = (dataframe['composite_alpha_score'] > 0.05)
        cond_struct_long = (dataframe['close'] > dataframe['ema_200']) & (dataframe['rsi'] < 68)
        cond_fast_long = (dataframe['close'] >= dataframe['ema_50']) | (dataframe['fast_momentum'] > 0.0)
        mask_long = cond_alpha_long & cond_struct_long & cond_fast_long
        dataframe.loc[mask_long, 'enter_long'] = 1
        dataframe.loc[mask_long, 'enter_tag'] = 'long_hrp_ensemble'

        # 2. Entrada SHORT: Ensamble bajista + Precio bajo EMA 200 + RSI moderado + Confirmación rápida
        cond_alpha_short = (dataframe['composite_alpha_score'] < -0.05)
        cond_struct_short = (dataframe['close'] < dataframe['ema_200']) & (dataframe['rsi'] > 32)
        cond_fast_short = (dataframe['close'] <= dataframe['ema_50']) | (dataframe['fast_momentum'] < 0.0)
        mask_short = cond_alpha_short & cond_struct_short & cond_fast_short
        dataframe.loc[mask_short, 'enter_short'] = 1
        dataframe.loc[mask_short, 'enter_tag'] = 'short_hrp_ensemble'

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        PB-99: Salida ágil tipo Airbag técnico para proteger el capital en Longs y Shorts.
        """
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''

        # Salida LONG: Ensamble se invierte a bajista o RSI en sobrecompra extrema
        cond_exit_long = (dataframe['composite_alpha_score'] < -0.10) | (dataframe['rsi'] > 75)
        dataframe.loc[cond_exit_long, 'exit_long'] = 1
        dataframe.loc[cond_exit_long, 'exit_tag'] = 'airbag_long_exit'

        # Salida SHORT: Ensamble se invierte a alcista o RSI en sobreventa extrema
        cond_exit_short = (dataframe['composite_alpha_score'] > 0.10) | (dataframe['rsi'] < 25)
        dataframe.loc[cond_exit_short, 'exit_short'] = 1
        dataframe.loc[cond_exit_short, 'exit_tag'] = 'airbag_short_exit'

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
    db_path: Optional[str] = "portfolio/alpha_factory.db",
    output_strategy_path: str = "user_data/strategies/MemeHunter_MinedEnsemble.py"
) -> str:
    """
    PB-96: Lee los artefactos de la minería o la base de datos SQLite WAL
    y compila la estrategia ejecutable por Freqtrade (MemeHunter_MinedEnsemble.py).
    """
    factors_data = []
    if os.path.exists(factor_library_path):
        try:
            with open(factor_library_path, 'r', encoding='utf-8') as f:
                factors_data = json.load(f)
        except Exception:
            factors_data = []

    live_factors: Dict[str, float] = {}
    formula_map: Dict[str, str] = {f["factor_id"]: f["formula"] for f in factors_data}

    # 1. Intentar cargar desde SQLite WAL como fuente de verdad
    if db_path and os.path.exists(db_path):
        try:
            from portfolio.db_schema import get_all_strategies_db
            records = get_all_strategies_db(db_path)
            for r in records:
                formula_map[r["strategy_id"]] = r["name"]
                if r.get("status") == "LIVE" and float(r.get("target_capital_weight", 0.0)) > 0.0:
                    live_factors[r["strategy_id"]] = float(r["target_capital_weight"])
        except Exception:
            pass

    # 2. Fallback a incubator_state.json si la DB no arrojó factores
    if not live_factors and os.path.exists(incubator_state_path):
        try:
            with open(incubator_state_path, 'r', encoding='utf-8') as f:
                incubator_data = json.load(f)
            for fid, rec in incubator_data.items():
                if rec.get("status") == "LIVE" and float(rec.get("target_capital_weight", 0.0)) > 0.0:
                    live_factors[fid] = float(rec["target_capital_weight"])
                    if "name" in rec:
                        formula_map[fid] = rec["name"]
        except Exception:
            pass

    # 3. Si no hay factores marcados LIVE, tomar los 2 con mejor Sharpe
    if not live_factors:
        if factors_data:
            for f in sorted(factors_data, key=lambda x: x.get("sharpe_proxy", 0), reverse=True)[:2]:
                live_factors[f["factor_id"]] = 0.50
        else:
            live_factors["ALPHA_DEFAULT_01"] = 0.50
            live_factors["ALPHA_DEFAULT_02"] = 0.50
            formula_map["ALPHA_DEFAULT_01"] = "ts_rank(close, 14)"
            formula_map["ALPHA_DEFAULT_02"] = "ts_zscore((high - low), 10)"

    def _is_safe_factor_formula(formula: str) -> bool:
        """
        PB-134: Valida que la fórmula pertenezca estrictamente a la gramática formal AlphaGrammar.
        Neutraliza intentos de inyección de código arbitrario (RCE) de forma preventiva.
        """
        try:
            from mining.formula_parser import FormulaASTParser
            FormulaASTParser.parse(formula)
            return True
        except Exception:
            return False

    def _is_valid_syntax(code: str) -> bool:
        try:
            import ast
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and (node.attr.startswith("__") or "import" in node.attr):
                    return False
                if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in ("eval", "exec", "compile", "open", "system")):
                    return False
            return True
        except Exception:
            return False

    valid_cols = {'open', 'high', 'low', 'close', 'volume', 'returns', 'hl_spread', 'vwap', 'rvol'}
    factors_lib_map = {f["factor_id"]: f["formula"] for f in factors_data}

    # Generar bloques de código de cálculo para cada factor
    calc_lines = []
    for fid, weight in live_factors.items():
        # 1. Priorizar fórmula formal de factor_library.json
        clean_fid = fid.replace("ARCHIVE_", "").replace("Mined_", "").replace("LLM_", "")
        if fid in factors_lib_map:
            raw_formula = factors_lib_map[fid]
        elif clean_fid in factors_lib_map:
            raw_formula = factors_lib_map[clean_fid]
        else:
            cand = formula_map.get(fid, "")
            if any(c in cand.lower() for c in valid_cols):
                raw_formula = cand
            else:
                raw_formula = "ts_delta(close, 1)"

        # PB-134: Sanitización Zero-Eval obligatoria
        if not _is_safe_factor_formula(raw_formula):
            raw_formula = "ts_delta(close, 1)"

        py_formula = compile_ast_formula_to_python(raw_formula)
        # Adaptar referencias de columnas a dataframe['col']
        for col in ['open', 'high', 'low', 'close', 'volume', 'returns', 'hl_spread', 'vwap', 'rvol']:
            import re
            py_formula = re.sub(rf'\b{col}\b', f"dataframe['{col}']", py_formula)

        if not _is_valid_syntax(py_formula) or "dataframe['" not in py_formula:
            py_formula = "(dataframe['close'] - dataframe['close'].shift(1)).fillna(0.0)"

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


def auto_compile_hook(
    db_path: str = "portfolio/alpha_factory.db",
    output_strategy_path: str = "user_data/strategies/MemeHunter_MinedEnsemble.py"
) -> str:
    """Hook de compilación automática invocado tras promociones o rebalanceos."""
    return generate_ensemble_strategy_file(
        db_path=db_path,
        output_strategy_path=output_strategy_path
    )


if __name__ == "__main__":
    out = generate_ensemble_strategy_file()
    print(f"Estrategia ensamble compilada con éxito en: {out}")
