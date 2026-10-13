"""
Meme Hunter - Test Suite for Sprint 32
Certificación de Cockpit Visual DAG, Endpoints REST de Telemetría y Controles HITL.
"""

import json
import os
import pytest

from dashboard.server import (
    DAG_TOPOLOGY,
    global_dag_orchestrator,
    global_risk_manager,
    global_degradation_guard,
    BASE_DIR
)


# =============================================================================
# PRUEBAS DE ENDPOINTS Y TELEMETRÍA DEL DAG (PB-113)
# =============================================================================

def test_dag_topology_structure():
    """PB-113: Verifica que la topología del DAG contiene las 3 capas y 8 nodos canónicos."""
    assert "layers" in DAG_TOPOLOGY
    layers = DAG_TOPOLOGY["layers"]
    layer_ids = [l["id"] for l in layers]

    assert "ingestion" in layer_ids
    assert "processing" in layer_ids
    assert "core_execution" in layer_ids

    # Verificar que los nodos del diseño institucional están presentes
    all_nodes = []
    for l in layers:
        for n in l["nodes"]:
            all_nodes.append(n["id"])

    expected_nodes = [
        "node_price_volume",
        "node_news_social",
        "node_macro_cal",
        "technical_analysis",
        "sentiment_agent",
        "regime_detector",
        "dag_orchestrator",
        "node_risk_manager",
        "node_execution_api"
    ]
    for exp_id in expected_nodes:
        assert exp_id in all_nodes, f"Nodo faltante en topología: {exp_id}"


def test_dag_status_telemetry():
    """PB-113: Verifica que la telemetría del orquestador DAG expone métricas en tiempo real."""
    telemetry = global_dag_orchestrator.get_telemetry()

    assert "pipeline_status" in telemetry
    assert "synthesis_algorithm" in telemetry
    assert telemetry["synthesis_algorithm"] == "Bayesian Fusion"
    assert "consensus_threshold" in telemetry
    assert "nodes" in telemetry

    # Validar presencia de agentes registrados
    nodes = telemetry["nodes"]
    assert "technical_analysis" in nodes
    assert "sentiment_agent" in nodes
    assert "regime_detector" in nodes


def test_dag_toggle_node_hitl():
    """PB-112 & PB-113: Control HITL pausando y reactivando un nodo."""
    # Pausar technical_analysis
    res_pause = global_dag_orchestrator.toggle_agent("technical_analysis", False)
    assert res_pause is True
    agent = global_dag_orchestrator.get_agent("technical_analysis")
    assert agent.active is False

    # Reactivar technical_analysis
    res_act = global_dag_orchestrator.toggle_agent("technical_analysis", True)
    assert res_act is True
    assert agent.active is True


def test_dag_set_threshold_hitl():
    """PB-112 & PB-113: Ajuste interactivo del consenso mínimo."""
    initial = global_dag_orchestrator.consensus_threshold
    global_dag_orchestrator.set_consensus_threshold(0.74)
    assert global_dag_orchestrator.consensus_threshold == 0.74

    # Restaurar al estándar de producción (0.68)
    global_dag_orchestrator.set_consensus_threshold(initial)
    assert global_dag_orchestrator.consensus_threshold == initial


def test_dag_trigger_cycle_execution():
    """PB-113: Ejecución de ciclo de inferencia y evaluación con gestor de riesgos."""
    vector = global_dag_orchestrator.run_inference_cycle(None)
    verdict = global_risk_manager.evaluate_proposal(vector, {"current_drawdown_pct": 3.5})

    assert vector is not None
    assert verdict is not None
    assert vector.inference_cycle_ms >= 0.0
    assert verdict.decision in ["APPROVED", "SCALED_DOWN", "REJECTED"]


# =============================================================================
# PRUEBAS DE INTEGRIDAD DEL FRONTEND (PB-111 & PB-112)
# =============================================================================

def test_frontend_markup_integrity():
    """PB-111: Verifica que index.html contiene el contenedor y los elementos del DAG."""
    html_path = os.path.join(BASE_DIR, "dashboard", "index.html")
    assert os.path.exists(html_path)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert 'id="tab-multi-agent-dag"' in html_content
    assert 'data-tab="tab-multi-agent-dag"' in html_content
    assert 'dag-pipeline-status-badge' in html_content
    assert 'dag_orchestrator' in html_content
    assert 'js/dag_flow.js' in html_content


def test_frontend_js_and_css_integrity():
    """PB-111 & PB-112: Verifica que dag_flow.js y las clases CSS existan y sean consistentes."""
    js_path = os.path.join(BASE_DIR, "dashboard", "js", "dag_flow.js")
    css_path = os.path.join(BASE_DIR, "dashboard", "css", "style.css")

    assert os.path.exists(js_path), "Falta el archivo dag_flow.js"
    assert os.path.exists(css_path), "Falta el archivo style.css"

    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()
    assert "selectNode" in js_content
    assert "fetchDAGStatus" in js_content
    assert "hitl-node-toggle-btn" in js_content

    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    assert ".dag-flow-card" in css_content
    assert ".dag-node-capsule" in css_content
    assert ".dag-inspector-card" in css_content
