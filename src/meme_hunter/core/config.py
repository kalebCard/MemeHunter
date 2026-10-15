"""
meme_hunter.core.config - Configuración Centralizada 12-Factor con Pydantic Settings.
Implementa validación estricta de tipos, fail-fast en producción y resolución canónica de rutas.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, SecretStr, field_validator
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings
    def SettingsConfigDict(**kwargs):
        return kwargs

from meme_hunter.core.exceptions import ConfigurationError


def find_repo_root() -> Path:
    """Detecta la raíz absoluta del repositorio buscando marcas canónicas."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / "user_data").exists():
            return parent
    return Path.cwd().resolve()


REPO_ROOT = find_repo_root()


class AppSettings(BaseSettings):
    """Configuración tipada del sistema Meme Hunter (12-Factor App)."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Entorno y Metadatos
    ENV: str = Field(default="production", description="production | development | test")
    APP_NAME: str = Field(default="Meme Hunter")
    LOG_LEVEL: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR | CRITICAL")

    # Rutas Canónicas del Sistema
    ROOT_DIR: Path = Field(default_factory=lambda: REPO_ROOT)
    DATA_DIR: Path = Field(default_factory=lambda: REPO_ROOT / "user_data" / "data")
    STORAGE_DIR: Path = Field(default_factory=lambda: REPO_ROOT / "storage")
    DB_PATH: Path = Field(default_factory=lambda: REPO_ROOT / "storage" / "meme_hunter.db")

    # Credenciales de Binance Futures / Spot
    BINANCE_API_KEY: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("BINANCE_API_KEY", "FREQTRADE__EXCHANGE__KEY"),
        description="API Key de Binance"
    )
    BINANCE_API_SECRET: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("BINANCE_API_SECRET", "FREQTRADE__EXCHANGE__SECRET"),
        description="Secret de Binance"
    )
    BINANCE_TESTNET: bool = Field(default=False)

    # Conexión Freqtrade REST API
    FREQTRADE_API_URL: str = Field(default="http://127.0.0.1:8081")
    FREQTRADE_API_USERNAME: str = Field(
        default="admin",
        validation_alias=AliasChoices("FREQTRADE_API_USERNAME", "FREQTRADE__API_SERVER__USERNAME")
    )
    FREQTRADE_API_PASSWORD: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("FREQTRADE_API_PASSWORD", "FREQTRADE__API_SERVER__PASSWORD")
    )

    # Cockpit Dashboard & Seguridad ASGI
    DASHBOARD_HOST: str = Field(default="127.0.0.1")
    DASHBOARD_PORT: int = Field(default=8088)
    DASHBOARD_SECRET_KEY: Optional[SecretStr] = Field(default=None)

    # Cognición IA (OpenRouter / DeepSeek / Claude)
    OPENROUTER_API_KEY: Optional[SecretStr] = Field(default=None)

    # Alertas de Telemetría (Telegram)
    TELEGRAM_TOKEN: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_TOKEN", "FREQTRADE__TELEGRAM__TOKEN")
    )
    TELEGRAM_CHAT_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_CHAT_ID", "FREQTRADE__TELEGRAM__CHAT_ID")
    )

    # Parámetros de Riesgo Institucional
    MAX_CONCURRENT_POSITIONS: int = Field(default=3, ge=1, le=10)
    HARD_STOPLOSS_RATIO: float = Field(default=-0.10, le=-0.01)
    GLOBAL_KILL_SWITCH_DRAWDOWN: float = Field(default=0.25, gt=0.05, le=0.50)

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in {"production", "development", "test"}:
            raise ValueError(f"ENV debe ser 'production', 'development' o 'test'. Recibido: {v}")
        return v_clean

    def validate_production_readiness(self) -> None:
        """
        Validación Fail-Fast: En entorno 'production', aborta si faltan secretos críticos.
        Elimina el uso accidental de contraseñas por defecto en producción.
        """
        if self.ENV != "production":
            return

        missing = []
        if not self.BINANCE_API_KEY or not self.BINANCE_API_KEY.get_secret_value():
            missing.append("BINANCE_API_KEY")
        if not self.BINANCE_API_SECRET or not self.BINANCE_API_SECRET.get_secret_value():
            missing.append("BINANCE_API_SECRET")
        if not self.FREQTRADE_API_PASSWORD or not self.FREQTRADE_API_PASSWORD.get_secret_value():
            missing.append("FREQTRADE_API_PASSWORD")
        if not self.DASHBOARD_SECRET_KEY or not self.DASHBOARD_SECRET_KEY.get_secret_value():
            missing.append("DASHBOARD_SECRET_KEY")

        if missing:
            raise ConfigurationError(
                f"Fail-Fast Violado: El entorno está configurado como 'production' pero "
                f"faltan los siguientes secretos obligatorios: {', '.join(missing)}. "
                f"Configure estas variables en su archivo .env o variables de entorno."
            )

    def get_raw_secret(self, secret: Optional[SecretStr]) -> Optional[str]:
        """Obtiene el valor plano de un SecretStr de manera segura para clientes externos (CCXT)."""
        return secret.get_secret_value() if secret else None


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Factoría Singleton de configuración."""
    s = AppSettings()
    return s
