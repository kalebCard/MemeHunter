---
id: SPRINT-HITL-COCKPIT-032
title: "Plan Scrum Sprint 32: Cockpit Visual DAG e Interfaz Human-in-the-Loop (HITL)"
category: sprints
version: 1.0
status: COMPLETED
last_updated: 2026-10-12
completed_date: 2026-10-12
author: Quantitative Engineering & Systems Architecture Team
references:
  - docs/sprints/SPRINT_PLAN_30_MULTI_AGENT_DAG_ORCHESTRATOR.md
  - docs/sprints/SPRINT_PLAN_31_LLM_SENTIMENT_AND_DEGRADATION.md
  - dashboard/index.html
  - dashboard/server.py
  - dashboard/css/style.css
---

# 🎮 Sprint 32: Cockpit Visual DAG e Interfaz Human-in-the-Loop (HITL)

## 🎯 Objetivo del Sprint
Materializar en el **Centro de Control Unificado (Cockpit)** la interfaz visual interactiva en tiempo real del **Grafo Acíclico Dirigido (DAG)**, calcada del diseño institucional de referencia. Esta vista empodera al trader como el verdadero **"Director de Orquesta" (Human-in-the-Loop)**, permitiéndole inspeccionar la salud y latencia de cada nodo, auditar en tiempo real en qué paso se aprueba o veta una propuesta de trading, y modular parámetros o pausar agentes con un solo clic.

---

## 🎨 Especificación de la Interfaz Visual (Sprint 32)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Trading Multi-Agente                                                ● PIPELINE ACTIVO  │
│ Arquitectura de Flujo e Inferencia en Tiempo Real                                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│     [ Precio y Volumen ]         [ Noticias y Redes ]         [ Calendario Macro ]     │
│       WebSockets L2/L3             APIs NLP Scraping            Eventos FED / IPC      │
│              │                            │                            │               │
│              ▼                            ▼                            ▼               │
│     [ Análisis Técnico ]         [ Agente Sentimiento ]       [ Detector Régimen ]     │
│       Cuantitativo / Micro          FinLLM Embeddings           HMM / Volatilidad      │
│                                                                                        │
│                                      Vector Alpha                                      │
│                                           │                                            │
│                                           ▼                                            │
│                              ┌─────────────────────────┐                               │
│                              │   * Orquestador DAG *   │  <-- [Nodo Seleccionado]      │
│                              │ Enrutador Central Señal │                               │
│                              └────────────┬────────────┘                               │
│                                           │ Propuesta                                  │
│                                           ▼                                            │
│     [ Gestor de Riesgos ]        ─── FIX ───>          [ API de Ejecución ]            │
│       Filtro VaR / Drawdown                              Broker / DMA FIX              │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Orquestador DAG (Enrutador Central de Señales)                   ORQUESTACIÓN CENTRAL  │
│ Grafo Acíclico Dirigido que sintetiza los alpha-vectors de todos los agentes,          │
│ aplicando pesos dinámicos según el régimen de mercado.                                 │
│ ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────────┐ │
│ │ Algoritmo Sint.        │  │ Consenso Min.          │  │ Ciclo Inferencia           │ │
│ │ Bayesian Fusion        │  │ 0.68 Score             │  │ 15 ms                      │ │
│ └────────────────────────┘  └────────────────────────┘  └────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [ ] Ingesta de Datos     [ ] Procesamiento & Riesgo     [x] Núcleo & Ejecución         │
│                                              Haz clic en cualquier nodo para inspeccionar│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Backlog de Historias de Usuario e Items Técnicos

### 1. PB-111: Lienzo Interactivo DAG en el Cockpit Web (`dashboard/index.html` + `dag_flow.js`)
- **Problema:** El Cockpit actual muestra tablas de KPIs y gráficos de series de tiempo, pero carece de un mapa topológico visual que ilustre la interacción viva entre los agentes y la ruta de inferencia.
- **Solución Técnica:**
  - Agregar una nueva pestaña especializada en [`dashboard/index.html`](file:///c:/meme_hunter/dashboard/index.html):
    `<button class="nav-tab" data-tab="tab-multi-agent-dag">🌐 Orquestación Multi-Agente (DAG)</button>`.
  - Crear [`dashboard/js/dag_flow.js`](file:///c:/meme_hunter/dashboard/js/dag_flow.js) con renderizado vectorial nativo (SVG reactivo / Canvas acelerado por GPU):
    - 8 nodos organizados en 3 capas visuales jerárquicas con paleta oscura neón (fondos `#161922`, bordes `#2a3042`, acento azul/cian `#3a86ff` / `#00f2fe`).
    - Conectores con flechas curvas y pulsos luminosos de micro-animación CSS representando el flujo de datos.
    - Badges de estado en tiempo real sobre cada nodo (`ACTIVO`, `CALCULANDO`, `PAUSADO`, `ALERTA`).
- **Criterio de Aceptación:**
  - El grafo se renderiza fluidamente sin librerías externas pesadas.
  - Todos los nodos son clicables con efecto visual de realce (*glow effect*).

---

### 2. PB-112: Inspector Dinámico de Nodos y Controles Human-in-the-Loop (HITL)
- **Problema:** Cuando el trader desea comprender el comportamiento de un nodo o intervenir en la operativa, no tiene un panel unificado de inspección y control en tiempo real.
- **Solución Técnica:**
  - Implementar en la parte inferior del lienzo el componente **Inspector de Nodo**:
    - **Cabecera:** Nombre canónico del nodo y badge de categoría (`INGESTA DE DATOS`, `PROCESAMIENTO & RIESGO`, `ORQUESTACIÓN CENTRAL`, `EJECUCIÓN`).
    - **Descripción Funcional:** Resumen del algoritmo activo y rol dentro del DAG.
    - **Tarjetas de Métricas Dinámicas:**
      - *Algoritmo de Síntesis:* `Bayesian Fusion` / `HMM Gaussian` / `AST Factor Parser`.
      - *Consenso Mínimo:* `0.68 Score` (con slider interactivo HITL para modificarlo en caliente).
      - *Ciclo de Inferencia:* Latencia real en milisegundos (`15 ms`).
    - **Controles HITL del Operador:**
      - Switch toggle `[Activo / Pausar Nodo]` para aislar agentes en mantenimiento.
      - Botón `[Simular Fallo]` para pruebas de resiliencia.
      - Selector de capas de la leyenda para filtrar la visualización del grafo.
- **Criterio de Aceptación:**
  - Hacer clic en cualquier nodo actualiza el inspector de manera instantánea.
  - Modificar un parámetro en el inspector envía una actualización al backend y refleja el nuevo estado.

---

### 3. PB-113: Endpoints REST de Telemetría y Control DAG en `dashboard/server.py`
- **Problema:** El servidor del Cockpit necesita exponer el estado de los agentes en tiempo real sin bloquear el hilo principal de trading ni generar latencias de red.
- **Solución Técnica:**
  - Añadir controladores en [`dashboard/server.py`](file:///c:/meme_hunter/dashboard/server.py):
    1. `GET /api/dag/topology`: Retorna la estructura estática de nodos y aristas con sus metadatos.
    2. `GET /api/dag/status`: Retorna la telemetría en vivo (estado de cada agente, último score emitido, latencia en ms, última propuesta de trading y motivos de veto).
    3. `POST /api/dag/node_toggle`: Permite al operador pausar o activar un agente específico.
    4. `POST /api/dag/threshold_update`: Permite ajustar el umbral de consenso mínimo del orquestador.
  - Implementar bloqueo atómico ligero (`threading.Lock`) para lecturas seguras sin contención.
- **Criterio de Aceptación:**
  - Endpoints responden en $< 5\text{ ms}$.
  - Manejo de concurrencia thread-safe verificado con múltiples lecturas simultáneas.

---

### 4. PB-114: Suite de Pruebas de Integración E2E y Compatibilidad
- **Problema:** Se debe asegurar que la integración de la nueva pestaña no rompa las funcionalidades existentes del Cockpit (Live, Backtests, Studio, Incubadora).
- **Solución Técnica:**
  - Crear [`tests/test_sprint32_dag_dashboard_telemetry.py`](file:///c:/meme_hunter/tests/test_sprint32_dag_dashboard_telemetry.py).
  - Verificar:
    - Serialización JSON impecable de todos los nodos del DAG.
    - Respuestas HTTP 200 de los nuevos endpoints.
    - Transición de estados en el inspector (Activo -> Pausado -> Activo).
- **Criterio de Aceptación:**
  - 100% de tests pasando en la suite automatizada.
  - Coexistencia armoniosa con las pestañas previas del Cockpit.

---

## 🎯 Definición de Hecho (DoD) del Sprint 32
1. Pestaña de Orquestación Multi-Agente (DAG) plenamente integrada en el Cockpit Web.
2. Diagrama interactivo idéntico al diseño de referencia con animación de flujo y selección de nodos.
3. Panel inspector con métricas de síntesis, consenso y ciclo de inferencia actualizado en vivo.
4. Endpoints `/api/dag/*` operativos y testeados al 100% en la suite de pruebas.
