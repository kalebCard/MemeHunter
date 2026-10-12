# 🏹 Meme Hunter - Sistema Cuantitativo, Auto-Evolutivo & Cockpit IA (v7.0)

Plataforma cuantitativa institucional que combina **minería genética de factores (NSGA-II)**, **ingesta continua de Dollar Bars en tiempo real desde Binance**, **bucle cerrado de auto-sanación con detección CUSUM e IC Decay**, **cerebro cognitivo de autopsias y síntesis semántica vía OpenRouter**, y un **Cockpit Visual interactivo** para monitoreo y control en vivo.

---

## 🏛️ Centro de Documentación (`docs/`)

La documentación del proyecto se encuentra estructurada en el directorio [`docs/`](docs/README.md):

* **[Índice General de Documentación:](docs/README.md)** Guía integral y rutas de lectura según perfil.
* **Plan Scrum de Remediación & Hardening (v7.1):** [docs/sprints/SPRINT_PLAN_REMEDIATION_AND_HARDENING.md](docs/sprints/SPRINT_PLAN_REMEDIATION_AND_HARDENING.md)
* **Arquitectura de Software Auto-Evolutiva (v7.0):** [docs/architecture/DAS_AUTONOMOUS_ENGINE.md](docs/architecture/DAS_AUTONOMOUS_ENGINE.md)
* **Arquitectura Tradicional (v4.0 - v6.0):** [docs/architecture/DAS.md](docs/architecture/DAS.md)
* **Sprint 1 (Motor Auto-Evolutivo & Self-Healing):** [docs/sprints/SPRINT_AUTONOMOUS_SELF_IMPROVING_ENGINE.md](docs/sprints/SPRINT_AUTONOMOUS_SELF_IMPROVING_ENGINE.md)
* **Sprint 2 (Cognición IA con OpenRouter):** [docs/sprints/SPRINT_LLM_AUGMENTED_AUTONOMOUS_ENGINE.md](docs/sprints/SPRINT_LLM_AUGMENTED_AUTONOMOUS_ENGINE.md)
* **Plan de Trabajo y Sprints Históricos:** [docs/strategy/SCRUM_PLAN.md](docs/strategy/SCRUM_PLAN.md)
* **Hipótesis Teórica del Edge:** [docs/strategy/HYPOTHESIS.md](docs/strategy/HYPOTHESIS.md)
* **Certificación Institucional (PSR, DSR, CPCV y PBO):** [docs/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md](docs/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md)

---

## 🚀 Innovaciones Clave de la Versión 7.0 & 7.1

1. **Bucle Cerrado Auto-Evolutivo (Closed-Loop Engine):**
   * **Monitoreo Continuo:** `AlphaHealthMonitor` calcula Information Coefficient (IC) rodante y detecta rupturas estructurales con CUSUM (Page-Hinkley) y *data drift* con Kolmogorov-Smirnov.
   * **Incubadora Autónoma:** Transición mecánica sin intervención humana entre `SANDBOX` $\rightarrow$ `LIVE` $\rightarrow$ `ALPHA_DECAY` $\rightarrow$ `RETIRED` con período de gracia real.
   * **Asignación HRP:** Reponderación dinámica de capital vía Paridad Jerárquica de Riesgo con regularización ante singularidades de varianza.
2. **Cerebro Cognitivo de IA (OpenRouter):**
   * **Autopsias Forenses (`AlphaAutopsyAgent`):** Modelos de razonamiento profundo (DeepSeek-R1 / Claude 3.5 Sonnet) identifican la causa raíz de la degradación y emiten recomendaciones de búsqueda con marcas de tiempo UTC dinámicas.
   * **Síntesis Semántica (`LLMAlphaSynthesizer`):** Formulación de factores basados en hipótesis de microestructura (desbalances de volumen, Amihud ratio, compresión en Dollar Bars).
   * **Compilador Seguro (`FormulaASTParser`):** Sanitizador AST *Zero Eval* compatible con Python 3.14 (`ast.Constant`).
   * **Control de Presupuesto:** Limitador de tasa y tope máximo de tokens por sesión para prevenir agotamiento de saldo.
3. **Cockpit Visual Seguro y Multihilo (Dashboard Web):**
   * Servidor HTTP concurrente (`ThreadingHTTPServer`) accesible en `http://localhost:8088` con autenticación por token Bearer en endpoints de control y CORS restringido.
4. **Streaming en Vivo sin Deadlock (`LiveMarketFeed`):**
   * Ingesta de velas y trades de memecoins (`DOGE`, `PEPE`, `SHIB`) con lock reentrante (`RLock`) y notificación de eventos desacoplada para máxima concurrencia.

---

## 📊 Síntesis Cuantitativa del Motor de Futuros (Certificación Oficial y OOS)

| Motor / Estrategia | Timeframe | Operaciones | Win Rate | Retorno Neto | Sharpe Anualizado | PSR (>0.0) | DSR Deflactado | Estado / Dictamen |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`MemeHunterFuturesV7_Quantum`** | **4h** | **—** | **—** | **—** | **—** | **—** | **—** | 🌌 **Canónica de Producción (FFD + Bet Sizing Continuo + Salidas Market)** |
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

## 🚀 Despliegue Rápido de la Plataforma v7.0 & v7.1

### 1. Iniciar Cockpit Visual Seguro de Monitoreo
```powershell
python scripts/start_dashboard.py
```
Acceder al panel interactivo: **[http://localhost:8088](http://localhost:8088)** *(Autenticación con Bearer token en mutaciones)*

### 2. Iniciar el Bucle Autónomo en Tiempo Real (Binance)
```powershell
python scripts/run_live_alpha_loop.py
```

### 3. Motor Tradicional de Futuros (Freqtrade en Docker)
```powershell
docker compose -f docker-compose.futures.yml up -d
```
* **Dashboard Web (FreqUI):** [http://localhost:8081](http://localhost:8081)
* **Cockpit Visual Seguro:** [http://localhost:8088](http://localhost:8088) *(No colisiona con FreqUI)*

### 4. Ejecutar la Suite Completa de Tests (110 Tests Certificados)
```powershell
docker compose run --rm -e PYTHONPATH=/freqtrade --entrypoint pytest freqtrade tests/ -v
```
* **Certificación:** **110/110 tests pasando al 100% (0 errores)** en contenedor hermético.

---

## 📂 Estructura del Repositorio

```
meme_hunter/
├── dashboard/                   # 🖥️ Cockpit Visual Web & API REST
│   ├── index.html               # Interfaz Glassmorphism con Chart.js
│   ├── css/style.css            # Sistema de diseño moderno en Vanilla CSS
│   ├── js/app.js                # Lógica reactiva y gráficos en tiempo real
│   └── server.py                # Servidor HTTP y API REST integrado
├── data_engine/                 # 📡 Ingesta y Microestructura
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
├── portfolio/                   # ⚖️ Incubadora, Salud y Asignación HRP
│   ├── alpha_health_monitor.py  # Rolling IC, detector CUSUM y KS drift
│   ├── alpha_autopsy.py         # Agente forense de autopsias de IA
│   ├── strategy_incubator.py    # Máquina de estados (SANDBOX/LIVE/DECAY)
│   ├── autonomous_orchestrator.py # Orquestador central del bucle cerrado
│   └── hrp_allocator.py         # Hierarchical Risk Parity
├── validation/                  # 🛡️ Validación Institucional Anti-Overfitting
│   ├── cpcv_engine.py           # Combinatorial Purged Cross-Validation
│   └── multiple_testing.py      # Control FDR (Benjamini-Hochberg) y PBO
├── docs/                        # 📚 Centro integral de documentación
│   ├── architecture/            # DAS v7.0 y registros ADR
│   ├── sprints/                 # Sprints de ingeniería ágil
│   ├── strategy/                # Hipótesis y modelos de escalado
│   └── reports/                 # Informes de auditoría forense
├── scripts/                     # 🛠️ Suite de herramientas ejecutables
└── tests/                       # 🧪 Pruebas unitarias e integrales (100% pass)
```

### Ejecutar las Pruebas Automatizadas
```powershell
python -m pytest tests
```

---

## 📜 Reglas de Oro del Proyecto
1. **Rigor Científico:** Nada pasa a capital real sin validación en datos ciegos (*Hold-Out*) y simulación de Monte Carlo.
2. **Microestructura Pasiva:** Órdenes exclusivamente límite (*Maker*) en el mejor *Bid/Ask* y rechazo de spreads $> 0.3\%$.
3. **Seguridad Absoluta de API:** Claves con restricción de IP estática y **prohibición terminante de permisos de retiro**.
