---
id: STRAT-PLAN-MINING-001
title: Plan Scrum Cuantitativo - Fábrica de Minería de Alphas y Backtesting Industrial (Sprints 21 a 24)
category: strategy
version: 6.0
status: ACTIVE
last_updated: 2026-10-11
author: Quantitative Engineering & Research Core
references:
  - docs/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md
  - docs/strategy/SCRUM_PLAN.md
  - docs/architecture/DAS.md
---

# 🚀 Plan Scrum: Fábrica de Minería de Alphas y Backtesting Industrial (Sprints 21 a 24)

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
  - Desarrollado [`data_engine/dollar_bars.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/data_engine/dollar_bars.py) con soporte para Dollar Bars, Volume Bars y Tick Imbalance Bars (TIB).
  - Implementado evaluador de normalidad estadística y test de Jarque-Bera.
* **PB-76 (Simulador de Microestructura y Slippage Dinámico - `slippage_engine.py`) — Completado ✅:**
  - Desarrollado [`data_engine/slippage_engine.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/data_engine/slippage_engine.py) implementando el modelo de impacto permanente/temporal de Almgren & Chriss.
  - Modelado de probabilidad de ejecución Maker condicional y cálculo de spread dinámico.
* **PB-77 (Suite de Pruebas y Validación de Microestructura) — Completado ✅:**
  - Creada [`tests/test_data_engine.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_data_engine.py) certificando 6/6 tests pasando al 100%.

---

### 🧬 Sprint 22: Motor Simbólico de Minería de Alphas (Completado ✅)
**Objetivo del Sprint:** Automatizar el descubrimiento de factores cuantitativos eliminando el sesgo discrecional mediante programación genética y expresiones simbólicas multi-operador.

* **PB-78 (Gramática Simbólica de Operadores - `alpha_grammar.py`) — Completado ✅:**
  - Desarrollado [`mining/alpha_grammar.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/mining/alpha_grammar.py) con árbol sintáctico (AST) de operadores temporales, unarios, binarios y microestructura.
  - Evaluación vectorial protegida contra división por cero y NaNs.
* **PB-79 (Algoritmo Genético Multi-Objetivo - `genetic_search.py`) — Completado ✅:**
  - Desarrollado [`mining/genetic_search.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/mining/genetic_search.py) con búsqueda NSGA-II maximizando el Information Ratio (IC_IR) y penalizando por multicolinealidad ($>0.60$).
  - Operadores genéticos de mutación y cruce de subárboles sintácticos.
* **PB-80 (Catálogo de Factores Validados & Suite de Tests) — Completado ✅:**
  - Persistencia en JSON estructurado de factores (`save_factor_library`).
  - Creada [`tests/test_alpha_mining.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_alpha_mining.py) certificando 4/4 tests unitarios pasando al 100%.

---

### 🛡️ Sprint 23: Blindaje Anti-Overfitting y Control de Falsos Descubrimientos
**Objetivo del Sprint:** Garantizar que ningún factor minado en el Sprint 22 sea producto del azar o la multiplicidad de pruebas mediante penalizaciones de López de Prado y correcciones estadísticas estrictas.

* **PB-81 (Motor CPCV Industrializado - `cpcv_engine.py`):**
  - Desarrollar `validation/cpcv_engine.py` con soporte para particionado combinatorio de $N=16$ bloques temporales tomando $k=4$ combinaciones ($1,820$ iteraciones OOS).
  - Purgado determinista de eventos superpuestos y embargo de 48 horas post-evento para destruir la memoria residual.

* **PB-82 (Filtro de Falsos Descubrimientos - `multiple_testing.py`):**
  - Implementar corrección de Benjamini-Hochberg (FDR) y corrección de Bonferroni (FWER) escaladas al número total de factores explorados ($M$).
  - Cálculo estricto de PBO: Descartar automáticamente cualquier hipótesis con $\text{PBO} \ge 5.0\%$.

* **PB-83 (Pipeline Automatizado de Certificación Cuantitativa):**
  - Generador de reportes en markdown `reports/INFORME_CERTIFICACION_ALPHA_XXX.md` con curvas de decaimiento y matrices de correlación.
  - Criterio de Aceptación: Todo factor en la biblioteca debe aprobar DSR $> 95\%$ y PBO $< 5\%$.

---

### ⚖️ Sprint 24: Orquestador de Portafolio Ensemble, HRP y Ciclo de Vida
**Objetivo del Sprint:** Integrar los factores validados en un portafolio multi-estrategia descorrelacionado con asignación por Paridad Jerárquica de Riesgo (HRP) y gobernanza de retiro por decaimiento de Alpha.

* **PB-84 (Optimizador Hierarchical Risk Parity - `hrp_allocator.py`):**
  - Desarrollar `portfolio/hrp_allocator.py` utilizando agrupamiento cuasi-diagonal (*tree clustering*) sobre la matriz de correlaciones de rendimientos.
  - Eliminar los pesos extremos e inestables de Markowitz, garantizando robustez ante errores de estimación de covarianza.

* **PB-85 (Orquestador de Ciclo de Vida de Estrategias - `strategy_incubator.py`):**
  - Implementar la máquina de estados:
    1. **Sandbox (Paper Trading):** 30 días de evaluación ciega en vivo.
    2. **Graduación a Producción:** Asignación de hasta el 10% del capital si retiene $\text{PSR} \ge 90\%$.
    3. **Detector de Alpha Decay:** Si el rendimiento cae 2 desviaciones estándar respecto al OOS durante 45 días, el orquestador reduce el peso a 0% y retira la estrategia.

* **PB-86 (Generador de Estrategias Freqtrade Dinámicas - `compile_ensemble_strategy.py`):**
  - Compilador que toma los factores activos de `factor_library.py` y genera una estrategia ejecutable nativa de Freqtrade compatible con la arquitectura Híbrida Barbell y la Bóveda Delta-Neutral.
  - Criterio de Aceptación: 100% de tests de integración pasando en Docker y simulación en vivo funcional.

---

## 📅 Matriz de Planificación y Asignación

| Sprint | Épica Asociada | Entregable Clave | Dependencias | Criterio de Éxito |
|:---:|---|---|---|---|
| **Sprint 21** | Épica 8: Microestructura & Barras | `dollar_bars.py`, `slippage_engine.py` | Datos 1m Binance | Normalidad Jarque-Bera mejorada y slippage dinámico calibrado |
| **Sprint 22** | Épica 9: Minería Simbólica | `alpha_grammar.py`, `genetic_search.py` | Sprint 21 | $\ge 10$ factores con $\text{IC} \ge 0.04$ y correlación $< 0.60$ |
| **Sprint 23** | Épica 10: Control Anti-Overfitting | `cpcv_engine.py`, `multiple_testing.py` | Sprint 22 | $\text{PBO} < 5.0\%$, DSR $> 95\%$ y corrección FDR aprobada |
| **Sprint 24** | Épica 11: Portafolio Ensemble | `hrp_allocator.py`, `strategy_incubator.py` | Sprint 23 | Ensamble HRP operando en Docker con retiro automático por decay |

---

## 🎯 Definición de Hecho (DoD) Específica para Minería Cuantitativa
1. **Cero Minería a Ciegas:** Ningún factor se acepta sin haber evaluado su matriz de correlación contra todos los factores preexistentes en la biblioteca.
2. **Penalización Obligatoria por Múltiples Ensayos:** El cálculo del DSR debe usar como parámetro $N$ el número exacto de combinaciones evaluadas por el algoritmo genético (ej. $N \ge 1,000$).
3. **Control Estricto de Fricción Microestructural:** Todo backtest de factor debe correr con el simulador de slippage dinámico de Almgren-Chriss activado.
4. **Validación Fuera de Muestra Cruzada:** Todo factor debe validarse en una ventana temporal ciega y sobre al menos 3 activos no empleados en la función de aptitud genética.
5. **100% Cobertura de Tests:** Suites de pruebas unitarias pasando al 100% en `tests/`.
