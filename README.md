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

---

## 📊 Síntesis Cuantitativa del Motor de Futuros (Certificación Oficial de Alta Fidelidad)

| Motor / Estrategia | Timeframe | Operaciones | Win Rate | Retorno Neto Freqtrade | Retorno Mediano Monte Carlo | Calmar | Sortino | Max Drawdown Real | Estado / Dictamen |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **MemeHunterFuturesV1_ShortOnly** | **4h** | **1,771** | **48.7%** | **+63.24% (+632.40 USDT)** | **+127.15% a +362.34%** | **4.00** | **2.48** | **31.15%** | 🏆 **Líder Cuantitativo Oficial (Sprint 10)** |
| `MemeHunterFuturesV1` (Bidireccional) | 4h | 2,942 | 45.5% | +5.57% *(vs -5.50% mercado)* | +26.29% ($126 USDT) | 0.35 | 0.42 | 39.49% | ✅ Certificado con `--timeframe-detail 1m` |
| `MemeHunterFuturesV2` (Intradiario) | 1h | 12,828 | 39.3% | -75.46% (-754.59 USDT) | N/A (Sobreoperación) | -1.97 | -1.01 | 75.74% | ❌ **Refutado (Trampa de Comisiones y Ruido)** |

> **La Verdad Cuantitativa del Mercado de Memecoins:** 
> 1. **La Trampa de 1h:** Bajar la temporalidad para "ganar todos los días" disparó 12,828 operaciones y $1.43 millones en volumen, destruyendo el 75% del capital en comisiones y mechas de liquidación intra-vela.
> 2. **El Alfa Asimétrico Puro (4h Short-Only):** Las memecoins se desinflan entre 80% y 95% tras cada pump eufórico. Al eliminar por completo las compras (Longs) y operar únicamente la tendencia macro bajista con margen aislado 1.0x (cero riesgo de liquidación), el sistema multiplicó el beneficio por **11.3X (+63.24% neto)**, con un Calmar de **4.00** y 8 de las 10 memecoins en positivo (+719.85 USDT acumulados).

---

## 🧠 Lecciones Críticas del Mundo Real

1. **La Ventaja Real es Estrecha (+0.50% a +0.70% por trade):**
   * El *Stress-Test* demostró que operar como *Taker* o permitir spreads $> 0.3\%$ devora el 100% de las ganancias en comisiones.
   * La ejecución pasiva **Maker al Bid** y el filtro de spread son obligatorios para no quebrar.
2. **El Rendimiento No es Lineal (Paciencia Psicológica):**
   * El sistema experimentó **6 meses consecutivos en negativo** (octubre 2025 a marzo 2026, perdiendo 271 USDT) antes de recuperarse. La disciplina de no apagar el bot en drawdowns es vital.
3. **El Presupuesto Mínimo Viable es 100 USDT (No 10 USDT):**
   * Con **10 USDT**, la orden mínima de Binance ($5 USD) fuerza a arriesgar el 50% o 100% de la cuenta por trade, con una **probabilidad de congelamiento/ruina de hasta el 92%**.
   * Con **100 USDT**, se pueden abrir 10 posiciones de $10 USD (10% por trade) con **riesgo de congelamiento del 0.0%**.

---

## 🛡️ Protecciones Institucionales de Producción (Sprint 8 Hardening)

1. **Kill-Switch de Equidad Total (PB-25):** Audita el balance realizado más el **PnL no realizado (*unrealized*)** de posiciones vivas concurrentes. Si el drawdown de capital vivo alcanza el 25%, se bloquean de inmediato nuevas entradas.
2. **Guardián de Tasa de Financiación (*Funding Bleed Guard*) (PB-24):** Rechaza órdenes Short si la tasa de financiación proyectada es inferior a **-0.05% por 8h**, evitando el desangrado pasivo de margen pagando comisiones a los Longs.
3. **Salidas Técnicas Dinámicas & Trailing Holgado (PB-23):** Salidas automáticas ante pérdida de la EMA 200 o cruce adverso de MACD/RSI, resolviendo el riesgo de operaciones *round-trip* (+11.5% cayendo a -10%). Trailing stop calibrado al 4.0% para absorber mechas intradía en velas de 4h.
4. **Ejecución Protegida & Squeeze Guard (PB-26 / PB-27):** Salidas de stoploss y emergencia ejecutadas como órdenes de mercado (`market`) para garantizar llenado inmediato en memecoins delgadas, con reconocimiento explícito del riesgo de liquidación en rallies de +80% en Shorts.

---

## 🛠️ Suite de Scripts Cuantitativos (`scripts/`)

| Script | Propósito / Función | Comando de Ejecución |
| :--- | :--- | :--- |
| `stress_test.py` | Somete los trades a choques de comisiones, deslizamiento hostil y mide rachas | `python scripts/stress_test.py` |
| `monte_carlo.py` | Simulación Bootstrap (7,500 caminos) para estimar riesgo de ruina y VaR | `python scripts/monte_carlo.py` |
| `dryrun_monitor.py` | Compara el dry-run en vivo (SQLite) contra los criterios de aceptación de PB-14 | `python scripts/dryrun_monitor.py` |
| `meme_sentinel.py` | Detector temprano de anomalías de volumen (RVOL) y explosiones en memecoins (PB-15) | `python scripts/meme_sentinel.py --top 10` |
| `dex_viral_radar.py` | Radar on-chain DEX (DexScreener API) para tracción y presión compradora viral (PB-16) | `python scripts/dex_viral_radar.py --top 10` |
| `funding_arbitrage.py` | Escáner y calculador de arbitraje Delta-Neutral de Funding Rates (PB-17) | `python scripts/funding_arbitrage.py --min-apr 20.0` |
| `order_flow_imbalance.py` | Análisis de microestructura N2, desequilibrio de libro (OFI) y presión de precio (PB-18) | `python scripts/order_flow_imbalance.py --symbol DOGE/USDT:USDT` |
| `regime_classifier.py` | Clasificador cuantitativo de régimen de mercado y adaptación dinámica de riesgo (PB-19) | `python scripts/regime_classifier.py --symbol BTC/USDT:USDT` |
| `simulate_micro_capital.py` | Evalúa la viabilidad de 10 USDT vs 100 USDT bajo límites reales de Binance | `python scripts/simulate_micro_capital.py` |
| `test_binance_connection.py` | Prueba latencia de red, sincronización horaria y libros de órdenes de Binance | `docker compose run --rm freqtrade scripts/test_binance_connection.py` |
| `telegram_healthcheck.py` | Valida credenciales del bot de Telegram y envía ping de prueba | `python scripts/telegram_healthcheck.py` |
| `deploy_vps.sh` | Aprovisiona un servidor cloud Ubuntu con Docker, UFW y Fail2ban en 1 paso | `bash scripts/deploy_vps.sh` |

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
