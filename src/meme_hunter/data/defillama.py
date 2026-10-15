"""
meme_hunter.data.defillama - Conector REST para DeFiLlama con Caché TTL Resiliente (PB-181).
Extrae métricas macroeconómicas, liquidez por cadena y rendimientos de pools con degradación elegante.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from meme_hunter.core.config import get_settings

logger = logging.getLogger("DeFiLlamaConnector")


class ChainTvlSnapshot(BaseModel):
    """Métricas de TVL de una blockchain específica."""
    chain: str
    tvl_usd: float = Field(ge=0.0)
    change_1d: Optional[float] = Field(default=0.0, description="Variación porcentual 24h")
    change_7d: Optional[float] = Field(default=0.0, description="Variación porcentual 7d")
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class PoolYieldSnapshot(BaseModel):
    """Rendimiento y liquidez de un pool en DeFiLlama Yields."""
    pool_id: str
    project: str
    chain: str
    symbol: str
    tvl_usd: float = Field(ge=0.0)
    apy: float = Field(default=0.0)
    apy_pct_1d: Optional[float] = None
    apy_pct_7d: Optional[float] = None


class MacroRegimeSnapshot(BaseModel):
    """Diagnóstico consolidado de régimen de liquidez global para modulación de riesgo."""
    total_tvl_usd: float = Field(ge=0.0)
    top_chains_tvl: Dict[str, float] = Field(default_factory=dict)
    average_1d_delta: float = Field(default=0.0, description="Cambio promedio 24h de cadenas top")
    risk_multiplier: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Multiplicador recomendado para position sizing"
    )
    regime: str = Field(default="NEUTRAL", description="EXPANSION | CONTRACTION | NEUTRAL")
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class DeFiLlamaConnector:
    """Cliente REST asíncrono para DeFiLlama con almacenamiento en caché bidireccional y fallback."""

    BASE_URL = "https://api.llama.fi"
    YIELDS_URL = "https://yields.llama.fi"

    def __init__(
        self,
        cache_ttl_seconds: int = 900,  # 15 minutos canónicos
        cache_dir: Optional[Path] = None,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.cache_ttl = cache_ttl_seconds
        settings = get_settings()
        self.cache_dir = cache_dir or (settings.STORAGE_DIR / "cache" / "defillama")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._external_client = client
        self._mem_cache: Dict[str, Dict[str, Any]] = {}

    def _get_from_cache(self, key: str) -> Optional[Any]:
        now = time.time()
        # 1. Caché en memoria
        if key in self._mem_cache:
            entry = self._mem_cache[key]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["data"]

        # 2. Caché en disco
        file_path = self.cache_dir / f"{key}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if now - entry.get("timestamp", 0) < self.cache_ttl:
                    self._mem_cache[key] = entry
                    return entry.get("data")
            except Exception as e:
                logger.debug(f"Aviso leyendo caché en disco ({key}): {e}")

        return None

    def _set_cache(self, key: str, data: Any) -> None:
        entry = {"timestamp": time.time(), "data": data}
        self._mem_cache[key] = entry
        file_path = self.cache_dir / f"{key}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entry, f)
        except Exception as e:
            logger.debug(f"Aviso guardando caché en disco ({key}): {e}")

    async def _fetch_url(self, url: str, cache_key: str) -> Any:
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            if self._external_client:
                resp = await self._external_client.get(url, timeout=self.timeout)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url)

            resp.raise_for_status()
            data = resp.json()
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.warning(f"Error consultando DeFiLlama ({url}): {e}. Buscando fallback en caché...")
            # Fallback a caché obsoleta si la red falló
            file_path = self.cache_dir / f"{cache_key}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        entry = json.load(f)
                    logger.info(f"Fallback exitoso con datos cacheados para {cache_key}")
                    return entry.get("data")
                except Exception:
                    pass
            raise

    async def get_all_chains(self) -> List[ChainTvlSnapshot]:
        """Extrae el TVL actual y variaciones temporales de todas las cadenas soportadas."""
        url = f"{self.BASE_URL}/v2/chains"
        raw_chains = await self._fetch_url(url, "all_chains")
        snapshots = []
        for c in raw_chains:
            snapshots.append(
                ChainTvlSnapshot(
                    chain=c.get("name", ""),
                    tvl_usd=float(c.get("tvl", 0.0) or 0.0),
                    change_1d=float(c.get("change_1d", 0.0) or 0.0) if c.get("change_1d") is not None else 0.0,
                    change_7d=float(c.get("change_7d", 0.0) or 0.0) if c.get("change_7d") is not None else 0.0,
                )
            )
        return snapshots

    async def get_chain_tvl(self, chain_name: str) -> Optional[ChainTvlSnapshot]:
        """Obtiene el snapshot de una blockchain concreta (ej: 'Ethereum', 'Solana', 'Arbitrum')."""
        chains = await self.get_all_chains()
        target = chain_name.strip().lower()
        for c in chains:
            if c.chain.lower() == target:
                return c
        return None

    async def get_yield_pools(self, min_tvl_usd: float = 1_000_000.0) -> List[PoolYieldSnapshot]:
        """Consulta pools con rendimientos significativos desde yields.llama.fi."""
        url = f"{self.YIELDS_URL}/pools"
        res = await self._fetch_url(url, "yield_pools")
        raw_list = res.get("data", []) if isinstance(res, dict) else []
        snapshots = []
        for p in raw_list:
            tvl = float(p.get("tvlUsd", 0.0) or 0.0)
            if tvl >= min_tvl_usd:
                snapshots.append(
                    PoolYieldSnapshot(
                        pool_id=p.get("pool", ""),
                        project=p.get("project", ""),
                        chain=p.get("chain", ""),
                        symbol=p.get("symbol", ""),
                        tvl_usd=tvl,
                        apy=float(p.get("apy", 0.0) or 0.0),
                        apy_pct_1d=float(p.get("apyPct1D", 0.0)) if p.get("apyPct1D") is not None else None,
                        apy_pct_7d=float(p.get("apyPct7D", 0.0)) if p.get("apyPct7D") is not None else None,
                    )
                )
        return snapshots

    async def get_macro_regime_metrics(self) -> MacroRegimeSnapshot:
        """Sintetiza la postura macroeconómica y calcula el multiplicador de riesgo de apalancamiento."""
        try:
            chains = await self.get_all_chains()
            # Ordenar por TVL descendente
            sorted_chains = sorted(chains, key=lambda x: x.tvl_usd, reverse=True)
            top_5 = sorted_chains[:5]

            total_tvl = sum(c.tvl_usd for c in chains)
            top_chains_dict = {c.chain: c.tvl_usd for c in top_5}
            deltas_1d = [c.change_1d for c in top_5 if c.change_1d is not None]
            avg_delta = sum(deltas_1d) / len(deltas_1d) if deltas_1d else 0.0

            # Determinación de régimen y multiplicador
            if avg_delta > 2.0:
                regime = "EXPANSION"
                risk_multiplier = 1.25
            elif avg_delta < -2.0:
                regime = "CONTRACTION"
                risk_multiplier = 0.50
            else:
                regime = "NEUTRAL"
                risk_multiplier = 1.0

            return MacroRegimeSnapshot(
                total_tvl_usd=total_tvl,
                top_chains_tvl=top_chains_dict,
                average_1d_delta=avg_delta,
                risk_multiplier=risk_multiplier,
                regime=regime,
            )
        except Exception as e:
            logger.error(f"Fallo calculando régimen macro en DeFiLlama: {e}")
            # Fallback seguro neutral
            return MacroRegimeSnapshot(
                total_tvl_usd=0.0,
                top_chains_tvl={},
                average_1d_delta=0.0,
                risk_multiplier=1.0,
                regime="NEUTRAL",
            )
