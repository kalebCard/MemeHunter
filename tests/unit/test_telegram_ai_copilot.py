"""
test_telegram_ai_copilot.py - Pruebas Unitarias del Copilot Cuantitativo en Telegram (Sprint 50: PB-174).
"""

import pytest
from unittest.mock import MagicMock, patch

from client.freqtrade_client import FreqtradeRestClient
from client.ai_copilot_engine import QuantAiCopilotEngine
from client.telegram_ai_copilot import TelegramAiCopilotService, TelegramBotClient
from client.multi_bot_orchestrator import MultiBotOrchestratorClient


@pytest.fixture
def mock_ft_client():
    client = MagicMock(spec=FreqtradeRestClient)
    client.ping.return_value = {"status": "ok", "data": {"status": "pong"}}
    client.get_status.return_value = {
        "status": "ok",
        "data": [
            {
                "trade_id": 1,
                "pair": "DOGE/USDT:USDT",
                "profit_pct": 2.50,
                "stake_amount": 50.0,
                "is_short": True,
                "open_date_hum": "2h ago"
            }
        ]
    }
    client.get_profit.return_value = {
        "status": "ok",
        "data": {
            "trade_count": 10,
            "profit_closed_coin": 45.20,
            "profit_closed_ratio_pct": 4.52,
            "winrate": 0.70,
            "winning_trades": 7,
            "losing_trades": 3,
            "best_pair": "PEPE/USDT:USDT"
        }
    }
    client.get_balance.return_value = {
        "status": "ok",
        "data": {
            "total": 1000.0,
            "free": 850.0,
            "used": 150.0
        }
    }
    client.get_count.return_value = {"status": "ok", "data": {"current": 1, "max": 4}}
    client.stopbuy_bot.return_value = {"status": "ok", "data": {"status": "stopbuy"}}
    client.stop_bot.return_value = {"status": "ok", "data": {"status": "stopping"}}
    client.start_bot.return_value = {"status": "ok", "data": {"status": "running"}}
    client.forcesell.return_value = {"status": "ok", "data": {"result": "order_created"}}
    client.reload_config.return_value = {"status": "ok", "reloaded": True}
    return client


@pytest.fixture
def mock_ai_engine():
    engine = MagicMock(spec=QuantAiCopilotEngine)
    engine.process_message.return_value = (
        "🤖 Respuesta generada por AI Copilot con telemetría viva.",
        {"action": "query_status", "confidence": 0.9}
    )
    return engine


@pytest.fixture
def copilot_service(mock_ft_client, mock_ai_engine):
    service = TelegramAiCopilotService(
        telegram_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        allowed_chat_id="99887766",
        freqtrade_client=mock_ft_client,
        ai_engine=mock_ai_engine
    )
    service.tg_client = MagicMock(spec=TelegramBotClient)
    service.orchestrator = MagicMock(spec=MultiBotOrchestratorClient)
    service.orchestrator.get_aggregated_status.return_value = {
        "status": "ok",
        "total_open_trades": 1,
        "total_stake_active_usdt": 50.0,
        "bots": {
            "bot_v5_ablation": {
                "name": "Bot 1 (Ablation v5.2)",
                "port": 8081,
                "is_online": True,
                "open_trades": 1,
                "stake_active_usdt": 50.0
            }
        },
        "trades": [
            {
                "trade_id": 1,
                "pair": "DOGE/USDT:USDT",
                "profit_pct": 2.50,
                "stake_amount": 50.0,
                "is_short": True,
                "origin_bot": "Ablation v5.2"
            }
        ]
    }
    service.hermes_op = MagicMock()
    service.hermes_op.run_cycle.return_value = {
        "explanation": "Hermes en ciclo activo.",
        "regime_info": {"regime": "RANGE_CHOP", "confidence": 0.85},
        "allocation_res": {"actions_taken": [{"bot_id": "bot_v5_ablation", "action": "maintain", "result": "ok"}]},
        "portfolio": {"total_open_trades": 1, "total_stake_active_usdt": 50.0}
    }
    service.hermes_op.regime_detector.detect_regime.return_value = {
        "regime": "RANGE_CHOP",
        "confidence": 0.85,
        "rationale": "Mercado lateral sin tendencia clara",
        "snapshot": {"btc_price": 68000.0, "btc_change_24h": -0.5, "avg_funding_rate": 0.0001},
        "recommended_allocations": {"bot_v5_ablation": 0.35, "bot_v7_quantum": 0.35, "bot_v8_ensemble": 0.30}
    }
    return service


def test_authorization_firewall(copilot_service):
    """Verifica que solo el chat_id autorizado tenga acceso a los controles."""
    assert copilot_service.is_authorized("99887766") is True
    assert copilot_service.is_authorized("11111111") is False
    assert copilot_service.is_authorized("attacker_chat") is False


def test_help_command(copilot_service):
    """Verifica la respuesta del menú de ayuda y telemetría."""
    reply = copilot_service.dispatch_command("/help", chat_id="99887766")
    assert "MEME HUNTER — AI TELEGRAM COPILOT" in reply
    assert "/status" in reply
    assert "/killswitch" in reply
    assert "/hermes" in reply


def test_status_command(copilot_service):
    """Verifica el formateo de posiciones abiertas y telemetría de la arena multi-bot."""
    reply = copilot_service.dispatch_command("/status", chat_id="99887766")
    assert "ARENA MULTI-BOT" in reply
    assert "DOGE/USDT:USDT" in reply
    assert "SHORT" in reply
    assert "+2.50%" in reply
    assert "Total Trades Vivos" in reply
    copilot_service.orchestrator.get_aggregated_status.assert_called_once()


def test_hermes_commands(copilot_service):
    """Verifica comandos específicos de gobernanza de Hermes: /hermes, /regime, /rebalance."""
    rep_hermes = copilot_service.dispatch_command("/hermes", chat_id="99887766")
    assert "Hermes en ciclo activo." in rep_hermes
    copilot_service.hermes_op.run_cycle.assert_called_once()

    rep_regime = copilot_service.dispatch_command("/regime", chat_id="99887766")
    assert "DETECCIÓN DE RÉGIMEN — HERMES AGENT" in rep_regime
    assert "RANGE_CHOP" in rep_regime
    assert "68,000.0" in rep_regime

    rep_rebal = copilot_service.dispatch_command("/rebalance", chat_id="99887766")
    assert "REBALANCEO DE CARTERA EJECUTADO" in rep_rebal


def test_profit_command(copilot_service, mock_ft_client):
    """Verifica el cálculo y reporte de PnL y Win Rate."""
    reply = copilot_service.dispatch_command("/profit", chat_id="99887766")
    assert "+45.20 USDT" in reply
    assert "70.0%" in reply
    mock_ft_client.get_profit.assert_called_once()


def test_balance_command(copilot_service, mock_ft_client):
    """Verifica el reporte de capital, margen libre y margen en uso."""
    reply = copilot_service.dispatch_command("/balance", chat_id="99887766")
    assert "1000.00 USDT" in reply
    assert "850.00 USDT" in reply
    mock_ft_client.get_balance.assert_called_once()


def test_control_commands_stopbuy_and_killswitch(copilot_service, mock_ft_client):
    """Verifica que los comandos operativos interactúen con la API del bot."""
    reply_stopbuy = copilot_service.dispatch_command("/stopbuy", chat_id="99887766")
    assert "stopbuy" in reply_stopbuy
    mock_ft_client.stopbuy_bot.assert_called_once()

    reply_killswitch = copilot_service.dispatch_command("/killswitch", chat_id="99887766")
    assert "KILL-SWITCH DE EMERGENCIA ACTIVADO" in reply_killswitch
    mock_ft_client.stop_bot.assert_called_once()


def test_control_commands_forcesell(copilot_service, mock_ft_client):
    """Verifica la orden de liquidación forzada con parámetro de trade ID."""
    reply = copilot_service.dispatch_command("/forcesell 42", chat_id="99887766")
    assert "#42" in reply
    mock_ft_client.forcesell.assert_called_with("42")


def test_ai_copilot_natural_language_intent():
    """Verifica la clasificación heurística de intención en el motor cognitivo."""
    engine = QuantAiCopilotEngine()

    intent_stopbuy = engine.extract_intent_heuristic("Por favor apaga las compras de nuevas monedas")
    assert intent_stopbuy["action"] == "stopbuy"

    intent_kill = engine.extract_intent_heuristic("Activa el kill switch de emergencia ya")
    assert intent_kill["action"] == "killswitch"

    intent_sell = engine.extract_intent_heuristic("Liquidemos y cerrar trade 19")
    assert intent_sell["action"] == "forcesell"
    assert intent_sell["trade_id"] == "19"

    intent_profit = engine.extract_intent_heuristic("Dime cuánto pnl llevamos hoy")
    assert intent_profit["action"] == "query_profit"


def test_poll_once_security_rejection(copilot_service):
    """Verifica que un mensaje de un usuario no autorizado sea rechazado y advertido."""
    copilot_service.tg_client.get_updates.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 101,
                "message": {
                    "chat": {"id": "intruso_123"},
                    "text": "/killswitch"
                }
            }
        ]
    }

    processed = copilot_service.poll_once()
    assert processed == 0
    copilot_service.tg_client.send_message.assert_called_once()
    args, kwargs = copilot_service.tg_client.send_message.call_args
    assert "Acceso Denegado" in kwargs["text"]
