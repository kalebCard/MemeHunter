"""
test_hermes_operator.py - Suite de Pruebas Unitarias para el Agente Autónomo Hermes (Sprint 52: PB-189).

Valida el motor de inferencia de régimen, la orquestación multi-bot,
la persistencia de memoria episódica y las salvaguardas de gobernanza.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.meme_hunter.hermes.regime_detector import HermesRegimeDetector, MarketRegime
from src.meme_hunter.hermes.capital_allocator import HermesCapitalAllocator
from src.meme_hunter.hermes.hermes_operator import HermesOperator
from client.multi_bot_orchestrator import MultiBotOrchestratorClient


@pytest.fixture
def mock_orchestrator():
    """Mock del orquestador multi-bot para pruebas deterministas sin red."""
    orch = MagicMock(spec=MultiBotOrchestratorClient)
    orch.clients = {
        "bot_v5_ablation": MagicMock(),
        "bot_v7_quantum": MagicMock(),
        "bot_mined_ensemble": MagicMock()
    }
    orch.get_aggregated_status.return_value = {
        "status": "ok",
        "total_open_trades": 6,
        "total_stake_active_usdt": 120.0,
        "bots": {
            "bot_v5_ablation": {"open_trades": 2, "stake_active_usdt": 40.0, "is_online": True},
            "bot_v7_quantum": {"open_trades": 2, "stake_active_usdt": 40.0, "is_online": True},
            "bot_mined_ensemble": {"open_trades": 2, "stake_active_usdt": 40.0, "is_online": True}
        },
        "trades": []
    }
    orch.stopbuy_bot.return_value = {"status": "ok"}
    orch.start_bot.return_value = {"status": "ok"}
    orch.stop_bot.return_value = {"status": "ok"}
    return orch


def test_regime_detector_bear_cascade():
    """Verifica que caídas pronunciadas o funding negativo cataloguen Cascada Bajista."""
    detector = HermesRegimeDetector()
    snap = {
        "btc_price": 79000.0,
        "btc_change_24h": -4.2,
        "avg_funding_rate": -0.0004
    }
    res = detector.detect_regime(snap)
    assert res["regime"] == MarketRegime.BEAR_CASCADE.value
    assert res["recommended_allocations"]["bot_v5_ablation"] == 0.50
    assert res["recommended_allocations"]["bot_v7_quantum"] == 0.40


def test_regime_detector_bull_parabolic():
    """Verifica que rallies parabólicos congelen la exposición de shorts (Ablation = 0.0)."""
    detector = HermesRegimeDetector()
    snap = {
        "btc_price": 88000.0,
        "btc_change_24h": +5.5,
        "avg_funding_rate": +0.0008
    }
    res = detector.detect_regime(snap)
    assert res["regime"] == MarketRegime.BULL_PARABOLIC.value
    assert res["recommended_allocations"]["bot_v5_ablation"] == 0.00
    assert res["recommended_allocations"]["bot_mined_ensemble"] == 0.80


def test_regime_detector_range_chop():
    """Verifica el comportamiento defensivo equilibrado en rangos laterales."""
    detector = HermesRegimeDetector()
    snap = {
        "btc_price": 81000.0,
        "btc_change_24h": +0.4,
        "avg_funding_rate": 0.00005
    }
    res = detector.detect_regime(snap)
    assert res["regime"] == MarketRegime.RANGE_CHOP.value
    assert res["recommended_allocations"]["bot_v7_quantum"] == 0.45


def test_capital_allocator_enforce_stopbuy(mock_orchestrator):
    """Verifica que el asignador pause compras cuando la ponderación del bot es 0."""
    allocator = HermesCapitalAllocator(orchestrator=mock_orchestrator)
    regime_info = {
        "regime": "BULL_PARABOLIC",
        "recommended_allocations": {
            "bot_v5_ablation": 0.00,
            "bot_v7_quantum": 0.20,
            "bot_mined_ensemble": 0.80
        }
    }
    res = allocator.evaluate_and_enforce(regime_info)
    assert res["status"] == "ok"
    # Debe haber ejecutado stopbuy sobre bot_v5_ablation
    mock_orchestrator.stopbuy_bot.assert_called_with("bot_v5_ablation")
    mock_orchestrator.start_bot.assert_any_call("bot_v7_quantum")
    mock_orchestrator.start_bot.assert_any_call("bot_mined_ensemble")


def test_hermes_operator_lifecycle_and_memory(tmp_path, mock_orchestrator):
    """Verifica el ciclo completo del operador y la persistencia de memoria episódica."""
    temp_mem = str(tmp_path / "hermes_test_mem.json")
    
    mock_detector = MagicMock(spec=HermesRegimeDetector)
    mock_detector.detect_regime.return_value = {
        "regime": "BEAR_CASCADE",
        "confidence": 0.88,
        "snapshot": {"btc_price": 79500.0, "btc_change_24h": -3.5},
        "recommended_allocations": {"bot_v5_ablation": 0.5, "bot_v7_quantum": 0.4, "bot_mined_ensemble": 0.1},
        "rationale": "Prueba unitaria"
    }

    operator = HermesOperator(
        memory_path=temp_mem,
        orchestrator=mock_orchestrator,
        regime_detector=mock_detector
    )

    # Ciclo 1
    cycle1 = operator.run_cycle()
    assert cycle1["total_cycles_run"] == 1
    assert "BEAR_CASCADE" in cycle1["explanation"]
    assert os.path.exists(temp_mem)

    # Ciclo 2
    cycle2 = operator.run_cycle()
    assert cycle2["total_cycles_run"] == 2
    assert len(operator.memory["regime_history"]) == 2

    # Verificar lectura en disco
    with open(temp_mem, "r", encoding="utf-8") as f:
        disk_mem = json.load(f)
        assert disk_mem["total_cycles_run"] == 2
