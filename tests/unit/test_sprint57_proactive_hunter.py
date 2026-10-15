"""
test_sprint57_proactive_hunter.py - Pruebas Unitarias del Motor Proactivo de I+D de Hermes (Sprint 57: PB-230 a PB-236).
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.meme_hunter.hermes.proactive_hunter import HermesProactiveHunter
from src.meme_hunter.hermes.hermes_operator import HermesOperator
from client.ai_copilot_engine import QuantAiCopilotEngine
from client.telegram_ai_copilot import TelegramAiCopilotService


@pytest.fixture
def temp_state_file(tmp_path):
    return str(tmp_path / "proactive_state.json")


def test_proactive_hunter_init(temp_state_file):
    """PB-230: Verifica la inicialización limpia y la persistencia de estado del motor proactivo."""
    hunter = HermesProactiveHunter(state_path=temp_state_file, target_sharpe=1.8, target_winrate=50.0)
    assert hunter.enabled is True
    assert hunter.target_sharpe == 1.8
    assert hunter.target_winrate == 50.0

    st = hunter.get_status()
    assert st["enabled"] is True
    assert st["is_busy"] is False
    assert st["total_cycles_run"] == 0


def test_proactive_hypotheses_per_regime(temp_state_file):
    """PB-231: Verifica que las fórmulas sugeridas se adapten a la dinámica del régimen."""
    hunter = HermesProactiveHunter(state_path=temp_state_file)

    chop_formulas = hunter._get_hypotheses_for_regime("RANGE_CHOP")
    assert len(chop_formulas) >= 2
    assert any("vwap" in f or "rvol" in f for f in chop_formulas)

    bear_formulas = hunter._get_hypotheses_for_regime("BEAR_CASCADE")
    assert len(bear_formulas) >= 2
    assert any("neg(" in f or "ts_delta" in f for f in bear_formulas)

    bull_formulas = hunter._get_hypotheses_for_regime("BULL_PARABOLIC")
    assert len(bull_formulas) >= 2
    assert any("close" in f for f in bull_formulas)


def test_proactive_rnd_cycle_evaluation_and_deployment(temp_state_file):
    """PB-232 & PB-233: Verifica la evaluación vectorial, filtrado y auto-despliegue del candidato ganador."""
    mock_operator = MagicMock()
    mock_messenger = MagicMock()
    hunter = HermesProactiveHunter(
        operator=mock_operator,
        messenger=mock_messenger,
        state_path=temp_state_file,
        target_sharpe=1.5,
        target_winrate=50.0
    )

    # Mock de backtest que devuelve un candidato calificado
    mock_bt_result = {
        "status": "ok",
        "metrics": {
            "sharpe_ratio": 2.25,
            "win_rate_pct": 60.0,
            "total_return_pct": 28.5,
            "max_drawdown_pct": 3.8,
            "total_trades": 12,
            "profit_factor": 2.1
        }
    }

    with patch("meme_hunter.alpha.tester.run_strategy_backtest", return_value=mock_bt_result):
        with patch.object(hunter, "_deploy_winning_factor") as mock_deploy:
            mock_deploy.return_value = {"status": "ok", "factor_id": "HERMES_PROACTIVE_01", "reload_bot3": True}

            res = hunter.run_proactive_rnd_cycle(
                trigger_reason="unit_test_run",
                force_regime="RANGE_CHOP"
            )

            assert res["status"] == "ok"
            assert res["is_qualified"] is True
            assert res["best_candidate"]["sharpe_ratio"] == 2.25
            mock_deploy.assert_called_once()
            mock_messenger.send_executive_report.assert_called_once()

    st = hunter.get_status()
    assert st["total_cycles_run"] == 1
    assert st["last_regime"] == "RANGE_CHOP"


def test_alpha_decay_guardian(temp_state_file):
    """PB-234: Verifica que el guardián detecte pérdidas consecutivas y dispare reemplazo de estrategia."""
    mock_operator = MagicMock()
    mock_orch = MagicMock()
    mock_bot3 = MagicMock()
    # Simular 3 pérdidas consecutivas en Bot 3
    mock_bot3.get_profit.return_value = {
        "status": "ok",
        "data": {
            "losing_trades": 3,
            "winning_trades": 0,
            "profit_closed_coin": -3.20
        }
    }
    mock_orch.clients = {"bot_mined_ensemble": mock_bot3}
    mock_operator.orchestrator = mock_orch

    hunter = HermesProactiveHunter(operator=mock_operator, state_path=temp_state_file)

    with patch.object(hunter, "run_proactive_rnd_cycle") as mock_cycle:
        mock_cycle.return_value = {"status": "ok"}
        decay_res = hunter.check_alpha_decay_and_replace()

        assert decay_res["status"] == "decay_detected"
        mock_cycle.assert_called_once_with(trigger_reason="alpha_decay_replacement")


def test_operator_run_cycle_proactive_triggers(tmp_path):
    """PB-231: Verifica que HermesOperator active el disparador por cambio de régimen en run_cycle."""
    mem_file = str(tmp_path / "hermes_mem.json")
    mock_proactive = MagicMock()

    operator = HermesOperator(
        memory_path=mem_file,
        proactive_hunter=mock_proactive
    )

    # Simular historial con régimen anterior RANGE_CHOP
    operator.memory["regime_history"] = [
        {"timestamp": "2026-10-15T00:00:00Z", "regime": "RANGE_CHOP"}
    ]

    # Mock detector para devolver nuevo régimen BEAR_CASCADE
    operator.regime_detector = MagicMock()
    operator.regime_detector.detect_regime.return_value = {
        "regime": "BEAR_CASCADE",
        "confidence": 0.85,
        "recommended_allocations": {}
    }
    operator.orchestrator = MagicMock()
    operator.orchestrator.get_aggregated_status.return_value = {"total_open_trades": 0, "total_stake_active_usdt": 0.0}

    res = operator.run_cycle()
    assert res["regime_info"]["regime"] == "BEAR_CASCADE"
    mock_proactive.on_regime_shift.assert_called_once_with(new_regime="BEAR_CASCADE", old_regime="RANGE_CHOP")
    mock_proactive.check_alpha_decay_and_replace.assert_called_once()


def test_ai_copilot_engine_proactive_intent():
    """PB-235: Verifica que el motor cognitivo identifique frases de proactividad y laboratorio de I+D."""
    engine = QuantAiCopilotEngine()

    phrases = [
        "sé más proactivo en la búsqueda de dinero",
        "activa el laboratorio de i+d",
        "quiero que busques dinero activamente",
        "gestiona activamente estrategias",
        "estado del laboratorio",
        "/proactive",
        "/proactivo on",
        "/lab",
        "/rnd"
    ]
    for p in phrases:
        intent = engine.extract_intent_heuristic(p)
        assert intent["action"] == "proactive_rnd", f"Fallo en frase '{p}': {intent}"


def test_telegram_copilot_proactive_commands():
    """PB-235: Verifica el despacho y ejecución de los comandos /proactive y /lab en Telegram."""
    mock_ft = MagicMock()
    mock_ai = MagicMock()
    service = TelegramAiCopilotService(
        telegram_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        allowed_chat_id="99887766",
        freqtrade_client=mock_ft,
        ai_engine=mock_ai
    )

    mock_hunter = MagicMock()
    mock_hunter.get_status.return_value = {
        "enabled": True,
        "worker_alive": True,
        "total_cycles_run": 5,
        "deployed_factors_count": 2,
        "last_regime": "RANGE_CHOP",
        "current_live_factor": {"formula": "ts_rank(rvol, 14)", "sharpe_proxy": 2.1}
    }
    service.hermes_op = MagicMock()
    service.hermes_op.proactive_hunter = mock_hunter

    # Test /lab status
    status_reply = service.dispatch_command("/lab", chat_id="99887766")
    assert "LABORATORIO DE I+D PROACTIVO" in status_reply
    assert "RANGE_CHOP" in status_reply

    # Test /proactive on
    on_reply = service.dispatch_command("/proactive on", chat_id="99887766")
    assert "HERMES PROACTIVO ACTIVADO" in on_reply
    mock_hunter.start_worker.assert_called()

    # Test /proactive off
    off_reply = service.dispatch_command("/proactive off", chat_id="99887766")
    assert "HERMES PROACTIVO PAUSADO" in off_reply
    mock_hunter.stop_worker.assert_called()
