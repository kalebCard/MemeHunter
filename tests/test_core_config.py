"""
test_core_config.py - Pruebas Unitarias de Configuración Tipada (Pydantic Settings), Tipos y Fail-Fast.
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

# Asegurar importación de src/meme_hunter
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from meme_hunter.core.config import AppSettings, find_repo_root
from meme_hunter.core.exceptions import (
    MemeHunterError,
    ConfigurationError,
    RiskGateError,
    KillSwitchActivatedError,
)
from meme_hunter.core.types import (
    MarketRegime,
    StrategyStatus,
    HealthStatus,
    OrderSide,
    OrderType,
    SignalAction,
    AgentSignalDTO,
    TradeOrderDTO,
)


def test_repo_root_detection():
    """Valida que la raíz del repositorio se detecte correctamente."""
    root = find_repo_root()
    assert root.exists()
    assert (root / "user_data").exists() or (root / "pyproject.toml").exists()


def test_app_settings_test_mode():
    """Valida la instanciación de configuración en modo test con rutas canónicas."""
    settings = AppSettings(
        ENV="test",
        BINANCE_API_KEY="test_key",
        BINANCE_API_SECRET="test_secret",
        FREQTRADE_API_PASSWORD="test_password",
        DASHBOARD_SECRET_KEY="test_dash_key",
    )
    assert settings.ENV == "test"
    assert settings.APP_NAME == "Meme Hunter"
    assert settings.ROOT_DIR.exists()
    assert settings.MAX_CONCURRENT_POSITIONS == 3
    assert settings.GLOBAL_KILL_SWITCH_DRAWDOWN == 0.25

    # En modo test no debe fallar la preparación para producción
    settings.validate_production_readiness()


def test_app_settings_production_fail_fast_missing_secrets():
    """Valida que en modo 'production' aborte de inmediato si faltan credenciales críticas."""
    settings = AppSettings(
        ENV="production",
        BINANCE_API_KEY=None,
        BINANCE_API_SECRET=None,
        FREQTRADE_API_PASSWORD=None,
        DASHBOARD_SECRET_KEY=None,
    )
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_production_readiness()

    err_msg = str(exc_info.value)
    assert "Fail-Fast Violado" in err_msg
    assert "BINANCE_API_KEY" in err_msg
    assert "FREQTRADE_API_PASSWORD" in err_msg


def test_app_settings_production_success_with_secrets():
    """Valida que en modo 'production' sea exitoso cuando se proveen todos los secretos."""
    settings = AppSettings(
        ENV="production",
        BINANCE_API_KEY="valid_binance_key",
        BINANCE_API_SECRET="valid_binance_secret",
        FREQTRADE_API_PASSWORD="valid_freq_password",
        DASHBOARD_SECRET_KEY="valid_dashboard_secret",
    )
    # No debe levantar ninguna excepción
    settings.validate_production_readiness()
    assert settings.get_raw_secret(settings.BINANCE_API_KEY) == "valid_binance_key"


def test_domain_types_and_immutability():
    """Valida los contratos inmutables DTO de Pydantic v2."""
    sig = AgentSignalDTO(
        symbol="DOGE/USDT:USDT",
        signal_value=0.85,
        confidence=0.92,
        regime=MarketRegime.BULL_MOMENTUM,
        action=SignalAction.ENTER_LONG,
        metadata={"indicator": "EMA_CROSS"},
    )
    assert sig.symbol == "DOGE/USDT:USDT"
    assert sig.signal_value == 0.85
    assert sig.regime == MarketRegime.BULL_MOMENTUM

    # Intentar mutar debe disparar error por frozen=True
    with pytest.raises(ValidationError):
        sig.signal_value = -0.50  # type: ignore

    # Intentar pasar campos fuera del contrato debe fallar por extra="forbid"
    with pytest.raises(ValidationError):
        AgentSignalDTO(
            symbol="PEPE/USDT:USDT",
            signal_value=0.1,
            confidence=0.5,
            regime=MarketRegime.CHOPPY_RANGE,
            campo_desconocido=123,  # type: ignore
        )


def test_trade_order_dto_validation():
    """Valida los límites y tipos de las órdenes de trading."""
    order = TradeOrderDTO(
        symbol="SHIB/USDT:USDT",
        side=OrderSide.SHORT,
        order_type=OrderType.MARKET,
        amount=1000.0,
        stoploss_price=0.000015,
        leverage=1.5,
    )
    assert order.side == OrderSide.SHORT
    assert order.leverage == 1.5

    # Cantidad <= 0 debe fallar
    with pytest.raises(ValidationError):
        TradeOrderDTO(
            symbol="SHIB/USDT:USDT",
            side=OrderSide.SHORT,
            order_type=OrderType.MARKET,
            amount=-10.0,
        )


def test_exception_hierarchy():
    """Valida que toda la jerarquía de excepciones herede de MemeHunterError."""
    assert issubclass(ConfigurationError, MemeHunterError)
    assert issubclass(RiskGateError, MemeHunterError)
    assert issubclass(KillSwitchActivatedError, RiskGateError)
    assert issubclass(KillSwitchActivatedError, MemeHunterError)
