"""
Meme Hunter - Test Suite for Sprint 32
Certificación de Cockpit Visual DAG, Endpoints REST de Telemetría y Controles HITL.
"""

import json
import os
import pytest

from meme_hunter.api.routers.quant import (
    DAG_TOPOLOGY,
    quant_dag_orchestrator as global_dag_orchestrator,
    quant_risk_manager as global_risk_manager,
    quant_degradation_guard as global_degradation_guard
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
# PRUEBAS DE INTEGRIDAD DEL FRONTEND FREQUI (PB-111 & PB-152)
# =============================================================================

def test_frontend_markup_integrity():
    """PB-111 & PB-152: Verifica que FreqUI contiene la vista reactiva y componentes del DAG."""
    dag_path = os.path.join(BASE_DIR, "web", "frequi", "src", "pages", "dag.vue")
    dist_path = os.path.join(BASE_DIR, "web", "frequi", "dist", "index.html")
    assert os.path.exists(dag_path), "Falta el componente FreqUI dag.vue"
    assert os.path.exists(dist_path), "Falta el bundle compilado de FreqUI dist/index.html"

    with open(dag_path, "r", encoding="utf-8") as f:
        vue_content = f.read()

    assert "handleTriggerCycle" in vue_content
    assert "selectNode" in vue_content
    assert "handleToggleNode" in vue_content
    assert "useQuantStore" in vue_content
    assert "quantStore.dagTopology" in vue_content


def test_frontend_js_and_css_integrity():
    """PB-111 & PB-152: Verifica los estilos y reactividad de los componentes institucionales."""
    dag_path = os.path.join(BASE_DIR, "web", "frequi", "src", "pages", "dag.vue")
    header_path = os.path.join(BASE_DIR, "web", "frequi", "src", "components", "layout", "InstitutionalHeader.vue")

    assert os.path.exists(dag_path)
    assert os.path.exists(header_path)

    with open(dag_path, "r", encoding="utf-8") as f:
        vue_content = f.read()
    assert "CAPA 1: INGESTA DE DATOS" in vue_content
    assert "CAPA 2: PROCESAMIENTO & AGENTES" in vue_content
    assert "CAPA 3: NÚCLEO DE SÍNTESIS & EJECUCIÓN" in vue_content
    assert "handleSliderChange" in vue_content

    with open(header_path, "r", encoding="utf-8") as f:
        header_content = f.read()
    assert "institutional-badge-strip" in header_content
    assert "kill_switch_active" in header_content
