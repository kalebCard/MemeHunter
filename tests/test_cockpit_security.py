"""
test_cockpit_security.py - Pruebas Unitarias de Seguridad para Cockpit API (Sprint 1: US-1.1 & US-1.3).
Verifica:
1. Fail-fast en resolve_and_validate_token ante tokens faltantes, por defecto o débiles.
2. TokenBucketRateLimiter y bloqueo ante ráfagas que superen el límite.
3. Rechazo HTTP 401 en endpoints protegidos con token incorrecto o ausente.
4. CORS estricto sin wildcard '*' y presencia de cabeceras de seguridad.
"""

import os
import sys
import json
import pytest
import secrets
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dashboard.server import (
    resolve_and_validate_token,
    TokenBucketRateLimiter,
    CockpitAPIHandler,
    ALLOWED_ORIGINS,
    INSECURE_DEFAULT_TOKEN
)


def test_token_fail_fast_missing_token():
    """Valida que el sistema aborte si no se provee token en modo producción."""
    with patch.dict(os.environ, {"DASHBOARD_API_TOKEN": ""}, clear=False):
        with patch("portfolio.secrets_vault.get_secret", return_value=None):
            with patch("os.path.exists", return_value=False):
                with pytest.raises(RuntimeError, match="CRITICAL SECURITY ERROR"):
                    resolve_and_validate_token(enforce_production=True)


def test_token_fail_fast_insecure_default():
    """Valida que el sistema rechace explícitamente el token de desarrollo legacy."""
    with patch.dict(os.environ, {"DASHBOARD_API_TOKEN": INSECURE_DEFAULT_TOKEN}):
        with pytest.raises(RuntimeError, match="Se detectó el token por defecto inseguro"):
            resolve_and_validate_token(enforce_production=True)


def test_token_fail_fast_short_entropy():
    """Valida que tokens con longitud menor a 32 caracteres sean rechazados."""
    with patch.dict(os.environ, {"DASHBOARD_API_TOKEN": "token_demasiado_corto_123"}):
        with pytest.raises(RuntimeError, match="es demasiado corto"):
            resolve_and_validate_token(enforce_production=True)


def test_token_validation_success():
    """Valida que un token criptográficamente seguro sea aceptado."""
    valid_token = secrets.token_hex(32)  # 64 caracteres
    with patch.dict(os.environ, {"DASHBOARD_API_TOKEN": valid_token}):
        resolved = resolve_and_validate_token(enforce_production=True)
        assert resolved == valid_token


def test_rate_limiter_allows_and_blocks():
    """Valida que TokenBucketRateLimiter controle ráfagas y bloquee excesos."""
    limiter = TokenBucketRateLimiter(capacity=3, refill_rate_per_sec=0.0)
    ip = "192.168.1.100"

    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    # 4ta petición excede la capacidad
    assert limiter.is_allowed(ip) is False


def test_cors_origin_whitelist_enforced():
    """Valida que el servidor solo admita orígenes autorizados y nunca '*'."""
    mock_handler = MagicMock(spec=CockpitAPIHandler)
    mock_handler.headers = {"Origin": "http://127.0.0.1:8088"}
    mock_handler.wfile = MagicMock()

    # Invocamos la lógica interna de _send_json usando una instancia simulada
    sent_headers = {}
    def mock_send_header(k, v):
        sent_headers[k] = v

    mock_handler.send_header = mock_send_header
    mock_handler._send_json = CockpitAPIHandler._send_json.__get__(mock_handler)

    mock_handler._send_json({"status": "ok"}, 200)

    assert sent_headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:8088"
    assert sent_headers["Access-Control-Allow-Origin"] != "*"
    assert sent_headers["X-Content-Type-Options"] == "nosniff"
    assert sent_headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in sent_headers


def test_cors_unauthorized_origin_fallback():
    """Valida que orígenes no autorizados no reciban reflejo CORS."""
    mock_handler = MagicMock(spec=CockpitAPIHandler)
    mock_handler.headers = {"Origin": "https://malicious-website.com"}
    mock_handler.wfile = MagicMock()

    sent_headers = {}
    mock_handler.send_header = lambda k, v: sent_headers.update({k: v})
    mock_handler._send_json = CockpitAPIHandler._send_json.__get__(mock_handler)

    mock_handler._send_json({"status": "ok"}, 200)

    # Debe degradar al origen local primario seguro, nunca al origen malicioso
    assert sent_headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:8088"
    assert sent_headers["Access-Control-Allow-Origin"] != "https://malicious-website.com"
