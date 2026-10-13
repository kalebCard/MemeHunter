---
id: DAS-AUTONOMOUS-001
title: Documento de Arquitectura de Software - Motor Autónomo Auto-Evolutivo & Cockpit IA
category: architecture
version: 7.4
status: ACTIVE
last_updated: 2026-10-12
author: Quantitative Core & Systems Architecture Team
---

# 🌌 DAS: Motor Cuantitativo Auto-Evolutivo, DAG Multi-Agente & Cockpit IA (v7.4)

## 1. Resumen Ejecutivo y Visión Arquitectónica

El sistema **Meme Hunter v7.4** ha evolucionado de un framework de backtesting y ejecución por lotes a un **organismo algorítmico multi-agente de bucle cerrado (Closed-Loop Autonomous Multi-Agent Engine)** con persistencia transaccional SQLite WAL, enrutamiento en Grafo Acíclico Dirigido (DAG) y enlace de producción bidireccional. El sistema es capaz de:
1. **Auto-observar** su propio rendimiento y microestructura en tiempo real sobre datos en vivo sincronizados continuamente desde Binance Futures (`auto_data_sync.py`).
2. **Detectar fatiga de señal (*Alpha Decay*)** y rupturas de régimen mediante algoritmos CUSUM y pruebas de Kolmogorov-Smirnov.
3. **Aislar y realizar autopsias cognitivas** de factores degradados mediante modelos de razonamiento profundo en OpenRouter (DeepSeek-R1 / Claude 3.5 Sonnet) con caché inteligente de autopsias.
4. **Sintetizar hipótesis semánticas de microestructura** validadas con un compilador AST seguro (*Zero Eval*).
5. **Gestionar concurrencia sin bloqueos** a través de una base de datos relacional transaccional SQLite WAL (`alpha_factory.db`) con pool de conexiones multihilo (`db_pool.py`).
6. **Filtrar alfas mediante compuertas rigurosas fuera de muestra (OOS Hard-Gating)** exigiendo $PBO < 15\%$, $DSR \ge 95\%$, correlación cruzada $< 0.40$ y zona muerta de turnover de 15%.
7. **Compilar automáticamente ensambles bidireccionales (Long & Short)** para Freqtrade (`scripts/compile_ensemble_strategy.py`) con confirmación de momentum rápido.
8. **Orquestar señales en Grafo Acíclico Dirigido (DAG)** con Fusión Bayesiana condicional al régimen, latencia $< 20\text{ ms}$ y filtro de consenso ($0.68$).
9. **Supervisar el sentimiento no estructurado** con LLMs locales/API (`SentimentAgent`) con fallback instantáneo de 0ms.
10. **Blindar el capital contra cisnes negros** mediante degradación elegante ante spreads tóxicos y cortes de liquidez (`GracefulDegradationGuard`).
11. **Ofrecer observabilidad y control Human-in-the-Loop** en tiempo real a través del Cockpit Web (`tab-multi-agent-dag`).

---

## 2. Diagrama del Bucle Cerrado Cognitivo (Closed-Loop Architecture v7.3)

```mermaid
graph TD
    subgraph Ingesta_RealTime [1. Ingesta y Sincronización Continua]
        BINANCE["Binance Futures API"] --> ASYNC["auto_data_sync.py<br/>(9 pares perpetuos Feather 4H)"]
        BINANCE --> LFEED["LiveMarketFeed<br/>(ccxt polling/stream)"]
        ASYNC --> RFEED["real_market_feed.py<br/>(Penalización Taker 0.05% + Spread)"]
        LFEED --> DBARS["InformationBarsGenerator<br/>(Dollar Bars Notional $500k)"]
    end

    subgraph Observabilidad_Salud [2. Motor de Diagnóstico & Salud]
        RFEED --> MON["AlphaHealthMonitor"]
        DBARS --> MON
        MON -->|Spearman Correlation| IC["Rolling IC & IC_IR"]
        MON -->|Page-Hinkley| CUSUM["CUSUM Structural Break"]
        MON -->|Two-Sample KS| DRIFT["Data Drift KS-Test"]
    end

    subgraph Cognicion_IA [3. Cerebro Cognitivo OpenRouter]
        MON -->|Alerta WARNING_DECAY| AUTOPSY["AlphaAutopsyAgent<br/>(DeepSeek-R1 + Smart Cache)"]
        AUTOPSY -->|Directivas de Exclusión| SYNTH["LLMAlphaSynthesizer<br/>(DeepSeek-V3 / Qwen 2.5 Coder)"]
        SYNTH --> PARSER["FormulaASTParser<br/>(Compilador Seguro Zero-Eval)"]
    end

    subgraph Fabrica_Concurrente [4. Fábrica de Alphas SQLite WAL]
        PARSER --> QD["QualityDiversityArchive<br/>(MAP-Elites 6 Nichos)"]
        DAEMON["AlphaMinerDaemon 24/7<br/>(NSGA-II)"] --> QD
        QD --> DBPOOL["SQLite WAL Pool (alpha_factory.db)<br/>(db_pool.py + db_schema.py)"]
    end

    subgraph Validacion_Gating [5. Compuertas Fuera de Muestra (OOS Gating)]
        DBPOOL --> GATING["OOSGatingEngine (oos_gating.py)<br/>(PBO < 15%, DSR >= 95%, Corr < 0.40)"]
        GATING --> INCUB["StrategyLifecycleIncubator<br/>(SANDBOX -> LIVE -> ALPHA_DECAY)"]
        INCUB --> HRP["HierarchicalRiskParityAllocator<br/>(Turnover Deadband 15%)"]
    end

    subgraph Ejecucion_Produccion [6. Enlace de Ejecución y Hot-Reload]
        HRP --> COMPILER["compile_ensemble_strategy.py<br/>(Ensamble Dual-Engine Long & Short)"]
        COMPILER --> STRAT["MemeHunter_MinedEnsemble.py<br/>(user_data/strategies/)"]
        STRAT --> FTCLIENT["Freqtrade REST Client<br/>(Hot-Reload Puerto 8081)"]
    end

    subgraph UI_Cockpit [7. Cockpit Visual de Monitoreo]
        DBPOOL --> DASH["Dashboard Server (Puerto 8088)<br/>(ThreadingHTTPServer, Async Lock, Chart.js)"]
    end
```

---

## 3. Módulos y Componentes del Sistema

### 3.1. `data_engine/live_market_feed.py` & `data_engine/auto_data_sync.py`
* **`auto_data_sync.py`:** Sincronizador continuo en vivo que descarga de Binance Futures las velas de 4h para 9 memecoins (`DOGE`, `PEPE`, `WIF`, `MEW`, `POPCAT`, `NEIRO`, `BONK`, `FLOKI`, `SHIB`) almacenándolas en `C:/meme_hunter_data/binance/futures/*.feather`.
* **`live_market_feed.py`:** Ingesta continua de velas 1m y compresión dinámica a Dollar Bars con lock reentrante (`RLock`) desacoplado.
* **`real_market_feed.py`:** Cargador de datos reales con deducción de fricción microestructural (0.05% comisiones taker + penalización de medio spread).

### 3.2. `portfolio/alpha_health_monitor.py`
* **CUSUMDetector:** Algoritmo acumulativo de Page-Hinkley ($h = 4.0\sigma, k = 0.5\sigma$) para detección temprana de saltos de volatilidad o quiebres estructurales.
* **Rolling IC:** Correlación por rangos de Spearman en ventanas móviles ($N = 15 - 60$ barras), con evaluación de $p\text{-valor}$ e Information Ratio del IC ($IC\_IR$).
* **KS-Test:** Detección de *data drift* entre la distribución histórica de referencia y la muestra reciente.
* **Estados de Salud:** `HEALTHY`, `WARNING_DECAY`, `CRITICAL_BREAK`, `REGIME_SHIFT`.

### 3.3. `mining/llm_client.py` & `mining/formula_parser.py`
* **`OpenRouterClient`:** Conector multimodelo con soporte para DeepSeek-V3, DeepSeek-R1 y Claude 3.5 Sonnet. Incluye control de presupuesto por sesión (`max_daily_tokens`) y modo degradado offline automático si no hay clave de API o conexión.
* **`FormulaASTParser`:** Compilador sintáctico formal basado en el módulo estándar `ast`. Traduce expresiones de texto a nodos ejecutables de `AlphaGrammar` (`FeatureNode`, `BinaryOpNode`, `TimeSeriesOpNode`, `UnaryOpNode`, `ConstantNode`) sin utilizar `eval()`, compatible con Python 3.14.

### 3.4. `portfolio/alpha_autopsy.py` & `mining/llm_alpha_generator.py`
* **`AlphaAutopsyAgent`:** Analizador causal que extrae la causa raíz de la degradación y emite recomendaciones de búsqueda con marcas de tiempo dinámicas en UTC y caché inteligente basada en hash de métricas para evitar llamadas redundantes a la API.
* **`LLMAlphaSynthesizer`:** Diseña fórmulas matemáticas basadas en conceptos de microestructura económica (order flow imbalance, ratio de iliquidez de Amihud, compresión de spread en Dollar Bars).

### 3.5. `portfolio/db_pool.py` & `portfolio/db_schema.py` (Fábrica SQLite WAL)
* **`DatabasePool`:** Pool de conexiones transaccional thread-safe con modo WAL (`PRAGMA journal_mode=WAL`), `synchronous=NORMAL` y timeout de 30s.
* **Esquema:** Tablas relacionales indexadas para `strategies`, `performance_snapshots`, `autopsies`, `rebalance_history` y `system_audit_log`.

### 3.6. `portfolio/oos_gating.py` & `portfolio/strategy_incubator.py`
* **`OOSGatingEngine`:** Compuertas cuantitativas obligatorias antes de promover estrategias a `LIVE`:
  * Probabilidad de Sobreajuste ($PBO < 15\%$).
  * Deflated Sharpe Ratio ($DSR \ge 95\%$).
  * Correlación cruzada máxima con alfas vivos ($< 0.40$).
* **`StrategyLifecycleIncubator`:** Máquina de estados formal (`SANDBOX` $\rightarrow$ `LIVE` $\rightarrow$ `ALPHA_DECAY` $\rightarrow$ `RETIRED`) con zona muerta de rotación (15% turnover deadband).
* **`HierarchicalRiskParityAllocator`:** Distribución de capital HRP inmune a singularidades de covarianza.

### 3.7. `scripts/compile_ensemble_strategy.py` & `client/freqtrade_client.py`
* **Compilador Dual-Engine Bidireccional:** Traduce el vector de alfas y pesos HRP a una estrategia de producción nativa de Freqtrade (`MemeHunter_MinedEnsemble.py`) con motores simétricos para `enter_long` y `enter_short`, filtrados por confirmación rápida (EMA 50 / 4h y RSI).
* **Cliente REST:** Comunicación con el demonio Freqtrade en el puerto 8081 para recarga en caliente (*hot reload*) sin interrupción operativa.

### 3.8. `portfolio/dag_orchestrator.py` & `portfolio/agents/` (Núcleo Multi-Agente & Fusión Bayesiana)
* **`DAGSignalOrchestrator`:** Enrutador central en DAG que sintetiza las señales de `RegimeHMMAgent`, `TechnicalMicroAgent` y `SentimentAgent` mediante **Fusión Bayesiana Ponderada**.
* **Latencia y Consenso:** Ciclos de inferencia $< 20\text{ ms}$ (promedio $\sim 2.8\text{ ms}$) y umbral de consenso configurable ($0.68\text{ Score}$).
* **`RiskManagerAgent`:** Evaluación dinámica de VaR al 99% paramétrico, Kill-Switch de equidad ($-25\%$) y veto por multicolinealidad ($< 0.40$).

### 3.9. `portfolio/graceful_degradation.py` (Degradación Elegante & Cisnes Negros)
* **`GracefulDegradationGuard`:** Monitorea spreads Level 2 y latencias en Binance Futures.
* **Escalado Progresivo:** Atenúa posiciones al $50\%$ ante spreads moderados ($0.15\% - 0.35\%$), restringe órdenes a Maker al Bid, y pausa nuevas entradas ante spreads tóxicos ($> 0.35\%$) preservando la telemetría viva.

### 3.10. `dashboard/` (Cockpit Visual Seguro & Interfaz DAG HITL)
* **Arquitectura:** HTML5 semántico + Vanilla CSS Glassmorphism + Vanilla JS reactivo + Chart.js + Visualizador DAG vectorial (`dag_flow.js`).
* **Pestaña DAG HITL (`tab-multi-agent-dag`):** Grafo interactivo en tema oscuro neón con 8 nodos, panel inspector en vivo, switches de activación en caliente y slider de consenso mínimo.
* **Backend:** Servidor REST multihilo (`ThreadingHTTPServer` en `dashboard/server.py`) con endpoints `/api/dag/*` thread-safe.
* **Puerto y Seguridad:** Escucha en `http://localhost:8088`, autorización con Bearer Token y CORS estricto.

---

## 4. 💰 Modelo Económico, Metas Cuantitativas y Límites de Parada

El motor autónomo implementa salvaguardas económicas y metas de convergencia para evitar consumo innecesario de recursos:

### 4.1. Estimación de Coste por Ciclo
| Operación | Modelo | Tokens Estimados | Coste por Evento |
| :--- | :--- | :---: | :---: |
| **Autopsia Forense** (Diagnóstico CUSUM / Drift) | DeepSeek-R1 | ~1,500 tokens | **$0.00095 USD** |
| **Síntesis de Alfas** (3 fórmulas validadas con AST) | DeepSeek-V3 | ~1,200 tokens | **$0.00030 USD** |
| **Minería Genética NSGA-II + Rebalanceo HRP** | Cómputo local | 0 tokens | **$0.00000 USD** |
| **COSTE TOTAL POR CICLO DE MEJORA** | — | **~2,700 tokens** | **~$0.00125 USD** |

### 4.2. Meta Cuantitativa de Convergencia (*Target Goal*)
* **Meta Programada:** **Sharpe Ponderado del Portafolio $\ge 2.50$** (`AUTONOMOUS_TARGET_SHARPE=2.50`) con al menos 2 estrategias activas en `LIVE`.
* **Comportamiento:** Al alcanzarse, el sistema marca `goal_reached = True`, consolida el vector de pesos HRP y detiene la generación de reemplazos para evitar sobreajuste.

### 4.3. Barreras de Contención y Parada de Emergencia (*Circuit Breakers*)
1. **Tope Presupuestario:** `AUTONOMOUS_MAX_BUDGET_USD=1.00` (Bloquea llamadas a OpenRouter si el gasto acumulado alcanza $1.00 USD).
2. **Tope de Iteraciones:** `AUTONOMOUS_MAX_CYCLES=10` (Máximo 10 ciclos consecutivos antes de requerir confirmación humana).
3. **Tope Diario de Tokens:** `OPENROUTER_MAX_DAILY_TOKENS=150000` (~150k tokens diarios).

---

## 5. Guía de Ejecución Rápida

### A. Sincronizar Datos Reales de Binance Futures
```bash
python data_engine/auto_data_sync.py
```

### B. Iniciar el Dashboard Visual Seguro (Puerto 8088)
```bash
python scripts/start_dashboard.py
```
Abrir en el navegador: [http://localhost:8088](http://localhost:8088).

### C. Compilar la Estrategia de Ensamble Bidireccional
```bash
python scripts/compile_ensemble_strategy.py
```

### D. Iniciar el Bucle Autónomo en Vivo con Binance
```bash
python scripts/run_live_alpha_loop.py
```

### E. Ejecutar la Suite Completa de Pruebas Automatizadas
```bash
python -m pytest tests -v
```
Resultado Oficial: **175+ tests unitarios e integrales pasando al 100% (24 nuevos tests de Sprints 30 a 32 certificados con 0 errores)**.

