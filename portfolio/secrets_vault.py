"""
secrets_vault.py - Gestor Criptográfico de Secretos y API Keys en Reposo (Sprint 1: US-1.2).
Implementa:
- Cifrado autenticado AES-256-GCM para almacenamiento seguro de credenciales.
- Derivación robusta de claves maestras mediante PBKDF2-HMAC-SHA256 (100,000 iteraciones).
- Respaldo atómico de secretos en 'user_data/.secrets.vault'.
- Acceso unificado con fallback a variables de entorno para compatibilidad transparente.
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger("SecretVaultManager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VAULT_PATH = os.path.join(BASE_DIR, "user_data", ".secrets.vault")


class SecretVaultManager:
    """
    Gestor de bóveda de secretos con cifrado autenticado AES-256-GCM.
    Protege API keys de exchanges y proveedores de IA frente a exposición en disco.
    """

    SALT_SIZE = 16
    NONCE_SIZE = 12

    def __init__(self, master_password: Optional[str] = None, vault_file: Optional[str] = None):
        self.vault_file = vault_file or DEFAULT_VAULT_PATH
        self.master_password = master_password or os.getenv("VAULT_MASTER_KEY", "")
        self._secrets_cache: Dict[str, str] = {}
        self._is_loaded = False

        if self.master_password and os.path.exists(self.vault_file):
            try:
                self.load_vault()
            except Exception as e:
                logger.warning(f"No se pudo descifrar la bóveda con la clave provista: {e}")

    def _derive_key(self, salt: bytes) -> bytes:
        """Deriva una clave simétrica de 256 bits (32 bytes) a partir de la contraseña maestra."""
        if not self.master_password:
            raise ValueError("No se ha configurado la contraseña o clave maestra (VAULT_MASTER_KEY).")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(self.master_password.encode("utf-8"))

    def encrypt_payload(self, data: Dict[str, Any]) -> bytes:
        """Cifra un diccionario estructurado usando AES-256-GCM y empaqueta salt + nonce + ciphertext."""
        salt = os.urandom(self.SALT_SIZE)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(self.NONCE_SIZE)

        plaintext = json.dumps(data).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        payload = {
            "version": 1,
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        return json.dumps(payload, indent=2).encode("utf-8")

    def decrypt_payload(self, raw_bytes: bytes) -> Dict[str, Any]:
        """Descifra el payload en formato JSON autenticado con AES-256-GCM."""
        payload = json.loads(raw_bytes.decode("utf-8"))
        salt = base64.b64decode(payload["salt"])
        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])

        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))

    def save_vault(self) -> None:
        """Persiste la caché de secretos de forma atómica en el archivo cifrado."""
        os.makedirs(os.path.dirname(self.vault_file), exist_ok=True)
        encrypted_bytes = self.encrypt_payload(self._secrets_cache)
        tmp_file = f"{self.vault_file}.tmp"
        with open(tmp_file, "wb") as f:
            f.write(encrypted_bytes)
        os.replace(tmp_file, self.vault_file)
        logger.info(f"Bóveda cifrada guardada exitosamente en {self.vault_file}")

    def load_vault(self) -> None:
        """Carga y descifra los secretos almacenados en el archivo de bóveda."""
        if not os.path.exists(self.vault_file):
            return
        with open(self.vault_file, "rb") as f:
            raw_bytes = f.read()
        self._secrets_cache = self.decrypt_payload(raw_bytes)
        self._is_loaded = True
        logger.info(f"Bóveda de secretos descifrada con éxito ({len(self._secrets_cache)} secretos cargados).")

    def set_secret(self, key: str, value: str) -> None:
        """Registra un nuevo secreto en la memoria y actualiza el archivo cifrado si hay clave maestra."""
        self._secrets_cache[key] = value
        if self.master_password:
            self.save_vault()

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Obtiene un secreto priorizando la bóveda cifrada en memoria.
        Si no se encuentra en la bóveda, consulta variables de entorno del sistema operativo.
        """
        # 1. Prioridad: Bóveda cifrada
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # 2. Respaldo secundario: Variable de entorno del sistema
        env_val = os.getenv(key)
        if env_val is not None:
            return env_val

        return default


# Instancia singleton predeterminada
_default_vault: Optional[SecretVaultManager] = None


def get_vault() -> SecretVaultManager:
    """Retorna la instancia global del gestor de bóveda."""
    global _default_vault
    if _default_vault is None:
        _default_vault = SecretVaultManager()
    return _default_vault


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Acceso rápido unificado para consultar un secreto del sistema."""
    return get_vault().get_secret(key, default)
