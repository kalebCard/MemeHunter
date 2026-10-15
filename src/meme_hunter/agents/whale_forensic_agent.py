"""
meme_hunter.agents.whale_forensic_agent - Agente Forense de Billeteras y Contratos con TrueBlocks (PB-187).
Rastrea carteras Smart Money en hardware propio e impone vetos preventivos anti-rugpull.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from meme_hunter.data.trueblocks import TrueBlocksConnector, ContractAuditResult

logger = logging.getLogger("WhaleForensicAgent")


class WhaleForensicSignal(BaseModel):
    """Veredicto forense on-chain emitido con máxima privacidad hacia el DAG."""
    contract_address: str
    is_safe: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    whale_accumulation_detected: bool = False
    veto_trade: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class WhaleForensicAgent:
    """Agente forense local para análisis de creadores de contratos y billeteras ballena."""

    def __init__(self, connector: Optional[TrueBlocksConnector] = None):
        self.connector = connector or TrueBlocksConnector()

    async def inspect_contract(self, contract_address: str) -> WhaleForensicSignal:
        """Audita el contrato localmente y determina si se activa un veto de salvaguarda."""
        audit = await self.connector.audit_contract(contract_address)

        if audit.is_flagged or audit.risk_score >= 0.70:
            return WhaleForensicSignal(
                contract_address=contract_address,
                is_safe=False,
                risk_score=audit.risk_score,
                whale_accumulation_detected=False,
                veto_trade=True,
                confidence=0.95,
                reason=f"VETO PREVENTIVO: Contrato clasificado como alto riesgo ({audit.risk_score:.2f}) en libro mayor local.",
            )

        if audit.recent_whale_activity:
            return WhaleForensicSignal(
                contract_address=contract_address,
                is_safe=True,
                risk_score=audit.risk_score,
                whale_accumulation_detected=True,
                veto_trade=False,
                confidence=0.85,
                reason="Acumulación activa de billeteras relevantes detectada en bloques recientes.",
            )

        return WhaleForensicSignal(
            contract_address=contract_address,
            is_safe=True,
            risk_score=audit.risk_score,
            whale_accumulation_detected=False,
            veto_trade=False,
            confidence=0.75,
            reason="Sin banderas de riesgo crítico en indexación local TrueBlocks.",
        )
