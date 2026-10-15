"""
meme_hunter.data.trueblocks - Adaptador Local TrueBlocks / Driver IPC chifra (PB-182).
Permite indexación local de transacciones EVM, auditoría privada de smart contracts y rastreo de ballenas.
"""

import asyncio
import json
import logging
import shutil
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("TrueBlocksConnector")


class WalletAppearance(BaseModel):
    """Resumen de apariciones de una dirección en la cadena indexada localmente."""
    address: str
    appearance_count: int = Field(default=0, ge=0)
    first_block: Optional[int] = None
    last_block: Optional[int] = None
    is_local_indexed: bool = True


class WalletTransactionTrace(BaseModel):
    """Traza individual de transacción obtenida localmente sin llamadas a RPCs externos."""
    hash: str
    block_number: int
    from_address: str
    to_address: Optional[str] = None
    value_eth: float = 0.0
    gas_used: Optional[int] = None
    is_error: bool = False


class ContractAuditResult(BaseModel):
    """Diagnóstico forense privado de un contrato inteligente."""
    contract_address: str
    total_txs: int = Field(default=0, ge=0)
    creator_address: Optional[str] = None
    recent_whale_activity: bool = False
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="0.0 seguro, 1.0 alto riesgo")
    is_flagged: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
    indexer_source: str = Field(default="TrueBlocks-Local")


class TrueBlocksConnector:
    """Cliente no bloqueante para interactuar con el daemon local de TrueBlocks vía el CLI chifra."""

    def __init__(self, binary_name: str = "chifra", timeout: float = 15.0):
        self.binary_name = binary_name
        self.timeout = timeout
        self._is_available: Optional[bool] = None

    async def is_available(self) -> bool:
        """Verifica si el binario 'chifra' está instalado y responde en el PATH del sistema."""
        if self._is_available is not None:
            return self._is_available

        path = shutil.which(self.binary_name)
        if not path:
            self._is_available = False
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_name,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            self._is_available = proc.returncode == 0
        except Exception as e:
            logger.debug(f"TrueBlocks/chifra no responde: {e}")
            self._is_available = False

        return self._is_available

    async def _run_command(self, args: List[str]) -> Optional[Dict[str, Any]]:
        """Ejecuta un comando chifra con formato JSON y timeout estricto."""
        if not await self.is_available():
            logger.info("TrueBlocks (chifra) no disponible en hardware local. Entrando en fallback.")
            return None

        cmd = [self.binary_name] + args + ["--json"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            if proc.returncode != 0:
                logger.warning(f"Comando chifra falló con código {proc.returncode}: {stderr.decode()}")
                return None

            output_str = stdout.decode().strip()
            if not output_str:
                return {}
            return json.loads(output_str)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout ({self.timeout}s) ejecutando chifra: {' '.join(cmd)}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en TrueBlocksConnector: {e}")
            return None

    async def list_appearances(self, address: str) -> WalletAppearance:
        """Obtiene la cantidad de bloques en los que una dirección ha participado."""
        data = await self._run_command(["list", address])
        if not data:
            return WalletAppearance(address=address, appearance_count=0, is_local_indexed=False)

        records = data.get("data", [])
        count = len(records)
        first_block = records[0].get("blockNumber") if records else None
        last_block = records[-1].get("blockNumber") if records else None

        return WalletAppearance(
            address=address,
            appearance_count=count,
            first_block=first_block,
            last_block=last_block,
            is_local_indexed=True,
        )

    async def export_transactions(
        self, address: str, max_records: int = 50
    ) -> List[WalletTransactionTrace]:
        """Extrae el historial de transacciones sin enviar consultas a servicios de terceros."""
        data = await self._run_command(["export", address, f"--maxRecords={max_records}"])
        if not data:
            return []

        raw_txs = data.get("data", [])
        traces = []
        for t in raw_txs:
            traces.append(
                WalletTransactionTrace(
                    hash=t.get("hash", ""),
                    block_number=int(t.get("blockNumber", 0)),
                    from_address=t.get("from", ""),
                    to_address=t.get("to"),
                    value_eth=float(t.get("value", 0.0) or 0.0),
                    gas_used=int(t.get("gasUsed", 0)) if t.get("gasUsed") else None,
                    is_error=bool(t.get("isError", False)),
                )
            )
        return traces

    async def audit_contract(self, contract_address: str) -> ContractAuditResult:
        """Audita el contrato para evaluar riesgo y actividad de ballenas en el libro mayor local."""
        appearances = await self.list_appearances(contract_address)
        if not appearances.is_local_indexed:
            # Fallback heurístico si no hay nodo TrueBlocks local
            return ContractAuditResult(
                contract_address=contract_address,
                total_txs=0,
                risk_score=0.20,
                is_flagged=False,
                details={"status": "HEURISTIC_FALLBACK", "message": "Indexador local inactivo"},
                indexer_source="Fallback-Heuristic",
            )

        # Análisis forense básico de actividad
        risk_score = 0.0
        is_flagged = False
        reasons = []

        if appearances.appearance_count < 5:
            risk_score += 0.40
            reasons.append("Contrato extremadamente nuevo o con muy pocas transacciones indexadas.")

        if appearances.appearance_count > 10000:
            # Alta actividad, reduce riesgo de rugpull inmediato
            risk_score = max(0.0, risk_score - 0.20)

        return ContractAuditResult(
            contract_address=contract_address,
            total_txs=appearances.appearance_count,
            recent_whale_activity=appearances.appearance_count > 500,
            risk_score=min(1.0, risk_score),
            is_flagged=is_flagged,
            details={"reasons": reasons, "blocks_span": (appearances.last_block or 0) - (appearances.first_block or 0)},
            indexer_source="TrueBlocks-Local",
        )
