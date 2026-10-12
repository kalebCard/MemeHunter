---
id: DOC-INDEX-001
title: Centro de Documentación y Convenciones del Sistema
category: index
version: 6.0
status: ACTIVE
last_updated: 2026-10-11
author: Quantitative Engineering & Research Core
---

# 📚 Centro de Documentación y Convenciones del Sistema (Meme Hunter v6.0)

Bienvenido al centro oficial de documentación cuantitativa, arquitectónica y operativa de **Meme Hunter**. Toda la información del proyecto ha sido estandarizada bajo convenciones formales de ingeniería documental (**DocOps**) y el marco pedagógico Diátaxis.

---

## 🌟 Documento de Referencia Principal

> ### 👉 [📖 Manual Maestro Unificado del Sistema (DOC-MASTER-001)](MANUAL_UNIFICADO_DEL_SISTEMA.md)
> *El compendio canónico integral que consolida en un solo documento: visión económica, arquitectura Barbell, evolución de estrategias (V1 a V7 Quantum), auditoría forense (DSR / PBO), microestructura y catálogo de scripts.*

---

## 🗺️ Mapa Estandarizado de Navegación

```
docs/
├── MANUAL_UNIFICADO_DEL_SISTEMA.md  # 🌟 Compendio canónico del sistema v6.0
├── architecture/
│   ├── DAS_AUTONOMOUS_ENGINE.md     # 🌌 Arquitectura v7.0: Motor Auto-Evolutivo & Cockpit IA
│   ├── DAS.md                       # Documento de Arquitectura de Software base (v6.0)
│   └── decisions/                   # Architecture Decision Records (ADRs)
│       ├── ADR-001_asymmetric_short_only_bias.md
│       ├── ADR-002_hybrid_barbell_cash_and_carry.md
│       ├── ADR-003_fractional_diff_and_continuous_bet_sizing.md
│       └── ADR-004_airbag_technical_exit_market_orders.md
├── sprints/
│   ├── SPRINT_PLAN_REMEDIATION_AND_HARDENING.md # 🛡️ Plan Scrum: Hardening, Streaming & DevOps
│   ├── SPRINT_AUTONOMOUS_SELF_IMPROVING_ENGINE.md # 🚀 Sprint 1: Bucle Cerrado & Self-Healing
│   └── SPRINT_LLM_AUGMENTED_AUTONOMOUS_ENGINE.md  # 🧠 Sprint 2: Cognición IA con OpenRouter
├── strategy/
│   ├── ESTRATEGIA_MAESTRA_UNIFICADA.md # 🌟 Compendio Maestro de Estrategia (STRAT-MASTER-001)
│   ├── PLAN_SCRUM_MINERIA_Y_BACKTESTING.md # 🚀 Plan Scrum: Minería de Alphas (Sprints 21-24)
│   ├── HYPOTHESIS.md                # Hipótesis Causal del Edge y Desinflación (STRAT-001)
│   ├── SCRUM_PLAN.md                # Roadmap Maestro de Sprints (1 a 20)
│   ├── PLAN_ESCALADO_100_A_1000_USDT.md # Modelo de Crecimiento de Micro-Capital (STRAT-002)
│   ├── PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md # Especificación del binomio Barbell (STRAT-003)
│   └── PLAN_DESMITIFICACION_RIESGOS.md # Protocolo de Pruebas de Estrés Anti-Overfitting (STRAT-004)
├── reports/
│   ├── INFORME_METRICAS_AVANZADAS_DSR_PBO.md # Certificación Oficial DSR 100% y PBO 6.67%
│   ├── INFORME_AUDITORIA_FORENSE_RIESGOS.md  # Auditoría de los 7 Riesgos Críticos
│   ├── INFORME_FUTUROS_100_USDT.md  # Estudio de Micro-Capital 100 USDT Anti-Freeze
│   └── PRELIMINARY_REPORT.md        # Auditoría Inicial Spot y Descarte de 1H
└── operations/
    └── OPERATIONAL_RUNBOOK.md       # Guía de Despliegue Docker, VPS, Kill-Switch y Bóveda
```

---

## 📐 Convenciones y Estándares Documentales (DocOps)

Para garantizar consistencia y rigor técnico en todo el repositorio, se aplican las siguientes convenciones obligatorias:

### 1. Metadatos Estandarizados (YAML Frontmatter)
Todo archivo markdown debe abrir con el bloque canónico de metadatos:
```yaml
---
id: [ID_UNICO]           # Ej: ADR-001, OPS-001, DOC-MASTER-001
title: [Titulo Claro]
category: [architecture | strategy | reports | operations]
version: [X.Y]
status: [ACTIVE | APPROVED | CERTIFIED | SUPERSEDED]
last_updated: YYYY-MM-DD
author: [Autor / Equipo]
---
```

### 2. Taxonomía de Directorios
| Directorio | Propósito | Convención de Nombres |
|---|---|---|
| `docs/architecture/` | Especificaciones de software y diseño | `DAS.md`, `decisions/ADR-XXX_*.md` |
| `docs/strategy/` | Visión económica, sprints y escalado | Planes estratégicos y roadmap |
| `docs/reports/` | Informes formales de auditoría y backtests | `INFORME_*.md` y reportes fechados |
| `docs/operations/` | Manuales operativos y contingencias | `OPERATIONAL_RUNBOOK.md` |

---

## 📂 Índice Clasificado de Documentos

### 🏛️ 1. Arquitectura y Decisiones de Diseño
* **[DAS.md](architecture/DAS.md) (Arquitectura v6.0):** Especificación completa de la infraestructura Freqtrade, CCXT, Bóveda Delta-Neutral y Machine Learning asimétrico.
* **[ADR-001: Asymmetric Short-Only Bias](architecture/decisions/ADR-001_asymmetric_short_only_bias.md):** Justificación de la supresión de Longs en memecoins (+63.24% neto).
* **[ADR-002: Arquitectura Híbrida Barbell](architecture/decisions/ADR-002_hybrid_barbell_cash_and_carry.md):** División entre motor de aceleración agresivo y bóveda Cash & Carry.
* **[ADR-003: Diferenciación Fraccionaria y Bet Sizing](architecture/decisions/ADR-003_fractional_diff_and_continuous_bet_sizing.md):** Integración de FFD ($d=0.40$) y la fórmula continua de López de Prado.
* **[ADR-004: Airbag Técnico y Órdenes Market](architecture/decisions/ADR-004_airbag_technical_exit_market_orders.md):** Retención de `exit_signal` y órdenes de mercado forzadas contra el riesgo de no-fill.

### 🧠 2. Estrategia Cuantitativa y Planificación
* **[ESTRATEGIA_MAESTRA_UNIFICADA.md](strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md) (STRAT-MASTER-001):** 🌟 Compendio canónico integral que consolida hipótesis, genealogía V1-V7, escalado 10X, arquitectura Barbell y blindaje anti-overfitting.
* **[HYPOTHESIS.md](strategy/HYPOTHESIS.md) (STRAT-001):** Fundamento económico del alfa en desinflación gravitacional post-pump y quiebre de EMA 200 en 4h.
* **[SCRUM_PLAN.md](strategy/SCRUM_PLAN.md) (STRAT-ROADMAP-001):** Registro histórico de los Sprints 1 a 20 con el Product Backlog trazable y Definición de Hecho (DoD).
* **[PLAN_ESCALADO_100_A_1000_USDT.md](strategy/PLAN_ESCALADO_100_A_1000_USDT.md) (STRAT-002):** Hoja de ruta de crecimiento exponencial 10X mediante micro-capital Anti-Freeze y criterio de Half-Kelly.
* **[PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md](strategy/PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md) (STRAT-003):** Especificación del traspaso mecánico del 60% de beneficios hacia la Bóveda Delta-Neutral al duplicar cuenta.
* **[PLAN_DESMITIFICACION_RIESGOS.md](strategy/PLAN_DESMITIFICACION_RIESGOS.md) (STRAT-004):** Protocolo de ablación y pruebas no-i.i.d. contra el autoengaño estadístico.
* **[PLAN_IMPLEMENTACION_V6_APEX.md](strategy/PLAN_IMPLEMENTACION_V6_APEX.md) (STRAT-EXP-001):** Registro post-mortem del experimento que refutó la supresión de salidas técnicas.

### 📊 3. Informes de Investigación y Auditoría Forense
* **[INFORME_METRICAS_AVANZADAS_DSR_PBO.md](reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md):** Certificación matemática de grado institucional (DSR = 100.0%, PBO = 6.67%, OOS Cross-Asset = +104.27%).
* **[INFORME_AUDITORIA_FORENSE_RIESGOS.md](reports/INFORME_AUDITORIA_FORENSE_RIESGOS.md):** Desglose empírico de los 215 trades de V5 y desmitificación de la estacionalidad de calendario.
* **[INFORME_FUTUROS_100_USDT.md](reports/INFORME_FUTUROS_100_USDT.md):** Estudio de micro-capital bajo restricciones reales de Binance ($5 Min Notional).
* **[PRELIMINARY_REPORT.md](reports/PRELIMINARY_REPORT.md):** Diagnóstico preliminar de Spot y refutación científica del timeframe intradiario de 1H.
* **[REPORTE_EJECUTIVO_MEME_HUNTER_V4.md](reports/REPORTE_EJECUTIVO_MEME_HUNTER_V4.md):** Resumen ejecutivo orientado a inversores.

### 🛠️ 4. Operaciones y Producción
* **[OPERATIONAL_RUNBOOK.md](operations/OPERATIONAL_RUNBOOK.md):** Procedimientos de despliegue Docker, variables `.env`, protocolos del Kill-Switch de 25% y comandos de contingencia.

---

## 🎯 Guía de Lectura Recomendada por Perfil

| Perfil | Ruta de Lectura Sugerida |
| :--- | :--- |
| **Inversor / Ejecutivo** | [`MANUAL_UNIFICADO_DEL_SISTEMA.md`](MANUAL_UNIFICADO_DEL_SISTEMA.md) ➔ [`reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md`](reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md) |
| **Investigador Cuantitativo** | [`strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md`](strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md) ➔ [`architecture/decisions/`](architecture/decisions/) ➔ [`reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md`](reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md) |
| **Ingeniero de Software** | [`architecture/DAS.md`](architecture/DAS.md) ➔ [`strategy/SCRUM_PLAN.md`](strategy/SCRUM_PLAN.md) ➔ [`operations/OPERATIONAL_RUNBOOK.md`](operations/OPERATIONAL_RUNBOOK.md) |
| **Operador de Producción** | [`operations/OPERATIONAL_RUNBOOK.md`](operations/OPERATIONAL_RUNBOOK.md) ➔ [`README.md`](../README.md) ➔ Dashboard FreqUI |

