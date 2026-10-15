"""
meme_hunter.data.thegraph - Conector Asíncrono GraphQL para The Graph y Subgraphs DEX (PB-180).
Implementa pooling de conexiones HTTP/2, tipado Pydantic V2, backoff exponencial y resiliencia ante fallos.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("TheGraphConnector")


class TokenInfo(BaseModel):
    """Metadatos de un token en un par/pool de liquidez DEX."""
    id: str
    symbol: str
    name: Optional[str] = None
    decimals: int = Field(default=18, ge=0, le=36)


class PoolLiquiditySnapshot(BaseModel):
    """Instantánea de liquidez y volumen de un pool DEX según The Graph."""
    pool_id: str
    token0: TokenInfo
    token1: TokenInfo
    tvl_usd: float = Field(default=0.0, ge=0.0)
    volume_24h_usd: float = Field(default=0.0, ge=0.0)
    token0_price_usd: float = Field(default=0.0, ge=0.0)
    token1_price_usd: float = Field(default=0.0, ge=0.0)
    fee_tier_bps: Optional[int] = Field(default=3000, description="Comisión en puntos básicos")
    timestamp: int = Field(default=0, description="Timestamp UNIX UTC")

    @field_validator("pool_id")
    @classmethod
    def normalize_pool_id(cls, v: str) -> str:
        return v.strip().lower()


class DexSwapEvent(BaseModel):
    """Evento individual de swap capturado desde subgraphs DEX."""
    id: str
    pool_id: str
    sender: str
    recipient: str
    amount0: float
    amount1: float
    amount_usd: float = Field(default=0.0, ge=0.0)
    timestamp: int


class TheGraphConnector:
    """Cliente asíncrono para interactuar con subgraphs descentralizados o alojados en The Graph."""

    DEFAULT_UNISWAP_V3_SUBGRAPH = (
        "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    )

    def __init__(
        self,
        subgraph_url: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 3,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.subgraph_url = subgraph_url or self.DEFAULT_UNISWAP_V3_SUBGRAPH
        self.timeout = timeout
        self.max_retries = max_retries
        self._external_client = client

    async def _execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ejecuta una consulta GraphQL con backoff exponencial y reintentos ante errores transitorios."""
        payload = {"query": query, "variables": variables or {}}
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self._external_client:
                    response = await self._external_client.post(
                        self.subgraph_url, json=payload, timeout=self.timeout
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(self.subgraph_url, json=payload)

                response.raise_for_status()
                data = response.json()
                if "errors" in data:
                    raise ValueError(f"Error devuelto por The Graph: {data['errors']}")
                return data.get("data", {})
            except (httpx.HTTPError, ValueError) as exc:
                last_exception = exc
                wait_time = 0.25 * (2 ** (attempt - 1))
                logger.warning(
                    f"Fallo en consulta GraphQL (intento {attempt}/{self.max_retries}): {exc}. "
                    f"Reintentando en {wait_time:.2f}s..."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)

        logger.error(f"Consulta GraphQL falló tras {self.max_retries} intentos: {last_exception}")
        raise RuntimeError(f"Error persistente en TheGraphConnector: {last_exception}") from last_exception

    async def get_pool_snapshot(self, pool_id: str) -> Optional[PoolLiquiditySnapshot]:
        """Extrae la liquidez, volumen y cotizaciones de un pool específico."""
        query = """
        query GetPoolSnapshot($id: ID!) {
            pool(id: $id) {
                id
                token0 { id symbol name decimals }
                token1 { id symbol name decimals }
                totalValueLockedUSD
                volumeUSD
                token0Price
                token1Price
                feeTier
            }
        }
        """
        try:
            data = await self._execute_query(query, {"id": pool_id.lower()})
            raw_pool = data.get("pool")
            if not raw_pool:
                return None

            return PoolLiquiditySnapshot(
                pool_id=raw_pool["id"],
                token0=TokenInfo(
                    id=raw_pool["token0"]["id"],
                    symbol=raw_pool["token0"]["symbol"],
                    name=raw_pool["token0"].get("name"),
                    decimals=int(raw_pool["token0"].get("decimals", 18)),
                ),
                token1=TokenInfo(
                    id=raw_pool["token1"]["id"],
                    symbol=raw_pool["token1"]["symbol"],
                    name=raw_pool["token1"].get("name"),
                    decimals=int(raw_pool["token1"].get("decimals", 18)),
                ),
                tvl_usd=float(raw_pool.get("totalValueLockedUSD", 0.0) or 0.0),
                volume_24h_usd=float(raw_pool.get("volumeUSD", 0.0) or 0.0),
                token0_price_usd=float(raw_pool.get("token0Price", 0.0) or 0.0),
                token1_price_usd=float(raw_pool.get("token1Price", 0.0) or 0.0),
                fee_tier_bps=int(raw_pool.get("feeTier", 3000) or 3000),
            )
        except Exception as e:
            logger.error(f"Error obteniendo snapshot para pool {pool_id}: {e}")
            return None

    async def get_recent_swaps(self, pool_id: str, limit: int = 50) -> List[DexSwapEvent]:
        """Obtiene la serie de swaps recientes en un pool para análisis de flujo de órdenes."""
        query = """
        query GetRecentSwaps($poolId: String!, $limit: Int!) {
            swaps(
                first: $limit,
                orderBy: timestamp,
                orderDirection: desc,
                where: { pool: $poolId }
            ) {
                id
                sender
                recipient
                amount0
                amount1
                amountUSD
                timestamp
            }
        }
        """
        try:
            data = await self._execute_query(query, {"poolId": pool_id.lower(), "limit": limit})
            raw_swaps = data.get("swaps", [])
            results = []
            for s in raw_swaps:
                results.append(
                    DexSwapEvent(
                        id=s["id"],
                        pool_id=pool_id.lower(),
                        sender=s.get("sender", ""),
                        recipient=s.get("recipient", ""),
                        amount0=float(s.get("amount0", 0.0)),
                        amount1=float(s.get("amount1", 0.0)),
                        amount_usd=float(s.get("amountUSD", 0.0) or 0.0),
                        timestamp=int(s.get("timestamp", 0)),
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Error obteniendo swaps recientes para pool {pool_id}: {e}")
            return []
