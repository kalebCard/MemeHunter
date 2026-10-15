"""
test_security_remediation_sprint54.py - Suite de Pruebas Unitarias de Seguridad y Remediación (Sprint 54).
Verifica:
1. PB-200: Firewall Fail-Closed en Telegram Copilot.
2. PB-201: Ausencia de contraseñas por defecto hardcodeadas.
3. PB-202: Cero métricas alucinadas en el bucle de Hermes.
4. PB-203: Sincronización Thread-Safe en memoria episódica.
5. PB-204: Invocación válida de run_cycle en la incubadora.
6. PB-208: Despacho de comandos desacoplado vía Command Pattern.
"""

import os
import json
import threading
import pytest
from unittest.mock import MagicMock, patch

from client.telegram_ai_copilot import TelegramAiCopilotService
from client.multi_bot_orchestrator import MultiBotOrchestratorClient
from src.meme_hunter.hermes.hermes_operator import HermesOperator
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator, SelfHealingCycleReport
from src.meme_hunter.api.routers.quant import trigger_incubator_loop


class TestSprint54SecurityRemediation:
    """Batería de pruebas de verificación para los entregables de Sprint 54."""

    def test_telegram_fail_closed_zero_trust(self):
        """PB-200: Verifica que si no hay chat_id configurado, is_authorized() rechaza todas las peticiones."""
        # 1. Caso sin chat_id configurado (vacío)
        copilot_unconfigured = TelegramAiCopilotService(
            telegram_token="123456:FAKE_TOKEN_FOR_TESTING_12345",
            allowed_chat_id=""
        )
        assert copilot_unconfigured.is_authorized("123456") is False
        assert copilot_unconfigured.is_authorized("any_chat_id") is False
        assert copilot_unconfigured.is_authorized(None) is False

        # 2. Caso con chat_id válido configurado
        copilot_configured = TelegramAiCopilotService(
            telegram_token="123456:FAKE_TOKEN_FOR_TESTING_12345",
            allowed_chat_id="998877"
        )
        assert copilot_configured.is_authorized("998877") is True
        assert copilot_configured.is_authorized("998878") is False
        assert copilot_configured.is_authorized("attacker_id") is False

    def test_no_hardcoded_passwords_in_clients(self, monkeypatch):
        """PB-201: Verifica que no existan contraseñas por defecto hardcodeadas si el entorno está vacío."""
        monkeypatch.delenv("FREQTRADE__API_SERVER__PASSWORD", raising=False)
        monkeypatch.delenv("FREQTRADE_API_PASSWORD", raising=False)

        with patch("portfolio.secrets_vault.get_secret", return_value=""):
            orch = MultiBotOrchestratorClient(password="")
            assert orch.password != "MemeHunter2026!"
            assert orch.password == ""

    def test_hermes_zero_metric_hallucination(self, tmp_path):
        """PB-202: Verifica que Hermes no invente Sharpe ratios positivos si el backtest falla."""
        mem_file = str(tmp_path / "hermes_mem.json")
        operator = HermesOperator(memory_path=mem_file)

        mock_synthesizer = MagicMock()
        mock_synthesizer.synthesize_alphas.return_value = [
            ("ts_rank(volume, 10)", MagicMock())
        ]

        # Simular que run_strategy_backtest lanza un error
        def mock_failing_backtest(*args, **kwargs):
            raise RuntimeError("Error en datos de mercado")

        with patch("mining.llm_alpha_generator.LLMAlphaSynthesizer", return_value=mock_synthesizer):
            with patch("meme_hunter.alpha.tester.run_strategy_backtest", side_effect=mock_failing_backtest):
                res = operator.run_autonomous_refinement_loop(
                    goal_text="Test Zero Hallucination",
                    max_iterations=1,
                    target_sharpe=2.0
                )

        # Debe haber evaluado el candidato pero con Sharpe 0.0 (descalificado, no inventado)
        assert res["status"] == "ok"
        best_cand = res["best_candidate"]
        assert best_cand is not None
        assert best_cand["sharpe_ratio"] == 0.0
        assert best_cand["is_qualified"] is False

    def test_hermes_thread_safe_memory_locking(self, tmp_path):
        """PB-203: Verifica que el guardado concurrente de memoria de Hermes no colisione ni corrompa el JSON."""
        mem_file = str(tmp_path / "concurrent_mem.json")
        operator = HermesOperator(memory_path=mem_file)

        errors = []

        def worker_task(worker_id: int):
            try:
                for i in range(20):
                    with operator._memory_lock:
                        operator.memory["total_cycles_run"] += 1
                        operator.memory["actions_history"].append(f"Worker {worker_id} - Iter {i}")
                    operator._save_memory()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(tid,)) for tid in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Se produjeron errores de concurrencia: {errors}"
        assert os.path.exists(mem_file)

        with open(mem_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_cycles_run"] == 100
        assert len(data["actions_history"]) == 100

    def test_autonomous_orchestrator_run_cycle_exists(self):
        """PB-204: Verifica que run_cycle() exista en AutonomousPortfolioOrchestrator y devuelva SelfHealingCycleReport."""
        orchestrator = AutonomousPortfolioOrchestrator()
        assert hasattr(orchestrator, "run_cycle")
        report = orchestrator.run_cycle()
        assert isinstance(report, SelfHealingCycleReport)
        assert hasattr(report, "cycle_timestamp")
        assert hasattr(report, "actions_taken")

    def test_quant_trigger_incubator_loop_endpoint(self):
        """PB-204: Verifica que trigger_incubator_loop() ejecute run_cycle() real y retorne status success."""
        res = trigger_incubator_loop()
        assert res["status"] == "success"
        assert "report" in res
        assert "cycle_timestamp" in res["report"]
        assert "actions_taken" in res["report"]

    def test_telegram_command_registry_dispatch(self):
        """PB-208: Verifica que dispatch_command utilice el Command Registry y resuelva comandos clave."""
        copilot = TelegramAiCopilotService(
            telegram_token="123456:TEST_TOKEN_1234567890",
            allowed_chat_id="112233"
        )
        assert "/status" in copilot._command_registry
        assert "/killswitch" in copilot._command_registry
        assert "/rebalance" in copilot._command_registry
        assert "/mine" in copilot._command_registry

        # Verificar respuesta determinista sin llamar a la red
        copilot._cmd_help = MagicMock(return_value="Mocked Help")
        res = copilot.dispatch_command("/help", "112233")
        assert res == "Mocked Help"
        copilot._cmd_help.assert_called_once()
