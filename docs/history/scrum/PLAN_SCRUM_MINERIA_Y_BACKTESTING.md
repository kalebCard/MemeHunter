---
id: HIST-SCRUM-002
title: "Plan Scrum Cuantitativo: Fábrica de Minería de Alphas y Backtesting Industrial (Sprints 21 a 24)"
category: history/scrum
version: 8.0
status: COMPLETED
last_updated: 2026-10-13
author: Quantitative Engineering & Research Core
canonical_sprint_file: docs/history/sprints/03_SPRINTS_021_024_ALPHA_MINING_AND_BACKTESTING.md
references:
  - docs/research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md
  - docs/history/scrum/SCRUM_PLAN.md
  - docs/history/sprints/03_SPRINTS_021_024_ALPHA_MINING_AND_BACKTESTING.md
  - docs/architecture/DAS.md
---

# 🚀 Plan Scrum: Fábrica de Minería de Alphas y Backtesting Industrial (Sprints 21 a 24)

> [!NOTE]
> **Alineación y Estandarización de Sprint:** Este documento representa el Backlog Temático de las Épicas 8 a 11 del proyecto. Su plan de ejecución y certificación táctica se encuentra sincronizado canónicamente en [03_SPRINTS_021_024_ALPHA_MINING_AND_BACKTESTING.md](../sprints/03_SPRINTS_021_024_ALPHA_MINING_AND_BACKTESTING.md).

Este documento define el **Plan de Desarrollo Scrum de Nueva Generación** para transformar **Meme Hunter** de una estrategia algorítmica aislada a un **Sistema Autónomo de Minería de Factores, Validación Fuera de Muestra y Backtesting Cuantitativo Institucional**.

---

## 🎯 Visión del Producto y Grandes Épicas

```mermaid
graph TD
    subgraph Épica 8: Microestructura & Barras de Información (Sprint 21)
        A[Datos Brutos Binance 1m / Ticks] --> B[Generador de Dollar & Volume Bars]
        B --> C[Order Book Impact & Slippage Simulator L2]
    end

    subgraph Épica 9: Motor de Minería Genética de Alphas (Sprint 22)
        C --> D[Gramática Simbólica de Operadores WorldQuant]
        D --> E[Algoritmo Genético Multi-Objetivo NSGA-II]
        E --> F[Zoológico de Factores Descorrelacionados]
    end

    subgraph Épica 10: Auditoría Anti-Falsos Descubrimientos (Sprint 23)
        F --> G[Combinatorial Purged CV Industrializado]
        G --> H[Correcciones Múltiples FDR / Bonferroni / DSR]
        H --> I[Filtro PBO < 5% & Auto-Ablación]
    end

    subgraph Épica 11: Orquestador de Portafolio Ensemble & HRP (Sprint 24)
        I --> J[Hierarchical Risk Parity Allocator]
        J --> K[Strategy Life-Cycle Incubator: Sandbox -> Live -> Retiro]
        K --> L[Despliegue Multi-Estrategia Barbell en Freqtrade]
    end
```

---

## 📋 Registro de Sprints Detallado

### 🏃 Sprint 21: Ingesta de Información y Simulación de Microestructura L2 (Completado ✅)
**Objetivo del Sprint:** Superar la limitación del tiempo cronológico rígido (velas fijas de 4h/1h) transformando el muestreo a **Barras de Información Económica** (Dollar & Volume Bars) y calibrar el impacto de mercado y deslizamiento mediante modelos de microestructura.

* **PB-75 (Generador de Barras de Información - `dollar_bars.py`) — Completado ✅:**
  - Desarrollado [`data_engine/dollar_bars.py`](file:///c:/meme_hunter/data_engine/dollar_bars.py) con soporte para Dollar Bars, Volume Bars y Tick Imbalance Bars (TIB).
  - Implementado evaluador de normalidad estadística y test de Jarque-Bera.
* **PB-76 (Simulador de Microestructura y Slippage Dinámico - `slippage_engine.py`) — Completado ✅:**
  - Desarrollado [`data_engine/slippage_engine.py`](file:///c:/meme_hunter/data_engine/slippage_engine.py) implementando el modelo de impacto permanente/temporal de Almgren & Chriss.
  - Modelado de probabilidad de ejecución Maker condicional y cálculo de spread dinámico.
* **PB-77 (Suite de Pruebas y Validación de Microestructura) — Completado ✅:**
  - Creada [`tests/test_data_engine.py`](file:///c:/meme_hunter/tests/test_data_engine.py) certificando 6/6 tests pasando al 100%.

---

### 🧬 Sprint 22: Motor Simbólico de Minería de Alphas (Completado ✅)
**Objetivo del Sprint:** Automatizar el descubrimiento de factores cuantitativos eliminando el sesgo discrecional mediante programación genética y expresiones simbólicas multi-operador.

* **PB-78 (Gramática Simbólica de Operadores - `alpha_grammar.py`) — Completado ✅:**
  - Desarrollado [`mining/alpha_grammar.py`](file:///c:/meme_hunter/mining/alpha_grammar.py) con árbol sintáctico (AST) de operadores temporales, unarios, binarios y microestructura.
  - Evaluación vectorial protegida contra división por cero y NaNs.
* **PB-79 (Algoritmo Genético Multi-Objetivo - `genetic_search.py`) — Completado ✅:**
  - Desarrollado [`mining/genetic_search.py`](file:///c:/meme_hunter/mining/genetic_search.py) con búsqueda NSGA-II maximizando el Information Ratio (IC_IR) y penalizando por multicolinealidad ($>0.60$).
  - Operadores genéticos de mutación y cruce de subárboles sintácticos.
* **PB-80 (Catálogo de Factores Validados & Suite de Tests) — Completado ✅:**
  - Persistencia en JSON estructurado de factores (`save_factor_library`).
  - Creada [`tests/test_alpha_mining.py`](file:///c:/meme_hunter/tests/test_alpha_mining.py) certificando 4/4 tests unitarios pasando al 100%.

---

### 🛡️ Sprint 23: Blindaje Anti-Overfitting y Control de Falsos Descubrimientos (Completado ✅)
**Objetivo del Sprint:** Garantizar que ningún factor minado en el Sprint 22 sea producto del azar o la multiplicidad de pruebas mediante penalizaciones de López de Prado y correcciones estadísticas estrictas.

* **PB-81 (Motor CPCV Industrializado - `cpcv_engine.py`) — Completado ✅:**
  - Desarrollado [`validation/cpcv_engine.py`](file:///c:/meme_hunter/validation/cpcv_engine.py) con soporte para particionado combinatorio de $N$ bloques y $k$ conjuntos de test ($C(N, k)$).
  - Purgado determinista de eventos adyacentes y cuarentena (embargo) temporal post-evaluación.
* **PB-82 (Filtro de Falsos Descubrimientos - `multiple_testing.py`) — Completado ✅:**
  - Desarrollado [`validation/multiple_testing.py`](file:///c:/meme_hunter/validation/multiple_testing.py) con corrección de Benjamini-Hochberg (FDR) y Bonferroni (FWER).
  - Estimador de Probabilidad de Sobreajuste en el Backtest (PBO) a partir de matrices CPCV.
* **PB-83 (Pipeline Automatizado de Certificación Cuantitativa & Tests) — Completado ✅:**
  - Creada [`tests/test_validation_engine.py`](file:///c:/meme_hunter/tests/test_validation_engine.py) certificando 4/4 tests unitarios pasando al 100%.

---

### ⚖️ Sprint 24: Orquestador de Portafolio Ensemble, HRP y Ciclo de Vida (Completado ✅)
**Objetivo del Sprint:** Integrar los factores validados en un portafolio multi-estrategia descorrelacionado con asignación por Paridad Jerárquica de Riesgo (HRP) y gobernanza de retiro por decaimiento de Alpha.

* **PB-84 (Optimizador Hierarchical Risk Parity - `hrp_allocator.py`) — Completado ✅:**
  - Desarrollado [`portfolio/hrp_allocator.py`](file:///c:/meme_hunter/portfolio/hrp_allocator.py) con árbol de enlace jerárquico, orden cuasi-diagonal y bisección recursiva inversa de varianza.
  - Erradica los pesos extremos de Markowitz y garantiza diversificación matemática robusta.
* **PB-85 (Orquestador de Ciclo de Vida de Estrategias - `strategy_incubator.py`) — Completado ✅:**
  - Desarrollado [`portfolio/strategy_incubator.py`](file:///c:/meme_hunter/portfolio/strategy_incubator.py) con máquina de estados finitos (`SANDBOX` $\to$ `LIVE` $\to$ `ALPHA_DECAY` $\to$ `RETIRED`).
  - Detector de Alpha Decay con $Z$-Score condicional al error estándar del Sharpe ratio.
* **PB-86 (Rebalanceo HRP & Suite de Tests) — Completado ✅:**
  - Rebalanceo dinámico de subcuentas vivas y persistencia estructurada en `portfolio/incubator_state.json`.
  - Creada [`tests/test_portfolio_engine.py`](file:///c:/meme_hunter/tests/test_portfolio_engine.py) certificando 3/3 tests unitarios pasando al 100%.

---

## 📅 Matriz de Planificación y Asignación

| Sprint | Épica Asociada | Entregable Clave | Estado | Criterio de Éxito |
|:---:|---|---|:---:|---|
| **Sprint 21** | Épica 8: Microestructura & Barras | `dollar_bars.py`, `slippage_engine.py` | ✅ Completado | Normalidad Jarque-Bera mejorada y slippage dinámico Almgren-Chriss |
| **Sprint 22** | Épica 9: Minería Simbólica | `alpha_grammar.py`, `genetic_search.py` | ✅ Completado | Algoritmo NSGA-II evaluando AST y penalizando correlación $>0.60$ |
| **Sprint 23** | Épica 10: Control Anti-Overfitting | `cpcv_engine.py`, `multiple_testing.py` | ✅ Completado | CPCV purgado/embargado, FDR Benjamini-Hochberg y estimador PBO |
| **Sprint 24** | Épica 11: Portafolio Ensemble | `hrp_allocator.py`, `strategy_incubator.py` | ✅ Completado | Paridad Jerárquica de Riesgo (HRP) y ciclo de vida Sandbox $\to$ Live $\to$ Retiro |

---

## 🎯 Definición de Hecho (DoD) Específica para Minería Cuantitativa
1. **Cero Minería a Ciegas:** Ningún factor se acepta sin haber evaluado su matriz de correlación contra todos los factores preexistentes en la biblioteca.
2. **Penalización Obligatoria por Múltiples Ensayos:** El cálculo del DSR debe usar como parámetro $N$ el número exacto de combinaciones evaluadas por el algoritmo genético (ej. $N \ge 1,000$).
3. **Control Estricto de Fricción Microestructural:** Todo backtest de factor debe correr con el simulador de slippage dinámico de Almgren-Chriss activado.
4. **Validación Fuera de Muestra Cruzada:** Todo factor debe validarse en una ventana temporal ciega y sobre al menos 3 activos no empleados en la función de aptitud genética.
5. **100% Cobertura de Tests:** Suites de pruebas unitarias pasando al 100% en `tests/`.
