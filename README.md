# 🏹 Meme Hunter - Sistema Cuantitativo, Auto-Evolutivo & Cockpit Unificado (v7.6)

Plataforma cuantitativa institucional que combina **arquitectura Multi-Agente en Grafo Acíclico Dirigido (DAG)** con **fusión bayesiana y telemetría < 20ms**, **arquitectura blindada de 4 capas (Cortafuegos Pydantic v2, Desacoplamiento Asíncrono, Ejecución Determinista y Kill Switch Absoluto)**, **minería genética de factores (NSGA-II)**, **fábrica de alphas transaccional en SQLite WAL**, **compuertas rigurosas fuera de muestra (OOS Gating: PBO < 15%, DSR >= 95%)**, **ensamble dinámico bidireccional Long/Short para Freqtrade**, **percepción semántica cualitativa vía OpenRouter (FinLLM con fallback offline 0ms)**, **protocolo de degradación elegante ante cisnes negros**, **sincronización continua de datos de Binance Futures**, y un **Centro de Control Unificado (Cockpit v7.4 con Visor Visual DAG y controles Human-in-the-Loop)**.

---

## 🏛️ Centro de Documentación (`docs/`)

La documentación del proyecto se encuentra estructurada en el directorio [`docs/`](docs/README.md):

* **[Manual Estándar de Ingeniería y Desarrollo (v8.0):](docs/MANUAL_ESTANDAR_DEL_PROYECTO.md)** Norma técnica canónica obligatoria para desarrollo, arquitectura modular, SQLite WAL, estándares de código y testing.
* **[Manual Maestro Unificado del Sistema (v7.4):](docs/MANUAL_UNIFICADO_DEL_SISTEMA.md)** Referencia canónica integral técnica, cuantitativa, estratégica y operativa.
* **[Índice General de Documentación:](docs/README.md)** Guía integral y rutas de lectura según perfil.
* **[Libro Maestro de Historia & Genealogía de Sprints:](docs/history/INDEX_HISTORICO.md)** Cronología canónica de las 7 eras del proyecto y trazabilidad de los 43 Sprints.
* **[Catálogo Maestro de Ejecución de Sprints:](docs/history/sprints/README.md)** Índice y especificaciones de los 13 ciclos de desarrollo (Sprints 1 al 43).
* **[Product Backlog Maestro Scrum (v8.0):](docs/history/scrum/SCRUM_PLAN.md)** Backlog unificado con 12 Grandes Épicas e Historias PB-01 a PB-143.
* **Sprints 40-43 (Remediación Crítica, Concurrencia y Arquitectura v8.0):** [docs/history/sprints/11_SPRINTS_040_043_REMEDIATION_CONCURRENCY_AND_ARCHITECTURE_V8.md](docs/history/sprints/11_SPRINTS_040_043_REMEDIATION_CONCURRENCY_AND_ARCHITECTURE_V8.md)
* **Sprints 36-39 (Blindaje 4 Capas, Cortafuegos Pydantic v2 y Kill Switch):** [docs/history/sprints/10_SPRINTS_036_039_ASYNC_DETERMINISTIC_FIREWALL_KILLSWITCH.md](docs/history/sprints/10_SPRINTS_036_039_ASYNC_DETERMINISTIC_FIREWALL_KILLSWITCH.md)
* **Sprints 33-35 (Aceleración Polars, VectorBT, Riskfolio HERC y OpenBB):** [docs/history/sprints/09_SPRINTS_033_035_PERFORMANCE_RISK_AND_OPENBB.md](docs/history/sprints/09_SPRINTS_033_035_PERFORMANCE_RISK_AND_OPENBB.md)
* **Sprints 30-32 (Arquitectura Multi-Agente, Orquestador DAG y Cockpit HITL):** [docs/history/sprints/06_SPRINT_030_MULTI_AGENT_DAG_ORCHESTRATOR.md](docs/history/sprints/06_SPRINT_030_MULTI_AGENT_DAG_ORCHESTRATOR.md)
* **Sprints 25-28 (Hardening del Bucle Autónomo, SQLite WAL & OOS Gating):** [docs/history/sprints/04_SPRINTS_025_028_AUTONOMOUS_LOOP_HARDENING.md](docs/history/sprints/04_SPRINTS_025_028_AUTONOMOUS_LOOP_HARDENING.md)
* **Hipótesis Teórica del Edge Asimétrico:** [docs/research/strategy/HYPOTHESIS.md](docs/research/strategy/HYPOTHESIS.md)
* **Certificación Matemática Institucional (PSR, DSR, CPCV y PBO):** [docs/research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md](docs/research/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md)
* **Compendio Maestro de Estrategia Cuantitativa:** [docs/research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md](docs/research/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md)

---

## 🛡️ Innovaciones Clave de la Versión 7.6 (Sprints 36 a 39: Arquitectura Blindada de 4 Capas)

1. **Cortafuegos de Datos y Gobernanza Pydantic v2 (`validation/schemas.py`, `validation/data_firewall.py`):**
   * Validación estricta de geometría OHLCV, libros L2 y ticks con esquemas inmutables.
   * Detección automática de huecos temporales (*gaps* de 1h/4h) y saltos anómalos (*flash spikes* > 35%), forzando el sistema a modo `STANDBY` antes de inyectar datos sucios al LLM.
2. **Desacoplamiento Asíncrono del Cerebro Lento (`portfolio/agent_bias_daemon.py`, `portfolio/bias_store.py`):**
   * Emisión periódica (4h, 12h, 24h) de directivas estructuradas en JSON (`market_bias.json`) con expiración por TTL y convicción mínima ($\ge 70\%$). Los agentes nunca tocan la API de órdenes.
3. **Capa de Ejecución Determinista & Filtro de Rentabilidad Pre-Trade (`portfolio/pre_trade_profitability.py`):**
   * Evaluación matemática en $< 0.05\text{ ms}$ de comisiones (ida y vuelta), spread bid/ask y slippage Almgren-Chriss. Exige que el target de rebote supere el costo friccional por $\ge 2.5\times$ o aborta silenciosamente.
4. **El Kill Switch Absoluto y Guardián de Salida (`validation/ai_output_guard.py`, `portfolio/execution_gatekeeper.py`):**
   * Aduana estricta Pydantic (`extra='forbid'`) que neutraliza texto alucinado o formato libre de LLMs.
   * Interceptor final de broker que impone reglas inquebrantables: Stop-Loss obligatorio en código en cada orden, máximo de 3 slots concurrentes y liquidación a mercado en $< 1.0\text{ s}$ ante drawdown intradía $\ge 5.0\%$.
5. **Certificación Institucional:**
   * **37 nuevos tests pasando al 100% (243 tests globales sin errores).**

---

## 🌌 Innovaciones Previas de la Versión 7.5 (Sprints 33 a 35: Polars, VectorBT, Riskfolio-Lib & OpenBB)

1. **Acelerador de Datos y FFD en Polars (`data_engine/polars_feed.py`):**
   * Ingesta *Zero-Copy* de archivos Feather (Arrow IPC) y vectorización de FFD en C (`np.convolve`), acelerando la preparación de series temporales de 10x a 30x sobre Pandas.
2. **Evaluador Matricial VectorBT y Simulación Numba (`mining/vectorbt_evaluator.py`):**
   * Evaluación paralela de matrices de alphas en NSGA-II con cálculo vectorizado de Spearman IC sub-milisegundo en C y simulación de portafolio de alta frecuencia.
3. **Asignador HERC con CVaR al 99% y Colas Pesadas (`portfolio/riskfolio_allocator.py`):**
   * Implementación de optimización jerárquica HERC (*Hierarchical Equal Risk Contribution*) minimizando Expected Shortfall (CVaR al 99%) y CDaR para memecoins, complementado con regla de veto marginal y Deadband del 15%.
4. **Inteligencia Macro, DeFi & On-Chain con OpenBB (`data_engine/openbb_provider.py`):**
   * Ingesta desacoplada con caché < 0.1 ms de TVL en Solana/Ethereum (DefiLlama) y dispersión de tasas de financiación, condicionando dinámicamente las probabilidades alcistas del `RegimeHMMAgent`.
5. **Certificación Institucional:**
   * **17 nuevos tests certificados pasando al 100% (44 tests de regresión global para Sprints 30 a 35 sin errores).**

---

## 🚀 Innovaciones Previas de la Versión 7.4 (Sprints 30 a 32: Multi-Agente & Cockpit DAG HITL)

1. **Orquestador DAG y Fusión Bayesiana (`portfolio/dag_orchestrator.py`):**
   * Enrutador central de señales que sintetiza los vectores alpha de múltiples agentes especializados aplicando **Fusión Bayesiana** y pesos adaptativos condicionados por el régimen de mercado activo.
   * Telemetría institucional de ciclo de inferencia auditada en tiempo de ejecución ($< 20\text{ ms}$) y filtro de consenso mínimo configurable ($0.68\text{ Score}$).
2. **Ecosistema de Agentes Especializados (`portfolio/agents/`):**
   * `RegimeHMMAgent`: Detección dinámica y probabilística de regímenes ($p_{\text{bull}}, p_{\text{bear}}, p_{\text{range}}$) para conmutar pesos de cartera.
   * `TechnicalMicroAgent`: Microestructura rápida, FFD con memoria fraccionaria ($d=0.40$), RSI dinámico y proxy de desequilibrio de libro (OFI).
   * `SentimentAgent`: Percepción cualitativa en tiempo real (noticias, social feed, catalizadores de memecoins) mediante OpenRouter FinLLM con **fallback offline instantáneo de $0\text{ ms}$** y caché semántica.
3. **Gobernanza de Riesgo Dinámico y Degradación Elegante (`portfolio/graceful_degradation.py`):**
   * `RiskManagerAgent`: Evaluación downstream de VaR al 99% paramétrico, control estricto de Kill-Switch de equidad ($-25\%$) y filtro de correlación cruzada ($< 0.40$).
   * `GracefulDegradationGuard`: Monitoreo de microestructura Level 2; ante spreads tóxicos ($> 0.35\%$) o picos de latencia, reduce progresivamente el tamaño de posición y conmuta a órdenes pasivas Maker al Bid sin colapsar el sistema.
4. **Cockpit Visual DAG e Interfaz Human-in-the-Loop (`dashboard/`):**
   * Nueva pestaña: **`🌐 Orquestación Multi-Agente (DAG)`** con 8 nodos estilizados en tema oscuro neón.
   * **Panel Inspector:** Inspección reactiva con métricas en tiempo real (`Algoritmo Sint.`, `Consenso Min.`, `Ciclo Inferencia`), switch HITL para pausar/activar nodos en caliente y slider de consenso mínimo.
   * Endpoints REST dedicados: `/api/dag/topology`, `/api/dag/status`, `/api/dag/toggle-node`, `/api/dag/set-threshold`, `/api/dag/trigger-cycle`.
5. **Certificación de Pruebas Institucionales:**
   * **175+ tests pasando al 100% (24 nuevos tests de Sprints 30-32 certificados).**

---

## ⚡ Innovaciones Previas de la Versión 7.3 (Sprints 25 a 29)

1. **Fábrica de Alphas Concurrente en SQLite WAL (`portfolio/alpha_factory.db`):**
   * Migración del estado de la incubadora desde archivos JSON planos a una base de datos relacional transaccional SQLite con modo **Write-Ahead Logging (WAL)** y pool de conexiones seguro multihilo (`db_pool.py`).
   * Elimina bloqueos de lectura/escritura concurrentes entre el Dashboard, el motor autónomo y los procesos de minería.
2. **Compuertas Rigurosas Fuera de Muestra (OOS Hard-Gating):**
   * Validación formal previa a la promoción de cualquier estrategia a `LIVE` (`portfolio/oos_gating.py`):
     * **Probabilidad de Sobreajuste (PBO):** $< 15\%$.
     * **Sharpe Deflactado (DSR):** $\ge 95\%$.
     * **Correlación Cruzada con Alphas Activos:** $< 0.40$ (evitando concentración de riesgo).
     * **Zona Muerta de Rotación (Turnover Deadband de 15%):** Evita cambios marginales de peso que destruyan capital en comisiones innecesarias.
3. **Ensamble Dual-Engine Bidireccional (Long & Short en Freqtrade):**
   * Compilación dinámica AST en `scripts/compile_ensemble_strategy.py` hacia `user_data/strategies/MemeHunter_MinedEnsemble.py`.
   * Permite capturar tanto expansiones parabólicas alcistas (`enter_long`) como desinflaciones gravitacionales post-pump (`enter_short`), respaldado por confirmación rápida de tendencia (EMA 50 / 4h y RSI dinámico).
4. **Sincronización Automática en Vivo de Binance Futures (`data_engine/auto_data_sync.py`):**
   * Descarga no-bloqueante y normalización de velas de 4h en formato Feather de los 9 pares perpetuos más líquidos (`DOGE`, `PEPE`, `WIF`, `MEW`, `POPCAT`, `NEIRO`, `BONK`, `FLOKI`, `SHIB`).
5. **Modelado Realista de Fricción Microestructural:**
   * Inclusión estricta de comisiones de futuros (0.05% taker) más penalización de medio *spread* bid/ask en el cálculo de retornos del backtesting vectorial y compuertas OOS.
6. **Enlace REST y Notificación de Telemetría:**
   * Cliente REST para Freqtrade (`client/freqtrade_client.py`) con capacidad de hot-reload de estrategias en vivo sin reiniciar contenedores Docker, y despachador de eventos de telemetría (`client/telemetry_notifier.py`).
7. **Centro de Control Unificado (Cockpit v7.2/v7.3) & Sistema de 4 Pestañas:**
   * **`🎮 Centro de Mando (Live)`:** Monitoreo en tiempo real de órdenes abiertas, trades cerrados desde SQLite, Profit Ratchet y Kill-Switch.
   * **`📚 Estrategias & Backtests (Freqtrade)`:** Catálogo de estrategias físicas y descompresor automático de reportes históricos `.zip`.
   * **`🧪 Laboratorio Cuantitativo (Studio)`:** Diseñador simbólico con validación AST *Zero-Eval*, backtesting vectorial 4H con comisiones y despliegue a Sandbox en 1 clic.
   * **`🧠 Incubadora Autónoma`:** Pipeline de 5 etapas, curvas de equity HRP, rolling IC decay, autopsias forenses con IA (OpenRouter) y MAP-Elites.

---

## 📊 Síntesis Cuantitativa del Motor de Futuros (Certificación Oficial y OOS)

| Motor / Estrategia | Timeframe | Operaciones | Win Rate | Retorno Neto | Sharpe Anualizado | PSR (>0.0) | DSR Deflactado | Estado / Dictamen |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`MemeHunter_ApexOmegaAlpha`** | **1h** | **153** | **44.4%** | **+6.78% / +18.1%** | **4.28 (Sortino 21.4)** | **100.0%** | **100.0%** | 👑 **Estrategia Definitiva v7.6 (4 Capas + FFD + Trinquete Breakeven + Bet Sizing)** |
| **`MemeHunterFuturesV7_Quantum`** | **4h** | **—** | **—** | **—** | **—** | **—** | **—** | 🌌 **Canónica de Producción Futuros (FFD + Bet Sizing Continuo + Salidas Market)** |
| **`V5_OOS_CrossAsset` (Activos Ciegos)** | **4h** | **955** | **53.1%** | **+104.27%** | **4.04** | **100.0%** | **100.0%** | 🏆 **Certificación Fuera de Muestra Pura (SOL, SUI, TIA, WLD)** |
| `MemeHunterFuturesV5_Ablation` (Sin Calendario) | 4h | 2,361 | 50.2% | +156.29% | 2.94 | 100.0% | 0.0% | ℹ️ Edge Estructural Puro ($p=0.0068$ en muestra masiva) |
| `MemeHunterFuturesV5_Leverage` (100 USDT) | 4h | 215 | 61.4% | +96.20% | 7.48 | 100.0% | 100.0% | ✅ Modelo de Micro-Capital Anti-Freeze duplicando cuenta |
| `MemeHunterFuturesV5_Flat1x` (Sensibilidad 1.0x) | 4h | 1,846 | 50.1% | +48.64% | 2.43 | 100.0% | 0.0% | ⚠️ Margen estrecho contra comisiones; 1.5x ratificado |
| `MemeHunterFuturesV1_ShortOnly` (Benchmark 1,000 USDT) | 4h | 1,771 | 48.7% | +63.24% | 1.11 | 99.8% | — | ✅ Benchmark previo Short-Only sin estacionalidad |
| `MemeHunterFuturesV2` (Intradiario) | 1h | 12,828 | 39.3% | -75.46% | Negativo | 0.0% | — | ❌ Refutado (Destrucción por comisiones y mechas intra-vela) |

> **La Verdad Cuantitativa del Mercado y Microestructura (Sprint 17-20):** 
> 1. **Probabilidad de Sobreajuste (PBO = 6.67%):** La validación combinatoria purgada (CPCV) certifica que el sistema tiene solo un 6.67% de probabilidad de sobreajuste, situándose en el rango institucional óptimo (<25%).
> 2. **DSR al 100.0% en Activos Ciegos:** Tras penalizar por el sesgo de múltiples ensayos previos ($N \ge 6$), el sistema retiene expectativa matemática positiva en activos nunca vistos durante el diseño.
> 3. **Arquitectura Híbrida Barbell & Trinquete de Ganancias:** Acelerar micro-capital en el extremo agresivo (Futuros Short 1.5x) y cosechar el 60% de utilidades hacia la Bóveda Delta-Neutral de Cash & Carry ([`delta_neutral_vault.py`](scripts/delta_neutral_vault.py)) para blindar el patrimonio de colapsos sistémicos.

---

## 🧠 Lecciones Críticas del Mundo Real

1. **La Ventaja Real es Estrecha (+0.50% a +1.50% por trade):**
   * El *Stress-Test* demostró que operar como *Taker* o permitir spreads $> 0.3\%$ devora el 100% de las ganancias en comisiones.
   * La ejecución pasiva **Maker al Bid** en entradas y órdenes **Market forzadas en salidas** son obligatorias para no sufrir no-fills ni selección adversa.
2. **El "Efecto Airbag" de las Salidas Técnicas (`exit_signal`):**
   * La prueba experimental de V6 demostró que eliminar `exit_signal` elevó el Win Rate (67.2%) pero triplicó las pérdidas por stoploss duro (-295 USDT en 73 stops).
   * Salir con pérdida moderada (-2% a -6%) cuando la estructura técnica se invalida es un salvavidas que preserva el capital.
3. **El Presupuesto Micro-Capital Viable (100 USDT):**
   * Con **10 USDT**, la orden mínima de Binance ($5 USD) fuerza a arriesgar el 50% o 100% de la cuenta por trade, con una probabilidad de congelamiento/ruina de hasta el 92%.
   * Con **100 USDT** y 4 slots concentrados, la cuenta opera con margen de seguridad 6x sobre el mínimo de Binance y **0.0% probabilidad de ruina**.

---

## 🛡️ Protecciones Institucionales de Producción

1. **Kill-Switch de Equidad Total (PB-25):** Audita el balance realizado más el **PnL no realizado (*unrealized*)** de posiciones vivas concurrentes. Si el drawdown de capital vivo alcanza el 25%, se bloquean de inmediato nuevas entradas.
2. **Guardián de Tasa de Financiación (*Funding Bleed Guard*) (PB-24):** Rechaza órdenes Short si la tasa de financiación proyectada es inferior a **-0.05% por 8h**, evitando el desangrado pasivo de margen pagando comisiones a los Longs.
3. **Salidas Técnicas Dinámicas & Trailing Holgado (PB-23):** Salidas automáticas ante pérdida de la EMA 200 o cruce adverso de MACD/RSI, resolviendo el riesgo de operaciones *round-trip* (+11.5% cayendo a -10%). Trailing stop calibrado al 4.0% para absorber mechas intradía en velas de 4h.
4. **Válvula de Trinquete & Bóveda Delta-Neutral (PB-68 / PB-69):** Traspaso mecánico de utilidades hacia Cash & Carry delta-neutral (12%–30% APR) para blindar el capital contra eventos de cola gorda.

---

## 🛠️ Suite de Scripts Cuantitativos (`scripts/`)

| Script | Propósito / Función | Comando de Ejecución |
| :--- | :--- | :--- |
| `start_dashboard.py` | 🌟 **Lanzador del Cockpit Visual en tiempo real (Puerto 8088)** | `python scripts/start_dashboard.py` |
| `backtest_apex_omega.py` | 👑 **Backtest institucional de alta fidelidad de la Estrategia Definitiva v7.6** | `python scripts/backtest_apex_omega.py` |
| `auto_data_sync.py` | 📡 **Sincronizador continuo en vivo de Binance Futures (Feather 4H)** | `python data_engine/auto_data_sync.py` |
| `compile_ensemble_strategy.py` | ⚙️ **Compilador del ensamble dinámico bidireccional (Long/Short)** | `python scripts/compile_ensemble_strategy.py` |
| `run_live_alpha_loop.py` | ⚡ **Bucle E2E continuo conectado a Binance en tiempo real** | `python scripts/run_live_alpha_loop.py` |
| `run_autonomous_engine_demo.py` | 🤖 Demostración E2E del bucle cerrado: decay, autopsia IA y HRP | `python scripts/run_autonomous_engine_demo.py` |
| `run_alpha_factory_pipeline.py` | 🏭 Pipeline industrial completo de minería NSGA-II, CPCV y PBO | `python scripts/run_alpha_factory_pipeline.py` |
| `advanced_metrics.py` | Métricas avanzadas de Marcos López de Prado: PSR, Deflated Sharpe (DSR), CPCV y PBO | `python scripts/advanced_metrics.py` |
| `audit_advanced_backtests.py` | Auditoría de backtests ZIP reales con cálculo de PBO y DSR | `python scripts/audit_advanced_backtests.py` |
| `fractional_diff.py` | Diferenciación fraccionaria FFD con preservación de memoria y grid search ADF | `python scripts/fractional_diff.py` |
| `triple_barrier_metalabeling.py` | Generador de Triple Barrera, Meta-Etiquetado y Bet Sizing continuo | `python scripts/triple_barrier_metalabeling.py` |
| `train_meta_model.py` | Pipeline integrado de ML financiero: FFD + Triple Barrera + Bet Sizing L2 | `python scripts/train_meta_model.py` |
| `delta_neutral_vault.py` | Orquestador de la Bóveda Segura Cash & Carry con escaneo en vivo de Binance | `python scripts/delta_neutral_vault.py --scan` |
| `profit_ratchet_daemon.py` | Daemon de trinquete de ganancias: extrae el 60% de beneficios al duplicar cuenta | `python scripts/profit_ratchet_daemon.py` |
| `simulate_hybrid_barbell.py` | Simulación Monte Carlo de trayectoria hacia $10,000 USDT/mes pasivos | `python scripts/simulate_hybrid_barbell.py` |
| `stress_test.py` | Somete los trades a choques de comisiones, deslizamiento hostil y mide rachas | `python scripts/stress_test.py` |
| `monte_carlo.py` | Simulación Bootstrap (7,500 caminos) para estimar riesgo de ruina y VaR | `python scripts/monte_carlo.py` |
| `regime_classifier.py` | Clasificador cuantitativo de régimen de mercado y adaptación dinámica de riesgo | `python scripts/regime_classifier.py --symbol BTC/USDT:USDT` |
| `order_flow_imbalance.py` | Análisis de microestructura N2, desequilibrio de libro (OFI) y presión de precio | `python scripts/order_flow_imbalance.py --symbol DOGE/USDT:USDT` |
| `meme_sentinel.py` | Detector temprano de anomalías de volumen (RVOL) y explosiones en memecoins | `python scripts/meme_sentinel.py --top 10` |
| `dex_viral_radar.py` | Radar on-chain DEX (DexScreener API) para tracción y presión compradora viral | `python scripts/dex_viral_radar.py --top 10` |

---

## 🕹️ Control Operativo con el CLI Unificado (`scripts/meme_cli.py`)

Para eliminar la dispersión de comandos y operar el sistema desde un único punto de entrada:

```powershell
# 1. Auditoría de Salud Operativa en 2 segundos (Docker, DB SQLite, Cockpit API, .env)
python scripts/meme_cli.py health

# 2. Consultar o Iniciar el Cockpit Visual (Puerto 8088)
python scripts/meme_cli.py cockpit

# 3. Sincronizar velas reales de Binance Futures en segundo plano
python data_engine/auto_data_sync.py

# 4. Compilar ensamble cuantitativo bidireccional para Freqtrade
python scripts/compile_ensemble_strategy.py

# 5. Gestionar el Motor de Futuros (Freqtrade en Docker - Puerto 8081)
python scripts/meme_cli.py futures status     # Ver estado del contenedor
python scripts/meme_cli.py futures start      # Iniciar en background
python scripts/meme_cli.py futures logs       # Ver logs en vivo
python scripts/meme_cli.py futures stop       # Detener con seguridad

# 6. Ejecutar la Suite Completa de Tests (151+ Tests Certificados al 100%)
python scripts/meme_cli.py test

# 7. Ejecutar Herramientas de Investigación (I+D)
python scripts/meme_cli.py research stress    # Stress-Test de fricciones
python scripts/meme_cli.py research vault     # Escáner Cash & Carry Delta-Neutral
```

* **Cockpit Visual Seguro:** [http://localhost:8088](http://localhost:8088)
* **FreqUI en Vivo:** [http://localhost:8081](http://localhost:8081)
* **Certificación:** **151+ tests pasando al 100% (0 errores)** en la suite de pruebas automatizadas.

---

## 🌐 API REST del Centro de Control Unificado (`http://localhost:8088`)

| Método | Endpoint | Descripción | Autenticación |
| :---: | :--- | :--- | :---: |
| `GET` | `/api/status` | Resumen global del sistema, estrategia activa, estado HRP, Barbell y métricas. | Pública |
| `GET` | `/api/strategies-catalog` | Catálogo de las 11 estrategias Python físicas en `user_data/strategies/`. | Pública |
| `GET` | `/api/backtests-catalog` | Historial de los 34 reportes `.zip` de backtesting en `user_data/backtest_results/`. | Pública |
| `GET` | `/api/stress-report` | Pruebas de choque de fricción y desglose trimestral de consistencia. | Pública |
| `GET` | `/api/live-trades` | Posiciones abiertas y trades cerrados extraídos de `tradesv3.futures.sqlite`. | Pública |
| `POST` | `/api/validate-formula` | Validación sintáctica y seguridad AST *Zero-Eval* de expresiones simbólicas. | Bearer Token |
| `POST` | `/api/test-strategy` | Backtest rápido vectorial de 4H con comisiones y slippage sobre datos de futuros. | Bearer Token |
| `POST` | `/api/deploy-to-sandbox` | Inyección transaccional SQLite WAL a la incubadora (`portfolio/alpha_factory.db`). | Bearer Token |
| `POST` | `/api/trigger-loop` | Disparo manual del ciclo autónomo (CUSUM, autopsia, síntesis, gating y HRP). | Bearer Token |
| `POST` | `/api/synthesize-alpha` | Generación de nuevos alphas semánticos vía inferencia OpenRouter. | Bearer Token |

---

## 📂 Estructura del Repositorio

```
meme_hunter/
├── dashboard/                   # 🖥️ Centro de Control Unificado & API REST
│   ├── index.html               # Interfaz Glassmorphism con 4 pestañas de mando
│   ├── css/style.css            # Sistema de diseño moderno en Vanilla CSS
│   ├── js/app.js                # Lógica reactiva, tab switching y Chart.js
│   ├── server.py                # Servidor HTTP multihilo y API REST integrada (Lock async)
│   ├── backtest_scanner.py      # Lector de estrategias, zips de backtest y SQLite
│   └── strategy_tester.py       # Motor vectorial de backtesting y AST Zero-Eval
├── data_engine/                 # 📡 Ingesta, Sincronización y Microestructura
│   ├── auto_data_sync.py        # Sincronizador automático en vivo Binance Futures
│   ├── real_market_feed.py      # Ingesta de velas Feather con penalización de fricción
│   ├── dollar_bars.py           # Generador de Information-Driven Bars
│   ├── live_market_feed.py      # Streaming en vivo con Binance Spot/Futures
│   └── slippage_engine.py       # Modelo de impacto Almgren-Chriss
├── mining/                      # 🧬 Fábrica Genética y Síntesis IA
│   ├── alpha_grammar.py         # Gramática formal y árbol AST
│   ├── formula_parser.py        # Compilador seguro AST (Zero-Eval)
│   ├── genetic_search.py        # Minería evolutiva NSGA-II
│   ├── alpha_daemon.py          # Demonio 24/7 y Archivo MAP-Elites
│   ├── llm_client.py            # Cliente OpenRouter con fallback
│   └── llm_alpha_generator.py   # Síntesis de alphas guiada por IA
├── portfolio/                   # ⚖️ Incubadora, Concurrencia SQLite WAL, Gating y HRP
│   ├── db_schema.py             # Esquema DDL relacional (alpha_factory.db)
│   ├── db_pool.py               # Pool transaccional multihilo SQLite WAL
│   ├── oos_gating.py            # Compuertas Out-of-Sample (PBO, DSR, correlación)
│   ├── alpha_health_monitor.py  # Rolling IC, detector CUSUM y KS drift
│   ├── alpha_autopsy.py         # Agente forense de autopsias de IA con smart cache
│   ├── strategy_incubator.py    # Máquina de estados con turnover deadband de 15%
│   ├── autonomous_orchestrator.py # Orquestador central del bucle cerrado
│   └── hrp_allocator.py         # Hierarchical Risk Parity
├── client/                      # 🔌 Clientes de Integración y Telemetría
│   ├── freqtrade_client.py      # Cliente REST Freqtrade (Hot-reload, balance, whitelist)
│   └── telemetry_notifier.py    # Emisor de eventos y alertas operativas
├── validation/                  # 🛡️ Validación Institucional Anti-Overfitting
│   ├── cpcv_engine.py           # Combinatorial Purged Cross-Validation
│   └── multiple_testing.py      # Control FDR (Benjamini-Hochberg) y PBO
├── user_data/                   # 📊 Datos de Producción, Estrategias y Resultados
│   ├── strategies/              # 12 Estrategias Freqtrade Python (Ensamble Mined activo)
│   ├── backtest_results/        # 34 Archivos .zip de backtests históricos y estrés
│   └── tradesv3.futures.sqlite  # Base de datos de posiciones y órdenes de futuros
├── docs/                        # 📚 Centro integral de documentación
│   ├── architecture/            # DAS v7.3 y registros ADR
│   ├── sprints/                 # Sprints de ingeniería ágil (Sprints 1 a 29)
│   ├── strategy/                # Hipótesis y modelos de escalado
│   └── reports/                 # Informes de auditoría forense
├── scripts/                     # 🛠️ Suite de herramientas ejecutables
│   └── compile_ensemble_strategy.py # Compilador dinámico Long/Short para Freqtrade
└── tests/                       # 🧪 Pruebas unitarias e integrales (151+ tests, 100% pass)
```

### Ejecutar las Pruebas Automatizadas
```powershell
python -m pytest tests -v
```

---

## 📜 Reglas de Oro del Proyecto
1. **Rigor Científico:** Nada pasa a capital real sin validación en datos ciegos (*Hold-Out*) y simulación de Monte Carlo.
2. **Microestructura Pasiva:** Órdenes exclusivamente límite (*Maker*) en el mejor *Bid/Ask* y rechazo de spreads $> 0.3\%$.
3. **Seguridad Absoluta de API:** Claves con restricción de IP estática y **prohibición terminante de permisos de retiro**.
