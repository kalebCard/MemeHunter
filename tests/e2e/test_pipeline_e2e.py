"""
tests/e2e/test_pipeline_e2e.py - Prueba de Ciclo de Vida Completo de Extremo a Extremo (v8.0).
Valida el flujo continuo:
1. Configuración Pydantic Settings
2. Base de datos SQLite WAL y StrategyRepository
3. Señal Multi-Agente DTO
4. Filtro Pre-Trade de Rentabilidad
5. Compilador AST Zero-Eval
6. Servidor FastAPI / Telemetría
"""

import pytest
from fastapi.testclient import TestClient

from meme_hunter.core.config import get_settings
from meme_hunter.core.types import (
    MarketRegime,
    StrategyStatus,
    SignalAction,
    AgentSignalDTO,
)
from meme_hunter.storage.repositories import StrategyRepository, MarketBiasRepository
from meme_hunter.risk.pre_trade import PreTradeProfitabilityGate
from meme_hunter.alpha.parser import FormulaASTParser
from meme_hunter.api.app import create_app


def test_full_pipeline_lifecycle_e2e(temp_wal_db):
    """Prueba E2E que atraviesa todas las capas arquitectónicas del sistema."""
    settings = get_settings()

    # 1. Capa de Datos y Persistencia
    strat_repo = StrategyRepository(db_path=temp_wal_db)
    bias_repo = MarketBiasRepository(db_path=temp_wal_db)

    strat_repo.upsert_strategy({
        "strategy_id": "e2e_apex_quantum",
        "name": "MemeHunter_ApexQuantum_E2E",
        "status": StrategyStatus.LIVE,
        "target_capital_weight": 0.40,
        "backtest_sharpe": 3.10,
    })

    bias_repo.save_bias(
        symbol="DOGE/USDT:USDT",
        posture="BEARISH_SHORT",
        confidence=0.91,
    )

    # 2. Capa de Dominio: Señal DTO
    signal = AgentSignalDTO(
        symbol="DOGE/USDT:USDT",
        signal_value=-0.85,
        confidence=0.91,
        regime=MarketRegime.BEAR_BLEED,
        action=SignalAction.ENTER_SHORT,
    )
    assert signal.signal_value == -0.85

    # 3. Capa de Riesgo: Compuerta Pre-Trade
    gate = PreTradeProfitabilityGate(
        default_safety_multiplier=2.50,
        maker_fee_pct=0.0005,
        taker_fee_pct=0.0005,
        default_min_target_pct=0.035,
    )
    decision = gate.evaluate_entry(
        symbol="DOGE/USDT:USDT",
        current_price=0.1500,
        target_price=0.1580,  # ~5.3% ganancia proyectada
        spread_pct=0.0005,
    )
    assert decision.is_approved is True

    # 4. Capa Cuantitativa: Validación de Fórmula AST Zero-Eval
    formula = "ts_rank(returns, 5) - ts_delta(close, 3)"
    ast_node = FormulaASTParser.parse(formula)
    assert ast_node is not None
    assert "ts_rank" in ast_node.to_formula()

    # 5. Capa de API y Presentación
    client = TestClient(create_app())
    health_resp = client.get("/api/system/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "HEALTHY"

    dag_resp = client.get("/api/dag/status")
    assert dag_resp.status_code == 200
    assert dag_resp.json()["is_active"] is True
