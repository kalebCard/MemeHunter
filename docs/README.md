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
  * **Propósito:** Hoja de ruta del proyecto organizada por Épicas y Sprints de 1 a 16.
  * **Puntos clave:** Auditoría de estado real, Sprints 12-13 (Auction Theory & Estacionalidad Humana), Sprint 14 (Micro-Capital 100 USDT Compounding), Sprint 15 (V5 Leverage +96.20% neto, Calmar 21.03) y Sprint 16 (Auditoría Forense de Salidas).
* **[PLAN_ESCALADO_100_A_1000_USDT.md](strategy/PLAN_ESCALADO_100_A_1000_USDT.md) (Plan de Escalado Exponencial 10X)**
  * **Propósito:** Modelo cuantitativo para multiplicar una cuenta de 100 a 1,000 USDT en Binance Futures mediante Half-Kelly fraccional y apalancamiento dinámico 1.5x - 2.0x.
* **[PLAN_IMPLEMENTACION_V6_APEX.md](strategy/PLAN_IMPLEMENTACION_V6_APEX.md) (Plan de Implementación y Hardening)**
  * **Propósito:** Especificación técnica de ingeniería para erradicar fugas de capital y optimizar la microestructura.

### 3. 📊 Reportes de Investigación y Rendimiento
* **[PRELIMINARY_REPORT.md](reports/PRELIMINARY_REPORT.md) (Reporte de Backtesting Oficial Inicial)**
  * **Propósito:** Análisis exhaustivo inicial sobre Universo Spot histórico y diagnóstico de salidas por MACD.
* **[INFORME_FUTUROS_100_USDT.md](reports/INFORME_FUTUROS_100_USDT.md) (Estudio Integral de Futuros en Memecoins)**
  * **Propósito:** Evaluación empírica de micro-capital, límites de orden mínima de Binance ($5 USD), y validación de la estrategia de interés compuesto.
* **[REPORTE_EJECUTIVO_MEME_HUNTER_V4.md](reports/REPORTE_EJECUTIVO_MEME_HUNTER_V4.md) (Reporte Ejecutivo para Inversores)**
  * **Propósito:** Resumen ejecutivo de alto nivel de los resultados certificados en Docker.

---

## 🎯 Guía de Lectura Recomendada

| Perfil | Ruta de Lectura Sugerida |
| :--- | :--- |
| **Cuantitativo / Trader** | `strategy/HYPOTHESIS.md` ➔ `reports/INFORME_FUTUROS_100_USDT.md` ➔ `reports/PRELIMINARY_REPORT.md` |
| **Ingeniero de Software** | `architecture/DAS.md` ➔ `strategy/SCRUM_PLAN.md` ➔ Scripts en `scripts/` |
| **Operador / DevOps** | `README.md` (raíz) ➔ `architecture/DAS.md` ➔ `scripts/deploy_vps.sh` |
