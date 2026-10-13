"""
portfolio/agent_bias_daemon.py - Demonio de Evaluación Periódica del Cerebro Lento (Sprint 37: PB-123).
Ejecuta la inferencia de baja frecuencia a través del DAGSignalOrchestrator en intervalos
configurables (4h, 12h, 24h), emitiendo directivas JSON estructuradas hacia BiasStore.
El agente NUNCA coloca órdenes en el exchange.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import logging
import time

from portfolio.dag_orchestrator import DAGSignalOrchestrator, VectorAlpha
from portfolio.bias_store import BiasStore
from validation.schemas import MarketBiasSchema, MarketBiasPosture

logger = logging.getLogger("AgentBiasDaemon")


class AgentBiasDaemon:
    """
    Controlador del Cerebro Lento.
    Sintetiza la macroestructura y sentimiento sin intervenir en el tiempo real,
    emitiendo permisos temporales que el Cerebro Rápido consulta antes de disparar.
    """

    def __init__(
        self,
        orchestrator: Optional[DAGSignalOrchestrator] = None,
        bias_store: Optional[BiasStore] = None,
        default_validity_hours: float = 4.0,
        min_confidence_to_authorize: float = 0.65
    ):
        self.orchestrator = orchestrator or DAGSignalOrchestrator()
        self.bias_store = bias_store or BiasStore()
        self.validity_hours = float(default_validity_hours)
        self.min_confidence = float(min_confidence_to_authorize)

    def evaluate_symbol(
        self,
        symbol: str,
        market_data: Any,
        validity_hours: Optional[float] = None,
        allowed_setups: Optional[List[str]] = None,
        max_leverage: float = 1.0
    ) -> MarketBiasSchema:
        """
        Ejecuta un ciclo de inferencia multi-agente en DAG para un símbolo
        y persiste la directiva resultante en el almacén de sesgos.
        """
        val_hours = validity_hours if validity_hours is not None else self.validity_hours
        now = datetime.now(timezone.utc)
        valid_until = now + timedelta(hours=val_hours)

        # 1. Ciclo de inferencia en el DAG
        vector_alpha: VectorAlpha = self.orchestrator.run_inference_cycle(market_data)

        # 2. Mapeo determinista de VectorAlpha a Postura Directiva
        posture = MarketBiasPosture.NEUTRAL_HOLD

        if vector_alpha.decision == "REGIME_VETO":
            posture = MarketBiasPosture.STRICT_VETO
        elif vector_alpha.decision == "APPROVED":
            if vector_alpha.direction == 1 and vector_alpha.confidence >= self.min_confidence:
                posture = MarketBiasPosture.ALLOW_LONG
            elif vector_alpha.direction == -1 and vector_alpha.confidence >= self.min_confidence:
                posture = MarketBiasPosture.ALLOW_SHORT
            else:
                posture = MarketBiasPosture.NEUTRAL_HOLD
        else:
            posture = MarketBiasPosture.NEUTRAL_HOLD

        setups = allowed_setups or [
            "spot_confirmed_capitulation",
            "spot_confirmed_wick_reversal",
            "spot_elastic_rebound"
        ]

        # 3. Construcción del contrato Pydantic inmutable
        bias = MarketBiasSchema(
            symbol=symbol.upper(),
            posture=posture,
            confidence=float(round(vector_alpha.confidence, 4)),
            consensus_score=float(round(vector_alpha.consensus_score, 4)),
            regime_detected=vector_alpha.regime_state,
            valid_until_utc=valid_until.isoformat(),
            max_leverage=float(max_leverage),
            allowed_setups=setups,
            metadata={
                "decision": vector_alpha.decision,
                "composite_score": vector_alpha.composite_score,
                "inference_cycle_ms": vector_alpha.inference_cycle_ms,
                "cycle_count": self.orchestrator.cycle_count
            }
        )

        # 4. Persistencia atómica
        self.bias_store.save_bias(bias)
        return bias

    def evaluate_universe(
        self,
        market_data_by_symbol: Dict[str, Any],
        validity_hours: Optional[float] = None
    ) -> Dict[str, MarketBiasSchema]:
        """Evalúa un universo completo de símbolos y actualiza sus autorizaciones."""
        results: Dict[str, MarketBiasSchema] = {}
        for symbol, data in market_data_by_symbol.items():
            results[symbol] = self.evaluate_symbol(
                symbol=symbol,
                market_data=data,
                validity_hours=validity_hours
            )
        return results

    def run_once(self, sample_data_dict: Dict[str, Any]) -> Dict[str, MarketBiasSchema]:
        """Ejecuta una ronda de evaluación para integración o tests."""
        logger.info(f"🔄 Iniciando ciclo puntual de evaluación para {len(sample_data_dict)} activos...")
        return self.evaluate_universe(sample_data_dict)
