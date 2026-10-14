---
id: REF-API-001
title: Referencia de API REST & WebSockets (Meme Hunter v8.5)
category: reference
version: 8.5
status: ACTIVE
last_updated: 2026-10-14
author: Quantitative Architecture & Systems Engineering Core
---

# 🌐 Referencia de API REST & WebSockets (Meme Hunter v8.5)

El sistema opera con dos capas de APIs coordinadas:
1. **API de Freqtrade Engine (`http://127.0.0.1:8081/api/v1`)**: Motor oficial de ejecución, trades, telemetría y UI.
2. **API del Cockpit I+D ASGI (`http://127.0.0.1:8088/api`)**: Microservicios de DAG, laboratorio de alfas y persistencia SQLite WAL.

---

## ⚡ 1. API Oficial Freqtrade Engine (:8081)

Utilizada tanto por **FreqUI** como por el **Telegram AI Copilot** ([`client/telegram_ai_copilot.py`](file:///c:/meme_hunter/client/telegram_ai_copilot.py)):

| Endpoint | Método | Autenticación | Descripción |
| :--- | :---: | :---: | :--- |
| `/api/v1/ping` | GET | Ninguna | Heartbeat del servidor (retorna `{"status": "pong"}`). |
| `/api/v1/status` | GET | HTTP Basic | Estado de trades abiertos, órdenes vivas y ratios de beneficio. |
| `/api/v1/balance` | GET | HTTP Basic | Balance de cuenta USDT, saldo libre, bloqueado y total. |
| `/api/v1/daily?days=7` | GET | HTTP Basic | PnL realizado desglosado por día calendario. |
| `/api/v1/profit` | GET | HTTP Basic | Métricas históricas acumuladas, winrate y factor de beneficio. |
| `/api/v1/whitelist` | GET | HTTP Basic | Lista de pares autorizados actualmente en el par de futuros. |
| `/api/v1/forcebuy` | POST | HTTP Basic | Disparo de orden forzada de entrada (`{"pair": "SOL/USDT"}`). |
| `/api/v1/forcesell` | POST | HTTP Basic | Cierre forzado de posición por Trade ID. |
| `/api/v1/reload_config`| POST | HTTP Basic | Recarga en caliente de configuraciones sin reiniciar contenedor. |

---

## 🔬 2. API ASGI Cockpit I+D (:8088)

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
