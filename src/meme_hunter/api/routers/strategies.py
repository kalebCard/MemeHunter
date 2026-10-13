"""
meme_hunter.api.routers.strategies - Endpoints de Gestión y Monitoreo de Alfas e Incubadora.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from meme_hunter.core.config import get_settings
from meme_hunter.storage.repositories import AutopsyRepository, StrategyRepository

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


@router.get("/")
def list_strategies(status: Optional[str] = Query(None, description="Filtrar por estado: SANDBOX, LIVE, ALPHA_DECAY, RETIRED")) -> List[Dict[str, Any]]:
    """Retorna la lista de todas las estrategias registradas en SQLite WAL."""
    settings = get_settings()
    repo = StrategyRepository(settings.DB_PATH)
    return repo.get_all(status=status)


@router.get("/autopsies/latest")
def get_latest_autopsies(limit: int = Query(10, ge=1, le=50)) -> List[Dict[str, Any]]:
    """Retorna las autopsias forenses cognitivas más recientes registradas por los LLMs."""
    settings = get_settings()
    repo = AutopsyRepository(settings.DB_PATH)
    return repo.get_latest(limit=limit)


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str) -> Dict[str, Any]:
    """Retorna los detalles y métricas de una estrategia específica."""
    settings = get_settings()
    repo = StrategyRepository(settings.DB_PATH)
    strat = repo.get_by_id(strategy_id)
    if not strat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estrategia con ID '{strategy_id}' no encontrada.",
        )
    return strat
