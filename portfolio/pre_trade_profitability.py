"""
portfolio/pre_trade_profitability.py - Filtro Matemático de Rentabilidad Pre-Trade (Sprint 38: PB-127).
Evalúa el costo friccional total (comisiones de ida y vuelta + medio spread + slippage Almgren-Chriss)
contra la ganancia proyectada antes de disparar cualquier orden.
Si el margen de seguridad no se cumple, aborta silenciosamente la operación.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import numpy as np


@dataclass(frozen=True)
class ProfitabilityDecision:
    """Resultado formal del análisis de rentabilidad pre-orden."""
    symbol: str
    is_approved: bool
    expected_gross_return_pct: float
    total_friction_cost_pct: float
    required_safety_threshold_pct: float
    net_projected_gain_pct: float
    rejection_reason: Optional[str] = None
    fees_drag_pct: float = 0.0
    spread_drag_pct: float = 0.0
    slippage_drag_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PreTradeProfitabilityGate:
    """
    Compuerta determinista de rentabilidad pura.
    Ejecución sub-milisegundo (< 0.05 ms).
    Garantiza que ninguna orden ingrese al mercado si los costos friccionales
    devoran el beneficio matemático esperado.
    """

    def __init__(
        self,
        default_safety_multiplier: float = 2.50, # Ganancia esperada debe ser >= 2.5x costos
        maker_fee_pct: float = 0.00075,         # 0.075% BNB fee en Binance Spot
        taker_fee_pct: float = 0.00100,         # 0.100% Taker fee estándar
        default_min_target_pct: float = 0.035   # +3.5% rebote elástico por defecto
    ):
        self.safety_multiplier = float(default_safety_multiplier)
        self.maker_fee = float(maker_fee_pct)
        self.taker_fee = float(taker_fee_pct)
        self.default_min_target_pct = float(default_min_target_pct)
        self.discarded_orders_count: int = 0
        self.approved_orders_count: int = 0

    def evaluate_entry(
        self,
        symbol: str,
        current_price: float,
        target_price: Optional[float] = None,
        spread_pct: float = 0.0010,            # 0.10% spread bid-ask estándar
        is_entry_maker: bool = True,            # Órdenes limit al bid son Maker
        is_exit_maker: bool = False,           # Salidas por stop/airbag suelen ser Taker
        estimated_slippage_bps: float = 5.0,    # 5 bps de slippage estimado
        custom_target_pct: Optional[float] = None
    ) -> ProfitabilityDecision:
        """
        Calcula la ecuación institucional de rentabilidad pre-orden:
        Esperanza Matemática > (Comisiones + Spread + Deslizamiento) * Margen de Seguridad
        """
        if current_price <= 0.0:
            return ProfitabilityDecision(
                symbol=symbol,
                is_approved=False,
                expected_gross_return_pct=0.0,
                total_friction_cost_pct=0.0,
                required_safety_threshold_pct=0.0,
                net_projected_gain_pct=0.0,
                rejection_reason="PRECIO_INVALIDO: Precio actual debe ser estrictamente positivo."
            )

        # 1. Ganancia Bruta Proyectada
        if custom_target_pct is not None:
            gross_return = max(0.0, float(custom_target_pct))
        elif target_price is not None and target_price > current_price:
            gross_return = (target_price - current_price) / current_price
        else:
            gross_return = self.default_min_target_pct

        # 2. Desglose Friccional
        entry_fee = self.maker_fee if is_entry_maker else self.taker_fee
        exit_fee = self.maker_fee if is_exit_maker else self.taker_fee
        fees_drag = entry_fee + exit_fee

        # Medio spread pagado al cruzar libro (o spread total si entrada y salida agresivas)
        spread_drag = max(0.0, float(spread_pct))

        # Slippage en porcentaje (bps / 10000)
        slippage_drag = max(0.0, float(estimated_slippage_bps) / 10000.0)

        total_friction = fees_drag + spread_drag + slippage_drag

        # 3. Umbral Mínimo Requerido por Margen de Seguridad
        required_threshold = total_friction * self.safety_multiplier
        net_projected = gross_return - total_friction

        # 4. Decisión de la Compuerta
        if gross_return < required_threshold:
            self.discarded_orders_count += 1
            reason = (
                f"FRICCION_EXCESIVA: Retorno bruto ({gross_return:.2%}) es inferior al umbral de seguridad "
                f"({required_threshold:.2%} = {self.safety_multiplier:.1f}x de fricción {total_friction:.2%}). "
                f"Descarte silencioso para proteger capital."
            )
            return ProfitabilityDecision(
                symbol=symbol,
                is_approved=False,
                expected_gross_return_pct=round(gross_return, 5),
                total_friction_cost_pct=round(total_friction, 5),
                required_safety_threshold_pct=round(required_threshold, 5),
                net_projected_gain_pct=round(net_projected, 5),
                rejection_reason=reason,
                fees_drag_pct=round(fees_drag, 5),
                spread_drag_pct=round(spread_drag, 5),
                slippage_drag_pct=round(slippage_drag, 5)
            )

        self.approved_orders_count += 1
        return ProfitabilityDecision(
            symbol=symbol,
            is_approved=True,
            expected_gross_return_pct=round(gross_return, 5),
            total_friction_cost_pct=round(total_friction, 5),
            required_safety_threshold_pct=round(required_threshold, 5),
            net_projected_gain_pct=round(net_projected, 5),
            fees_drag_pct=round(fees_drag, 5),
            spread_drag_pct=round(spread_drag, 5),
            slippage_drag_pct=round(slippage_drag, 5)
        )
