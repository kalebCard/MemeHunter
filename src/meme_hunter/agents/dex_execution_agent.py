"""
meme_hunter.agents.dex_execution_agent - Agente de Microestructura y Gatillos de Ejecución DEX (PB-185).
Analiza desbalance de flujo de órdenes (OFI) en swaps y liquidez concentrada vía The Graph.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from meme_hunter.data.thegraph import TheGraphConnector, PoolLiquiditySnapshot, DexSwapEvent

logger = logging.getLogger("DexExecutionAgent")


class DexTriggerSignal(BaseModel):
    """Señal emitida por el agente DEX hacia el sintetizador Bayesiano del DAG."""
    pool_id: str
    action: str = Field(description="BUY | SELL | HOLD")
    confidence: float = Field(ge=0.0, le=1.0)
    order_flow_imbalance: float = Field(default=0.0, description="OFI normalizado entre -1.0 y 1.0")
    projected_slippage_pct: float = Field(default=0.0, ge=0.0)
    reason: str


class DexExecutionAgent:
    """Agente especializado en análisis de liquidez granular en pools y ejecución táctica."""

    def __init__(self, connector: Optional[TheGraphConnector] = None):
        self.connector = connector or TheGraphConnector()

    @staticmethod
    def compute_order_flow_imbalance(swaps: List[DexSwapEvent]) -> float:
        """Calcula el Order Flow Imbalance (OFI) a partir de los swaps recientes."""
        if not swaps:
            return 0.0

        buy_vol = sum(s.amount_usd for s in swaps if s.amount0 < 0 or s.amount1 > 0)
        sell_vol = sum(s.amount_usd for s in swaps if s.amount0 > 0 or s.amount1 < 0)
        total_vol = buy_vol + sell_vol

        if total_vol <= 0:
            return 0.0

        return (buy_vol - sell_vol) / total_vol

    @staticmethod
    def estimate_slippage(tvl_usd: float, order_size_usd: float) -> float:
        """Estima el impacto en precio (slippage) basado en el tamaño relativo respecto al TVL."""
        if tvl_usd <= 0:
            return 100.0
        # Regla empírica basada en constant product / concentrated liquidity
        impact = (order_size_usd / (tvl_usd * 0.5)) * 100.0
        return max(0.0, min(100.0, impact))

    async def evaluate_pool(
        self, pool_id: str, order_size_usd: float = 1000.0
    ) -> DexTriggerSignal:
        """Evalúa un pool y genera una señal de compra/venta con estimación de impacto."""
        snapshot = await self.connector.get_pool_snapshot(pool_id)
        if not snapshot:
            return DexTriggerSignal(
                pool_id=pool_id,
                action="HOLD",
                confidence=0.0,
                order_flow_imbalance=0.0,
                projected_slippage_pct=0.0,
                reason="Pool no encontrado o error en subgraphs de The Graph",
            )

        swaps = await self.connector.get_recent_swaps(pool_id, limit=30)
        ofi = self.compute_order_flow_imbalance(swaps)
        slippage = self.estimate_slippage(snapshot.tvl_usd, order_size_usd)

        # Reglas institucionales de ejecución
        if slippage > 5.0:
            return DexTriggerSignal(
                pool_id=pool_id,
                action="HOLD",
                confidence=0.90,
                order_flow_imbalance=ofi,
                projected_slippage_pct=slippage,
                reason=f"Slippage prohibitivo ({slippage:.2f}% > 5.0%). Riesgo de front-running/sandwich.",
            )

        if ofi > 0.40 and snapshot.volume_24h_usd > 50000:
            confidence = min(0.95, 0.50 + ofi * 0.45)
            return DexTriggerSignal(
                pool_id=pool_id,
                action="BUY",
                confidence=confidence,
                order_flow_imbalance=ofi,
                projected_slippage_pct=slippage,
                reason=f"Presión compradora neta (OFI: {ofi:.2f}) con volumen sostenido (${snapshot.volume_24h_usd:,.0f}).",
            )
        elif ofi < -0.40:
            confidence = min(0.95, 0.50 + abs(ofi) * 0.45)
            return DexTriggerSignal(
                pool_id=pool_id,
                action="SELL",
                confidence=confidence,
                order_flow_imbalance=ofi,
                projected_slippage_pct=slippage,
                reason=f"Presión vendedora neta (OFI: {ofi:.2f}). Desacumulación activa en DEX.",
            )

        return DexTriggerSignal(
            pool_id=pool_id,
            action="HOLD",
            confidence=0.60,
            order_flow_imbalance=ofi,
            projected_slippage_pct=slippage,
            reason="Flujo de órdenes equilibrado; sin ventaja direccional clara.",
        )
