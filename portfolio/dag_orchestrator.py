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


@dataclass
class DAGNode:
    """
    Nodo formal de procesamiento dentro de la topología acíclica dirigida (DAG).
    """
    node_id: str
    agent: BaseSignalAgent
    dependencies: List[str] = field(default_factory=list)
    layer: str = "processing"   # 'input', 'processing', 'synthesis', 'risk'
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agent_type": self.agent.agent_type,
            "layer": self.layer,
            "dependencies": list(self.dependencies),
            "active": self.agent.active,
            "weight": self.agent.weight,
            "last_latency_ms": self.agent.last_latency_ms,
            "metadata": self.metadata
        }


class DAGSignalOrchestrator:
    """
    Enrutador central y orquestador en Grafo Acíclico Dirigido (DAG).
    Sintetiza las propuestas de múltiples agentes especializados aplicando Fusión Bayesiana
    y pesos condicionados por el régimen de mercado, evaluados a través de etapas topológicas.
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

        self._nodes: Dict[str, DAGNode] = {}
        self.last_vector_alpha: Optional[VectorAlpha] = None
        self.cycle_count: int = 0
        self.total_latency_ms: float = 0.0
        self._latencies: List[float] = []
        self._history: List[Dict[str, Any]] = []

    @property
    def _agents(self) -> Dict[str, BaseSignalAgent]:
        """Compatibilidad hacia atrás para componentes que acceden a self._agents."""
        return {nid: node.agent for nid, node in self._nodes.items()}

    # -------------------------------------------------------------------------
    # Gestión de Nodos y Topología del DAG
    # -------------------------------------------------------------------------
    def register_agent(
        self,
        agent: BaseSignalAgent,
        dependencies: Optional[List[str]] = None,
        layer: str = "processing"
    ) -> None:
        """Registra un agente con dependencias y capa topológica en el DAG."""
        deps = list(dependencies or [])
        node = DAGNode(
            node_id=agent.agent_id,
            agent=agent,
            dependencies=deps,
            layer=layer
        )
        self._nodes[agent.agent_id] = node

    def add_dependency(self, child_id: str, parent_id: str) -> None:
        """Añade una arista dirigida en el DAG: parent_id -> child_id."""
        if child_id not in self._nodes:
            raise KeyError(f"Nodo hijo '{child_id}' no encontrado en el DAG.")
        if parent_id not in self._nodes[child_id].dependencies:
            self._nodes[child_id].dependencies.append(parent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Elimina un agente y sus dependencias de la topología."""
        self._nodes.pop(agent_id, None)
        for node in self._nodes.values():
            if agent_id in node.dependencies:
                node.dependencies.remove(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseSignalAgent]:
        """Obtiene una referencia al agente por su ID."""
        node = self._nodes.get(agent_id)
        return node.agent if node else None

    def toggle_agent(self, agent_id: str, active: bool) -> bool:
        """Control HITL: Activa o pausa un agente individual en caliente."""
        if agent_id in self._nodes:
            self._nodes[agent_id].agent.toggle(active)
            return True
        return False

    def set_agent_weight(self, agent_id: str, weight: float) -> bool:
        """Ajusta el peso base de un agente."""
        if agent_id in self._nodes:
            self._nodes[agent_id].agent.set_weight(weight)
            return True
        return False

    def set_consensus_threshold(self, threshold: float) -> None:
        """Ajusta el umbral mínimo de consenso para aprobación de señales."""
        self.consensus_threshold = float(np.clip(threshold, 0.1, 1.0))

    def topological_sort(self) -> List[str]:
        """
        Calcula el orden de ejecución topológico mediante el Algoritmo de Kahn.
        Lanza ValueError si se detectan ciclos en la estructura del grafo.
        """
        nodes = self._nodes
        if not nodes:
            return []

        in_degree = {nid: 0 for nid in nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in nodes}

        for child_id, node in nodes.items():
            valid_deps = [dep for dep in node.dependencies if dep in nodes]
            in_degree[child_id] = len(valid_deps)
            for parent_id in valid_deps:
                adj[parent_id].append(child_id)

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_order: List[str] = []

        while queue:
            curr = queue.pop(0)
            sorted_order.append(curr)
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_order) != len(nodes):
            unresolved = [nid for nid, deg in in_degree.items() if deg > 0]
            raise ValueError(f"Ciclo detectado en la topología del DAG. Nodos no resueltos: {unresolved}")

        return sorted_order

    def get_execution_stages(self) -> List[List[str]]:
        """
        Calcula etapas ordenadas de ejecución (stages) para paralelismo o propagación secuencial.
        Cada etapa contiene nodos cuyas dependencias fueron computadas en etapas previas.
        """
        order = self.topological_sort()
        nodes = self._nodes
        if not nodes:
            return []

        node_levels: Dict[str, int] = {}
        for nid in order:
            deps = [d for d in nodes[nid].dependencies if d in nodes]
            if not deps:
                node_levels[nid] = 0
            else:
                node_levels[nid] = max(node_levels[d] for d in deps) + 1

        max_level = max(node_levels.values()) if node_levels else 0
        stages: List[List[str]] = [[] for _ in range(max_level + 1)]
        for nid in order:
            stages[node_levels[nid]].append(nid)

        return stages

    # -------------------------------------------------------------------------
    # Ciclo de Inferencia del DAG
    # -------------------------------------------------------------------------
    def run_inference_cycle(self, market_data: Any) -> VectorAlpha:
        """
        Ejecuta un ciclo completo de inferencia a través de las etapas del DAG.
        """
        t_start = time.perf_counter_ns()
        self.cycle_count += 1

        all_nodes = self._nodes

        if not all_nodes or not any(node.agent.active for node in all_nodes.values()):
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
                agent_proposals={nid: node.agent.evaluate(market_data).to_dict() for nid, node in all_nodes.items()},
                agent_weights={}
            )
            self._record_telemetry(vector, elapsed_ms)
            return vector

        # 1. Ejecución ordenada por etapas topológicas con inyección de upstream context
        stages = self.get_execution_stages()
        proposals: Dict[str, AgentProposal] = {}

        for stage in stages:
            for aid in stage:
                node = self._nodes[aid]
                agent = node.agent
                upstream_ctx = {dep: proposals[dep] for dep in node.dependencies if dep in proposals}
                proposals[aid] = agent.evaluate(market_data, upstream_proposals=upstream_ctx)

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

        # Generar aristas y orden de ejecución formal del DAG
        edges = []
        for nid, node in self._nodes.items():
            for dep in node.dependencies:
                if dep in self._nodes:
                    edges.append({"source": dep, "target": nid})

        try:
            topo_order = self.topological_sort()
            stages = self.get_execution_stages()
        except ValueError:
            topo_order = list(self._nodes.keys())
            stages = [list(self._nodes.keys())]

        return {
            "pipeline_status": "ACTIVE" if any(a.active for a in self._agents.values()) else "PAUSED",
            "synthesis_algorithm": self.synthesis_algorithm,
            "consensus_threshold": self.consensus_threshold,
            "cycle_count": self.cycle_count,
            "avg_latency_ms": float(np.round(avg_lat, 2)),
            "p99_latency_ms": float(np.round(p99, 2)),
            "nodes": nodes_status,
            "topology": {
                "nodes": {nid: node.to_dict() for nid, node in self._nodes.items()},
                "edges": edges,
                "execution_order": topo_order,
                "execution_stages": stages
            },
            "last_vector_alpha": self.last_vector_alpha.to_dict() if self.last_vector_alpha else None,
            "recent_history": self._history[-10:]
        }
