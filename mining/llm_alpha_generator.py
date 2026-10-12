"""
Generador y Sintetizador Semántico de Factores Cuantitativos mediante LLMs (OpenRouter).
Sprint 2: Motor de Investigación Cuantitativa Aumentado por IA (US-2.3 y US-2.4).

Implementa:
- Formulación de hipótesis de microestructura económica adaptadas al régimen actual de mercado.
- Generación de fórmulas simbólicas parseadas estrictamente con `FormulaASTParser`.
- Inyección de factores semánticos en el catálogo de candidatos.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd

from mining.llm_client import OpenRouterClient, OpenRouterModel
from mining.formula_parser import FormulaASTParser
from mining.alpha_grammar import ASTNode
from mining.genetic_search import AlphaFactor

logger = logging.getLogger("LLMAlphaSynthesizer")


class LLMAlphaSynthesizer:
    """
    Sintetizador de factores cuantitativos guiado por modelos de lenguaje vía OpenRouter.
    """

    def __init__(self, client: Optional[OpenRouterClient] = None, model: str = OpenRouterModel.DEEPSEEK_V3):
        self.client = client or OpenRouterClient()
        self.model = model

    def synthesize_alphas(
        self,
        market_regime: str = "VOLATILE_MEMECOIN_PUMP_DUMP",
        failed_factors: Optional[List[str]] = None,
        n_candidates: int = 5
    ) -> List[Tuple[str, ASTNode]]:
        """
        Pide a OpenRouter formular candidatos de alpha expresados en la gramática simbólica.
        Retorna únicamente pares (formula_str, ASTNode) que pasaron la validación sintáctica estricta.
        """
        failed_context = ", ".join(failed_factors) if failed_factors else "Ninguno (inicio nominal)"

        system_prompt = (
            "Eres un Senior Quantitative Researcher especializado en microestructura de criptomonedas y memecoins. "
            "Tu tarea es proponer fórmulas matemáticas precisas para predecir retornos futuros a corto plazo "
            "utilizando únicamente la gramática simbólica especificada."
        )

        user_prompt = f"""
        Régimen de mercado actual: {market_regime}
        Factores recientemente degradados o en falla: {failed_context}
        Cantidad solicitada: {n_candidates} fórmulas ortogonales.

        REGLAS GRAMATICALES OBLIGATORIAS:
        1. Variables permitidas: open, high, low, close, volume, returns, hl_spread, vwap, rvol
        2. Operadores temporales: ts_rank(x, window), ts_zscore(x, window), ts_std(x, window), ts_delta(x, window), ts_delay(x, window), ts_decay_linear(x, window)
           (El argumento 'window' debe ser un entero entre 3 y 30)
        3. Operadores matemáticos: +, -, *, /, abs(x), sign(x), log(x)
        4. No inventar funciones ni usar librerías externas.

        Responde ÚNICAMENTE un objeto JSON con el siguiente formato:
        {{
            "formulas": ["ts_rank(rvol, 14) * (close - vwap)", "ts_zscore(hl_spread, 10) / (ts_std(close, 20) + 1e-6)"],
            "economic_rationale": "Breve explicación de la hipótesis económica",
            "expected_horizon": "15m"
        }}
        """

        response = self.client.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=0.35,
            json_mode=True
        )

        raw_formulas = response.get("formulas", [])
        verified_candidates: List[Tuple[str, ASTNode]] = []

        for f_str in raw_formulas:
            try:
                ast_node = FormulaASTParser.parse(f_str)
                verified_candidates.append((f_str, ast_node))
            except Exception as e:
                logger.warning(f"Fórmula '{f_str}' rechazada por el parser sintáctico: {e}")

        logger.info(f"Sintetizador LLM: {len(verified_candidates)}/{len(raw_formulas)} fórmulas validadas con éxito.")
        return verified_candidates

    def evaluate_and_build_factors(
        self,
        verified_candidates: List[Tuple[str, ASTNode]],
        df: pd.DataFrame,
        forward_returns: pd.Series
    ) -> List[AlphaFactor]:
        """
        Calcula las métricas empíricas (IC, IC_IR, Sharpe proxy) para las fórmulas validadas del LLM
        y las convierte en objetos AlphaFactor listos para el QualityDiversityArchive.
        """
        factors = []
        for i, (f_str, node) in enumerate(verified_candidates):
            try:
                series = node.evaluate(df)
                series = series.replace([np.inf, -np.inf], np.nan).fillna(0.0)
                if series.std() < 1e-7:
                    continue

                norm_series = (series - series.mean()) / (series.std() + 1e-8)
                rolling_corr = norm_series.rolling(30, min_periods=10).corr(forward_returns).dropna()
                if len(rolling_corr) == 0:
                    continue

                ic_mean = float(rolling_corr.mean())
                ic_std = float(rolling_corr.std()) if len(rolling_corr) > 1 else 1.0
                ic_ir = ic_mean / (ic_std + 1e-6)

                # Sharpe Proxy estimado de posición long/short proporcional a zscore
                strategy_ret = norm_series.shift(1).fillna(0.0) * forward_returns
                mean_r = strategy_ret.mean()
                std_r = strategy_ret.std() + 1e-8
                sharpe = float((mean_r / std_r) * np.sqrt(365 * 6))

                # Rotación estimada
                turnover = float(norm_series.diff().abs().mean())

                factor = AlphaFactor(
                    factor_id=f"LLM_ALPHA_{i+1:02d}",
                    formula=f_str,
                    ic_mean=ic_mean,
                    ic_std=ic_std,
                    ic_ir=ic_ir,
                    sharpe_proxy=sharpe,
                    turnover=turnover,
                    depth=node.get_depth(),
                    correlation_with_existing=0.0
                )
                factors.append(factor)
            except Exception as e:
                logger.debug(f"Error evaluando fórmula {f_str}: {e}")

        return factors
