"""
meme_hunter.portfolio.order_router - Enrutador Inteligente de Órdenes y Microestructura.
Implementa la enmienda ADR-004.1: Adaptive Microstructure Order Routing for Exits.

Provee:
1. Enrutamiento adaptativo de salidas en 3 etapas (Maker Post-Only, Sliced TWAP, Hard Stop Market).
2. Integración nativa con MicrostructureSlippageEngine (Almgren-Chriss).
3. Auditoría y desglose de comisiones, deslizamiento efectivo e impacto de mercado.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import numpy as np

from meme_hunter.data.slippage_engine import MicrostructureSlippageEngine, ExecutionResult


class ExitUrgency(str, Enum):
    LOW = "LOW"             # Salida por reversión técnica leve o Take Profit gradual
    MEDIUM = "MEDIUM"       # Trailing Stop o quiebre de media móvil rápida
    EMERGENCY = "EMERGENCY" # Stop-loss estructural duro o anomalía adversarial crítica


class OrderExecutionStage(str, Enum):
    MAKER_POST_ONLY = "MAKER_POST_ONLY"
    SLICED_TWAP = "SLICED_TWAP"
    HARD_STOP_MARKET = "HARD_STOP_MARKET"


@dataclass
class SmartExitOrder:
    """Representación formal de una orden de salida gestionada por el SmartExitRouter."""
    symbol: str
    side: str                          # 'buy' (cierre de corto) o 'sell' (cierre de largo)
    requested_price: float
    total_size_usdt: float
    unrealized_pnl_pct: float
    urgency: ExitUrgency
    stage: OrderExecutionStage
    executed_price: float = 0.0
    effective_slippage_bps: float = 0.0
    total_fees_usdt: float = 0.0
    slippage_drag_usdt: float = 0.0
    slices_count: int = 1
    is_fully_filled: bool = True
    execution_notes: str = ""


class SmartExitRouter:
    """
    Enrutador inteligente de órdenes de salida para futuros de memecoins.
    Elimina el desangrado de capital por órdenes Market ciegas manteniendo
    la protección de airbag técnico.
    """

    def __init__(
        self,
        slippage_engine: Optional[MicrostructureSlippageEngine] = None,
        maker_timeout_seconds: float = 3.0,
        default_slices: int = 4,
        hard_stoploss_pct: float = -0.08
    ):
        self.slippage_engine = slippage_engine or MicrostructureSlippageEngine()
        self.maker_timeout = maker_timeout_seconds
        self.default_slices = max(2, default_slices)
        self.hard_stoploss_pct = hard_stoploss_pct

    def determine_stage(
        self,
        unrealized_pnl_pct: float,
        urgency: ExitUrgency,
        volatility: float = 0.02,
        rvol: float = 1.0
    ) -> OrderExecutionStage:
        """
        Determina la etapa óptima de ejecución según el nivel de pérdida y régimen de mercado.
        """
        if unrealized_pnl_pct <= self.hard_stoploss_pct or urgency == ExitUrgency.EMERGENCY:
            return OrderExecutionStage.HARD_STOP_MARKET

        if urgency == ExitUrgency.MEDIUM or rvol >= 3.0:
            return OrderExecutionStage.SLICED_TWAP

        return OrderExecutionStage.MAKER_POST_ONLY

    def route_exit(
        self,
        symbol: str,
        side: str,
        current_price: float,
        order_size_usdt: float,
        unrealized_pnl_pct: float,
        daily_volume_usdt: float,
        volatility: float = 0.02,
        rvol: float = 1.0,
        urgency: ExitUrgency = ExitUrgency.LOW,
        force_stage: Optional[OrderExecutionStage] = None
    ) -> SmartExitOrder:
        """
        Ejecuta el enrutamiento inteligente de la salida calculando precios efectivos y fricciones.
        """
        stage = force_stage or self.determine_stage(unrealized_pnl_pct, urgency, volatility, rvol)
        side = side.lower()

        # ETAPA 1: Maker Post-Only
        if stage == OrderExecutionStage.MAKER_POST_ONLY:
            maker_res = self.slippage_engine.simulate_order_execution(
                side=side,
                order_type='maker',
                price=current_price,
                order_size_usdt=order_size_usdt,
                daily_volume_usdt=daily_volume_usdt,
                volatility=volatility,
                rvol=rvol
            )

            if maker_res.is_filled:
                return SmartExitOrder(
                    symbol=symbol,
                    side=side,
                    requested_price=current_price,
                    total_size_usdt=order_size_usdt,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    urgency=urgency,
                    stage=OrderExecutionStage.MAKER_POST_ONLY,
                    executed_price=maker_res.executed_price,
                    effective_slippage_bps=0.0,
                    total_fees_usdt=maker_res.liquidity_cost_usdt,
                    slippage_drag_usdt=0.0,
                    slices_count=1,
                    is_fully_filled=True,
                    execution_notes="Ejecutado al precio límite como Maker (Rebate/0.02% fee, 0 bps slippage)."
                )
            else:
                stage = OrderExecutionStage.SLICED_TWAP

        # ETAPA 2: Sliced TWAP
        if stage == OrderExecutionStage.SLICED_TWAP:
            n_slices = self.default_slices
            slice_size_usdt = order_size_usdt / n_slices
            total_fee = 0.0
            total_slippage_drag = 0.0
            executed_prices = []

            for _ in range(n_slices):
                slice_res = self.slippage_engine.simulate_order_execution(
                    side=side,
                    order_type='market',
                    price=current_price,
                    order_size_usdt=slice_size_usdt,
                    daily_volume_usdt=daily_volume_usdt,
                    volatility=volatility,
                    rvol=rvol
                )
                executed_prices.append(slice_res.executed_price)
                total_fee += slice_size_usdt * self.slippage_engine.taker_fee
                slice_slippage_cost = slice_size_usdt * (slice_res.slippage_bps / 10_000.0)
                total_slippage_drag += slice_slippage_cost

            avg_price = float(np.mean(executed_prices))
            effective_slip_bps = float(abs(avg_price - current_price) / current_price * 10_000.0)

            return SmartExitOrder(
                symbol=symbol,
                side=side,
                requested_price=current_price,
                total_size_usdt=order_size_usdt,
                unrealized_pnl_pct=unrealized_pnl_pct,
                urgency=urgency,
                stage=OrderExecutionStage.SLICED_TWAP,
                executed_price=avg_price,
                effective_slippage_bps=effective_slip_bps,
                total_fees_usdt=total_fee,
                slippage_drag_usdt=total_slippage_drag,
                slices_count=n_slices,
                is_fully_filled=True,
                execution_notes=f"Ejecutado con TWAP fraccionado ({n_slices} micro-órdenes). Impacto minimizado."
            )

        # ETAPA 3: Hard Stop Emergency Market Order
        market_res = self.slippage_engine.simulate_order_execution(
            side=side,
            order_type='market',
            price=current_price,
            order_size_usdt=order_size_usdt,
            daily_volume_usdt=daily_volume_usdt,
            volatility=volatility,
            rvol=rvol,
            is_breakdown_candle=True
        )
        total_fee = order_size_usdt * self.slippage_engine.taker_fee
        slippage_drag = order_size_usdt * (market_res.slippage_bps / 10_000.0)

        return SmartExitOrder(
            symbol=symbol,
            side=side,
            requested_price=current_price,
            total_size_usdt=order_size_usdt,
            unrealized_pnl_pct=unrealized_pnl_pct,
            urgency=urgency,
            stage=OrderExecutionStage.HARD_STOP_MARKET,
            executed_price=market_res.executed_price,
            effective_slippage_bps=market_res.slippage_bps,
            total_fees_usdt=total_fee,
            slippage_drag_usdt=slippage_drag,
            slices_count=1,
            is_fully_filled=True,
            execution_notes="Circuito de emergencia activado (Hard Stoploss a mercado para proteger capital)."
        )


__all__ = [
    "ExitUrgency",
    "OrderExecutionStage",
    "SmartExitOrder",
    "SmartExitRouter",
]
