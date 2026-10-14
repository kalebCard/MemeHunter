"""
meme_hunter.api.security - Módulo Institucional de Seguridad y Control de Acceso.
Sprint 1 & Sprint 45-47: Token validation, Rate Limiting y Cabeceras CORS estrictas.
"""

import os
import sys
import json
import secrets
import threading
import time
import hmac
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from http.server import SimpleHTTPRequestHandler

INSECURE_DEFAULT_TOKEN = "meme_hunter_dev_token_2026"
MIN_TOKEN_LENGTH = 32

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def resolve_and_validate_token(enforce_production: bool = False) -> str:
    """
    Resuelve el token API y valida los estándares de seguridad 2026 (Sprint 1: US-1.1).
    Falla tempranamente (fail-fast) si el token falta, es inseguro o menor a 32 caracteres.
    """
    token = os.getenv("DASHBOARD_API_TOKEN", "")
    if not token:
        try:
            from portfolio.secrets_vault import get_secret
            token = get_secret("DASHBOARD_API_TOKEN", "") or ""
        except Exception:
            pass

    if not token:
        env_path = os.path.join(str(REPO_ROOT), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("DASHBOARD_API_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass

    if enforce_production:
        if not token:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: 'DASHBOARD_API_TOKEN' no está configurado. "
                "Para operar de forma segura, defina la variable DASHBOARD_API_TOKEN en su entorno o archivo .env "
                "con al menos 32 caracteres criptográficos (ej. generado con `secrets.token_hex(32)`)."
            )
        if token == INSECURE_DEFAULT_TOKEN:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Se detectó el token por defecto inseguro ('meme_hunter_dev_token_2026'). "
                "Por favor configure un token criptográficamente seguro en DASHBOARD_API_TOKEN."
            )
        if len(token) < MIN_TOKEN_LENGTH:
            raise RuntimeError(
                f"SECURITY ERROR: 'DASHBOARD_API_TOKEN' es demasiado corto ({len(token)} caracteres). "
                f"Debe tener al menos {MIN_TOKEN_LENGTH} caracteres para prevenir ataques de fuerza bruta."
            )
    else:
        if not token or token == INSECURE_DEFAULT_TOKEN:
            token = secrets.token_hex(32)

    return token


class TokenBucketRateLimiter:
    """Limitador de tasa por IP en memoria para proteger endpoints de mutación REST (Sprint 1: US-1.3)."""

    def __init__(self, capacity: int = 30, refill_rate_per_sec: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self._tokens: Dict[str, float] = {}
        self._last_check: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        with self._lock:
            last = self._last_check.get(client_ip, now)
            tokens = self._tokens.get(client_ip, float(self.capacity))
            elapsed = now - last
            tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)
            self._last_check[client_ip] = now
            if tokens >= 1.0:
                self._tokens[client_ip] = tokens - 1.0
                return True
            else:
                self._tokens[client_ip] = tokens
                return False


try:
    API_SECRET_TOKEN = resolve_and_validate_token(enforce_production=False)
except Exception:
    API_SECRET_TOKEN = secrets.token_hex(32)

rate_limiter = TokenBucketRateLimiter(capacity=30, refill_rate_per_sec=2.0)

# Orígenes CORS estrictos configurables (nunca wildcard '*')
RAW_ALLOWED_ORIGINS = os.getenv(
    "DASHBOARD_ALLOWED_ORIGINS",
    "http://127.0.0.1:8088,http://localhost:8088,http://127.0.0.1:8081,http://localhost:8081"
)
ALLOWED_ORIGINS: Set[str] = {orig.strip() for orig in RAW_ALLOWED_ORIGINS.split(",") if orig.strip()}


class CockpitAPIHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP y verificador de seguridad defensivo (compatibilidad de suite de seguridad)."""

    def _check_auth(self) -> bool:
        """Verifica el token de autorización Bearer de forma segura en tiempo constante."""
        auth_header = self.headers.get("Authorization", "").strip() if hasattr(self, "headers") and self.headers else ""
        expected = f"Bearer {API_SECRET_TOKEN}"
        if auth_header and hmac.compare_digest(auth_header, expected):
            return True
        self._send_json({"error": "No autorizado. Token Bearer requerido o inválido."}, status_code=401)
        return False

    def do_POST(self):
        client_ip = self.client_address[0] if hasattr(self, "client_address") and self.client_address else "127.0.0.1"
        if not rate_limiter.is_allowed(client_ip):
            self._send_json(
                {"error": "Límite de peticiones excedido (429 Too Many Requests). Espere antes de reintentar."},
                status_code=429
            )
            return

        if not self._check_auth():
            return

        self._send_json({"status": "ok", "message": "Procesado"})

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        if hasattr(self, "send_response"):
            self.send_response(status_code)
        if hasattr(self, "send_header"):
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))

            client_origin = self.headers.get("Origin", "").strip() if hasattr(self, "headers") and self.headers else ""
            if client_origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", client_origin)
                self.send_header("Vary", "Origin")
            else:
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8088")

            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self'")
        if hasattr(self, "end_headers"):
            self.end_headers()
        if hasattr(self, "wfile") and hasattr(self.wfile, "write"):
            self.wfile.write(body)
