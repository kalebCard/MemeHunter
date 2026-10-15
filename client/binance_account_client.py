#!/usr/bin/env python3
"""
Cliente de Consulta de Billeteras Reales de Binance (Spot y Futuros USDⓈ-M)
Permite a Hermes y Telegram Copilot distinguir entre:
1. Saldo Real en Binance (Spot / Futuros).
2. Saldo Simulado de la Arena Multi-Bot (Dry-Run).
"""
import os
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    root_env = Path(__file__).resolve().parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv(".env")
except ImportError:
    pass

logger = logging.getLogger("BinanceAccountClient")


class BinanceAccountClient:
    """
    Cliente liviano con caché para consultar saldos reales de Binance.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        cache_ttl_sec: float = 120.0
    ):
        try:
            from portfolio.secrets_vault import get_secret
        except ImportError:
            get_secret = lambda k, default="": os.getenv(k, default)

        self.api_key = (
            api_key
            or os.getenv("BINANCE_API_KEY", "")
            or os.getenv("FREQTRADE__EXCHANGE__KEY", "")
            or get_secret("BINANCE_API_KEY", "")
        ).strip()
        self.api_secret = (
            api_secret
            or os.getenv("BINANCE_API_SECRET", "")
            or os.getenv("FREQTRADE__EXCHANGE__SECRET", "")
            or get_secret("BINANCE_API_SECRET", "")
        ).strip()
        self.cache_ttl_sec = float(cache_ttl_sec)
        self._cached_data: Optional[Dict[str, Any]] = None
        self._last_fetch_time: float = 0.0

    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret and len(self.api_key) > 10)

    def get_real_balances(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Obtiene los saldos de Binance Spot y Futuros USDT-M.
        Usa caché de 120 segundos para evitar saturar rate-limits o ralentizar respuestas.
        """
        now = time.time()
        if not force_refresh and self._cached_data and (now - self._last_fetch_time < self.cache_ttl_sec):
            return self._cached_data

        if not self.has_credentials():
            return {
                "has_keys": False,
                "spot_usdt_free": 0.0,
                "spot_usdt_total": 0.0,
                "futures_usdt_free": 0.0,
                "futures_usdt_total": 0.0,
                "other_assets": {},
                "note": "Sin credenciales de Binance en .env"
            }

        try:
            import ccxt
            # 1. Consultar Spot (timeout 3500ms para evitar cuelgues)
            spot_client = ccxt.binance({
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "timeout": 3500,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"}
            })
            b_spot = spot_client.fetch_balance()
            spot_usdt_free = float(b_spot.get("USDT", {}).get("free", 0.0) or 0.0)
            spot_usdt_total = float(b_spot.get("USDT", {}).get("total", 0.0) or 0.0)

            # Activos adicionales relevantes en spot (> 0.0001)
            other_assets = {}
            for asset, val in b_spot.items():
                if isinstance(val, dict) and asset not in ("USDT", "info", "free", "used", "total"):
                    tot = float(val.get("total", 0.0) or 0.0)
                    if tot > 0.0001:
                        other_assets[asset] = round(tot, 4)

            # 2. Consultar Futuros USDT-M (timeout 3500ms)
            futures_client = ccxt.binance({
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "timeout": 3500,
                "enableRateLimit": True,
                "options": {"defaultType": "future"}
            })
            b_fut = futures_client.fetch_balance()
            fut_usdt_free = float(b_fut.get("USDT", {}).get("free", 0.0) or 0.0)
            fut_usdt_total = float(b_fut.get("USDT", {}).get("total", 0.0) or 0.0)

            result = {
                "has_keys": True,
                "spot_usdt_free": spot_usdt_free,
                "spot_usdt_total": spot_usdt_total,
                "futures_usdt_free": fut_usdt_free,
                "futures_usdt_total": fut_usdt_total,
                "other_assets": other_assets,
                "timestamp": now,
                "status": "ok"
            }
            self._cached_data = result
            self._last_fetch_time = now
            return result

        except Exception as e:
            logger.warning(f"Error consultando saldos reales de Binance: {e}")
            fallback = {
                "has_keys": True,
                "spot_usdt_free": 0.0,
                "spot_usdt_total": 0.0,
                "futures_usdt_free": 0.0,
                "futures_usdt_total": 0.0,
                "other_assets": {},
                "error": str(e),
                "status": "error"
            }
            return fallback
