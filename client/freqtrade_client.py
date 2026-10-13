"""
freqtrade_client.py - Cliente REST API de Producción para Freqtrade (Sprint 28: PB-97).

Permite el enlace bidireccional entre la incubadora autónoma de Meme Hunter
y el motor de ejecución en vivo de Freqtrade:
1. `reload_config`: Hot-reload de la configuración y recarga de estrategias compiladas
   sin reiniciar el contenedor ni abortar órdenes activas.
2. `ping`: Sondeo de salud de la instancia de Freqtrade.
3. `get_status`: Consulta de estado y posiciones abiertas en Binance Futures.
"""

import os
import json
import logging
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from portfolio.secrets_vault import get_secret

logger = logging.getLogger("FreqtradeClient")


class FreqtradeRestClient:
    """
    Cliente REST API liviano y robusto para interactuar con la API interna de Freqtrade.
    Utiliza urllib para cero dependencias externas obligatorias.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout_sec: float = 3.0
    ):
        self.base_url = (base_url or get_secret("FREQTRADE_API_URL") or "http://127.0.0.1:8081").rstrip("/")
        self.username = username or get_secret("FREQTRADE_API_USER") or "admin"
        self.password = password or get_secret("FREQTRADE_API_PASSWORD") or ""
        self.api_token = api_token or get_secret("FREQTRADE_API_TOKEN")
        self.timeout_sec = float(timeout_sec)

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MemeHunter-AlphaFactory/2.0"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        elif self.username and self.password:
            auth_str = f"{self.username}:{self.password}"
            encoded = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
            headers["Authorization"] = f"Basic {encoded}"
        return headers

    def _request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = self._build_headers()
        body = json.dumps(data).encode('utf-8') if data else None

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                resp_data = resp.read().decode('utf-8')
                return {
                    "status": "ok",
                    "status_code": resp.status,
                    "data": json.loads(resp_data) if resp_data else {}
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            logger.warning(f"Freqtrade API HTTP {e.code} en {endpoint}: {error_body}")
            return {
                "status": "error",
                "status_code": e.code,
                "error": error_body,
                "endpoint": endpoint
            }
        except (urllib.error.URLError, TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.info(f"Freqtrade API offline o inalcanzable ({url}): {e}")
            return {
                "status": "offline",
                "status_code": 0,
                "error": str(e),
                "endpoint": endpoint
            }

    def ping(self) -> Dict[str, Any]:
        """Verifica la conectividad y estado activo de la API de Freqtrade."""
        return self._request("/api/v1/ping", method="GET")

    def reload_config(self) -> Dict[str, Any]:
        """
        PB-97: Dispara el hot-reload de configuración y recarga de estrategias en caliente.
        No interrumpe el bucle local si el bot está offline.
        """
        res = self._request("/api/v1/reload_config", method="POST")
        if res.get("status") == "ok":
            logger.info("Hot-Reload de Freqtrade ejecutado exitosamente.")
            res["reloaded"] = True
        else:
            res["reloaded"] = False
        return res

    def get_status(self) -> Dict[str, Any]:
        """Consulta el estado del bot y las operaciones abiertas."""
        return self._request("/api/v1/status", method="GET")
