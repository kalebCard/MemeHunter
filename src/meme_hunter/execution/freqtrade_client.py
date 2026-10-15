"""
meme_hunter.execution.freqtrade_client - Cliente REST API de Producción para Freqtrade.

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

try:
    from meme_hunter.core.config import get_settings
except ImportError:
    get_settings = None

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
        cfg_url = "http://127.0.0.1:8081"
        cfg_user = "admin"
        cfg_pass = ""
        if get_settings:
            try:
                s = get_settings()
                cfg_url = s.FREQTRADE_API_URL
                cfg_user = s.FREQTRADE_API_USERNAME
                cfg_pass = s.get_raw_secret(s.FREQTRADE_API_PASSWORD) or ""
            except Exception:
                pass

        self.base_url = (base_url or os.getenv("FREQTRADE_API_URL") or cfg_url).rstrip("/")
        self.username = username or os.getenv("FREQTRADE_API_USER") or cfg_user
        self.password = password or os.getenv("FREQTRADE_API_PASSWORD") or cfg_pass
        self.api_token = api_token or os.getenv("FREQTRADE_API_TOKEN")
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
        """Dispara el hot-reload de configuración y recarga de estrategias en caliente."""
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

    def get_profit(self) -> Dict[str, Any]:
        """Consulta métricas consolidadas de rendimiento y PnL acumulado."""
        return self._request("/api/v1/profit", method="GET")

    def get_balance(self) -> Dict[str, Any]:
        """Consulta balances de billetera, capital disponible y márgenes aislados."""
        return self._request("/api/v1/balance", method="GET")

    def get_daily(self, days: int = 7) -> Dict[str, Any]:
        """Consulta desglose de PnL por días recientes."""
        return self._request(f"/api/v1/daily?timescale={days}", method="GET")

    def get_count(self) -> Dict[str, Any]:
        """Consulta el número de trades abiertos y límite máximo."""
        return self._request("/api/v1/count", method="GET")

    def start_bot(self) -> Dict[str, Any]:
        """Reanuda la ejecución operativa del bot."""
        return self._request("/api/v1/start", method="POST")

    def stop_bot(self) -> Dict[str, Any]:
        """Detiene la ejecución operativa del bot de forma ordenada."""
        return self._request("/api/v1/stop", method="POST")

    def stopbuy_bot(self) -> Dict[str, Any]:
        """Inhibe la apertura de nuevas posiciones manteniendo el trailing de las abiertas."""
        return self._request("/api/v1/stopbuy", method="POST")

    def forcesell(self, trade_id: str) -> Dict[str, Any]:
        """Fuerza la salida y liquidación inmediata de un trade específico."""
        return self._request("/api/v1/forcesell", method="POST", data={"tradeid": str(trade_id)})

    def forcebuy(self, pair: str, price: Optional[float] = None) -> Dict[str, Any]:
        """Fuerza la apertura de una posición específica."""
        payload: Dict[str, Any] = {"pair": pair}
        if price is not None:
            payload["price"] = price
        return self._request("/api/v1/forcebuy", method="POST", data=payload)

    def get_locks(self) -> Dict[str, Any]:
        """Consulta bloqueos temporales activos sobre pares."""
        return self._request("/api/v1/locks", method="GET")

    def delete_lock(self, lock_id: int) -> Dict[str, Any]:
        """Libera un bloqueo temporal sobre un par."""
        return self._request("/api/v1/delete_lock", method="POST", data={"lockid": lock_id})

    def get_whitelist(self) -> Dict[str, Any]:
        """Consulta lista blanca actual de pares en vigilancia."""
        return self._request("/api/v1/whitelist", method="GET")

    def get_blacklist(self) -> Dict[str, Any]:
        """Consulta lista negra actual de pares bloqueados."""
        return self._request("/api/v1/blacklist", method="GET")

    def get_version(self) -> Dict[str, Any]:
        """Consulta la versión del motor Freqtrade."""
        return self._request("/api/v1/version", method="GET")


__all__ = ["FreqtradeRestClient"]
