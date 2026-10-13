"""
meme_hunter.api.routers.dag - Endpoints del Orquestador DAG y Estado Multi-Agente.
"""

from typing import Any, Dict, List
from fastapi import APIRouter
from meme_hunter.core.config import get_settings
from meme_hunter.storage.repositories import MarketBiasRepository

router = APIRouter(prefix="/api/dag", tags=["DAG Multi-Agent"])


@router.get("/status")
def get_dag_status() -> Dict[str, Any]:
    """Retorna la topología y estado activo de los nodos del DAG multi-agente."""
    return {
        "is_active": True,
        "topology": {
            "ingestion_nodes": ["LiveMarketFeed", "DollarBarsGenerator"],
            "feature_nodes": ["FractionalDiff", "OrderFlowImbalance", "RegimeHMM"],
            "agent_nodes": ["TechnicalAgent", "SentimentAgent", "RiskManagerAgent"],
            "fusion_nodes": ["BayesianConditionalSynthesizer"],
        },
        "consensus_threshold": 0.68,
        "max_latency_ms": 20.0,
    }


@router.get("/biases")
def get_active_biases() -> List[Dict[str, Any]]:
    """Retorna los sesgos de mercado activos computados por el DAG en SQLite WAL."""
    settings = get_settings()
    repo = MarketBiasRepository(settings.DB_PATH)
    return repo.get_all_active()
