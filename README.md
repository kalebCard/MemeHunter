# 🏹 Meme Hunter - Sistema Cuantitativo y de Microestructura

Sistema de trading algorítmico sobre [Freqtrade](https://www.freqtrade.io/) y [CCXT](https://ccxt.trade/) diseñado para **validar empíricamente una ventaja estadística real (*edge*)** frente a los retos del mercado cripto (comisiones, deslizamiento, deslistados y cambios de régimen) antes de arriesgar capital.

---

## 🏛️ Centro de Documentación (`docs/`)

La documentación del proyecto se encuentra estructurada en el directorio [`docs/`](docs/README.md):

* **[Índice General de Documentación:](docs/README.md)** Guía integral y rutas de lectura según perfil.
* **Arquitectura de Software (v4.0):** [docs/architecture/DAS.md](docs/architecture/DAS.md)
* **Plan de Trabajo y Sprints Scrum:** [docs/strategy/SCRUM_PLAN.md](docs/strategy/SCRUM_PLAN.md)
* **Hipótesis Teórica del Edge:** [docs/strategy/HYPOTHESIS.md](docs/strategy/HYPOTHESIS.md)
* **Reporte Oficial de Backtesting:** [docs/reports/PRELIMINARY_REPORT.md](docs/reports/PRELIMINARY_REPORT.md)
* **Informe de Viabilidad con 100 USDT:** [docs/reports/INFORME_FUTUROS_100_USDT.md](docs/reports/INFORME_FUTUROS_100_USDT.md)
* **Auditoría Forense de Riesgos y Overfitting:** [docs/reports/INFORME_AUDITORIA_FORENSE_RIESGOS.md](docs/reports/INFORME_AUDITORIA_FORENSE_RIESGOS.md)
* **Certificación Institucional (PSR, DSR, CPCV y PBO):** [docs/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md](docs/reports/INFORME_METRICAS_AVANZADAS_DSR_PBO.md)

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

## 🚀 Despliegue Rápido en Vivo (Modo Dry-Run en Docker)

### 0. Preparar configuración (una sola vez)
Los configs con credenciales de FreqUI no se versionan. Crea los tuyos desde las plantillas y cambia `CAMBIAR_ME` en `jwt_secret_key` y `password`:
```powershell
Copy-Item user_data/config_futures.example.json user_data/config_futures.json
Copy-Item user_data/config_live.example.json user_data/config_live.json
Copy-Item .env.example .env   # y completa Binance / Telegram
```

### A. Motor de Futuros (Recomendado - Bidireccional Long/Short)
```powershell
# Iniciar en segundo plano
docker compose -f docker-compose.futures.yml up -d

# Ver logs en tiempo real
docker compose -f docker-compose.futures.yml logs -f
```
* **Dashboard Web (FreqUI):** [http://localhost:8081](http://localhost:8081)
* **Credenciales:** usuario y clave definidos por ti en `config_futures.json`

---

## 📂 Estructura del Repositorio

```
meme_hunter/
├── docs/                        # Centro integral de documentación
│   ├── README.md                # Índice y guía de lectura
│   ├── architecture/DAS.md      # Arquitectura de software (v4.0)
│   ├── strategy/                # Hipótesis cuantitativa y Scrum plan
│   └── reports/                 # Informes de backtest y capital de 100 USDT
├── docker-compose.futures.yml   # Despliegue de Futuros (Puerto 8081)
├── docker-compose.yml           # Base para comandos generales
├── .env.example                 # Plantilla de secretos (Binance / Telegram)
├── scripts/                     # Herramientas estadísticas, microestructura y radares
│   ├── daily_performance.py     # Análisis de rendimiento diario, win rate día a día y estacionalidad
│   ├── dryrun_monitor.py        # Auditoría continua de trades simulados en SQLite vs criterios de aceptación
│   ├── meme_sentinel.py         # Scanner de spikes de volumen relativo (RVOL) y liquidez en Binance
│   ├── dex_viral_radar.py       # Radar on-chain DEX (DexScreener) para tracción viral Web3
│   ├── funding_arbitrage.py     # Calculador de arbitraje Delta-Neutral de Funding Rates (Cash & Carry)
│   ├── order_flow_imbalance.py  # Análisis de microestructura Nivel 2 (OFI) y Micro-Price
│   ├── regime_classifier.py     # Clasificador de régimen de mercado (Volatilidad/Tendencia) y sizing dinámico
│   ├── stress_test.py           # Choque de fricción adversa (slippage, fees, delays)
│   ├── monte_carlo.py           # Remuestreo bootstrap de 7,500 caminos y riesgo de ruina
│   ├── simulate_micro_capital.py# Simulación con restricciones de orden mínima ($5 Binance)
│   ├── deploy_vps.sh            # Script de aprovisionamiento en VPS Ubuntu
│   └── telegram_healthcheck.py  # Diagnóstico y alertas en Telegram
├── user_data/
│   ├── config_futures.example.json # Plantilla de Futuros (copiar a config_futures.json, no versionado)
│   ├── config_futures_backtest.json
│   └── strategies/
│       └── MemeHunterFuturesV1.py # Estrategia Long/Short aislada 1x con Sizing Asimétrico y Kill-Switch
└── tests/                       # Suite pytest (48 tests unitarios pasando al 100%)
```

### Ejecutar los tests
```powershell
docker run --rm -v "${PWD}:/freqtrade/proj" -w /freqtrade/proj --entrypoint python meme_hunter:2026.9 -m pytest -q tests
```

---

## 📜 Reglas de Oro del Proyecto
1. **Rigor Científico:** Nada pasa a capital real sin validación en datos ciegos (*Hold-Out*) y simulación de Monte Carlo.
2. **Microestructura Pasiva:** Órdenes exclusivamente límite (*Maker*) en el mejor *Bid/Ask* y rechazo de spreads $> 0.3\%$.
3. **Seguridad Absoluta de API:** Claves con restricción de IP estática y **prohibición terminante de permisos de retiro**.
