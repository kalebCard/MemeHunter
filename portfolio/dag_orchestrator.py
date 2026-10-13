"""
Meme Hunter - DAG Signal Router & Bayesian Fusion Orchestrator (PB-103)
Sprint 30: Núcleo central de decisión y enrutamiento en Grafo Acíclico Dirigido (DAG).
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import time
from typing import Dict, List, Optional, Any
import numpy as np

from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from portfolio.agents.regime_agent import RegimeHMMAgent


@dataclass
class VectorAlpha:
    """
    Vector consolidado resultante del ciclo de inferencia y fusión bayesiana del DAG.
    """
    direction: int                      # +1 (Long), -1 (Short), 0 (Neutral)
    composite_score: float              # [-1.0, 1.0] Magnitud de la señal consolidada
    confidence: float                   # [0.0, 1.0] Convicción agregada
    consensus_score: float              # [0.0, 1.0] Grado de alineación entre agentes
    inference_cycle_ms: float           # Tiempo total de ejecución del ciclo en ms
    decision: str                       # 'APPROVED', 'INSUFFICIENT_CONSENSUS', 'REGIME_VETO', 'DEGRADED', 'ALL_AGENTS_PAUSED'
    regime_state: str                   # Régimen activo que condicionó la decisión
    agent_proposals: Dict[str, Any] = field(default_factory=dict)
    agent_weights: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DAGSignalOrchestrator:
    """
    Enrutador central y orquestador en DAG.
    Sintetiza las propuestas de múltiples agentes especializados aplicando Fusión Bayesiana
    y pesos condicionados por el régimen de mercado, garantizando latencias < 20 ms.
    """

    def __init__(
        self,
        consensus_threshold: float = 0.68,
        synthesis_algorithm: str = "Bayesian Fusion",
        max_history_len: int = 50
    ):
        self.consensus_threshold = float(consensus_threshold)
        self.synthesis_algorithm = synthesis_algorithm
        self.max_history_len = max_history_len

        self._agents: Dict[str, BaseSignalAgent] = {}
        self.last_vector_alpha: Optional[VectorAlpha] = None
        self.cycle_count: int = 0
        self.total_latency_ms: float = 0.0
        self._latencies: List[float] = []
        self._history: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Gestión de Agentes (Registro, Toggle, Pesos)
    # -------------------------------------------------------------------------
    def register_agent(self, agent: BaseSignalAgent) -> None:
        """Registra un agente en la topología del DAG."""
        self._agents[agent.agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Elimina un agente de la topología."""
        self._agents.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> Optional[BaseSignalAgent]:
        """Obtiene una referencia al agente por su ID."""
        return self._agents.get(agent_id)

    def toggle_agent(self, agent_id: str, active: bool) -> bool:
        """Control HITL: Activa o pausa un agente individual en caliente."""
        if agent_id in self._agents:
            self._agents[agent_id].toggle(active)
            return True
        return False

    def set_agent_weight(self, agent_id: str, weight: float) -> bool:
        """Ajusta el peso base de un agente."""
        if agent_id in self._agents:
            self._agents[agent_id].set_weight(weight)
            return True
        return False

    def set_consensus_threshold(self, threshold: float) -> None:
        """Ajusta el umbral mínimo de consenso para aprobación de señales."""
        self.consensus_threshold = float(np.clip(threshold, 0.1, 1.0))

    # -------------------------------------------------------------------------
    # Ciclo de Inferencia del DAG
    # -------------------------------------------------------------------------
    def run_inference_cycle(self, market_data: Any) -> VectorAlpha:
        """
        Ejecuta un ciclo completo de inferencia a través de los nodos del DAG.
        """
        t_start = time.perf_counter_ns()
        self.cycle_count += 1

        all_agents = self._agents

        if not all_agents or not any(a.active for a in all_agents.values()):
            t_end = time.perf_counter_ns()
            elapsed_ms = (t_end - t_start) / 1_000_000.0
            vector = VectorAlpha(
                direction=0,
                composite_score=0.0,
                confidence=0.0,
                consensus_score=0.0,
                inference_cycle_ms=elapsed_ms,
                decision="ALL_AGENTS_PAUSED",
                regime_state="UNKNOWN",
                agent_proposals={aid: a.evaluate(market_data).to_dict() for aid, a in all_agents.items()},
                agent_weights={}
            )
            self._record_telemetry(vector, elapsed_ms)
            return vector

        # 1. Ejecución de Agentes (los inactivos devuelven status PAUSED_BY_OPERATOR)
        proposals: Dict[str, AgentProposal] = {}
        for aid, agent in all_agents.items():
            proposals[aid] = agent.evaluate(market_data)

        # 2. Extracción del Estado de Régimen
        regime_state = self._extract_regime_state(proposals)

        # 3. Fusión Bayesiana de Señales y Consenso
        vector = self._synthesize_bayesian_fusion(proposals, regime_state, t_start)

        # 4. Auditoría de Latencia y Telemetría
        t_end = time.perf_counter_ns()
        elapsed_ms = (t_end - t_start) / 1_000_000.0
        vector.inference_cycle_ms = elapsed_ms
        self._record_telemetry(vector, elapsed_ms)

        self.last_vector_alpha = vector
        return vector

    # -------------------------------------------------------------------------
    # Fusión Bayesiana Ponderada
    # -------------------------------------------------------------------------
    def _synthesize_bayesian_fusion(
        self,
        proposals: Dict[str, AgentProposal],
        regime_state: str,
        t_start_ns: int
    ) -> VectorAlpha:
        """
        Calcula la síntesis bayesiana con pesos condicionados por el régimen.
        """
        # Excluir agentes no direccionales o en error del cálculo del score direccional
        directional_proposals: Dict[str, AgentProposal] = {}
        effective_weights: Dict[str, float] = {}

        for aid, prop in proposals.items():
            agent = self._agents.get(aid)
            if not agent or not agent.active:
                continue

            base_w = agent.weight
            # Ajuste de peso condicionado por el régimen
            regime_mult = self._get_regime_multiplier(prop, regime_state)
            w = max(0.01, base_w * regime_mult)

            # Penalizar propuestas con error o confianza nula
            if prop.metadata.get("status") == "ERROR_FALLBACK" or prop.confidence <= 0.0:
                w *= 0.1

            directional_proposals[aid] = prop
            effective_weights[aid] = w

        sum_w = sum(effective_weights.values())
        if sum_w <= 0:
            sum_w = 1.0
        normalized_weights = {aid: float(w / sum_w) for aid, w in effective_weights.items()}

        # Cómputo del score compuesto ponderado: sum(w_i * raw_score_i)
        composite_score = float(sum(
            normalized_weights[aid] * prop.raw_score
            for aid, prop in directional_proposals.items()
        ))
        composite_score = float(np.clip(composite_score, -1.0, 1.0))

        # Cómputo de la convicción agregada
        aggregated_conf = float(sum(
            normalized_weights[aid] * prop.confidence
            for aid, prop in directional_proposals.items()
        ))
        aggregated_conf = float(np.clip(aggregated_conf, 0.0, 1.0))

        # Cómputo del consenso: alineación direccional ponderada
        # Grado en que los agentes apuntan en la misma dirección (+1, -1, 0)
        numerator = abs(sum(
            normalized_weights[aid] * prop.direction * prop.confidence
            for aid, prop in directional_proposals.items()
        ))
        denominator = sum(
            normalized_weights[aid] * prop.confidence
            for aid, prop in directional_proposals.items()
        )
        consensus_score = float(numerator / max(1e-6, denominator))
        consensus_score = float(np.clip(consensus_score, 0.0, 1.0))

        # Determinación de Decisión y Dirección Final
        if consensus_score < self.consensus_threshold:
            decision = "INSUFFICIENT_CONSENSUS"
            direction = 0
        else:
            if composite_score > 0.08:
                direction = 1
                decision = "APPROVED"
            elif composite_score < -0.08:
                direction = -1
                decision = "APPROVED"
            else:
                direction = 0
                decision = "APPROVED"

        # Veto estricto si el régimen es de pánico hostil o choque de volatilidad
        if regime_state == "CHOPPY_HIGH_VOLATILITY" and consensus_score < 0.85:
            decision = "REGIME_VETO"
            direction = 0

        serialized_proposals = {aid: p.to_dict() for aid, p in proposals.items()}

        return VectorAlpha(
            direction=direction,
            composite_score=float(np.round(composite_score, 4)),
            confidence=float(np.round(aggregated_conf, 4)),
            consensus_score=float(np.round(consensus_score, 4)),
            inference_cycle_ms=0.0,  # Se calcula al final del ciclo
            decision=decision,
            regime_state=regime_state,
            agent_proposals=serialized_proposals,
            agent_weights=normalized_weights,
            metadata={
                "algorithm": self.synthesis_algorithm,
                "consensus_threshold": self.consensus_threshold,
                "active_agents_count": len(directional_proposals)
            }
        )

    def _extract_regime_state(self, proposals: Dict[str, AgentProposal]) -> str:
        """Extrae el estado de régimen a partir de la propuesta del RegimeAgent."""
        for prop in proposals.values():
            if "detected_regime" in prop.metadata:
                return prop.metadata["detected_regime"]
        return "NEUTRAL_BALANCED"

    def _get_regime_multiplier(self, prop: AgentProposal, regime_state: str) -> float:
        """Modula la influencia del agente según la afinidad con el régimen actual."""
        if not prop.regime_compatibility:
            return 1.0
        return float(prop.regime_compatibility.get(regime_state, 1.0))

    def _record_telemetry(self, vector: VectorAlpha, elapsed_ms: float) -> None:
        """Registra métricas y latencia para telemetría continua."""
        self.total_latency_ms += elapsed_ms
        self._latencies.append(elapsed_ms)
        if len(self._latencies) > 200:
            self._latencies.pop(0)

        entry = {
            "cycle": self.cycle_count,
            "timestamp": vector.timestamp_utc,
            "direction": vector.direction,
            "decision": vector.decision,
            "consensus_score": vector.consensus_score,
            "composite_score": vector.composite_score,
            "latency_ms": elapsed_ms,
            "regime": vector.regime_state
        }
        self._history.append(entry)
        if len(self._history) > self.max_history_len:
            self._history.pop(0)

    # -------------------------------------------------------------------------
    # Métricas y Telemetría para API y Dashboard
    # -------------------------------------------------------------------------
    def get_telemetry(self) -> Dict[str, Any]:
        """Estructura completa de telemetría para el endpoint REST del Dashboard."""
        p99 = float(np.percentile(self._latencies, 99)) if self._latencies else 0.0
        avg_lat = float(np.mean(self._latencies)) if self._latencies else 0.0

        nodes_status = {}
        for aid, agent in self._agents.items():
            nodes_status[aid] = {
                "agent_id": aid,
                "type": agent.agent_type,
                "active": agent.active,
                "weight": agent.weight,
                "last_latency_ms": agent.last_latency_ms,
                "last_direction": agent.last_proposal.direction if agent.last_proposal else 0,
                "last_confidence": agent.last_proposal.confidence if agent.last_proposal else 0.0
            }

        return {
            "pipeline_status": "ACTIVE" if any(a.active for a in self._agents.values()) else "PAUSED",
            "synthesis_algorithm": self.synthesis_algorithm,
            "consensus_threshold": self.consensus_threshold,
            "cycle_count": self.cycle_count,
            "avg_latency_ms": float(np.round(avg_lat, 2)),
            "p99_latency_ms": float(np.round(p99, 2)),
            "nodes": nodes_status,
            "last_vector_alpha": self.last_vector_alpha.to_dict() if self.last_vector_alpha else None,
            "recent_history": self._history[-10:]
        }
