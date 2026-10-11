# 📚 Centro de Documentación - Meme Hunter

Bienvenido al centro de documentación técnica, cuantitativa y operativa de **Meme Hunter**, un sistema algorítmico diseñado para capturar movimientos asimétricos en Futuros USDT-M de Binance con apalancamiento aislado 1.0x y microestructura avanzada.

---

## 🗺️ Mapa de Navegación de la Documentación

```
docs/
├── architecture/
│   └── DAS.md                      # Documento de Arquitectura de Software (v4.0)
├── strategy/
│   ├── HYPOTHESIS.md               # Hipótesis Teórica del Edge Estadístico
│   └── SCRUM_PLAN.md               # Plan de Sprints, Product Backlog y Épicas
└── reports/
    ├── PRELIMINARY_REPORT.md       # Reporte Oficial de Backtesting y Stress-Testing
    └── INFORME_FUTUROS_100_USDT.md # Simulación de Viabilidad con 100 USDT y Sizing Asimétrico
```

---

## 📂 Índice de Documentos por Categoría

### 1. 🏛️ Arquitectura del Sistema
* **[DAS.md](architecture/DAS.md) (Documento de Arquitectura de Software v4.0)**
  * **Propósito:** Especificación de la infraestructura en Freqtrade, microservicios satélite y conectividad CCXT.
  * **Puntos clave:** Diseño de ejecución Maker al bid/ask, protecciones de riesgo institucionales (Kill-Switch al 25% DD sobre equidad total viva, Guardián de Funding Rate, salidas técnicas dinámicas y órdenes market de emergencia), y filtros dinámicos de liquidez mínima ($1M USDT en 24h).

### 2. 🧠 Estrategia y Planificación
* **[HYPOTHESIS.md](strategy/HYPOTHESIS.md) (Hipótesis del Edge Cuantitativo)**
  * **Propósito:** Fundamento matemático y financiero del porqué la estrategia genera alfa sobre memecoins.
  * **Puntos clave:** Asimetría de desinflado rápido en rallies agotados (Short Edge) y captura de momentum temprano con volumen inusual (RVOL).
* **[SCRUM_PLAN.md](strategy/SCRUM_PLAN.md) (Plan de Trabajo y Backlog Scrum)**
  * **Propósito:** Hoja de ruta del proyecto organizada por Épicas y Sprints de 1 a 10.
  * **Puntos clave:** Seguimiento del progreso en tiempo real, certificación de alta fidelidad con `--timeframe-detail 1m` (Sprint 9) y salto al **alfa asimétrico puro Short-Only (+63.24% de retorno, Calmar 4.00, Sortino 2.48)** en Sprint 10.

### 3. 📊 Reportes de Investigación y Rendimiento
* **[PRELIMINARY_REPORT.md](reports/PRELIMINARY_REPORT.md) (Reporte de Backtesting Oficial Inicial)**
  * **Propósito:** Análisis exhaustivo inicial sobre Universo Spot histórico y diagnóstico de salidas por MACD.
* **[INFORME_FUTUROS_100_USDT.md](reports/INFORME_FUTUROS_100_USDT.md) (Estudio Integral de Futuros en Memecoins)**
  * **Propósito:** Evaluación empírica de 4 baterías de pruebas en el Top 10 memecoins de Binance Futures.
  * **Puntos clave:** Certificación de 1m, simulación Monte Carlo (2,500 caminos), límites de orden mínima de Binance ($5 USD), y validación de la estrategia **MemeHunterFuturesV1_ShortOnly (+63.24% de beneficio, 8 de 10 monedas ganadoras con +719 USDT)**.

---

## 🎯 Guía de Lectura Recomendada

| Perfil | Ruta de Lectura Sugerida |
| :--- | :--- |
| **Cuantitativo / Trader** | `strategy/HYPOTHESIS.md` ➔ `reports/INFORME_FUTUROS_100_USDT.md` ➔ `reports/PRELIMINARY_REPORT.md` |
| **Ingeniero de Software** | `architecture/DAS.md` ➔ `strategy/SCRUM_PLAN.md` ➔ Scripts en `scripts/` |
| **Operador / DevOps** | `README.md` (raíz) ➔ `architecture/DAS.md` ➔ `scripts/deploy_vps.sh` |
