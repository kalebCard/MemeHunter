"""
tests/test_quant_api.py - Suite de Pruebas de Integración para Endpoints Cuantitativos Unificados (Sprint 45-47).
Valida:
1. Topología y telemetría del Grafo DAG (/api/quant/dag/*).
2. Controles Human-in-the-Loop (toggle-node, set-threshold, trigger-cycle).
3. Estado y ciclo de la Incubadora Autónoma (/api/quant/incubator/*).
4. Laboratorio Quant Studio con AST Zero-Eval y Backtest Vectorial (/api/quant/studio/*).
5. Monitoreo y control del Kill-Switch y Salvaguardas (/api/quant/safeguards/*).
"""

import pytest
from fastapi.testclient import TestClient

from meme_hunter.api.app import create_app

app = create_app()
client = TestClient(app)


def test_quant_dag_topology():
    """PB-149: Valida que la topología del DAG exponga las 3 capas y nodos canónicos."""
    response = client.get("/api/quant/dag/topology")
    assert response.status_code == 200
    data = response.json()
    assert "layers" in data
    layer_ids = [l["id"] for l in data["layers"]]
    assert "ingestion" in layer_ids
    assert "processing" in layer_ids
    assert "core_execution" in layer_ids


def test_quant_dag_status():
    """PB-149: Valida la telemetría en tiempo real y el umbral de consenso."""
    response = client.get("/api/quant/dag/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "consensus_threshold" in data
    assert "registered_agents" in data
    assert "technical_analysis" in data["registered_agents"]


def test_quant_dag_toggle_node_hitl():
    """PB-152: Valida el control HITL pausando y reactivando un nodo."""
    # 1. Pausar nodo
    resp_pause = client.post("/api/quant/dag/toggle-node", json={"node_id": "technical_analysis", "active": False})
    assert resp_pause.status_code == 200
    assert resp_pause.json()["active"] is False

    # 2. Reactivar nodo
    resp_reactivate = client.post("/api/quant/dag/toggle-node", json={"node_id": "technical_analysis", "active": True})
    assert resp_reactivate.status_code == 200
    assert resp_reactivate.json()["active"] is True


def test_quant_dag_set_threshold_hitl():
    """PB-152: Valida el ajuste reactivo del umbral de consenso."""
    resp = client.post("/api/quant/dag/set-threshold", json={"threshold": 0.72})
    assert resp.status_code == 200
    assert resp.json()["consensus_threshold"] == 0.72

    # Restablecer a 0.68
    client.post("/api/quant/dag/set-threshold", json={"threshold": 0.68})


def test_quant_dag_trigger_cycle():
    """PB-152: Valida el disparo manual de ciclo de inferencia."""
    resp = client.post("/api/quant/dag/trigger-cycle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "elapsed_ms" in data
    assert "consensus_score" in data


def test_quant_incubator_status():
    """PB-153: Valida la lectura de estado de incubadora, autopsias y nichos."""
    resp = client.get("/api/quant/incubator/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "strategies" in data
    assert len(data["strategies"]) >= 1


def test_quant_studio_validate_formula():
    """PB-154: Valida sintaxis AST Zero-Eval para fórmulas legítimas y maliciosas."""
    # Fórmula válida
    resp_valid = client.post("/api/quant/studio/validate-formula", json={"formula": "ts_decay_linear(returns, 5) * ts_rank(volume, 10)"})
    assert resp_valid.status_code == 200
    assert resp_valid.json()["valid"] is True

    # Código malicioso bloqueado
    resp_invalid = client.post("/api/quant/studio/validate-formula", json={"formula": "import os; os.system('rm -rf')" })
    assert resp_invalid.status_code == 200
    assert resp_invalid.json()["valid"] is False


def test_quant_studio_test_strategy():
    """PB-154: Valida la simulación vectorial de alta velocidad."""
    resp = client.post("/api/quant/studio/test-strategy", json={
        "formula": "ts_decay_linear(returns, 5) * ts_rank(volume, 10)",
        "pair": "1000PEPE",
        "timeframe": "4h",
        "direction": "short_only",
        "leverage": 1.5,
        "stoploss": 0.10,
        "trailing_stop": 0.04
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "metrics" in data
    assert "sharpe_ratio" in data["metrics"]


def test_quant_studio_deploy_to_sandbox():
    """PB-154: Valida el despliegue directo a la incubadora."""
    resp = client.post("/api/quant/studio/deploy-to-sandbox", json={
        "formula": "ts_rank(volume, 10) * returns",
        "backtest_sharpe": 2.15
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["strategy"]["status"] == "SANDBOX"


def test_quant_safeguards_status():
    """PB-151: Valida la auditoría en tiempo real de salvaguardas institucionales."""
    resp = client.get("/api/quant/safeguards/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "safeguards" in data
    assert data["safeguards"]["ffd_enabled"] is True
    assert data["safeguards"]["ffd_d_parameter"] == 0.40
