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

| Motor / Estrategia | Timeframe | Operaciones | Win Rate | Retorno Neto Freqtrade | Retorno Anual (CAGR) | Calmar | Sortino | Max Drawdown Real | Estado / Dictamen |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **MemeHunterFuturesV5_Leverage (100 USDT)** | **4h** | **215** | **61.4%** | **+96.20% (Pico $211.48)** | **+110.27%** | **21.03** | **3.12** | **26.41%** (Piso $88.24) | 🏆 **Líder Cuantitativo Oficial (Sprint 15/16)** |
| `MemeHunterFuturesV4` (100 USDT Base) | 4h | 223 | 53.4% | +58.93% (+58.93 USDT) | +66.68% | 16.62 | 2.32 | 20.47% (Piso $92.52) | ✅ Certificado con Estacionalidad & Subasta |
| `MemeHunterFuturesV1_ShortOnly` (1,000 USDT) | 4h | 1,771 | 48.7% | +63.24% (+632.40 USDT) | +63.24% | 4.00 | 2.48 | 31.15% | ✅ Benchmark Previo Short-Only |
| `MemeHunterFuturesV6_Apex` (Sin exit_signal) | 4h | 241 | 67.2% | +27.01% (+27.01 USDT) | +30.17% | 3.48 | 1.04 | 45.74% | 🔬 Experimental (Airbag técnico ratificado en V5) |
| `MemeHunterFuturesV2` (Intradiario) | 1h | 12,828 | 39.3% | -75.46% (-754.59 USDT) | N/A | -1.97 | -1.01 | 75.74% | ❌ Refutado (Trampa de Comisiones y Ruido) |

> **La Verdad Cuantitativa del Mercado de Memecoins & Micro-Capital:** 
> 1. **La Asimetría de Estacionalidad Humana (Sprint 13/15):** Los Viernes y Domingos concentran más del **88% de las ganancias anuales (+94.21 USDT netos con >71% Win Rate)**. Operar Lunes/Martes destruía capital (-756 USDT en V3); la máscara de calendario protegió el 100% de la liquidez.
> 2. **Apalancamiento Dinámico Asimétrico (1.5x - 2.0x):** Asignar 2.0x exclusivamente en techos confirmados por rechazo de subasta (*Trapped Longs*) y 1.5x en continuación macro elevó el Win Rate al **61.4%**, casi duplicando la cuenta de 100 USDT (**+96.20% neto / pico de $211.48 USDT**) con un **Calmar récord de 21.03**.
> 3. **El Modelo Anti-Freeze de Micro-Capital (PB-51):** Concentrar los 100 USDT en **4 slots dinámicos ($25 USDT base)** elimina el riesgo de congelamiento ante el límite de $5.00 USDT de Binance Futures; el stake promedio operado fue de **$31.10 USDT**, creciendo a $42.80 en los picos.

---

## 🧠 Lecciones Críticas del Mundo Real

1. **La Ventaja Real es Estrecha (+0.50% a +1.50% por trade):**
   * El *Stress-Test* demostró que operar como *Taker* o permitir spreads $> 0.3\%$ devora el 100% de las ganancias en comisiones.
   * La ejecución pasiva **Maker al Bid** y el filtro de spread son obligatorios para no quebrar.
2. **El "Efecto Airbag" de las Salidas Técnicas (`exit_signal`):**
   * La prueba experimental de V6 demostró que eliminar `exit_signal` elevó el Win Rate (67.2%) pero triplicó las pérdidas por stoploss duro (-295 USDT en 73 stops).
   * Salir con pérdida moderada (-2% a -6%) cuando la estructura técnica se invalida es un salvavidas que preserva el capital.
3. **El Presupuesto Micro-Capital Viable (100 USDT):**
   * Con **10 USDT**, la orden mínima de Binance ($5 USD) fuerza a arriesgar el 50% o 100% de la cuenta por trade, con una probabilidad de congelamiento/ruina de hasta el 92%.
   * Con **100 USDT** y 4 slots concentrados, la cuenta opera con margen de seguridad 6x sobre el mínimo de Binance y **0.0% probabilidad de ruina**.

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
