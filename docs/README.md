---
id: DOC-INDEX-001
title: Centro Canónico de Documentación y Convenciones (Meme Hunter v8.0)
category: index
version: 8.0
status: ACTIVE
last_updated: 2026-10-13
author: Quantitative Architecture & Systems Engineering Core
---

# 📚 Centro Canónico de Documentación (Meme Hunter v8.0)

Bienvenido al centro oficial de documentación del ecosistema **Meme Hunter**. Toda la información técnica, cuantitativa, histórica y operativa se encuentra organizada bajo las convenciones de **DocOps** y el marco pedagógico internacional **Diátaxis**.

---

## 🌟 Documentos Maestros Canónicos

> ### 🛡️ [📖 Manual Estándar de Ingeniería y Desarrollo (MANUAL-STD-001)](MANUAL_ESTANDAR_DEL_PROYECTO.md)
> *La norma técnica canónica obligatoria para desarrolladores e ingenieros: arquitectura modular `src/meme_hunter`, eliminación del Split-Brain (SQLite WAL), desacoplamiento asíncrono con Event Bus, Pydantic Settings, pirámide de testing y catálogo CLI `meme-hunter`.*

> ### 🌌 [📖 Manual Maestro Unificado del Sistema (DOC-MASTER-001)](MANUAL_UNIFICADO_DEL_SISTEMA.md)
> *El compendio cuantitativo integral que consolida: visión económica, arquitectura Híbrida Barbell, evolución de estrategias (V1 a V7 Quantum), auditoría forense (DSR / PBO), microestructura y motor auto-evolutivo.*

---

## 🗺️ Mapa de Navegación Estructurado (Marco Diátaxis)

```text
docs/
├── MANUAL_ESTANDAR_DEL_PROYECTO.md  # 🛡️ Norma técnica obligatoria de desarrollo (v8.0)
├── MANUAL_UNIFICADO_DEL_SISTEMA.md  # 🌌 Compendio canónico cuantitativo y estratégico (v7.4)
│
├── architecture/                    # 🏛️ EXPLICACIÓN: Arquitectura y Decisiones
│   ├── DAS.md                       # Documento de Arquitectura de Software base (v6.0)
│   ├── DAS_AUTONOMOUS_ENGINE.md     # Motor Multi-Agente, Grafo DAG & Cockpit HITL (v7.4)
│   └── decisions/                   # Architecture Decision Records (ADRs 001 a 004.1)
│
├── guides/                          # 🛠️ CÓMO HACER (HOW-TO): Guías Operativas
│   └── OPERATIONAL_RUNBOOK.md       # Procedimientos de despliegue, Docker, VPS y contingencias
│
├── reference/                       # 📖 REFERENCIA: Especificaciones Técnicas
│   ├── CLI_REFERENCE.md             # Catálogo exhaustivo de comandos del CLI 'meme-hunter'
│   ├── DATABASE_SCHEMA.md           # Esquema relacional SQLite WAL, pragmas y repositorios
│   └── API_REFERENCE.md             # Especificación OpenAPI ASGI FastAPI y WebSockets (<5ms)
│
├── research/                        # 🔬 INVESTIGACIÓN: Teoría Cuantitativa e Informes
│   ├── strategy/                    # Estrategia Maestra, Hipótesis causal, Modelo Barbell y Escalado
│   └── reports/                     # Certificación DSR 100%, PBO 6.67%, Auditoría Forense y Futuros
│
└── history/                         # 📜 HISTORIA: Genealogía, Backlog y Sprints
    ├── INDEX_HISTORICO.md           # Memoria técnica y lecciones aprendidas de cada era
    ├── scrum/                       # 🛡️ Scrum Governance y Product Backlog (Épicas 1-12, PB-01 a PB-143)
    └── sprints/                     # 🏃 Catálogo y planes cronológicos de sprints (Sprints 1 al 43)
```

---

## 📂 Índice Detallado por Cuadrantes

### 🏛️ 1. Arquitectura y Decisiones de Diseño (`docs/architecture/`)
* **[DAS_AUTONOMOUS_ENGINE.md](architecture/DAS_AUTONOMOUS_ENGINE.md):** Motor autónomo de bucle cerrado, persistencia SQLite WAL, compuertas OOS y orquestador DAG.
* **[DAS.md](architecture/DAS.md):** Especificación fundacional de la infraestructura Freqtrade, CCXT y Bóveda Delta-Neutral.
* **[ADR-001: Asymmetric Short-Only Bias](architecture/decisions/ADR-001_asymmetric_short_only_bias.md):** Fundamento de la supresión de Longs en memecoins.
* **[ADR-002: Arquitectura Híbrida Barbell](architecture/decisions/ADR-002_hybrid_barbell_cash_and_carry.md):** Binomio de aceleración agresiva y bóveda pasiva Cash & Carry.
* **[ADR-003: Diferenciación Fraccionaria y Bet Sizing](architecture/decisions/ADR-003_fractional_diff_and_continuous_bet_sizing.md):** FFD ($d=0.40$) y fórmula continua sigmoidal.
* **[ADR-004: Airbag Técnico y Órdenes Market](architecture/decisions/ADR-004_airbag_technical_exit_market_orders.md):** Cierres técnicos dinámicos y protección anti no-fill.

### 🛠️ 2. Guías Operativas (`docs/guides/`)
* **[OPERATIONAL_RUNBOOK.md](guides/OPERATIONAL_RUNBOOK.md):** Procedimientos de despliegue Docker, variables `.env`, protocolos del Kill-Switch de 25%, sincronización de Binance y mantenimiento SQLite WAL.

### 📖 3. Referencia Técnica (`docs/reference/`)
* **[CLI_REFERENCE.md](reference/CLI_REFERENCE.md):** Manual completo de comandos `meme-hunter` (`db`, `run`, `mine`, `backtest`, `sim`, `serve`).
* **[DATABASE_SCHEMA.md](reference/DATABASE_SCHEMA.md):** Esquema relacional de SQLite WAL (`strategies`, `portfolio_allocations`, `alpha_autopsies`, `market_biases`, etc.).
* **[API_REFERENCE.md](reference/API_REFERENCE.md):** Documentación de endpoints FastAPI (`/api/system`, `/api/strategies`, `/api/dag`) y WebSockets.
* **[Manual Operativo de Scripts](../scripts/README.md):** Catálogo y guía operativa de los 47 scripts organizados en 6 dominios funcionales.

### 🔬 4. Investigación Cuantitativa (`docs/research/`)
* **[ESTRATEGIA_MAESTRA_UNIFICADA.md](research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md):** Compendio cuantitativo integral de hipótesis, genealogía V1-V7 y escalado.
* **[HYPOTHESIS.md](research/strategy/HYPOTHESIS.md):** Justificación económica del edge por desinflación gravitacional post-pump.
* **[INFORME_METRICAS_AVANZADAS_DSR_PBO.md](research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md):** Certificación matemática institucional (DSR = 100%, PBO = 6.67%).
* **[INFORME_AUDITORIA_FORENSE_RIESGOS.md](research/reports/INFORME_AUDITORIA_FORENSE_RIESGOS.md):** Auditoría empírica de 215 trades y desmitificación de riesgos de calendario.
* **[PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md](research/strategy/PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md):** Especificación del traspaso mecánico del 60% hacia la Bóveda Cash & Carry.

### 📜 5. Historia y Evolución de Sprints (`docs/history/`)
* **[INDEX_HISTORICO.md](history/INDEX_HISTORICO.md):** Registro evolutivo de las 7 eras del proyecto y lecciones aprendidas.
* **[scrum/SCRUM_PLAN.md](history/scrum/SCRUM_PLAN.md):** Product Backlog Maestro unificado (Épicas 1 a 12, Historias PB-01 a PB-143 y DoD).
* **[scrum/README.md](history/scrum/README.md):** Marco ágil, roles, ceremonias y gobernanza Scrum.
* **[sprints/README.md](history/sprints/README.md):** Catálogo maestro de ejecución de los 13 planes de sprint cronológicos (Sprints 1 al 43).

---

## 🎯 Rutas de Lectura Recomendadas por Perfil

| Perfil | Ruta de Lectura Sugerida |
| :--- | :--- |
| **Ingeniero de Software** | [`MANUAL_ESTANDAR_DEL_PROYECTO.md`](MANUAL_ESTANDAR_DEL_PROYECTO.md) ➔ [`reference/CLI_REFERENCE.md`](reference/CLI_REFERENCE.md) ➔ [`reference/DATABASE_SCHEMA.md`](reference/DATABASE_SCHEMA.md) ➔ [`guides/OPERATIONAL_RUNBOOK.md`](guides/OPERATIONAL_RUNBOOK.md) |
| **Investigador Cuantitativo** | [`MANUAL_UNIFICADO_DEL_SISTEMA.md`](MANUAL_UNIFICADO_DEL_SISTEMA.md) ➔ [`research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md`](research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md) ➔ [`research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md`](research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md) |
| **Operador de Producción** | [`guides/OPERATIONAL_RUNBOOK.md`](guides/OPERATIONAL_RUNBOOK.md) ➔ [`reference/CLI_REFERENCE.md`](reference/CLI_REFERENCE.md) ➔ Cockpit Web ([http://localhost:8088](http://localhost:8088)) |
| **Inversor / Auditor** | [`MANUAL_UNIFICADO_DEL_SISTEMA.md`](MANUAL_UNIFICADO_DEL_SISTEMA.md) ➔ [`research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md`](research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md) ➔ [`history/INDEX_HISTORICO.md`](history/INDEX_HISTORICO.md) |
