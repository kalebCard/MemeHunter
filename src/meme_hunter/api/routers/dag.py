"""
meme_hunter.api.routers.dag - Endpoints del Orquestador DAG y Estado Multi-Agente (PB-183).
Integra nodos de ingestión on-chain (The Graph, DeFiLlama, TrueBlocks) y persistencia en SQLite WAL.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from meme_hunter.core.config import get_settings
from meme_hunter.storage.repositories import MarketBiasRepository, OnChainDataRepository
from meme_hunter.data.thegraph import TheGraphConnector, PoolLiquiditySnapshot
from meme_hunter.data.defillama import DeFiLlamaConnector, MacroRegimeSnapshot
from meme_hunter.data.trueblocks import TrueBlocksConnector, ContractAuditResult

router = APIRouter(prefix="/api/dag", tags=["DAG Multi-Agent"])


class IngestTheGraphRequest(BaseModel):
    pool_id: str = Field(description="Dirección del pool DEX a consultar en The Graph")
    custom_subgraph_url: Optional[str] = None


class IngestDeFiLlamaRequest(BaseModel):
    chain_name: Optional[str] = Field(default=None, description="Cadena específica o None para régimen global")


class IngestTrueBlocksRequest(BaseModel):
    address: str = Field(description="Dirección de billetera o contrato inteligente a auditar")


@router.get("/status")
def get_dag_status() -> Dict[str, Any]:
    """Retorna la topología canónica y estado activo de los nodos del DAG multi-agente."""
    return {
        "is_active": True,
        "topology": {
            "ingestion_nodes": [
                "LiveMarketFeed",
                "DollarBarsGenerator",
                "TheGraphIngestor",
                "DeFiLlamaIngestor",
                "TrueBlocksIngestor",
            ],
            "feature_nodes": [
                "FractionalDiff",
                "OrderFlowImbalance",
                "RegimeHMM",
                "OnChainLiquidityDelta",
            ],
            "agent_nodes": [
                "TechnicalAgent",
                "SentimentAgent",
                "RiskManagerAgent",
                "DexExecutionAgent",
                "MacroRegimeRiskAgent",
                "WhaleForensicAgent",
            ],
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


@router.post("/ingest/thegraph", response_model=Dict[str, Any])
async def ingest_thegraph(req: IngestTheGraphRequest) -> Dict[str, Any]:
    """Nodo de Ingestión: Consulta The Graph para un pool DEX y persiste el snapshot en SQLite WAL."""
    connector = TheGraphConnector(subgraph_url=req.custom_subgraph_url)
    snapshot = await connector.get_pool_snapshot(req.pool_id)
    if not snapshot:
        raise HTTPException(
            status_code=404, detail=f"No se pudo extraer snapshot para el pool {req.pool_id}"
        )

    settings = get_settings()
    repo = OnChainDataRepository(settings.DB_PATH)
    metric_id = repo.save_metric(
        source="thegraph",
        entity_id=snapshot.pool_id,
        metric_type="pool_liquidity_snapshot",
        data=snapshot.model_dump(),
        confidence=1.0,
    )

    return {
        "status": "SUCCESS",
        "metric_id": metric_id,
        "source": "thegraph",
        "data": snapshot.model_dump(),
    }


@router.post("/ingest/defillama", response_model=Dict[str, Any])
async def ingest_defillama(req: Optional[IngestDeFiLlamaRequest] = None) -> Dict[str, Any]:
    """Nodo de Ingestión: Consulta DeFiLlama (cadena individual o régimen macro) y persiste en SQLite WAL."""
    connector = DeFiLlamaConnector()
    settings = get_settings()
    repo = OnChainDataRepository(settings.DB_PATH)

    if req and req.chain_name:
        chain_snap = await connector.get_chain_tvl(req.chain_name)
        if not chain_snap:
            raise HTTPException(
                status_code=404, detail=f"Cadena '{req.chain_name}' no encontrada en DeFiLlama"
            )
        metric_id = repo.save_metric(
            source="defillama",
            entity_id=chain_snap.chain,
            metric_type="chain_tvl_snapshot",
            data=chain_snap.model_dump(),
            confidence=1.0,
        )
        return {
            "status": "SUCCESS",
            "metric_id": metric_id,
            "source": "defillama",
            "data": chain_snap.model_dump(),
        }
    else:
        macro_snap = await connector.get_macro_regime_metrics()
        metric_id = repo.save_metric(
            source="defillama",
            entity_id="global_macro",
            metric_type="macro_regime_snapshot",
            data=macro_snap.model_dump(),
            confidence=1.0,
        )
        return {
            "status": "SUCCESS",
            "metric_id": metric_id,
            "source": "defillama",
            "data": macro_snap.model_dump(),
        }


@router.post("/ingest/trueblocks", response_model=Dict[str, Any])
async def ingest_trueblocks(req: IngestTrueBlocksRequest) -> Dict[str, Any]:
    """Nodo de Ingestión: Audita una dirección localmente con TrueBlocks sin fuga de privacidad."""
    connector = TrueBlocksConnector()
    audit_res = await connector.audit_contract(req.address)

    settings = get_settings()
    repo = OnChainDataRepository(settings.DB_PATH)
    metric_id = repo.save_metric(
        source="trueblocks",
        entity_id=req.address,
        metric_type="contract_audit_result",
        data=audit_res.model_dump(),
        confidence=0.9 if audit_res.indexer_source == "TrueBlocks-Local" else 0.5,
    )

    return {
        "status": "SUCCESS",
        "metric_id": metric_id,
        "source": "trueblocks",
        "data": audit_res.model_dump(),
    }


@router.get("/onchain/summary")
def get_onchain_summary(
    source: Optional[str] = Query(None, description="Filtrar por thegraph, defillama o trueblocks"),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Consulta la telemetría y métricas on-chain consolidadas en SQLite WAL."""
    settings = get_settings()
    repo = OnChainDataRepository(settings.DB_PATH)
    return repo.get_recent_metrics(source=source, limit=limit)


class N8nWorkflowWebhookPayload(BaseModel):
    """Payload recibido desde los flujos de trabajo visuales de n8n."""
    workflow_id: str
    workflow_name: Optional[str] = "Orquestador n8n"
    bias_posture: str = Field(description="BULLISH_AGGRESSIVE | BEARISH_DEFENSIVE | NEUTRAL")
    confidence: float = Field(ge=0.0, le=1.0)
    risk_multiplier: float = Field(default=1.0, ge=0.0, le=2.0)
    llm_reasoning: Optional[str] = None
    target_symbols: List[str] = Field(default_factory=lambda: ["1000PEPE/USDT:USDT", "1000SHIB/USDT:USDT"])


@router.post("/n8n/webhook", response_model=Dict[str, Any])
def receive_n8n_webhook(payload: N8nWorkflowWebhookPayload) -> Dict[str, Any]:
    """
    Gateway Webhook Bidireccional n8n (PB-188).
    Recibe inferencias heurísticas o semánticas desde n8n e impacta el estado de sesgos en SQLite WAL.
    """
    settings = get_settings()
    bias_repo = MarketBiasRepository(settings.DB_PATH)
    onchain_repo = OnChainDataRepository(settings.DB_PATH)

    # Actualizar sesgos para los símbolos objetivo
    updated_symbols = []
    for sym in payload.target_symbols:
        bias_repo.save_bias(
            symbol=sym,
            posture=payload.bias_posture,
            confidence=payload.confidence,
        )
        updated_symbols.append(sym)

    # Persistir evento de orquestación en la auditoría onchain
    metric_id = onchain_repo.save_metric(
        source="n8n_orchestrator",
        entity_id=payload.workflow_id,
        metric_type="n8n_webhook_event",
        data=payload.model_dump(),
        confidence=payload.confidence,
    )

    return {
        "status": "ACCEPTED",
        "metric_id": metric_id,
        "updated_symbols": updated_symbols,
        "applied_posture": payload.bias_posture,
        "risk_multiplier": payload.risk_multiplier,
    }

