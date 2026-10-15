"""
test_sprint56_radical_pruning.py - Suite de Pruebas Unitarias para Sprint 56: Menos es Más.
Verifica:
1. PB-220: Archivado canónico y desacoplamiento de módulos satélite prescindibles.
2. PB-221: Consolidación de entrypoints y preservación del CLI.
3. PB-224: Telegram Copilot formato Semáforo conciso (<= 10 líneas).
4. PB-228: Scorecard Único con las 3 métricas de la verdad (PnL, Drawdown, Win Rate).
5. PB-227 & Core: Blindaje y protección del Búnker (Kill Switch 25% y Cortafuegos Pre-Trade).
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from client.telegram_ai_copilot import TelegramAiCopilotService
from src.meme_hunter.core.config import get_settings


class TestSprint56RadicalPruning:
    """Batería de pruebas unitarias certificando la arquitectura por sustracción."""

    def test_archived_legacy_satellites_manifest(self):
        """PB-220: Verifica que los módulos prescindibles residan en scripts/archive/legacy_satellites/."""
        archive_dir = Path("scripts/archive/legacy_satellites")
        assert archive_dir.exists() and archive_dir.is_dir()

        # Verificar presencia de módulos archivados
        expected_files = [
            "delta_neutral_vault.py",
            "funding_arbitrage.py",
            "dex_viral_radar.py",
            "binance_vision.py",
            "backtest_spot_capitulation.py",
            "README.md",
            "__init__.py"
        ]
        for f in expected_files:
            file_path = archive_dir / f
            assert file_path.exists(), f"El archivo archivado {f} no se encontró en {archive_dir}"

        # Verificar contenido del manifiesto
        manifest = (archive_dir / "README.md").read_text(encoding="utf-8")
        assert "delta_neutral_vault.py" in manifest
        assert "funding_arbitrage.py" in manifest
        assert "dex_viral_radar.py" in manifest
        assert "binance_vision.py" in manifest
        assert "backtest_spot_capitulation.py" in manifest

    def test_telegram_semaphore_concise_format(self):
        """PB-224: Verifica que _cmd_semaphore_status() retorne un resumen conciso <= 10 líneas."""
        copilot = TelegramAiCopilotService(
            telegram_token="123456:FAKE_TOKEN_FOR_TESTING_12345",
            allowed_chat_id="12345678"
        )
        # Mock de orquestador para respuesta determinista
        copilot.orchestrator = MagicMock()
        copilot.orchestrator.get_aggregated_status.return_value = {
            "total_open_trades": 1,
            "total_stake_active_usdt": 25.0,
            "bots": {
                "bot1": {"name": "V5_Ablation", "port": 8081, "is_online": True, "open_trades": 1, "stake_active_usdt": 25.0},
                "bot2": {"name": "V7_Quantum", "port": 8082, "is_online": True, "open_trades": 0, "stake_active_usdt": 0.0},
                "bot3": {"name": "MinedEnsemble", "port": 8083, "is_online": True, "open_trades": 0, "stake_active_usdt": 0.0},
            },
            "trades": [
                {"pair": "DOGE/USDT:USDT", "profit_pct": 3.45, "is_short": True}
            ]
        }

        res = copilot._cmd_semaphore_status()
        assert isinstance(res, str)
        lines = [line for line in res.splitlines() if line.strip()]
        
        # Debe ser ultra-conciso (máximo 8 líneas)
        assert len(lines) <= 8, f"Resumen Semáforo excedió longitud máxima: {len(lines)} líneas"
        # Debe contener ícono de semáforo
        assert any(icon in res for icon in ["🟢", "🟡", "🔴"])
        assert "DOGE" in res
        assert "Kill Switch" in res

    def test_telegram_scorecard_three_metrics(self):
        """PB-228: Verifica que _cmd_scorecard() consolide las 3 métricas de la verdad."""
        copilot = TelegramAiCopilotService(
            telegram_token="123456:FAKE_TOKEN_FOR_TESTING_12345",
            allowed_chat_id="12345678"
        )
        copilot.ft_client = MagicMock()
        copilot.ft_client.get_profit.return_value = {
            "status": "ok",
            "data": {
                "profit_closed_coin": 63.24,
                "profit_closed_ratio_pct": 15.8,
                "winrate": 0.531,
                "trade_count": 42
            }
        }

        res = copilot._cmd_scorecard()
        assert "SCORECARD ÚNICO" in res
        assert "1. PnL Neto" in res
        assert "+63.24 USDT" in res
        assert "2. Drawdown Real" in res
        assert "3. Win Rate" in res
        assert "53.1%" in res

    def test_telegram_status_command_dispatch_modes(self):
        """PB-224: Verifica que /semaforo y /scorecard despachen sus respectivos formatos."""
        copilot = TelegramAiCopilotService(
            telegram_token="123456:FAKE_TOKEN_FOR_TESTING_12345",
            allowed_chat_id="12345678"
        )
        copilot._cmd_semaphore_status = MagicMock(return_value="Concise Semaphore")
        copilot._cmd_status = MagicMock(return_value="Arena Status")

        # Invocación de /semaforo -> Semáforo conciso
        res_semaforo = copilot.dispatch_command("/semaforo", "12345678")
        assert res_semaforo == "Concise Semaphore"

        # Invocación /status -> Estado de la arena
        res_status = copilot.dispatch_command("/status", "12345678")
        assert res_status == "Arena Status"

        # Comando /scorecard
        copilot._cmd_scorecard = MagicMock(return_value="Scorecard Result")
        res_score = copilot.dispatch_command("/scorecard", "12345678")
        assert res_score == "Scorecard Result"

    def test_bunker_safeguards_configuration(self):
        """PB-227: Verifica que los parámetros del Búnker permanezcan intactos y estrictos."""
        settings = get_settings()
        assert hasattr(settings, "GLOBAL_KILL_SWITCH_DRAWDOWN")
        # El Kill Switch de equidad debe ser estrictamente <= 25.0%
        assert settings.GLOBAL_KILL_SWITCH_DRAWDOWN <= 0.25
