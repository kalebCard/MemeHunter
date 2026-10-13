---
id: REF-API-001
title: Referencia de API ASGI & WebSockets (Cockpit v8.0)
category: reference
version: 8.0
status: ACTIVE
last_updated: 2026-10-13
author: Quantitative Architecture & Systems Engineering Core
---

# 🌐 Referencia de API ASGI & WebSockets (Cockpit v8.0)

La API del Cockpit se construye sobre **FastAPI** y se ejecuta con **Uvicorn**, exponiendo endpoints REST tipados y un canal bidireccional WebSocket para telemetría en tiempo real (< 5 ms).

---

## 📌 Documentación Interactiva OpenAPI
* **Swagger UI:** `http://127.0.0.1:8088/api/docs`
* **ReDoc:** `http://127.0.0.1:8088/api/redoc`

---

## 🚀 Endpoints REST

### 1. Sistema & Salud (`/api/system`)

#### `GET /api/system/health`
Retorna el estado operativo, versión, entorno y conectividad con la base de datos canónica.
* **Respuesta 200 OK:**
  ```json
  {
    "status": "HEALTHY",
    "version": "8.0.0",
    "env": "production",
    "db_path": "C:\\meme_hunter\\storage\\meme_hunter.db",
    "db_exists": true,
    "live_strategies_count": 3,
    "active_biases_count": 9
  }
  ```

---

### 2. Estrategias & Alfas (`/api/strategies`)

#### `GET /api/strategies/`
Lista todas las estrategias registradas en la incubadora.
* **Parámetros Query:**
  * `status` (opcional): Filtro por estado (`SANDBOX`, `LIVE`, `ALPHA_DECAY`, `RETIRED`).
* **Respuesta 200 OK:** Lista de objetos con ID, nombre, Sharpe, días en etapa y peso de capital.

#### `GET /api/strategies/autopsies/latest`
Recupera los dictámenes forenses cognitivos más recientes generados por los LLMs.
* **Parámetros Query:**
  * `limit` (opcional, default: 10): Cantidad máxima de registros.

#### `GET /api/strategies/{strategy_id}`
Obtiene los detalles específicos de una estrategia.
* **Respuesta 404:** Si el ID no existe en la base de datos.

---

### 3. Orquestador DAG & Multi-Agente (`/api/dag`)

#### `GET /api/dag/status`
Retorna la topología del Grafo Acíclico Dirigido (nodos de ingesta, features, agentes de análisis y nodo de fusión bayesiana), junto con el umbral de consenso (0.68) y la latencia máxima admisible (20 ms).

#### `GET /api/dag/biases`
Recupera todos los sesgos direccionales y clasificaciones de régimen activos que aún no han expirado (TTL).

---

## ⚡ Canal WebSocket (`/ws/telemetry`)

* **URL de Conexión:** `ws://127.0.0.1:8088/ws/telemetry`
* **Protocolo:** JSON bidireccional.
* **Latencia Promedio:** $< 5\text{ ms}$.
* **Propósito:** Sustituye el sondeo continuo (polling) HTTP del Cockpit, transmitiendo actualizaciones reactivas de PnL vivo, estado de los agentes en el visor DAG y alertas de seguridad.
