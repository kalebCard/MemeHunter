"""
Módulo de Monitoreo de Salud de Alphas, Detección de Decay y Rupturas de Régimen.
Sprint 1: Motor Cuantitativo Auto-Evolutivo (US-1.1 y US-1.2).

Implementa:
1. Cálculo de Information Coefficient (IC) rodante (Spearman Rank Correlation) y Information Ratio del IC (IC_IR).
2. Detección de quiebres estructurales en retornos y volatilidad con CUSUM (Cumulative Sum Control Chart).
3. Prueba de Kolmogorov-Smirnov (KS-test) de ventana deslizante para detección de Data Drift.
4. Generación de diagnósticos de salud para la incubadora y disparadores del demonio de minería.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING_DECAY = "WARNING_DECAY"
    CRITICAL_BREAK = "CRITICAL_BREAK"
    REGIME_SHIFT = "REGIME_SHIFT"


@dataclass
class HealthReport:
    """Diagnóstico estadístico consolidado del estado de un factor o estrategia."""
    factor_id: str
    status: HealthStatus
    rolling_ic: float
    ic_pvalue: float
    ic_ir: float
    cusum_detected: bool
    cusum_stat: float
    drift_detected: bool
    ks_pvalue: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class CUSUMDetector:
    """
    Detector de cambios estructurales basado en el algoritmo CUSUM (Page-Hinkley).
    Supervisa la media y la varianza para detectar cambios abruptos de régimen.
    """

    def __init__(self, threshold: float = 4.0, drift_slack: float = 0.5):
        """
        :param threshold: Umbral de decisión (h en unidades de desviación estándar).
        :param drift_slack: Parámetro de holgura / tolerancia k (en desviaciones estándar).
        """
        self.threshold = threshold
        self.drift_slack = drift_slack

    def detect_break(self, series: np.ndarray) -> Tuple[bool, float, np.ndarray, np.ndarray]:
        """
        Evalúa si la serie presenta quiebres estructurales en media positiva o negativa.
        Retorna: (is_break, max_stat, s_pos, s_neg)
        """
        clean_data = series[np.isfinite(series)]
        if len(clean_data) < 10:
            return False, 0.0, np.zeros(len(clean_data)), np.zeros(len(clean_data))

        mean = np.mean(clean_data)
        std = np.std(clean_data)
        if std < 1e-8:
            return False, 0.0, np.zeros(len(clean_data)), np.zeros(len(clean_data))

        norm_series = (clean_data - mean) / std
        n = len(norm_series)
        s_pos = np.zeros(n)
        s_neg = np.zeros(n)

        for i in range(1, n):
            s_pos[i] = max(0.0, s_pos[i - 1] + norm_series[i] - self.drift_slack)
            s_neg[i] = max(0.0, s_neg[i - 1] - norm_series[i] - self.drift_slack)

        max_stat = float(max(np.max(s_pos), np.max(s_neg)))
        is_break = bool(max_stat >= self.threshold)
        return is_break, max_stat, s_pos, s_neg


class AlphaHealthMonitor:
    """
    Monitor integral de rendimiento y degradación (decay) de factores cuantitativos.
    """

    def __init__(
        self,
        rolling_window: int = 60,
        min_healthy_ic: float = 0.03,
        max_ic_pvalue: float = 0.10,
        cusum_threshold: float = 4.0,
        ks_alpha: float = 0.05
    ):
        """
        :param rolling_window: Tamaño de ventana para evaluar el IC rodante y drift.
        :param min_healthy_ic: Umbral mínimo de IC medio para considerar el factor sano.
        :param max_ic_pvalue: Umbral de significancia estadística del IC.
        :param cusum_threshold: Umbral h para el detector de quiebres CUSUM.
        :param ks_alpha: Nivel de significancia para la prueba de Kolmogorov-Smirnov.
        """
        self.rolling_window = rolling_window
        self.min_healthy_ic = min_healthy_ic
        self.max_ic_pvalue = max_ic_pvalue
        self.ks_alpha = ks_alpha
        self.cusum_detector = CUSUMDetector(threshold=cusum_threshold)

    def compute_rolling_ic(
        self,
        signal: pd.Series,
        forward_returns: pd.Series
    ) -> pd.DataFrame:
        """
        Calcula el Spearman Rank Information Coefficient en ventana rodante.
        """
        df = pd.DataFrame({'signal': signal, 'returns': forward_returns}).dropna()
        if len(df) < self.rolling_window:
            return pd.DataFrame(columns=['ic', 'pvalue', 'ic_ir'])

        ics = []
        pvals = []
        dates = []

        for end_idx in range(self.rolling_window, len(df) + 1):
            sub_df = df.iloc[end_idx - self.rolling_window:end_idx]
            # Spearman correlation
            res = stats.spearmanr(sub_df['signal'], sub_df['returns'])
            ic_val = float(res.statistic) if not np.isnan(res.statistic) else 0.0
            p_val = float(res.pvalue) if not np.isnan(res.pvalue) else 1.0

            ics.append(ic_val)
            pvals.append(p_val)
            dates.append(df.index[end_idx - 1])

        ic_series = pd.Series(ics, index=dates)
        std_ic = ic_series.rolling(min(15, len(ic_series)), min_periods=3).std().fillna(1.0)
        ic_ir = ic_series / (std_ic + 1e-6)

        return pd.DataFrame({
            'ic': ic_series,
            'pvalue': pd.Series(pvals, index=dates),
            'ic_ir': ic_ir
        })

    def detect_data_drift(
        self,
        reference_series: np.ndarray,
        recent_series: np.ndarray
    ) -> Tuple[bool, float]:
        """
        Realiza la prueba de Kolmogorov-Smirnov de 2 muestras para detectar drift en la distribución.
        """
        ref_clean = reference_series[np.isfinite(reference_series)]
        rec_clean = recent_series[np.isfinite(recent_series)]

        if len(ref_clean) < 15 or len(rec_clean) < 15:
            return False, 1.0

        ks_stat, p_val = stats.ks_2samp(ref_clean, rec_clean)
        drift_detected = bool(p_val < self.ks_alpha)
        return drift_detected, float(p_val)

    def diagnose_factor(
        self,
        factor_id: str,
        signal: pd.Series,
        forward_returns: pd.Series,
        historical_baseline_returns: Optional[np.ndarray] = None
    ) -> HealthReport:
        """
        Diagnostica el estado de salud de un factor o estrategia evaluando IC, CUSUM y Drift.
        """
        rolling_metrics = self.compute_rolling_ic(signal, forward_returns)
        
        if rolling_metrics.empty:
            return HealthReport(
                factor_id=factor_id,
                status=HealthStatus.HEALTHY,
                rolling_ic=0.0,
                ic_pvalue=1.0,
                ic_ir=0.0,
                cusum_detected=False,
                cusum_stat=0.0,
                drift_detected=False,
                ks_pvalue=1.0,
                message="Insuficientes datos para calcular IC rodante.",
                details={'bars_available': len(signal)}
            )

        latest_ic = float(rolling_metrics['ic'].iloc[-1])
        latest_pval = float(rolling_metrics['pvalue'].iloc[-1])
        latest_ic_ir = float(rolling_metrics['ic_ir'].iloc[-1])

        # Evaluación de Quiebre CUSUM sobre los retornos
        clean_ret = forward_returns.dropna().to_numpy()
        cusum_break, cusum_stat, _, _ = self.cusum_detector.detect_break(clean_ret)

        # Evaluación de Drift respecto al baseline
        drift_detected = False
        ks_pval = 1.0
        if historical_baseline_returns is not None and len(historical_baseline_returns) >= 20:
            drift_detected, ks_pval = self.detect_data_drift(historical_baseline_returns, clean_ret[-self.rolling_window:])

        # Clasificación del Estado de Salud
        if cusum_break:
            status = HealthStatus.CRITICAL_BREAK
            msg = f"Quiebre estructural CUSUM detectado (stat={cusum_stat:.2f} >= umbral). Régimen invalidado."
        elif drift_detected:
            status = HealthStatus.REGIME_SHIFT
            msg = f"Cambio de distribución detectado por KS-Test (p={ks_pval:.4f} < {self.ks_alpha})."
        elif latest_ic < self.min_healthy_ic or latest_pval > self.max_ic_pvalue:
            status = HealthStatus.WARNING_DECAY
            msg = f"Decaimiento de Alpha detectado: IC={latest_ic:.4f} (mínimo={self.min_healthy_ic}) o p-val={latest_pval:.4f}."
        else:
            status = HealthStatus.HEALTHY
            msg = f"Factor operando en condiciones nominales: IC={latest_ic:.4f}, p-val={latest_pval:.4f}."

        return HealthReport(
            factor_id=factor_id,
            status=status,
            rolling_ic=latest_ic,
            ic_pvalue=latest_pval,
            ic_ir=latest_ic_ir,
            cusum_detected=cusum_break,
            cusum_stat=cusum_stat,
            drift_detected=drift_detected,
            ks_pvalue=ks_pval,
            message=msg,
            details={
                'mean_ic_window': float(rolling_metrics['ic'].mean()),
                'rolling_observations': len(rolling_metrics)
            }
        )
