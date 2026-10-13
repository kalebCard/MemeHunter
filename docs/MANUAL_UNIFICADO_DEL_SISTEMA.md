---
id: DOC-MASTER-001
title: Manual Maestro Unificado del Sistema Meme Hunter
category: master
version: 7.4
status: CERTIFIED
last_updated: 2026-10-12
author: Quantitative Engineering & Research Core
---

# 📖 Manual Maestro Unificado del Sistema Meme Hunter (Versión 7.4)

Este documento consolida la totalidad del conocimiento teórico, arquitectónico, cuantitativo y operativo del proyecto **meme_hunter**, unificando los planes estratégicos, informes forenses, especificaciones técnicas del motor autónomo auto-evolutivo y gobernanza de costes en una única referencia canónica.

---

## 📑 Tabla de Contenidos

1. [Visión y Fundamentos Teóricos](#1-visión-y-fundamentos-teóricos)
2. [Arquitectura Global: El Modelo Híbrido Barbell](#2-arquitectura-global-el-modelo-híbrido-barbell)
3. [Evolución de Estrategias y el Motor Canónico V7 Quantum](#3-evolución-de-estrategias-y-el-motor-canónico-v7-quantum)
4. [Auditoría Forense y Certificación Cuantitativa de Grado Institucional](#4-auditoría-forense-y-certificación-cuantitativa-de-grado-institucional)
5. [Microestructura de Mercado y Control de Fricciones](#5-microestructura-de-mercado-y-control-de-fricciones)
6. [Motor Cuantitativo Auto-Evolutivo, Cognición IA y Modelo Económico](#6-motor-cuantitativo-auto-evolutivo-cognición-ia-y-modelo-económico)
7. [Catálogo Integral de Scripts y Módulos Satélite](#7-catálogo-integral-de-scripts-y-módulos-satélite)
8. [Protocolos Operativos, CLI Unificado y Runbook de Producción](#8-protocolos-operativos-cli-unificado-y-runbook-de-producción)
9. [Registro de Decisiones Arquitectónicas (ADRs)](#9-registro-de-decisiones-arquitectónicas-adrs)
10. [Compendio de Estrategia y Hoja de Ruta Cuantitativa](#10-compendio-de-estrategia-y-hoja-de-ruta-cuantitativa)
11. [Centro de Control Unificado (Cockpit v7.2) y Laboratorio Cuantitativo](#11-centro-de-control-unificado-cockpit-v72-y-laboratorio-cuantitativo)
12. [Arquitectura de Estabilización y Blindaje Operativo](#12-arquitectura-de-estabilización-y-blindaje-operativo)
13. [Fábrica de Alphas SQLite WAL, Gating OOS y Enlace Bidireccional](#13-fábrica-de-alphas-sqlite-wal-gating-oos-y-enlace-bidireccional-sprints-25-a-29)
14. [Arquitectura Multi-Agente, Orquestador DAG y Cockpit Human-in-the-Loop](#14-arquitectura-multi-agente-orquestador-dag-y-cockpit-human-in-the-loop-sprints-30-a-32)

---

## 1. Visión y Fundamentos Teóricos

### 1.1 El Problema de la Compresión de Pérdidas en Finanzas
Las metodologías técnicas clásicas describen procesos estocásticos continuos mediante micro-patrones discretos (velas japonesas, figuras chartistas). La minería irrestricta de estos patrones ha erosionado las ineficiencias del mercado debido al arbitraje masivo de capital cuantitativo (Regla de Rentabilidad).

Para evitar descubrir anomalías puramente espurias, **meme_hunter** adopta el enfoque de **Descubrimiento Guiado por el Dominio (DDID-PD)**: toda estrategia algorítmica debe descansar sobre una justificación económica causal antes de someterse a backtesting.

### 1.2 La Hipótesis Causal del Edge en Memecoins (Short-Bias)
* **Las memecoins no poseen valor intrínseco ni flujos de caja.**
* Tras una fase de euforia parabólica (3 a 7 días) impulsada por viralidad en redes, los tokens entran en un régimen secular de distribución y desinflado gravitacional que dura meses, perdiendo entre el 80% y 95% de su valor.
* **El Alfa Institucional:** Operar exclusivamente en el lado **Short** en velas de 4H al confirmarse el quiebre de estructura bajo la EMA 200, eliminando las compras Long que históricamente destruían capital en *bull traps*.

---

## 2. Arquitectura Global: El Modelo Híbrido Barbell

Para resolver el dilema entre "alto retorno con riesgo de ruina" y "seguridad absoluta con crecimiento microscópico", el sistema implementa la **Arquitectura Híbrida Barbell (de Pesas)**:

```mermaid
graph TD
    subgraph Extremo Agresivo (Alpha Engine)
        A[Micro-Capital: 100 USDT] --> B[Freqtrade Futures Engine: 4H]
        B -->|MemeHunterFuturesV7_Quantum 1.5x| C[Equity Dinámico en Futuros]
    end

    subgraph Válvula de Trinquete (Risk Isolation)
        C --> D{Profit Ratchet Daemon}
        D -->|Duplicación +100%| E[Extracción Mecánica del 60%]
        E -->|Transferencia CCXT| F[Balance Spot / Bóveda]
        D -->|Drawdown >= 25%| K[Kill-Switch Inmediato]
    end

    subgraph Extremo Conservador (Delta-Neutral Vault)
        F --> G[Delta-Neutral Vault Manager]
        G --> H[Short Futuros 1.0x + Long Spot]
        H --> I[Cobro de Funding: 12% - 30% APR]
        I --> J[Acumulación de Flujo Pasivo Continuo]
    end
```

1. **Alpha Engine:** Acelera micro-capital mediante quiebres de estructura y dimensionamiento continuo de apuestas.
2. **Válvula de Trinquete (`scripts/profit_ratchet_daemon.py`):** Inmuniza el 60% de las ganancias en cada hito de duplicación (+100%), reseteando la base de cálculo de Freqtrade para que las pérdidas futuras no afecten el capital ya asegurado.
3. **Bóveda Delta-Neutral (`scripts/delta_neutral_vault.py`):** Despliega el capital cosechado en posiciones Cash & Carry simétricas ($\Delta = 0$), extrayendo tasas de financiación sin exposición direccional al mercado.

---

## 3. Evolución de Estrategias y el Motor Canónico V7 Quantum

### 3.1 Tabla Evolutiva de Versiones

| Versión | Setup Clave | Win Rate | Retorno Neto | Calmar | Lección Cuantitativa |
|---|---|:---:|:---:|:---:|---|
| **Intradía 1h/15m (PB-39)** | Scalping de alta frecuencia | 39.3% | **-75.46%** | Negativo | **Refutado:** Destrucción masiva por comisiones de exchange y mechas intra-vela. |
| **V1 Short-Only (PB-40)** | Tendencia macro 4h bajista | 48.7% | **+63.24%** | 4.00 | **Validado:** Multiplicó el retorno por 11.3X al eliminar compras Long. |
| **V4 Subasta + Calendario (PB-50)** | Trapped Longs + Jueves-Domingo | 53.4% | **+58.93%** | 16.62 | **Validado:** Modelo Anti-Freeze concentrado en 4 slots de 25 USDT. |
| **V5 Leverage (PB-56)** | Apalancamiento dinámico 1.5x-2.0x | 61.4% | **+96.20%** | 21.03 | **Auditoría Forense:** Gran retorno pero setup 2.0x tenía $N=2$ y minería de calendario. |
| **V6 Apex (PB-58)** | Supresión de `exit_signal` | 67.2% | +27.01% | 3.48 | **Refutado:** Salidas técnicas actúan como airbag salvavidas; eliminarlas triplica pérdidas. |
| **V5 Ablation (PB-61)** | Sin filtros de calendario ($N=2,361$) | 50.2% | **+156.29%** | 7.06 | **Edge Puro:** Retorno medio $\mu=+0.667\%$ con $p=0.0068$ en muestra masiva. |
| **V5 OOS Cross-Asset (PB-60)** | Activos ciegos: SOL, SUI, TIA, WLD | 53.1% | **+104.27%** | 8.90 | **Prueba Definitiva:** Edge transferible y no sobreajustado ($DSR = 100.0\%$). |
| **V7 Quantum (PB-74)** | FFD d=0.40 + Bet Sizing Continuo | — | — | — | 🌌 **Canónica de Producción Oficial.** |

### 3.2 Lógica del Motor Canónico: `MemeHunterFuturesV7_Quantum.py`
* **Diferenciación Fraccionaria (FFD d=0.40):** Calcula la serie fraccionaria de precios para retener memoria a largo plazo mientras rechaza raíz unitaria (ADF test $p < 0.05$).
* **Bet Sizing Continuo en `leverage()`:** Transforma la convicción del setup en una probabilidad $p \in [0.50, 0.95]$ y calcula el apalancamiento continuo vía:
  $$m = 2 Z\left[\frac{p - 0.5}{\sqrt{p(1-p)}}\right] - 1 \implies \text{Apalancamiento} \in [1.0x, 2.0x]$$
* **Órdenes Market en Salidas:** Entradas pasivas Maker al Bid para pagar comisiones mínimas (0.02%), pero salidas técnicas y de emergencia forzadas como `market` para evitar el riesgo de *no-fill*.

---

## 4. Auditoría Forense y Certificación Cuantitativa de Grado Institucional

Los resultados de los backtests oficiales fueron sometidos a la suite estadística de Marcos López de Prado y Campbell Harvey ([`scripts/audit_advanced_backtests.py`](../scripts/audit_advanced_backtests.py)):

### 4.1 Métricas Clave de Certificación
1. **Probabilidad de Sobreajuste (PBO = 6.67%):**
   * Evaluada mediante Combinatorial Purged Cross-Validation (**CPCV**) con 15 particiones combinatorias, *purging* de solapamientos y *embargo* temporal.
   * Un PBO de 6.67% está ampliamente por debajo del umbral de peligro (50.0%) y en la zona de excelencia (<25.0%).
2. **Deflated Sharpe Ratio (DSR = 100.0%):**
   * Tras penalizar por el sesgo de múltiples ensayos acumulados ($N \ge 6$) y la asimetría de colas de las memecoins, la estrategia retiene significancia estadística formal en activos ciegos fuera de muestra.
3. **Ratificación del Apalancamiento 1.5x:**
   * La prueba a 1.0x plano (`V5_Flat1x`) obtuvo $\mu = +0.458\%$, un margen tan estrecho que el DSR lo penalizó a 0% de significancia ante comisiones. El apalancamiento moderado 1.5x es indispensable para generar colchón matemático sin elevar el riesgo de ruina.

---

## 5. Microestructura de Mercado y Control de Fricciones

1. **Libro de Órdenes (LOB) y Desequilibrio (OFI):**
   * Implementado en [`scripts/order_flow_imbalance.py`](../scripts/order_flow_imbalance.py) para monitorizar el Micro-Price y evitar selección adversa en la colocación de órdenes.
2. **Ley de la Raíz Cuadrada del Impacto de Mercado:**
   * Las órdenes institucionales de salida trocean el flujo para mitigar el deslizamiento: $\text{Impacto} \propto \sigma \sqrt{V_{\text{orden}} / V_{24h}}$.
3. **El Guardián de Tasa de Financiación (Funding Bleed Guard):**
   * Bloquea aperturas Short si el funding rate proyectado es $< -0.05\%$ por 8h, previniendo el sangrado pasivo pagando comisiones a los Longs.

---

## 6. Motor Cuantitativo Auto-Evolutivo, Cognición IA y Modelo Económico

A partir de la versión 7.0, el sistema incorpora un bucle cerrado continuo de auto-sanación y optimización cognitiva:

```mermaid
graph LR
    A[Mercado en Vivo Binance] --> B[AlphaHealthMonitor]
    B -->|Decay / CUSUM Break| C[AlphaAutopsyAgent DeepSeek-R1]
    C -->|Diagnóstico Causal| D[LLMAlphaSynthesizer DeepSeek-V3]
    D -->|Fórmulas Validadas AST| E[QualityDiversityArchive MAP-Elites]
    E --> F[StrategyLifecycleIncubator]
    F --> G[HRP Risk Parity Allocator]
    G --> H[Cockpit Visual Puerto 8088]
```

### 6.1 Diagnóstico Forense y Bucle Closed-Loop
1. **Detección Temprana de Degradación:** `AlphaHealthMonitor` evalúa correlación móvil de Spearman ($IC$), ratio de información ($IC\_IR$), quiebres estructurales CUSUM ($h = 4.0\sigma$) y desplazamiento de datos con Kolmogorov-Smirnov.
2. **Ciclo de Vida Formal:** Transición atómica y persistida (`os.replace`) entre `SANDBOX` $\rightarrow$ `LIVE` $\rightarrow$ `ALPHA_DECAY` $\rightarrow$ `RETIRED` con 10 días de gracia.
3. **Asignación HRP:** Reponderación de capital inmune a singularidades de varianza cero.

### 6.2 Modelo Económico, Costes y Meta de Convergencia
* **Coste por Ciclo:** **~$0.00125 USD** (~2,700 tokens combinados entre DeepSeek-R1 y DeepSeek-V3; modo fallback offline automático a **$0.00 USD**).
* **Meta Programada de Parada (*Target Goal*):** **Sharpe Ponderado $\ge 2.50$** (`AUTONOMOUS_TARGET_SHARPE=2.50`). Al alcanzarse, el sistema marca `goal_reached = True`, congela la generación y preserva la estabilidad del portafolio.
* **Salvaguardas de Gasto:** Límite presupuestario estricto de **$1.00 USD** (`AUTONOMOUS_MAX_BUDGET_USD=1.00`), tope de **10 ciclos** (`AUTONOMOUS_MAX_CYCLES=10`) y límite diario de 150,000 tokens.

---

## 7. Catálogo Integral de Scripts y Módulos Satélite

> **Catálogo Modular:** Para la especificación exhaustiva y categorizada de los 47 scripts distribuidos en sus 6 dominios funcionales (`research/`, `backtest/`, `simulation/`, `pipelines/`, `data/`, `ops/`), consultar el [**Manual Operativo de Scripts**](../scripts/README.md).

| Módulo / Script | Propósito Cuantitativo | Comando de Ejecución |
|---|---|---|
| [`meme_cli.py`](../scripts/meme_cli.py) | 🌟 **CLI Unificado de Operaciones, Salud, Test y Control** | `python scripts/meme_cli.py [health|cockpit|futures|test|research]` |
| [`auto_data_sync.py`](../data_engine/auto_data_sync.py) | 📡 **Sincronizador continuo en vivo de Binance Futures (Feather 4H)** | `python data_engine/auto_data_sync.py` |
| [`compile_ensemble_strategy.py`](../scripts/compile_ensemble_strategy.py) | ⚙️ **Compilador del ensamble dinámico bidireccional (Long/Short)** | `python scripts/compile_ensemble_strategy.py` |
| [`oos_gating.py`](../portfolio/oos_gating.py) | 🛡️ **Compuertas Fuera de Muestra OOS (PBO < 15%, DSR >= 95%)** | `python -m portfolio.oos_gating` |
| [`db_pool.py`](../portfolio/db_pool.py) | 🗄️ **Pool transaccional multihilo SQLite WAL (alpha_factory.db)** | `python -m portfolio.db_pool` |
| [`freqtrade_client.py`](../client/freqtrade_client.py) | 🔌 **Cliente REST Freqtrade (Hot-Reload en vivo puerto 8081)** | `python -m client.freqtrade_client` |
| [`check_health.py`](../scripts/check_health.py) | 🩺 **Centinela de Salud y Diagnóstico Rápido (2 segundos)** | `python scripts/check_health.py` |
| [`start_dashboard.py`](../scripts/start_dashboard.py) | Cockpit Visual Web multihilo con Chart.js (Puerto 8088) | `python scripts/start_dashboard.py` |
| [`run_live_alpha_loop.py`](../scripts/run_live_alpha_loop.py) | Bucle cerrado continuo E2E conectado a Binance | `python scripts/run_live_alpha_loop.py` |
| [`run_autonomous_engine_demo.py`](../scripts/run_autonomous_engine_demo.py) | Demostración E2E del bucle cerrado auto-evolutivo | `python scripts/run_autonomous_engine_demo.py` |
| [`autonomous_orchestrator.py`](../portfolio/autonomous_orchestrator.py) | Orquestador central del bucle cerrado y control de costes | `python -m portfolio.autonomous_orchestrator` |
| [`alpha_health_monitor.py`](../portfolio/alpha_health_monitor.py) | Monitoreo de salud: Rolling IC, CUSUM y KS drift | `python -m portfolio.alpha_health_monitor` |
| [`alpha_autopsy.py`](../portfolio/alpha_autopsy.py) | Agente forense de autopsias con LLM (OpenRouter) | `python -m portfolio.alpha_autopsy` |
| [`llm_alpha_generator.py`](../mining/llm_alpha_generator.py) | Sintetizador de factores cuantitativos guiado por LLM | `python -m mining.llm_alpha_generator` |
| [`formula_parser.py`](../mining/formula_parser.py) | Compilador seguro AST Zero-Eval (Python 3.14) | `python -m mining.formula_parser` |
| [`live_market_feed.py`](../data_engine/live_market_feed.py) | Ingesta continua en streaming con RLock reentrante | `python -m data_engine.live_market_feed` |
| [`advanced_metrics.py`](../scripts/advanced_metrics.py) | Cálculo de PSR, Deflated Sharpe (DSR), CPCV y PBO | `python scripts/advanced_metrics.py` |
| [`fractional_diff.py`](../scripts/fractional_diff.py) | Expansión FFD y búsqueda automática de $d$ óptimo | `python scripts/fractional_diff.py` |
| [`triple_barrier_metalabeling.py`](../scripts/triple_barrier_metalabeling.py) | Triple Barrera, Meta-Etiquetado y Bet Sizing continuo | `python scripts/triple_barrier_metalabeling.py` |
| [`audit_advanced_backtests.py`](../scripts/audit_advanced_backtests.py) | Ingesta de backtests ZIP oficiales y certificación PBO | `python scripts/audit_advanced_backtests.py` |
| [`train_meta_model.py`](../scripts/train_meta_model.py) | Pipeline integrado de ML financiero con compuertas DSR | `python scripts/train_meta_model.py` |
| [`delta_neutral_vault.py`](../scripts/delta_neutral_vault.py) | Bóveda Cash & Carry con escaneo en vivo de Binance | `python scripts/delta_neutral_vault.py --scan` |
| [`profit_ratchet_daemon.py`](../scripts/profit_ratchet_daemon.py) | Válvula de extracción del 60% de utilidades en duplicaciones | `python scripts/profit_ratchet_daemon.py` |
| [`simulate_hybrid_barbell.py`](../scripts/simulate_hybrid_barbell.py) | Modelado Monte Carlo hacia $10,000 USDT/mes pasivos | `python scripts/simulate_hybrid_barbell.py` |
| [`dollar_bars.py`](../data_engine/dollar_bars.py) | Generador de Dollar, Volume y Tick Imbalance Bars (TIB) | `python -m data_engine.dollar_bars` |
| [`slippage_engine.py`](../data_engine/slippage_engine.py) | Simulador de microestructura L2 y slippage Almgren-Chriss | `python -m data_engine.slippage_engine` |
| [`alpha_grammar.py`](../mining/alpha_grammar.py) | Árbol sintáctico AST y operadores de factores WorldQuant | `python -m mining.alpha_grammar` |
| [`genetic_search.py`](../mining/genetic_search.py) | Algoritmo genético NSGA-II y minería de factores | `python -m mining.genetic_search` |
| [`cpcv_engine.py`](../validation/cpcv_engine.py) | Combinatorial Purged Cross-Validation purgado y embargado | `python -m validation.cpcv_engine` |
| [`multiple_testing.py`](../validation/multiple_testing.py) | Control de falsos descubrimientos FDR, Bonferroni y PBO | `python -m validation.multiple_testing` |
| [`hrp_allocator.py`](../portfolio/hrp_allocator.py) | Asignación de capital por Paridad Jerárquica de Riesgo (HRP) | `python -m portfolio.hrp_allocator` |
| [`strategy_incubator.py`](../portfolio/strategy_incubator.py) | Orquestador de ciclo de vida (Sandbox -> Live -> Retiro) | `python -m portfolio.strategy_incubator` |
| [`backtest_scanner.py`](../dashboard/backtest_scanner.py) | Lector de 11 estrategias Freqtrade, 34 zips de backtests y SQLite | `python -m dashboard.backtest_scanner` |
| [`strategy_tester.py`](../dashboard/strategy_tester.py) | Motor vectorial de backtesting y AST Zero-Eval para el Studio | `python -m dashboard.strategy_tester` |
| [`regime_classifier.py`](../scripts/regime_classifier.py) | Clasificador dinámico de régimen (Bull/Bear/Chop) | `python scripts/regime_classifier.py --symbol BTC/USDT:USDT` |
| [`order_flow_imbalance.py`](../scripts/order_flow_imbalance.py) | Microestructura Nivel 2 y desequilibrio de órdenes (OFI) | `python scripts/order_flow_imbalance.py --symbol DOGE/USDT:USDT` |
| [`meme_sentinel.py`](../scripts/meme_sentinel.py) | Detección temprana de volumen relativo anormal (RVOL) | `python scripts/meme_sentinel.py --top 10` |
| [`dex_viral_radar.py`](../scripts/dex_viral_radar.py) | Radar on-chain DEX (Solana/Base/ETH) vía DexScreener | `python scripts/dex_viral_radar.py --top 10` |

---

## 8. Protocolos Operativos, CLI Unificado y Runbook de Producción

1. **Gestión Estandarizada mediante CLI (`meme_cli.py`):**
   * Auditoría de salud operativa: `python scripts/meme_cli.py health` (diagnóstico en ~1.5s).
   * Monitoreo y control del Cockpit: `python scripts/meme_cli.py cockpit` (puerto 8088).
   * Motor de futuros en Docker: `python scripts/meme_cli.py futures [start|stop|logs|status]`.
   * Pruebas automáticas: `python scripts/meme_cli.py test`.
   * Herramientas de I+D: `python scripts/meme_cli.py research [stress|vault|monte-carlo|sentinel]`.
2. **Protección Kill-Switch:** Si el drawdown de equidad total alcanza el **25%**, se crea el testigo `user_data/KILL_SWITCH`, bloqueando nuevas entradas de inmediato.
3. **Criterio de Liberación a Producción:** Ningún código se despliega sin que los **151+ tests de la suite completa** pasen al 100%:
   ```powershell
   python -m pytest tests -v
   ```
   **Certificación Oficial:** **151+ tests pasando al 100% (0 errores)** certificando la suite integral sin regresiones.

---

## 9. Registro de Decisiones Arquitectónicas (ADRs)

* **[ADR-001: Asymmetric Short-Only Bias](architecture/decisions/ADR-001_asymmetric_short_only_bias.md):** Justificación matemática del descarte de Longs y explotación de la desinflación secular.
* **[ADR-002: Arquitectura Híbrida Barbell](architecture/decisions/ADR-002_hybrid_barbell_cash_and_carry.md):** Justificación de la aceleración agresiva + trinquete del 60% + bóveda Cash & Carry.
* **[ADR-003: Diferenciación Fraccionaria y Bet Sizing Continuo](architecture/decisions/ADR-003_fractional_diff_and_continuous_bet_sizing.md):** Transición de parámetros discretos subjetivos a modelos continuos derivados de Kelly y FFD ($d=0.40$).
* **[ADR-004: Airbag Técnico y Órdenes Market](architecture/decisions/ADR-004_airbag_technical_exit_market_orders.md):** Justificación del uso de `exit_signal` como amortiguador y órdenes de mercado para erradicar no-fills.

---

## 10. Compendio de Estrategia y Hoja de Ruta Cuantitativa

* **[ESTRATEGIA_MAESTRA_UNIFICADA.md](strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md) (STRAT-MASTER-001):** Compendio canónico integral de estrategia cuantitativa, micro-capital 10X, arquitectura Barbell y blindaje anti-overfitting.
* **[HYPOTHESIS.md](strategy/HYPOTHESIS.md) (STRAT-001):** Formulación de la hipótesis causal del edge Short-Bias 4h.
* **[PLAN_ESCALADO_100_A_1000_USDT.md](strategy/PLAN_ESCALADO_100_A_1000_USDT.md) (STRAT-002):** Trayectoria de micro-capital 10X y gestión de tamaño por Half-Kelly.
* **[PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md](strategy/PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md) (STRAT-003):** Especificación técnica del trinquete del 60% y la Bóveda Delta-Neutral.
* **[PLAN_DESMITIFICACION_RIESGOS.md](strategy/PLAN_DESMITIFICACION_RIESGOS.md) (STRAT-004):** Protocolo de ablación, CPCV y certificación fuera de muestra.
* **[SCRUM_PLAN.md](strategy/SCRUM_PLAN.md) (STRAT-ROADMAP-001):** Roadmap maestro y registro detallado de los Sprints 1 a 20.
* **[SPRINT_PLAN_REMEDIATION_AND_HARDENING.md](sprints/SPRINT_PLAN_REMEDIATION_AND_HARDENING.md):** Plan Scrum de 4 Sprints para hardening de seguridad, streaming desacoplado y gobernanza económica.

---

## 11. Centro de Control Unificado (Cockpit v7.2) y Laboratorio Cuantitativo

El Cockpit Web (`http://localhost:8088`) integra la totalidad del ecosistema algorítmico y operativo en una única interfaz multihilo y modular.

### 11.1 Arquitectura de Pestañas Operativas
1. **`🎮 Centro de Mando (Live)`:**
   * Monitoreo de la estrategia en ejecución (`MemeHunterFuturesV7_Quantum`) en Docker.
   * Conexión en tiempo real con la base de datos `tradesv3.futures.sqlite` para listar órdenes abiertas (precio de entrada, stake, apalancamiento) y trades cerrados con ganancia neta.
   * Visualización del estado del Profit Ratchet (pico de equidad, capital base) y de la Bóveda Cash & Carry (rendimiento pasivo diario).
   * Consola interactiva de auditoría autónoma en vivo.
2. **`📚 Estrategias & Backtests (Freqtrade)`:**
   * **Catálogo de 11 Estrategias Físicas (`user_data/strategies/`):** Inspector con badges de Timeframe, Stop Loss, Short-Bias, diferenciación fraccionaria FFD ($d=0.40$), dimensionamiento continuo Kelly y KillSwitch.
   * **Historial de 34 Backtests Freqtrade (`user_data/backtest_results/`):** Lector de archivos `.zip` que extrae en milisegundos número de trades, winrate, retorno en USDT, max drawdown, Sharpe, Sortino y Profit Factor, con filtrado dinámico por estrategia.
   * **Auditoría de Resiliencia Institucional:** Desglose de Choque de Fricciones (5 escenarios hasta iliquidez severa) y consistencia trimestral 2024-2026.
3. **`🧪 Laboratorio Cuantitativo (Studio Designer & Live Tester)`:**
   * Diseñador de fórmulas simbólicas con 5 plantillas pre-construidas.
   * Validador AST *Zero-Eval* en tiempo real (`/api/validate-formula`) que rechaza inyecciones de código y reporta profundidad y variables detectadas.
   * Backtester vectorial 4H ultrarrápido sobre datos reales de Binance Futures (`C:/meme_hunter_data/binance/futures/*.feather`), aplicando fees reales (maker 0.02%, taker 0.05%) y deslizamiento.
   * Generación de curva de equidad interactiva con Chart.js y despliegue a Sandbox en 1 clic con persistencia atómica.
4. **`🧠 Incubadora Autónoma & Autopsias Forenses`:**
   * Stepper interactivo del pipeline de 5 etapas (CUSUM -> Autopsia DeepSeek-R1 -> Síntesis AST -> MAP-Elites -> HRP).
   * Curva de equidad de portafolio y monitoreo de Information Coefficient (IC) con alerta de CUSUM decay.
   * Tabla de máquina de estados (`LIVE`, `SANDBOX`, `ALPHA_DECAY`, `RETIRED`) y autopsias forenses.

### 11.2 Especificación de la API REST del Cockpit (`server.py`)
| Endpoint | Verbo | Descripción | Autenticación |
| :--- | :---: | :--- | :---: |
| `/api/status` | `GET` | Estado del sistema, estrategia activa, métricas HRP y Barbell | Pública |
| `/api/strategies-catalog` | `GET` | Catálogo de las 11 estrategias Python físicas en `user_data/strategies/` | Pública |
| `/api/backtests-catalog` | `GET` | Historial de los 34 reportes de backtest extraídos de los `.zip` | Pública |
| `/api/stress-report` | `GET` | Escenarios de estrés de fricción y desglose trimestral | Pública |
| `/api/live-trades` | `GET` | Posiciones abiertas y trades cerrados desde SQLite | Pública |
| `/api/validate-formula` | `POST` | Validación sintáctica y seguridad AST *Zero-Eval* | Bearer Token |
| `/api/test-strategy` | `POST` | Backtesting vectorial rápido con fricciones de futuros | Bearer Token |
| `/api/deploy-to-sandbox` | `POST` | Despliegue transaccional SQLite WAL a la fábrica (`portfolio/alpha_factory.db`) | Bearer Token |
| `/api/trigger-loop` | `POST` | Disparo manual de ciclo autónomo de optimización (CUSUM, Autopsia, Gating, HRP) | Bearer Token |
| `/api/synthesize-alpha` | `POST` | Síntesis semántica de factores vía OpenRouter | Bearer Token |

### 11.3 Certificación de Calidad Oficial
La suite completa cuenta con **151+ tests pasando al 100% (0 fallos)**:
```powershell
python -m pytest tests -v
```
Certificando la no-regresión de todos los módulos matemáticos, de microestructura, concurrencia SQLite WAL, compuertas OOS y ensamble bidireccional.

---

## 12. Arquitectura de Estabilización y Blindaje Operativo

Para mitigar el riesgo de hiper-crecimiento y sobre-ingeniería tras iterar de la versión v1.0 a la v7.2, el sistema adopta el **Modelo de 3 Capas Herméticas**:

```mermaid
flowchart LR
    subgraph Capa 1: Core de Ejecución [Capa 1: Core de Ejecución (Misión Crítica)]
        FT[Freqtrade Futures Engine]
        DB[(tradesv3.futures.sqlite)]
        KS[Killswitch -25% & Funding Bleed Guard]
        V7[MemeHunterFuturesV7_Quantum]
    end

    subgraph Capa 2: Observabilidad [Capa 2: Cockpit de Observabilidad]
        CP[Cockpit Web Server :8088]
        RD[Read-Only SQLite Concurrency]
        UI[Glassmorphism Dashboard]
    end

    subgraph Capa 3: Laboratorio I+D [Capa 3: Strategy Studio & Mining Lab]
        GM[Genetic Miner NSGA-II]
        LLM[OpenRouter / DeepSeek-R1]
        INC[Incubadora Sandbox State]
        ST[Vectorial Strategy Tester]
    end

    Capa 1 -.->|Solo Lectura Telemetría| Capa 2
    Capa 3 -.->|Promoción Manual Auditada| Capa 1
```

### 12.1 Las 3 Capas Herméticas de Protección
1. **Capa 1: Core de Ejecución (Zero External Dependency):**
   * El bot de trading (`docker-compose.futures.yml`) ejecuta exclusivamente la estrategia canónica `MemeHunterFuturesV7_Quantum` con margin aislado (`isolated`) y orden pasiva Maker.
   * **Inviolabilidad:** No realiza llamadas HTTP externas a LLMs ni depende de procesos de minería en vivo. Si el dashboard o servicios satélite fallan, el bot continúa operando y liquidando posiciones por trailing stop o airbag técnico sin interrupciones.
2. **Capa 2: Observabilidad Pasiva y Concurrencia SQLite:**
   * El Cockpit (`:8088`) consulta la base de datos `tradesv3.futures.sqlite` mediante URI de solo lectura estricta (`mode=ro`) con timeout defensivo. Esto impide bloqueos o excepciones de `database is locked` contra el motor en vivo.
   * Monitoreo instantáneo con el centinela `python scripts/meme_cli.py health` en ~1.5 segundos.
3. **Capa 3: Laboratorio de I+D & Sandbox (Confinamiento de Riesgo):**
   * La minería genética (NSGA-II), las autopsias cognitivas vía OpenRouter (DeepSeek-R1) y las nuevas fórmulas AST residen en la incubadora (`portfolio/incubator_state.json`) en estado `SANDBOX`.
   * **Regla de Oro:** Ninguna estrategia generada automáticamente puede ejecutar órdenes reales en vivo sin una auditoría de significancia estadística ($p < 0.01$), validación fuera de muestra (CPCV/PBO) y promoción manual explícita.

---

## 13. Fábrica de Alphas SQLite WAL, Gating OOS y Enlace Bidireccional (Sprints 25 a 29)

A partir de la versión **v7.3**, Meme Hunter consolida su arquitectura de producción resolviendo la persistencia transaccional, eliminando los datos sintéticos del dashboard y enlazando las decisiones de la incubadora con Freqtrade en tiempo real.

```mermaid
graph TD
    subgraph "Ingesta y Sincronización"
        SYNC["data_engine/auto_data_sync.py<br/>(9 pares Binance Futures REST API)"] --> FEAT["C:/meme_hunter_data/binance/futures/<br/>(*.feather reales)"]
        FEAT --> FEED["data_engine/real_market_feed.py<br/>(Evaluación Vectorial con Fricción)"]
    end

    subgraph "Gobernanza y Fábrica de Alphas"
        FEED --> ORCH["portfolio/autonomous_orchestrator.py"]
        ORCH --> GATE["portfolio/oos_gating.py<br/>(CPCV, PBO < 15%, DSR >= 95%, Corr < 0.40)"]
        ORCH --> HRP["portfolio/strategy_incubator.py<br/>(HRP + 15% Turnover Deadband)"]
        ORCH <--> DB["portfolio/alpha_factory.db<br/>(SQLite WAL ACID - 0 Locks)"]
    end

    subgraph "Producción Freqtrade"
        ORCH --> HOOK["scripts/compile_ensemble_strategy.py<br/>(Dual-Engine: Long & Short)"]
        HOOK --> STRAT["user_data/strategies/MemeHunter_MinedEnsemble.py"]
        ORCH --> REST["client/freqtrade_client.py<br/>(POST /api/v1/reload_config)"]
        ORCH --> TELEM["client/telemetry_notifier.py<br/>(cycle_history & Webhooks)"]
    end
```

### 13.1 Persistencia Transaccional ACID en SQLite WAL (Sprint 25: PB-87 a PB-89)
* **Base de Datos Canónica:** [`portfolio/alpha_factory.db`](file:///c:/meme_hunter/portfolio/alpha_factory.db).
* **Modo WAL y Pragma Defensivos:** Conexiones gestionadas por [`portfolio/db_pool.py`](file:///c:/meme_hunter/portfolio/db_pool.py) con `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, y `busy_timeout = 30000ms`.
* **Cero Bloqueos:** Certificado bajo pruebas de estrés de 15 hilos concurrentes simultáneos ([`tests/test_db_concurrency.py`](file:///c:/meme_hunter/tests/test_db_concurrency.py)).
* **Tablas Relacionales:**
  - `strategies`: Metadatos, estado (`SANDBOX`, `LIVE`, `ALPHA_DECAY`, `RETIRED`), Sharpe OOS y decay Z-Score.
  - `portfolio_allocations`: Historial inmutable de pesos de capital asignados por HRP.
  - `alpha_autopsies`: Dictámenes forenses cognitivos de autopsias de factores caídos.
  - `diversity_archive`: Celdas del archivo MAP-Elites para preservación de diversidad.
  - `cycle_history`: Registro cronológico completo de cada ejecución del bucle.

### 13.2 Eliminación de Datos Sintéticos y Sincronización Automática (Sprint 26 & 29: PB-90 & PB-100)
* **Erradicación de Mocks:** El servidor del Cockpit ([`dashboard/server.py`](file:///c:/meme_hunter/dashboard/server.py)) no utiliza datos aleatorios (`np.random.normal`).
* **Sincronizador Continuo ([`data_engine/auto_data_sync.py`](file:///c:/meme_hunter/data_engine/auto_data_sync.py)):** Descarga incrementalmente velas OHLCV desde la API pública de Binance Futures para los 9 pares activos (`DOGE`, `PEPE`, `WIF`, `MEW`, `POPCAT`, `NEIRO`, `BONK`, `FLOKI`, `SHIB`), manteniendo los archivos `.feather` locales actualizados al día.
* **Smart Cache de Autopsias (PB-92):** Evita llamadas redundantes a OpenRouter reutilizando dictámenes idénticos en milisegundos.

### 13.3 Protocolo Estricto de Aceptación OOS y Multicolinealidad (Sprint 27: PB-93 & PB-94)
* **Validador de Gobernanza ([`portfolio/oos_gating.py`](file:///c:/meme_hunter/portfolio/oos_gating.py)):**
  - Ningún factor es promovido a `LIVE` basándose únicamente en métricas de ventana corta.
  - **Filtro Combinatorio (CPCV):** Particiones combinatorias con purga y embargo temporal (`validation/cpcv_engine.py`).
  - **Límites Estadísticos:** Probabilidad de Sobreajuste en el Backtest **$PBO < 15\%$** y Deflated Sharpe Ratio **$DSR \ge 95\%$**.
  - **Filtro de Multicolinealidad Cruzada:** Máxima correlación contra cualquier estrategia activa en producción **$|\rho| < 0.40$**.

### 13.4 Control de Fricción por Banda Muerta y Spread (Sprint 27 & 29: PB-95 & PB-101)
* **Banda Muerta de Turnover (15% Deadband):** Si la rotación de pesos sugerida por HRP es $< 15\%$, se activa la regla de no-intervención, preservando los pesos vigentes y ahorrando el 100% de comisiones por rotación marginal.
* **Deducción Realista de Fricción:** Cálculo de Sharpe en la incubadora descontando comisión taker de Binance Futures ($0.05\%$) y penalización de spread en cada cambio de señal:
  $$R_{\text{neto}, t} = (\text{Señal}_t \times R_{t+1}) - |\Delta \text{Señal}_t| \times (0.0005 + \frac{1}{2}\text{Spread}_t)$$

### 13.5 Ensamble Dual-Engine Bidireccional Long/Short (Sprint 29: PB-99 & PB-102)
* **Estrategia Compilada:** [`user_data/strategies/MemeHunter_MinedEnsemble.py`](file:///c:/meme_hunter/user_data/strategies/MemeHunter_MinedEnsemble.py).
* **Entradas Bidireccionales:**
  - **LONG:** `composite_alpha_score > +0.05` $\land$ `close > ema_200` $\land$ `rsi < 68` $\land$ confirmación rápida (`fast_momentum > 0` o `close >= ema_50`).
  - **SHORT:** `composite_alpha_score < -0.05` $\land$ `close < ema_200` $\land$ `rsi > 32` $\land$ confirmación rápida.
* **Salidas Asimétricas tipo Airbag:** Salida ágil de Longs si el score colapsa a $<-0.10$ o RSI $>75$; salida de Shorts si el score rebota a $>+0.10$ o RSI $<25$.

### 13.6 Cliente REST API de Freqtrade y Telemetría (Sprint 28: PB-96, PB-97 & PB-98)
* **Auto-Compilador:** Tras cada promoción o retiro, el orquestador regenera automáticamente la estrategia ejecutable.
* **Hot-Reload REST Client ([`client/freqtrade_client.py`](file:///c:/meme_hunter/client/freqtrade_client.py)):** Notifica al bot en vivo (`POST /api/v1/reload_config` en puerto 8081) con soporte para fallbacks offline si Docker está pausado.
* **Telemetría y Notificaciones ([`client/telemetry_notifier.py`](file:///c:/meme_hunter/client/telemetry_notifier.py)):** Despacho estructurado a webhooks de Discord/Telegram y registro inmutable en `portfolio/alpha_factory.db`.

---

## 14. Arquitectura Multi-Agente, Orquestador DAG y Cockpit Human-in-the-Loop (Sprints 30 a 32)

Para superar definitivamente la opacidad de los algoritmos monolíticos clásicos (la "caja negra"), el sistema Meme Hunter v7.4 adopta la **arquitectura multi-agente modular y visual orientada a Grafos Acíclicos Dirigidos (DAG)** bajo la metodología **Human-in-the-Loop (HITL)**.

```mermaid
graph TD
    subgraph Capa_1_Ingesta [1. Ingesta de Datos Multimodal]
        IN_PV["Precio y Volumen<br/>(WebSockets L2/L3)"]
        IN_NEWS["Noticias y Redes<br/>(APIs NLP Scraping)"]
        IN_MACRO["Calendario Macro<br/>(Eventos FED / IPC / Funding)"]
    end

    subgraph Capa_2_Agentes [2. Procesamiento & Agentes Especializados]
        AG_TECH["Análisis Técnico & Microestructura<br/>(AST Factors, FFD d=0.40, OFI Proxy)"]
        AG_SENT["Agente Sentimiento<br/>(FinLLM + Fallback Offline 0ms)"]
        AG_REG["Detector de Régimen<br/>(Gaussian HMM / CUSUM Volatilidad)"]
    end

    subgraph Capa_3_Orquestacion [3. Núcleo & Orquestador DAG]
        ORQ["Orquestador DAG (portfolio/dag_orchestrator.py)<br/>• Algoritmo: Bayesian Fusion<br/>• Consenso Mínimo: 0.68 Score<br/>• Ciclo de Inferencia: < 20 ms"]
    end

    subgraph Capa_4_Riesgo_Ejecucion [4. Gobernanza de Riesgo & Ejecución]
        RISK["Gestor de Riesgos (portfolio/agents/risk_manager_agent.py)<br/>• VaR 99% Paramétrico / Cornish-Fisher<br/>• Kill-Switch Total (-25%)<br/>• Multicolinealidad Corr < 0.40"]
        GUARD["Graceful Degradation Guard<br/>(portfolio/graceful_degradation.py)<br/>• Mitigación Spread Tóxico > 0.35%"]
        EXEC["API de Ejecución Freqtrade DMA<br/>(Maker al Bid / Salidas Market Airbag)"]
    end

    IN_PV --> AG_TECH
    IN_NEWS --> AG_SENT
    IN_MACRO --> AG_REG
    AG_TECH -->|Vector Micro| ORQ
    AG_SENT -->|Score Cualitativo| ORQ
    AG_REG -->|Probabilidades Régimen| ORQ
    ORQ -->|Vector Alpha| RISK
    GUARD -->|Atenuador Sizing| RISK
    RISK -->|Orden Aprobada| EXEC
```

### 14.1 Orquestador DAG y Fusión Bayesiana (`portfolio/dag_orchestrator.py` - Sprint 30: PB-103)
* **Grafo Acíclico Dirigido (DAG):** Reemplaza el ensamble estático lineal por un enrutador central donde cada agente opera como un nodo desacoplado, transparente y auditable.
* **Fusión Bayesiana Ponderada:** Las probabilidades y direcciones emitidas por los agentes se sintetizan ponderando por la afinidad condicional del régimen de mercado y la convicción estadística:
  $$P(\text{Señal} \mid \mathbf{D}) \propto P(\text{Prior Régimen}) \prod_{i=1}^{K} P(\mathbf{S}_i \mid \text{Estado}_i)^{\omega_i}$$
* **Telemetría de Ciclo de Inferencia:** Medición estricta de tiempo de ejecución con `time.perf_counter_ns()`, auditando que el ciclo total del grafo se complete en $< 20\text{ ms}$ (promedio real de producción: $\sim 2.8\text{ ms}$).
* **Filtro de Consenso Mínimo ($0.68\text{ Score}$):** Si los agentes discrepan en dirección o la certeza agregada es menor a $0.68$, la propuesta se veta con dictamen formal `INSUFFICIENT_CONSENSUS`, protegiendo la cuenta de señales dudosas.

### 14.2 Detección Dinámica de Régimen y Agentes Cuantitativos (PB-104 & PB-105)
* **`RegimeHMMAgent` ([`portfolio/agents/regime_agent.py`](file:///c:/meme_hunter/portfolio/agents/regime_agent.py)):**
  - Evalúa la dispersión respecto a la EMA 200, volatilidad realizada anualizada y ATR normalizado.
  - Emite un vector continuo de probabilidades $[p_{\text{bull}}, p_{\text{bear}}, p_{\text{range}}]$ que modula la influencia de los demás agentes según el entorno.
* **`TechnicalMicroAgent` ([`portfolio/agents/technical_agent.py`](file:///c:/meme_hunter/portfolio/agents/technical_agent.py)):**
  - Integra factores de memoria fraccionaria FFD ($d=0.40$), RSI dinámico adaptativo y proxy de Order Flow Imbalance (OFI) intradiario en un formato canónico `AgentProposal`.

### 14.3 Agente de Sentimiento y Noticias en Tiempo Real (Sprint 31: PB-107)
* **`SentimentAgent` ([`portfolio/agents/sentiment_agent.py`](file:///c:/meme_hunter/portfolio/agents/sentiment_agent.py)):**
  - Conector de cognición cualitativa que ingesta noticias, eventos macroeconómicos y flujo social de memecoins.
  - Normaliza el tono semántico en un score cuantitativo continuo $[-1.0, +1.0]$ con convicción estadística.
  - **Fallback Offline Instantáneo ($0\text{ ms}$):** Incorpora caché léxica y semántica local de alta velocidad. Si las APIs remotas de LLM (OpenRouter) experimentan latencia o corte de red, conmuta a modo local sin degradar el ciclo de inferencia del DAG.

### 14.4 Gobernanza de Riesgo y Degradación Elegante ante Cisnes Negros (PB-108 & PB-109)
* **`RiskManagerAgent` ([`portfolio/agents/risk_manager_agent.py`](file:///c:/meme_hunter/portfolio/agents/risk_manager_agent.py)):**
  - Valida el `VectorAlpha` contra el Value at Risk al 99% paramétrico, el Kill-Switch de Equidad total ($-25\%$) y el límite de correlación cruzada ($< 0.40$).
  - Emite dictámenes formales: `APPROVED`, `SCALED_DOWN` o `REJECTED`.
* **`GracefulDegradationGuard` ([`portfolio/graceful_degradation.py`](file:///c:/meme_hunter/portfolio/graceful_degradation.py)):**
  - Monitorea la microestructura Level 2 de Binance Futures:
    - *Spread Normal ($< 0.15\%$):* Modo institucional normal (Sizing 1.0x).
    - *Spread Moderado ($0.15\% - 0.35\%$):* Modo degradado, sizing al $50\%$ y ejecución forzada Maker al Bid.
    - *Spread Tóxico ($> 0.35\%$):* Pausa inmediata de nuevas aperturas para evitar devorar el edge en comisiones.
    - *Cisne Negro / Flash Crash ($> 0.70\%$ o latencia $> 1500\text{ ms}$):* Modo supervivencia con paradas protectoras sin colapso del sistema.

### 14.5 Cockpit Visual DAG e Interfaz Human-in-the-Loop (HITL) (Sprint 32: PB-111 a PB-114)
* **Pestaña de Orquestación Multi-Agente ([`dashboard/index.html`](file:///c:/meme_hunter/dashboard/index.html)):**
  - Vista topológica interactiva con 8 nodos organizados en tema oscuro neón con pulsos de inferencia y glow dinámico.
* **Panel Inspector HITL:**
  - Al hacer clic en cualquier nodo, muestra el algoritmo activo, métricas en tiempo real y tiempo de ciclo de inferencia.
  - **Controles del Operador:** Switch para pausar o activar nodos en caliente, slider de consenso mínimo en tiempo real y botón para disparar ciclos de inferencia manuales.
* **Endpoints REST de Telemetría ([`dashboard/server.py`](file:///c:/meme_hunter/dashboard/server.py)):**
  - `/api/dag/topology`, `/api/dag/status`, `/api/dag/toggle-node`, `/api/dag/set-threshold`, `/api/dag/trigger-cycle`.
* **Certificación Oficial:** **24/24 pruebas automatizadas pasando al 100%** en `tests/test_sprint30*`, `tests/test_sprint31*` y `tests/test_sprint32*`.



