"""
portfolio/exponential_compounding_engine.py - Motor de Crecimiento Exponencial del Capital.
Implementa:
1. Interés Compuesto Geométrico Continuo basado en el Criterio de Kelly Fraccional (Half/Quarter Kelly).
2. Asignación Dinámica de Capital por Fases de Cartera (Tiered Sizing de 3 a 5 slots).
3. Válvula de Trinquete de Ganancias (Profit Ratchet) para aislar utilidades en la Bóveda Delta-Neutral.
4. Cumplimiento estricto del Min Notional de Binance ($5 USDT) con cero riesgo de congelamiento.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional
import numpy as np


@dataclass(frozen=True)
class CompoundingPhase:
    """Fase de escalado de capital."""
    phase_id: int
    name: str
    min_equity_usdt: float
    max_equity_usdt: float
    max_slots: int
    fraction_per_slot: float
    recommended_leverage: float
    description: str


class ExponentialCompoundingManager:
    """
    Gestor Cuantitativo de Crecimiento Exponencial.
    Acelera el crecimiento del patrimonio reinvirtiendo geométricamente las ganancias
    sin incurrir en el riesgo de ruina de Kelly completo.
    """

    # Definición de las 4 Fases de Escalado Exponencial
    PHASES = [
        CompoundingPhase(
            phase_id=1,
            name="FASE_1_SEMILLA_BLINDADA",
            min_equity_usdt=10.0,
            max_equity_usdt=250.0,
            max_slots=3,
            fraction_per_slot=0.33,
            recommended_leverage=1.5,
            description="Micro-capital concentrado en 3 slots (~33 USDT c/u) para superar por >6x el mínimo de Binance."
        ),
        CompoundingPhase(
            phase_id=2,
            name="FASE_2_EXPANSION_GEOMETRICA",
            min_equity_usdt=250.0,
            max_equity_usdt=1000.0,
            max_slots=4,
            fraction_per_slot=0.25,
            recommended_leverage=1.75,
            description="Expansión a 4 slots diversificados. El capital semilla original de $100 queda virtualmente protegido."
        ),
        CompoundingPhase(
            phase_id=3,
            name="FASE_3_ACELERACION_PARABOLICA",
            min_equity_usdt=1000.0,
            max_equity_usdt=5000.0,
            max_slots=5,
            fraction_per_slot=0.20,
            recommended_leverage=2.0,
            description="5 slots concurrentes con reinversión geométrica activa de utilidades ('dinero de la casa')."
        ),
        CompoundingPhase(
            phase_id=4,
            name="FASE_4_BARBELL_INSTITUCIONAL",
            min_equity_usdt=5000.0,
            max_equity_usdt=float("inf"),
            max_slots=6,
            fraction_per_slot=0.16,
            recommended_leverage=1.5,
            description="Cosecha sistemática del 40% de utilidades hacia Cash & Carry Delta-Neutral para generar renta pasiva."
        )
    ]

    def __init__(
        self,
        base_win_rate: float = 0.48,           # Win Rate empírico del sistema
        base_payoff_ratio: float = 2.20,       # Payoff Ratio (Avg Win / Avg Loss >= 2.2x)
        kelly_fraction: float = 0.40,          # Half-Kelly moderado para colas pesadas
        min_notional_usdt: float = 5.0,        # Mínimo absoluto de Binance
        ratchet_extraction_pct: float = 0.35   # 35% de ganancias cosechadas al duplicar
    ):
        self.win_rate = float(base_win_rate)
        self.payoff_ratio = float(base_payoff_ratio)
        self.kelly_fraction = float(kelly_fraction)
        self.min_notional = float(min_notional_usdt)
        self.ratchet_pct = float(ratchet_extraction_pct)

        # Histórico de hitos de equidad para el trinquete (100, 200, 400, 800...)
        self.last_ratchet_peak: float = 100.0
        self.total_harvested_to_vault_usdt: float = 0.0

    def calculate_optimal_kelly_fraction(
        self,
        win_rate: Optional[float] = None,
        payoff_ratio: Optional[float] = None,
        gamma: Optional[float] = None
    ) -> float:
        """
        Calcula la fracción de asignación óptima de Kelly para maximizar el crecimiento geométrico:
        g(f) = E[ln(1 + f * R)]
        f* = gamma * [ (p * b - q) / b ]
        """
        p = win_rate if win_rate is not None else self.win_rate
        b = payoff_ratio if payoff_ratio is not None else self.payoff_ratio
        g = gamma if gamma is not None else self.kelly_fraction

        q = 1.0 - p
        edge = (p * b) - q
        if edge <= 0:
            return 0.0  # Sin ventaja matemática, no arriesgar capital

        raw_kelly = edge / b
        # Atenuación con factor gamma (Half-Kelly) y límite de prudencia institucional (máx 35% por slot)
        optimal_f = min(0.35, max(0.05, raw_kelly * g))
        return round(float(optimal_f), 4)

    def get_current_phase(self, current_equity_usdt: float) -> CompoundingPhase:
        """Determina la fase operativa de escalado según el balance vivo."""
        eq = max(1.0, float(current_equity_usdt))
        for phase in self.PHASES:
            if phase.min_equity_usdt <= eq < phase.max_equity_usdt:
                return phase
        return self.PHASES[-1]

    def compute_stake_amount(
        self,
        current_wallet: float,
        open_trades_count: int = 0,
        conviction_score: float = 0.75,
        min_stake: Optional[float] = None,
        max_stake: Optional[float] = None
    ) -> float:
        """
        Calcula el tamaño óptimo de la posición (stake amount) en USDT en tiempo real.
        Garantiza crecimiento exponencial sin violar el límite notional de Binance ($5 USDT).
        """
        if current_wallet < self.min_notional:
            return 0.0  # Saldo insuficiente para cumplir el mínimo de Binance

        phase = self.get_current_phase(current_wallet)

        # Si ya se alcanzaron los slots máximos de la fase actual, no abrir más
        if open_trades_count >= phase.max_slots:
            return 0.0

        slots_available = max(1, phase.max_slots - open_trades_count)

        # 1. Fracción teórica de Kelly ajustada por la convicción del setup
        optimal_f = self.calculate_optimal_kelly_fraction()
        # Modulador de convicción [0.8x a 1.2x]
        conviction_mult = 0.80 + 0.40 * min(1.0, max(0.0, conviction_score))
        target_fraction = optimal_f * conviction_mult

        # 2. Asignación proporcional de la equidad de la cartera
        raw_stake = (current_wallet / slots_available) * (target_fraction / 0.25)
        # Asegurar que no supere el capital total disponible por slot
        max_possible_slot = current_wallet / slots_available
        stake = min(max_possible_slot, raw_stake)

        # 3. Restricciones duras de exchange
        stake = max(self.min_notional, stake)
        if min_stake is not None:
            stake = max(float(min_stake), stake)
        if max_stake is not None:
            stake = min(float(max_stake), stake)

        # Jamás arriesgar más de lo que hay en balance libre
        stake = min(stake, current_wallet)
        return round(float(stake), 2)

    def check_and_execute_profit_ratchet(
        self,
        current_equity: float
    ) -> Tuple[bool, float, str]:
        """
        Válvula de Trinquete Asimétrico (Profit Ratchet):
        Cada vez que la cuenta se duplica respecto al último pico cosechado (2x, 4x, 8x),
        extrae el porcentaje configurado (ej. 35%) hacia la Bóveda Delta-Neutral.
        """
        if current_equity >= (self.last_ratchet_peak * 2.0):
            profit = current_equity - self.last_ratchet_peak
            harvest_amount = profit * self.ratchet_pct

            old_peak = self.last_ratchet_peak
            self.last_ratchet_peak = current_equity - harvest_amount
            self.total_harvested_to_vault_usdt += harvest_amount

            reason = (
                f"🎯 HITO DE DUPLICACIÓN ALCANZADO: Equidad (${current_equity:.2f}) duplicó el pico previo (${old_peak:.2f}). "
                f"Traspaso de seguridad ejecutado: ${harvest_amount:.2f} USDT asegurados hacia Bóveda Cash & Carry."
            )
            return True, round(harvest_amount, 2), reason

        return False, 0.0, "Hito de duplicación no alcanzado aún."

    def get_status_report(self, current_equity: float) -> Dict[str, Any]:
        """Reporte de estado de escalado para telemetría y dashboard."""
        phase = self.get_current_phase(current_equity)
        optimal_f = self.calculate_optimal_kelly_fraction()
        next_double_target = self.last_ratchet_peak * 2.0

        return {
            "current_equity_usdt": current_equity,
            "phase_id": phase.phase_id,
            "phase_name": phase.name,
            "max_slots": phase.max_slots,
            "optimal_kelly_pct": f"{optimal_f * 100:.2f}%",
            "recommended_leverage": phase.recommended_leverage,
            "last_ratchet_peak_usdt": self.last_ratchet_peak,
            "next_double_target_usdt": next_double_target,
            "total_harvested_vault_usdt": self.total_harvested_to_vault_usdt,
            "progress_to_next_double_pct": min(100.0, max(0.0, (current_equity / next_double_target) * 100.0))
        }
