# 🏹 Meme Hunter - Sistema Cuantitativo y de Microestructura

Sistema de trading algorítmico sobre [Freqtrade](https://www.freqtrade.io/) y [CCXT](https://ccxt.trade/) diseñado para **validar empíricamente una ventaja estadística real (*edge*)** frente a los retos del mercado cripto (comisiones, deslizamiento, deslistados y cambios de régimen) antes de arriesgar capital.

---

## 🏛️ Documentación Central

* **Arquitectura de Software:** [DAS.md](DAS.md)
* **Plan de Trabajo y Sprints:** [SCRUM_PLAN.md](SCRUM_PLAN.md)
* **Hipótesis Teórica del Edge:** [HYPOTHESIS.md](HYPOTHESIS.md)
* **Reporte Oficial de Backtesting y Stress-Test:** [PRELIMINARY_REPORT.md](PRELIMINARY_REPORT.md)
* **Plan de Transición a Producción (VPS & Cloud):** [plan_implementacion_produccion.md](file:///C:/Users/kaleb/.gemini/antigravity-ide/brain/8aa12c5e-3d22-44b4-9bd4-070fcfb13712/plan_implementacion_produccion.md)

---

## 📊 Síntesis Cuantitativa: Evolución del Sistema

| Motor / Estrategia | Mercado | Operaciones | Win Rate | Retorno Neto | Sortino | Max Drawdown | Estado / Dictamen |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MemeHunterV1** | Spot (2020–2025) | 5,562 | 39.5% | **-48.62%** | -0.68 | 77.17% | ❌ **Descartado (Salidas prematuras MACD)** |
| **MemeHunterV2** | Spot Hold-Out (2025–2026) | 462 | 57.8% | **+20.57%** | 1.41 | 26.20% | ✅ **Validado (+75.6% vs mercado -55%)** |
| **MemeHunterFuturesV1** | **Futuros USDT-M (2024–2026)** | **1,439** | **66.6%** | **+56.82%** | **1.76** | **21.85%** | 🏆 **Motor Primario (Monetiza el invierno)** |

> **El Gran Descubrimiento:** En Futuros, las operaciones **Short (+61.68%)** amortizaron por completo el sangrado lateral de los Longs (-4.86%), monetizando los desplomes de mercado con margen aislado 1.0x (cero riesgo de liquidación).

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

## 🛠️ Suite de Scripts Cuantitativos (`scripts/`)

| Script | Propósito / Función | Comando de Ejecución |
| :--- | :--- | :--- |
| `stress_test.py` | Somete los trades a choques de comisiones, deslizamiento hostil y mide rachas | `python scripts/stress_test.py` |
| `monte_carlo.py` | Simulación Bootstrap (7,500 caminos) para estimar riesgo de ruina y VaR | `python scripts/monte_carlo.py` |
| `simulate_micro_capital.py` | Evalúa la viabilidad de 10 USDT vs 100 USDT bajo límites reales de Binance | `python scripts/simulate_micro_capital.py` |
| `test_binance_connection.py` | Prueba latencia de red, sincronización horaria y libros de órdenes de Binance | `docker compose run --rm freqtrade scripts/test_binance_connection.py` |
| `telegram_healthcheck.py` | Valida credenciales del bot de Telegram y envía ping de prueba | `python scripts/telegram_healthcheck.py` |
| `deploy_vps.sh` | Aprovisiona un servidor cloud Ubuntu con Docker, UFW y Fail2ban en 1 paso | `bash scripts/deploy_vps.sh` |

---

## 🚀 Despliegue Rápido en Vivo (Modo Dry-Run en Docker)

### A. Motor de Futuros (Recomendado - Bidireccional Long/Short)
```powershell
# Iniciar en segundo plano
docker compose -f docker-compose.futures.yml up -d

# Ver logs en tiempo real
docker compose -f docker-compose.futures.yml logs -f
```
* **Dashboard Web (FreqUI):** [http://localhost:8081](http://localhost:8081)
* **Credenciales:** Usuario `admin` | Clave `MemeHunter2026!`

### B. Motor Spot (Binance Spot Long-Only)
```powershell
# Iniciar en segundo plano
docker compose -f docker-compose.live.yml up -d

# Ver logs en tiempo real
docker compose -f docker-compose.live.yml logs -f
```
* **Dashboard Web (FreqUI):** [http://localhost:8080](http://localhost:8080)
* **Credenciales:** Usuario `admin` | Clave `MemeHunter2026!`

---

## 📂 Estructura del Repositorio

```
meme_hunter/
├── docker-compose.futures.yml   # Despliegue de Futuros (Puerto 8081)
├── docker-compose.live.yml      # Despliegue de Spot (Puerto 8080)
├── docker-compose.yml           # Base para comandos generales
├── .env.example                 # Plantilla de secretos (Binance / Telegram)
├── scripts/                     # Herramientas estadísticas y de stress testing
│   ├── daily_performance.py     # Análisis de rendimiento diario, win rate día a día y estacionalidad
│   ├── stress_test.py           # Choque de fricción adversa (slippage, fees, delays)
│   ├── monte_carlo.py           # Remuestreo bootstrap de 7,500 caminos y riesgo de ruina
│   ├── simulate_micro_capital.py# Simulación con restricciones de orden mínima ($5 Binance)
│   ├── deploy_vps.sh            # Script de aprovisionamiento en VPS Ubuntu
│   └── telegram_healthcheck.py  # Diagnóstico y alertas en Telegram
├── user_data/
│   ├── config_futures.json      # Configuración de Futuros (Live / Dry-Run)
│   ├── config_live.json         # Configuración de Spot (Live / Dry-Run)
│   ├── config_futures_backtest.json
│   └── strategies/
│       ├── MemeHunterFuturesV1.py # Estrategia Long/Short aislada 1x
│       ├── MemeHunterV2.py        # Estrategia Spot blindada
│       └── MemeHunterV1.py        # Estrategia histórica de investigación
└── tests/                       # Suite de pruebas unitarias pytest
```

---

## 📜 Reglas de Oro del Proyecto
1. **Rigor Científico:** Nada pasa a capital real sin validación en datos ciegos (*Hold-Out*) y simulación de Monte Carlo.
2. **Microestructura Pasiva:** Órdenes exclusivamente límite (*Maker*) en el mejor *Bid/Ask* y rechazo de spreads $> 0.3\%$.
3. **Seguridad Absoluta de API:** Claves con restricción de IP estática y **prohibición terminante de permisos de retiro**.
