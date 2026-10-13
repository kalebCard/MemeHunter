"""
tests/unit/test_api.py - Pruebas Unitarias del Servidor ASGI FastAPI (Meme Hunter v8.0).
"""

import pytest
from fastapi.testclient import TestClient
from meme_hunter.api.app import create_app

client = TestClient(create_app())


def test_system_health():
    """Valida el endpoint de salud del sistema."""
    response = client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["version"] == "8.0.0"
    assert "db_exists" in data


def test_strategies_list():
    """Valida la consulta de estrategias registradas."""
    response = client.get("/api/strategies/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_dag_status():
    """Valida la consulta de topología y estado del DAG multi-agente."""
    response = client.get("/api/dag/status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True
    assert "topology" in data
    assert data["consensus_threshold"] == 0.68


def test_active_biases():
    """Valida la consulta de sesgos de mercado activos."""
    response = client.get("/api/dag/biases")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
