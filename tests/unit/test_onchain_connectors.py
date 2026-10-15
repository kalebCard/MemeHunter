"""
tests/unit/test_onchain_connectors.py - Suite Hermética de Pruebas para Conectores On-Chain (PB-184).
Valida TheGraphConnector, DeFiLlamaConnector, TrueBlocksConnector y OnChainDataRepository.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from meme_hunter.data.thegraph import TheGraphConnector, PoolLiquiditySnapshot, DexSwapEvent
from meme_hunter.data.defillama import DeFiLlamaConnector, ChainTvlSnapshot, MacroRegimeSnapshot
from meme_hunter.data.trueblocks import TrueBlocksConnector, WalletAppearance, ContractAuditResult
from meme_hunter.storage.repositories.onchain_repo import OnChainDataRepository
from meme_hunter.storage.schema import init_database
from meme_hunter.api.app import create_app
from fastapi.testclient import TestClient


# ==============================================================================
# 1. PRUEBAS THE GRAPH CONNECTOR (PB-180)
# ==============================================================================

def test_thegraph_get_pool_snapshot_success():
    async def _run():
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "pool": {
                    "id": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                    "token0": {"id": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "symbol": "USDC", "name": "USD Coin", "decimals": "6"},
                    "token1": {"id": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "symbol": "WETH", "name": "Wrapped Ether", "decimals": "18"},
                    "totalValueLockedUSD": "185000000.50",
                    "volumeUSD": "45000000.00",
                    "token0Price": "0.00038",
                    "token1Price": "2600.50",
                    "feeTier": "500",
                }
            }
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        connector = TheGraphConnector(client=mock_client)
        snapshot = await connector.get_pool_snapshot("0x88E6A0C2DDD26FEEB64F039A2C41296FCB3F5640")

        assert snapshot is not None
        assert snapshot.pool_id == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        assert snapshot.token0.symbol == "USDC"
        assert snapshot.token1.symbol == "WETH"
        assert snapshot.tvl_usd == 185000000.50
        assert snapshot.token1_price_usd == 2600.50
        assert snapshot.fee_tier_bps == 500

    asyncio.run(_run())


def test_thegraph_get_recent_swaps():
    async def _run():
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "swaps": [
                    {
                        "id": "swap_01",
                        "sender": "0xuser1",
                        "recipient": "0xuser1",
                        "amount0": "-1000.0",
                        "amount1": "0.38",
                        "amountUSD": "1000.0",
                        "timestamp": "1728925000",
                    }
                ]
            }
        }
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        connector = TheGraphConnector(client=mock_client)
        swaps = await connector.get_recent_swaps("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", limit=1)

        assert len(swaps) == 1
        assert swaps[0].id == "swap_01"
        assert swaps[0].amount_usd == 1000.0

    asyncio.run(_run())


def test_thegraph_retry_exhaustion():
    async def _run():
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectTimeout("Network unavailable"))

        connector = TheGraphConnector(client=mock_client, max_retries=2, timeout=0.05)
        snapshot = await connector.get_pool_snapshot("0xpool")
        assert snapshot is None

    asyncio.run(_run())


# ==============================================================================
# 2. PRUEBAS DEFILLAMA CONNECTOR (PB-181)
# ==============================================================================

def test_defillama_get_chain_tvl(tmp_path):
    async def _run():
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {"name": "Ethereum", "tvl": 55000000000.0, "change_1d": 1.25, "change_7d": 4.5},
            {"name": "Solana", "tvl": 4500000000.0, "change_1d": 5.80, "change_7d": 12.0},
        ]

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        connector = DeFiLlamaConnector(cache_dir=tmp_path, client=mock_client)
        solana = await connector.get_chain_tvl("solana")

        assert solana is not None
        assert solana.chain == "Solana"
        assert solana.tvl_usd == 4500000000.0
        assert solana.change_1d == 5.80

    asyncio.run(_run())


def test_defillama_cache_hit(tmp_path):
    async def _run():
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [{"name": "Ethereum", "tvl": 50000000000.0}]

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        connector = DeFiLlamaConnector(cache_dir=tmp_path, client=mock_client, cache_ttl_seconds=300)
        # Primera consulta (va a la red)
        await connector.get_all_chains()
        assert mock_client.get.call_count == 1

        # Segunda consulta inmediata (debe usar caché en memoria)
        chains2 = await connector.get_all_chains()
        assert mock_client.get.call_count == 1
        assert len(chains2) == 1

    asyncio.run(_run())


def test_defillama_macro_regime_expansion(tmp_path):
    async def _run():
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {"name": "Ethereum", "tvl": 60000000000.0, "change_1d": 3.5},
            {"name": "Solana", "tvl": 5000000000.0, "change_1d": 4.0},
            {"name": "Arbitrum", "tvl": 3000000000.0, "change_1d": 2.5},
        ]
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        connector = DeFiLlamaConnector(cache_dir=tmp_path, client=mock_client)
        macro = await connector.get_macro_regime_metrics()

        assert macro.regime == "EXPANSION"
        assert macro.risk_multiplier == 1.25
        assert macro.total_tvl_usd == 68000000000.0

    asyncio.run(_run())


# ==============================================================================
# 3. PRUEBAS TRUEBLOCKS CONNECTOR (PB-182)
# ==============================================================================

def test_trueblocks_fallback_when_unavailable():
    async def _run():
        connector = TrueBlocksConnector(binary_name="non_existent_binary_xyz")
        is_avail = await connector.is_available()
        assert is_avail is False

        audit = await connector.audit_contract("0x1234567890abcdef1234567890abcdef12345678")
        assert audit.indexer_source == "Fallback-Heuristic"
        assert audit.risk_score == 0.20

    asyncio.run(_run())


def test_trueblocks_with_mocked_cli():
    async def _run():
        connector = TrueBlocksConnector(binary_name="chifra")
        connector._is_available = True

        mock_json = {
            "data": [
                {"blockNumber": 1000},
                {"blockNumber": 1050},
                {"blockNumber": 1100},
            ]
        }

        with patch.object(connector, "_run_command", new=AsyncMock(return_value=mock_json)):
            appearances = await connector.list_appearances("0xcontract")
            assert appearances.appearance_count == 3
            assert appearances.first_block == 1000
            assert appearances.last_block == 1100
            assert appearances.is_local_indexed is True

            audit = await connector.audit_contract("0xcontract")
            assert audit.total_txs == 3
            assert audit.risk_score >= 0.40  # Por muy pocas apariciones

    asyncio.run(_run())


# ==============================================================================
# 4. PRUEBAS ONCHAIN DATA REPOSITORY EN SQLITE WAL (PB-183)
# ==============================================================================

def test_onchain_repository_lifecycle(temp_wal_db):
    repo = OnChainDataRepository(temp_wal_db)

    # Inserción
    m_id = repo.save_metric(
        source="thegraph",
        entity_id="0xpool123",
        metric_type="pool_liquidity_snapshot",
        data={"tvl": 1000000.0, "symbol": "PEPE"},
        confidence=0.95,
    )
    assert m_id > 0

    # Recuperación individual
    latest = repo.get_latest_metric("thegraph", "0xpool123")
    assert latest is not None
    assert latest["source"] == "thegraph"
    assert latest["entity_id"] == "0xpool123"
    assert latest["confidence"] == 0.95
    assert latest["data"]["symbol"] == "PEPE"

    # Recuperación de lista
    recent = repo.get_recent_metrics(source="thegraph", limit=10)
    assert len(recent) == 1
    assert recent[0]["data"]["symbol"] == "PEPE"


# ==============================================================================
# 5. PRUEBAS ENDPOINTS FASTAPI DAG (PB-183)
# ==============================================================================

def test_dag_onchain_endpoints(temp_wal_db, monkeypatch):
    from meme_hunter.core import config
    settings = config.AppSettings(ENV="test", DB_PATH=temp_wal_db)
    monkeypatch.setattr("meme_hunter.core.config.get_settings", lambda: settings)
    monkeypatch.setattr("meme_hunter.api.routers.dag.get_settings", lambda: settings)

    # Asegurar que el esquema canónico completo esté inicializado en temp_wal_db
    init_database(temp_wal_db)

    app = create_app()
    client = TestClient(app)

    # Estado del DAG
    status_resp = client.get("/api/dag/status")
    assert status_resp.status_code == 200
    top = status_resp.json()["topology"]
    assert "TheGraphIngestor" in top["ingestion_nodes"]
    assert "DeFiLlamaIngestor" in top["ingestion_nodes"]
    assert "TrueBlocksIngestor" in top["ingestion_nodes"]

    # Ingest TrueBlocks
    with patch(
        "meme_hunter.data.trueblocks.TrueBlocksConnector.audit_contract",
        new=AsyncMock(
            return_value=ContractAuditResult(
                contract_address="0xabc",
                total_txs=150,
                risk_score=0.10,
                indexer_source="TrueBlocks-Local",
            )
        ),
    ):
        resp = client.post("/api/dag/ingest/trueblocks", json={"address": "0xabc"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "SUCCESS"
        assert resp.json()["data"]["contract_address"] == "0xabc"

    # Resumen de métricas
    summary_resp = client.get("/api/dag/onchain/summary")
    assert summary_resp.status_code == 200
    items = summary_resp.json()
    assert len(items) >= 1
    assert items[0]["source"] == "trueblocks"
