"""
Meme Hunter - Institutional Risk Manager Agent (PB-108)
Sprint 31: Filtro dinámico VaR 99%, Kill-Switch de drawdown y control de correlación cruzada.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from portfolio.dag_orchestrator import VectorAlpha


@dataclass
class RiskVerdict:
    """Dictamen institucional del gestor de riesgos previo a la ejecución."""
    decision: str                       # 'APPROVED', 'SCALED_DOWN', 'REJECTED'
    sizing_multiplier: float            # [0.0, 1.0] Factor multiplicador de tamaño de posición
    reason: str                         # Justificación cuantitativa del dictamen
    var_99_pct: float = 0.0             # Value at Risk al 99% proyectado
    current_drawdown_pct: float = 0.0   # Drawdown actual de la cuenta
    max_correlation: float = 0.0        # Máxima correlación cruzada con posiciones vivas
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RiskManagerAgent:
    """
    Nodo de gobernanza y control de riesgo institucional.
    Audita la propuesta de VectorAlpha contra límites de VaR, Drawdown y Correlación.
    """

    def __init__(
        self,
        max_drawdown_limit_pct: float = 25.0,   # PB-25 Kill-Switch al -25%
        max_var_99_limit_pct: float = 5.0,      # VaR máximo tolerable por posición
        max_cross_correlation: float = 0.40,    # Límite estricto de multicolinealidad
        base_leverage_cap: float = 1.5          # Apalancamiento máximo permitido
    ):
        self.max_drawdown_limit_pct = float(max_drawdown_limit_pct)
        self.max_var_99_limit_pct = float(max_var_99_limit_pct)
        self.max_cross_correlation = float(max_cross_correlation)
        self.base_leverage_cap = float(base_leverage_cap)

    def evaluate_proposal(
        self,
        vector: Any,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> RiskVerdict:
        """
        Evalúa si la propuesta del DAG cumple los estándares de seguridad de capital.
        """
        # Si el orquestador no aprobó la señal, el gestor de riesgos no autoriza posición
        if vector.decision != "APPROVED" or vector.direction == 0:
            return RiskVerdict(
                decision="REJECTED",
                sizing_multiplier=0.0,
                reason=f"SIGNAL_NOT_APPROVED_BY_DAG: {vector.decision}"
            )

        state = portfolio_state or {}
        current_dd = float(state.get("current_drawdown_pct", 0.0))
        volatility_4h = float(state.get("volatility_4h", 0.03))  # 3% vol diaria/4h por defecto
        active_correlations = state.get("correlations", {})

        # 1. Chequeo del Kill-Switch de Equidad Total (PB-25)
        if current_dd >= self.max_drawdown_limit_pct:
            return RiskVerdict(
                decision="REJECTED",
                sizing_multiplier=0.0,
                reason=f"KILL_SWITCH_ACTIVE: Drawdown actual ({current_dd:.2f}%) supera límite ({self.max_drawdown_limit_pct:.2f}%)",
                current_drawdown_pct=current_dd
            )

        # 2. Cálculo de Value at Risk (VaR 99% Paramétrico: 2.33 * sigma)
        var_99 = 2.326 * volatility_4h * 100.0
        sizing_mult = 1.0

        if var_99 > self.max_var_99_limit_pct:
            # Escalamiento hacia abajo para contener el VaR
            sizing_mult = float(np.clip(self.max_var_99_limit_pct / var_99, 0.25, 0.75))

        # 3. Control de Correlación Cruzada (Evitar Concentración de Riesgo)
        max_corr = 0.0
        if active_correlations:
            max_corr = float(max(active_correlations.values()))
            if max_corr > self.max_cross_correlation:
                # Si la correlación es excesiva, reducir tamaño al 50%
                sizing_mult = min(sizing_mult, 0.50)

        # 4. Atenuación por Convicción del Vector
        if vector.confidence < 0.65:
            sizing_mult *= 0.75

        # Decisión final
        sizing_mult = float(np.round(np.clip(sizing_mult, 0.0, 1.0), 3))
        if sizing_mult <= 0.10:
            decision = "REJECTED"
            reason = "EXCESSIVE_RISK_SCALE_DOWN_BELOW_THRESHOLD"
        elif sizing_mult < 1.0:
            decision = "SCALED_DOWN"
            reason = f"POSITION_SCALED_TO_{sizing_mult*100:.1f}% (VaR: {var_99:.2f}%, Corr: {max_corr:.2f})"
        else:
            decision = "APPROVED"
            reason = "ALL_RISK_CHECKS_PASSED"

        return RiskVerdict(
            decision=decision,
            sizing_multiplier=sizing_mult,
            reason=reason,
            var_99_pct=float(np.round(var_99, 3)),
            current_drawdown_pct=float(np.round(current_dd, 2)),
            max_correlation=float(np.round(max_corr, 3)),
            metadata={
                "leverage_cap": self.base_leverage_cap,
                "volatility_used": volatility_4h
            }
        )
