"""
meme_hunter.agents.macro_risk_agent - Agente de Régimen y Riesgo Macro con DeFiLlama (PB-186).
Modula dinámicamente el apalancamiento permitido y el tamaño de posiciones según la liquidez global.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from meme_hunter.data.defillama import DeFiLlamaConnector, MacroRegimeSnapshot

logger = logging.getLogger("MacroRegimeRiskAgent")


class MacroRiskSignal(BaseModel):
    """Veredicto de riesgo macroeconómico inyectado al orquestador DAG."""
    regime: str = Field(description="EXPANSION | CONTRACTION | NEUTRAL")
    risk_multiplier: float = Field(ge=0.0, le=2.0)
    max_recommended_leverage: float = Field(ge=0.0, le=3.0)
    allow_long_entries: bool = True
    allow_short_entries: bool = True
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class MacroRegimeRiskAgent:
    """Agente guardián de régimen de liquidez macroeconómica basado en DeFiLlama."""

    def __init__(self, connector: Optional[DeFiLlamaConnector] = None):
        self.connector = connector or DeFiLlamaConnector()

    async def evaluate_risk(self) -> MacroRiskSignal:
        """Determina los límites de apalancamiento y asignación de capital del sistema."""
        macro = await self.connector.get_macro_regime_metrics()

        if macro.regime == "EXPANSION":
            return MacroRiskSignal(
                regime="EXPANSION",
                risk_multiplier=1.25,
                max_recommended_leverage=1.5,
                allow_long_entries=True,
                allow_short_entries=False,
                confidence=0.85,
                reason=f"Expansión de liquidez global (+{macro.average_1d_delta:.1f}% 24h). Mercado receptivo a pumps.",
            )
        elif macro.regime == "CONTRACTION":
            return MacroRiskSignal(
                regime="CONTRACTION",
                risk_multiplier=0.50,
                max_recommended_leverage=1.0,
                allow_long_entries=False,
                allow_short_entries=True,
                confidence=0.90,
                reason=f"Fuga neta de TVL ({macro.average_1d_delta:.1f}% 24h). Salvaguarda activa: bloqueo de longs agresivos.",
            )

        return MacroRiskSignal(
            regime="NEUTRAL",
            risk_multiplier=1.0,
            max_recommended_leverage=1.2,
            allow_long_entries=True,
            allow_short_entries=True,
            confidence=0.70,
            reason="Flujo de liquidez macro neutral o sin tendencia dominante definida.",
        )
