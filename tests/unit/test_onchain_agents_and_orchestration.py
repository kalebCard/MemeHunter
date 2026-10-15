"""
tests/unit/test_onchain_agents_and_orchestration.py - Pruebas Unitarias para Sprint 53 (PB-185 a PB-189).
Verifica DexExecutionAgent, MacroRegimeRiskAgent, WhaleForensicAgent y Webhook n8n.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from meme_hunter.agents.dex_execution_agent import DexExecutionAgent, DexTriggerSignal
from meme_hunter.agents.macro_risk_agent import MacroRegimeRiskAgent, MacroRiskSignal
from meme_hunter.agents.whale_forensic_agent import WhaleForensicAgent, WhaleForensicSignal
from meme_hunter.data.thegraph import PoolLiquiditySnapshot, TokenInfo, DexSwapEvent
from meme_hunter.data.defillama import MacroRegimeSnapshot
from meme_hunter.data.trueblocks import ContractAuditResult
from meme_hunter.api.app import create_app
from meme_hunter.storage.schema import init_database
from meme_hunter.storage.repositories import MarketBiasRepository


# ==============================================================================
# 1. PRUEBAS DEX EXECUTION AGENT (PB-185)
# ==============================================================================

def test_dex_execution_agent_buy_trigger():
    async def _run():
        mock_connector = MagicMock()
        mock_connector.get_pool_snapshot = AsyncMock(
            return_value=PoolLiquiditySnapshot(
                pool_id="0xpool",
                token0=TokenInfo(id="0xt0", symbol="USDC"),
                token1=TokenInfo(id="0xt1", symbol="PEPE"),
                tvl_usd=1000000.0,
                volume_24h_usd=250000.0,
            )
        )
        mock_connector.get_recent_swaps = AsyncMock(
            return_value=[
                DexSwapEvent(id="s1", pool_id="0xpool", sender="a", recipient="b", amount0=-5000.0, amount1=100000.0, amount_usd=5000.0, timestamp=100),
                DexSwapEvent(id="s2", pool_id="0xpool", sender="c", recipient="d", amount0=-4000.0, amount1=80000.0, amount_usd=4000.0, timestamp=101),
            ]
        )

        agent = DexExecutionAgent(connector=mock_connector)
        signal = await agent.evaluate_pool("0xpool", order_size_usd=1000.0)

        assert signal.action == "BUY"
        assert signal.confidence > 0.80
        assert signal.order_flow_imbalance == 1.0  # Solo compras

    asyncio.run(_run())


def test_dex_execution_agent_high_slippage_hold():
    async def _run():
        mock_connector = MagicMock()
        mock_connector.get_pool_snapshot = AsyncMock(
            return_value=PoolLiquiditySnapshot(
                pool_id="0xpool_illiquid",
                token0=TokenInfo(id="0xt0", symbol="USDC"),
                token1=TokenInfo(id="0xt1", symbol="MICRO"),
                tvl_usd=5000.0,  # Liquidez bajísima
                volume_24h_usd=1000.0,
            )
        )
        mock_connector.get_recent_swaps = AsyncMock(return_value=[])

        agent = DexExecutionAgent(connector=mock_connector)
        # Orden de $1,000 en pool de $5,000 causará > 5% slippage
        signal = await agent.evaluate_pool("0xpool_illiquid", order_size_usd=1000.0)

        assert signal.action == "HOLD"
        assert "Slippage prohibitivo" in signal.reason

    asyncio.run(_run())


# ==============================================================================
# 2. PRUEBAS MACRO REGIME RISK AGENT (PB-186)
# ==============================================================================

def test_macro_risk_agent_contraction():
    async def _run():
        mock_connector = MagicMock()
        mock_connector.get_macro_regime_metrics = AsyncMock(
            return_value=MacroRegimeSnapshot(
                total_tvl_usd=50000000000.0,
                average_1d_delta=-3.5,
                risk_multiplier=0.50,
                regime="CONTRACTION",
            )
        )

        agent = MacroRegimeRiskAgent(connector=mock_connector)
        signal = await agent.evaluate_risk()

        assert signal.regime == "CONTRACTION"
        assert signal.risk_multiplier == 0.50
        assert signal.allow_long_entries is False
        assert signal.allow_short_entries is True

    asyncio.run(_run())


# ==============================================================================
# 3. PRUEBAS WHALE FORENSIC AGENT (PB-187)
# ==============================================================================

def test_whale_forensic_agent_veto_trade():
    async def _run():
        mock_connector = MagicMock()
        mock_connector.audit_contract = AsyncMock(
            return_value=ContractAuditResult(
                contract_address="0xscam",
                total_txs=2,
                risk_score=0.85,
                is_flagged=True,
                indexer_source="TrueBlocks-Local",
            )
        )

        agent = WhaleForensicAgent(connector=mock_connector)
        signal = await agent.inspect_contract("0xscam")

        assert signal.veto_trade is True
        assert signal.is_safe is False
        assert "VETO PREVENTIVO" in signal.reason

    asyncio.run(_run())


# ==============================================================================
# 4. PRUEBAS GATEWAY WEBHOOK N8N (PB-188)
# ==============================================================================

def test_n8n_webhook_integration(temp_wal_db, monkeypatch):
    from meme_hunter.core import config
    settings = config.AppSettings(ENV="test", DB_PATH=temp_wal_db)
    monkeypatch.setattr("meme_hunter.core.config.get_settings", lambda: settings)
    monkeypatch.setattr("meme_hunter.api.routers.dag.get_settings", lambda: settings)

    init_database(temp_wal_db)
    app = create_app()
    client = TestClient(app)

    payload = {
        "workflow_id": "wf_test_001",
        "workflow_name": "Test Macro Flow",
        "bias_posture": "BULLISH_AGGRESSIVE",
        "confidence": 0.88,
        "risk_multiplier": 1.25,
        "llm_reasoning": "TVL expandiéndose con fuerte compra DEX confirmada.",
        "target_symbols": ["1000PEPE/USDT:USDT"],
    }

    resp = client.post("/api/dag/n8n/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACCEPTED"
    assert "1000PEPE/USDT:USDT" in data["updated_symbols"]

    # Verificar que el sesgo fue actualizado en SQLite WAL
    bias_repo = MarketBiasRepository(temp_wal_db)
    bias = bias_repo.get_bias("1000PEPE/USDT:USDT")
    assert bias is not None
    assert bias["posture"] == "BULLISH_AGGRESSIVE"
    assert bias["confidence"] == 0.88
