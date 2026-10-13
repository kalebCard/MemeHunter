"""
Meme Hunter - Base Signal Agent Interface & Proposal Schema (PB-105)
Sprint 30: Arquitectura Multi-Agente & Orquestación en Grafo (DAG).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import time
from typing import Dict, Any, Optional


@dataclass
class AgentProposal:
    """
    Estructura canónica de propuesta de señal emitida por cualquier agente del DAG.
    """
    agent_id: str
    direction: int                      # +1 (Long), -1 (Short), 0 (Neutral)
    confidence: float                   # [0.0, 1.0] Nivel de convicción estadística
    raw_score: float                    # [-1.0, 1.0] Magnitud de la señal continua
    regime_compatibility: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializa la propuesta a diccionario para telemetría y API."""
        return asdict(self)


class BaseSignalAgent(ABC):
    """
    Interfaz abstracta para agentes especializados del sistema Multi-Agente.
    """

    def __init__(self, agent_id: str, agent_type: str, weight: float = 1.0, active: bool = True):
        self.agent_id = agent_id
        self.agent_type = agent_type    # 'technical', 'regime', 'sentiment', 'risk'
        self.weight = weight            # Peso base en el ensamble bayesiano
        self.active = active            # Switch Human-in-the-Loop (HITL)
        self.last_latency_ms: float = 0.0
        self.last_proposal: Optional[AgentProposal] = None

    def toggle(self, active: bool) -> None:
        """Activa o pausa el agente en caliente sin reiniciar el sistema."""
        self.active = active

    def set_weight(self, weight: float) -> None:
        """Actualiza el peso relativo del agente."""
        self.weight = max(0.0, float(weight))

    def evaluate(self, market_data: Any) -> AgentProposal:
        """
        Ejecuta la evaluación del agente con medición precisa de latencia.
        """
        if not self.active:
            proposal = AgentProposal(
                agent_id=self.agent_id,
                direction=0,
                confidence=0.0,
                raw_score=0.0,
                metadata={"status": "PAUSED_BY_OPERATOR"},
                latency_ms=0.0
            )
            self.last_proposal = proposal
            return proposal

        t_start = time.perf_counter_ns()
        try:
            proposal = self._compute_proposal(market_data)
        except Exception as e:
            t_end = time.perf_counter_ns()
            elapsed_ms = (t_end - t_start) / 1_000_000.0
            proposal = AgentProposal(
                agent_id=self.agent_id,
                direction=0,
                confidence=0.0,
                raw_score=0.0,
                metadata={"error": str(e), "status": "ERROR_FALLBACK"},
                latency_ms=elapsed_ms
            )

        t_end = time.perf_counter_ns()
        proposal.latency_ms = (t_end - t_start) / 1_000_000.0
        self.last_latency_ms = proposal.latency_ms
        self.last_proposal = proposal
        return proposal

    @abstractmethod
    def _compute_proposal(self, market_data: Any) -> AgentProposal:
        """Lógica interna de cómputo que debe implementar cada agente concreto."""
        pass
