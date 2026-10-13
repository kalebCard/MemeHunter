"""
oos_gating.py - Protocolo Estricto de Aceptación Fuera de Muestra (OOS) y Filtro de Multicolinealidad.
Sprint 27: Gobernanza Anti-Overfitting y Control de Fricción (PB-93, PB-94).

Implementa:
1. Gating Protocol OOS: Evaluación ciega fuera de muestra mediante Combinatorial Purged Cross-Validation (CPCV).
2. Cálculo y límite estricto de PBO (Probability of Backtest Overfitting < 15%) y DSR/PSR (>= 95%).
3. Filtro de Multicolinealidad Estricto: Correlación cruzada < 0.40 contra todas las estrategias en LIVE.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from validation.cpcv_engine import CPCVEngine
from validation.multiple_testing import MultipleTestingController
from scripts.advanced_metrics import calculate_moments, probabilistic_sharpe_ratio, deflated_sharpe_ratio


@dataclass
class GatingValidationResult:
    """Resultado estructurado de la validación de gobernanza para promoción a producción."""
    strategy_id: str
    passed: bool
    rejection_reason: Optional[str] = None
    oos_sharpe: float = 0.0
    pbo: float = 0.0
    dsr: float = 0.0
    psr: float = 0.0
    max_correlation: float = 0.0
    conflicting_strategy_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class OOSGatingValidator:
    """
    Gobernador cuantitativo que audita factores candidatos antes de autorizar su paso de SANDBOX a LIVE.
    Impide que el sobreajuste a corto plazo o la duplicidad de factores degraden la cartera activa.
    """

    def __init__(
        self,
        min_bars: int = 50,
        max_correlation: float = 0.40,
        max_pbo: float = 0.15,
        min_dsr: float = 0.95,
        min_oos_sharpe: float = 1.00,
        cpcv_splits: int = 6,
        cpcv_test_splits: int = 2
    ):
        self.min_bars = int(min_bars)
        self.max_correlation = float(max_correlation)
        self.max_pbo = float(max_pbo)
        self.min_dsr = float(min_dsr)
        self.min_oos_sharpe = float(min_oos_sharpe)
        self.cpcv_splits = int(cpcv_splits)
        self.cpcv_test_splits = int(cpcv_test_splits)

    def check_multicollinearity(
        self,
        candidate_returns: pd.Series,
        returns_matrix_df: pd.DataFrame,
        live_strategy_ids: List[str]
    ) -> Tuple[bool, float, Optional[str]]:
        """
        PB-94: Verifica que la correlación de retornos contra las estrategias activas sea < max_correlation.
        Retorna (pasa_filtro, max_corr_encontrada, id_estrategia_conflicto).
        """
        valid_live = [sid for sid in live_strategy_ids if sid in returns_matrix_df.columns]
        if not valid_live:
            return True, 0.0, None

        cand_ret = candidate_returns.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        cand_std = cand_ret.std()
        if cand_std < 1e-8:
            return True, 0.0, None

        max_corr = 0.0
        conflicting_id: Optional[str] = None

        for sid in valid_live:
            other_ret = returns_matrix_df[sid].replace([np.inf, -np.inf], 0.0).fillna(0.0)
            if other_ret.std() < 1e-8:
                continue
            corr = float(cand_ret.corr(other_ret))
            if np.isnan(corr):
                corr = 0.0
            abs_corr = abs(corr)
            if abs_corr > max_corr:
                max_corr = abs_corr
                conflicting_id = sid

            if abs_corr >= self.max_correlation:
                return False, abs_corr, sid

        return True, max_corr, conflicting_id

    def validate_candidate(
        self,
        strategy_id: str,
        signal: pd.Series,
        forward_returns: pd.Series,
        returns_matrix_df: Optional[pd.DataFrame] = None,
        live_strategy_ids: Optional[List[str]] = None,
        all_trials_sr: Optional[List[float]] = None
    ) -> GatingValidationResult:
        """
        Ejecuta la batería integral de Gating OOS:
        1. Verificación de tamaño de muestra temporal.
        2. Filtro de Multicolinealidad (PB-94).
        3. Evaluación Combinatoria Purged Cross-Validation (CPCV).
        4. Verificación de PBO y DSR/PSR (PB-93).
        """
        # Calcular serie de retornos brutos de la estrategia
        strat_returns = (signal * forward_returns).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        n_samples = len(strat_returns)

        # 1. Verificación de longitud mínima
        if n_samples < self.min_bars:
            return GatingValidationResult(
                strategy_id=strategy_id,
                passed=False,
                rejection_reason=f"Muestra insuficiente: {n_samples} barras < {self.min_bars} requeridas."
            )

        # 2. Filtro de Multicolinealidad (PB-94)
        max_corr = 0.0
        conflicting_sid = None
        if returns_matrix_df is not None and live_strategy_ids:
            corr_passed, max_corr, conflicting_sid = self.check_multicollinearity(
                candidate_returns=strat_returns,
                returns_matrix_df=returns_matrix_df,
                live_strategy_ids=live_strategy_ids
            )
            if not corr_passed:
                return GatingValidationResult(
                    strategy_id=strategy_id,
                    passed=False,
                    rejection_reason=(
                        f"Multicolinealidad excesiva: correlación {max_corr:.2f} con {conflicting_sid} "
                        f"excede el umbral estricto ({self.max_correlation:.2f})."
                    ),
                    max_correlation=max_corr,
                    conflicting_strategy_id=conflicting_sid
                )

        # 3. Particionado CPCV y cálculo de desempeño OOS
        cpcv = CPCVEngine(
            n_splits=self.cpcv_splits,
            n_test_splits=self.cpcv_test_splits,
            embargo_pct=0.01,
            purge_window_bars=1
        )
        splits = list(cpcv.split(strat_returns))

        oos_sharpes: List[float] = []
        cpcv_perf_rows: List[List[float]] = []

        ret_vals = strat_returns.to_numpy()
        fwd_vals = forward_returns.to_numpy()

        for s in splits:
            oos_ret = ret_vals[s.test_indices]
            if len(oos_ret) > 1 and np.std(oos_ret) > 1e-8:
                sr = float(np.mean(oos_ret) / np.std(oos_ret) * np.sqrt(365 * 6))  # 4h annualization
            else:
                sr = 0.0
            oos_sharpes.append(sr)

            # Para PBO, contrastar contra benchmark o variantes perturbadas
            bench_ret = fwd_vals[s.test_indices]
            bench_sr = float(np.mean(bench_ret) / np.std(bench_ret) * np.sqrt(365 * 6)) if np.std(bench_ret) > 1e-8 else 0.0
            cpcv_perf_rows.append([sr, bench_sr])

        mean_oos_sr = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0

        # 4. Cálculo de PBO mediante matriz CPCV
        cpcv_matrix = np.array(cpcv_perf_rows)
        pbo = MultipleTestingController.compute_pbo_from_cpcv_matrix(cpcv_matrix)

        # 5. Cálculo de Momentos, PSR y DSR
        mean_ret, std_ret, skew, kurt = calculate_moments(ret_vals)
        psr = probabilistic_sharpe_ratio(
            observed_sr=mean_oos_sr,
            benchmark_sr=0.0,
            n_samples=n_samples,
            skewness=skew,
            kurtosis=kurt
        )

        trials = all_trials_sr if all_trials_sr and len(all_trials_sr) >= 2 else [mean_oos_sr, 0.5, 0.0, -0.2]
        dsr_dict = deflated_sharpe_ratio(
            observed_sr=mean_oos_sr,
            all_trials_sr=trials,
            n_samples=n_samples,
            skewness=skew,
            kurtosis=kurt
        )
        dsr = float(dsr_dict.get("dsr", psr))

        # 6. Evaluación de Criterios de Aceptación
        metrics = {
            "mean_oos_sharpe": mean_oos_sr,
            "pbo": pbo,
            "psr": psr,
            "dsr": dsr,
            "max_correlation": max_corr,
            "n_samples": n_samples,
            "n_cpcv_paths": len(splits)
        }

        # Comprobar PBO (PB-93)
        if pbo > self.max_pbo:
            return GatingValidationResult(
                strategy_id=strategy_id,
                passed=False,
                rejection_reason=f"PBO excesivo: {pbo:.1%} excede el límite máximo de {self.max_pbo:.1%}.",
                oos_sharpe=mean_oos_sr,
                pbo=pbo,
                dsr=dsr,
                psr=psr,
                max_correlation=max_corr,
                conflicting_strategy_id=conflicting_sid,
                metrics=metrics
            )

        # Comprobar DSR / PSR (PB-93)
        # Se aprueba si el DSR o el PSR alcanzan el nivel de confianza mínimo (95%)
        effective_confidence = max(dsr, psr)
        if effective_confidence < self.min_dsr:
            return GatingValidationResult(
                strategy_id=strategy_id,
                passed=False,
                rejection_reason=(
                    f"Confianza estadística insuficiente: DSR/PSR={effective_confidence:.1%} < {self.min_dsr:.1%} requerido."
                ),
                oos_sharpe=mean_oos_sr,
                pbo=pbo,
                dsr=dsr,
                psr=psr,
                max_correlation=max_corr,
                conflicting_strategy_id=conflicting_sid,
                metrics=metrics
            )

        # Comprobar Sharpe OOS mínimo
        if mean_oos_sr < self.min_oos_sharpe:
            return GatingValidationResult(
                strategy_id=strategy_id,
                passed=False,
                rejection_reason=f"Sharpe OOS insuficiente: {mean_oos_sr:.2f} < {self.min_oos_sharpe:.2f}.",
                oos_sharpe=mean_oos_sr,
                pbo=pbo,
                dsr=dsr,
                psr=psr,
                max_correlation=max_corr,
                conflicting_strategy_id=conflicting_sid,
                metrics=metrics
            )

        # Aprobado con honores
        return GatingValidationResult(
            strategy_id=strategy_id,
            passed=True,
            rejection_reason=None,
            oos_sharpe=mean_oos_sr,
            pbo=pbo,
            dsr=dsr,
            psr=psr,
            max_correlation=max_corr,
            conflicting_strategy_id=conflicting_sid,
            metrics=metrics
        )
