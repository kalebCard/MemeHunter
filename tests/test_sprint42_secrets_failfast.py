"""
tests/test_sprint42_secrets_failfast.py - Certificación de Seguridad de Secretos y Fail-Fast (PB-140).
"""

import os
import pytest
from unittest.mock import patch

from client.freqtrade_client import FreqtradeRestClient
from portfolio.secrets_vault import validate_production_secrets, get_vault


def test_freqtrade_client_no_hardcoded_credentials(monkeypatch):
    """PB-140: Verifica que FreqtradeRestClient no posea passwords hardcodeadas."""
    # Limpiar variables de entorno
    monkeypatch.delenv("FREQTRADE_API_PASSWORD", raising=False)
    monkeypatch.delenv("FREQTRADE_API_USER", raising=False)
    monkeypatch.delenv("FREQTRADE_API_TOKEN", raising=False)

    # Limpiar caché de vault
    vault = get_vault()
    vault._secrets_cache.pop("FREQTRADE_API_PASSWORD", None)

    client = FreqtradeRestClient(password=None)
    # No debe ser jamás el valor inseguro MemeHunter2026!
    assert client.password != "MemeHunter2026!"
    assert client.password == ""


def test_freqtrade_client_reads_from_vault_or_env(monkeypatch):
    """PB-140: Verifica lectura de credenciales desde vault o variable de entorno."""
    monkeypatch.setenv("FREQTRADE_API_PASSWORD", "SuperSecureProdSecret_2026$#")
    client = FreqtradeRestClient()
    assert client.password == "SuperSecureProdSecret_2026$#"


def test_validate_production_secrets_status(monkeypatch):
    """PB-140: Verifica auditoría no destructiva de secretos requeridos."""
    monkeypatch.setenv("BINANCE_API_KEY", "real_key_abc")
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    monkeypatch.delenv("FREQTRADE_API_PASSWORD", raising=False)

    status = validate_production_secrets(
        required_keys=["BINANCE_API_KEY", "BINANCE_API_SECRET", "FREQTRADE_API_PASSWORD"],
        fail_fast=False
    )
    assert status["BINANCE_API_KEY"] is True
    assert status["BINANCE_API_SECRET"] is False
    assert status["FREQTRADE_API_PASSWORD"] is False


def test_validate_production_secrets_fail_fast_raises(monkeypatch):
    """PB-140: Verifica que en modo fail_fast=True lance RuntimeError si faltan secretos."""
    monkeypatch.delenv("CRITICAL_SECRET_X", raising=False)

    with pytest.raises(RuntimeError, match="Fallo de seguridad Fail-Fast"):
        validate_production_secrets(required_keys=["CRITICAL_SECRET_X"], fail_fast=True)
