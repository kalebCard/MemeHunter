"""
meme_hunter.api.routers.system - Endpoints de Salud del Sistema y Control de Emergencia.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from meme_hunter.core.config import get_settings
from meme_hunter.storage.repositories import MarketBiasRepository, StrategyRepository

router = APIRouter(prefix="/api/system", tags=["System"])


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str
    db_path: str
    db_exists: bool
    live_strategies_count: int
    active_biases_count: int


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Verifica el estado del servicio y conectividad con la base de datos canónica."""
    settings = get_settings()
    db_exists = settings.DB_PATH.exists()
    live_count = 0
    biases_count = 0

    if db_exists:
        strat_repo = StrategyRepository(settings.DB_PATH)
        bias_repo = MarketBiasRepository(settings.DB_PATH)
        live_strats = strat_repo.get_all(status="LIVE")
        live_count = len(live_strats)
        biases_count = len(bias_repo.get_all_active())

    return HealthResponse(
        status="HEALTHY",
        version="8.0.0",
        env=settings.ENV,
        db_path=str(settings.DB_PATH),
        db_exists=db_exists,
        live_strategies_count=live_count,
        active_biases_count=biases_count,
    )
