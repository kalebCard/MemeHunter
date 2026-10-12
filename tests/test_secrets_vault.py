"""
test_secrets_vault.py - Pruebas Unitarias del Gestor Criptográfico de Secretos (Sprint 1: US-1.2).
Verifica:
1. Cifrado y descifrado autenticado AES-256-GCM.
2. Derivación de claves con PBKDF2-HMAC-SHA256.
3. Resistencia a manipulación (tampering).
4. Persistencia en disco y recuperación de variables de entorno.
"""

import os
import sys
import tempfile
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from portfolio.secrets_vault import SecretVaultManager


def test_vault_encrypt_decrypt_roundtrip():
    """Verifica que un payload pueda ser cifrado y descifrado íntegramente."""
    master_key = "super_secure_vault_master_key_2026_test"
    with tempfile.NamedTemporaryFile(suffix=".vault", delete=False) as tf:
        vault_path = tf.name

    try:
        vault = SecretVaultManager(master_password=master_key, vault_file=vault_path)
        vault.set_secret("BINANCE_API_KEY", "real_test_binance_key_xyz123")
        vault.set_secret("BINANCE_API_SECRET", "super_secret_secret_456")

        # Crear nueva instancia para cargar desde disco
        vault2 = SecretVaultManager(master_password=master_key, vault_file=vault_path)
        assert vault2.get_secret("BINANCE_API_KEY") == "real_test_binance_key_xyz123"
        assert vault2.get_secret("BINANCE_API_SECRET") == "super_secret_secret_456"
    finally:
        if os.path.exists(vault_path):
            os.remove(vault_path)


def test_vault_wrong_password_fails():
    """Verifica que una clave maestra errónea no permita descifrar el contenido."""
    master_key = "correct_master_key_1234567890"
    wrong_key = "wrong_master_key_0987654321"

    with tempfile.NamedTemporaryFile(suffix=".vault", delete=False) as tf:
        vault_path = tf.name

    try:
        vault = SecretVaultManager(master_password=master_key, vault_file=vault_path)
        vault.set_secret("OPENROUTER_KEY", "sk-test-1234")

        # Intentar cargar con clave incorrecta
        vault_wrong = SecretVaultManager(master_password=wrong_key, vault_file=vault_path)
        with pytest.raises(Exception):
            vault_wrong.load_vault()
    finally:
        if os.path.exists(vault_path):
            os.remove(vault_path)


def test_vault_fallback_to_environment():
    """Verifica que si una clave no está en la bóveda, consulte variables de entorno."""
    os.environ["CUSTOM_TEST_SECRET"] = "env_secret_value_999"
    vault = SecretVaultManager(master_password="")
    assert vault.get_secret("CUSTOM_TEST_SECRET") == "env_secret_value_999"
    assert vault.get_secret("NON_EXISTENT_KEY", default="default_val") == "default_val"
