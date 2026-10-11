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
  * **Propósito:** Hoja de ruta del proyecto organizada por Épicas y Sprints de 1 a 9.
  * **Puntos clave:** Seguimiento del progreso en tiempo real, historias de usuario completadas (`PB-01` a `PB-27` incluyendo Hardening de Producción Real) y estado de despliegue en Dry-Run y VPS.

### 3. 📊 Reportes de Investigación y Rendimiento
* **[PRELIMINARY_REPORT.md](reports/PRELIMINARY_REPORT.md) (Reporte de Backtesting Oficial)**
  * **Propósito:** Análisis exhaustivo de 1,439 trades sobre datos históricos sin sesgo de supervivencia.
  * **Puntos clave:** Resultados iniciales del motor simétrico, desglose mes a mes y análisis de distribución de retornos.
* **[INFORME_FUTUROS_100_USDT.md](reports/INFORME_FUTUROS_100_USDT.md) (Estudio de Viabilidad con 100 USDT)**
  * **Propósito:** Evaluación empírica de 4 baterías de pruebas con capital real mínimo de 100 USDT.
  * **Puntos clave:** Simulación Monte Carlo (7,500 caminos), límites de orden mínima de Binance ($5 USD), y validación de la optimización con **dimensionamiento asimétrico (+65.50% de retorno neto, Sortino 1.92, Max DD 21.03%)**.

---

## 🎯 Guía de Lectura Recomendada

| Perfil | Ruta de Lectura Sugerida |
| :--- | :--- |
| **Cuantitativo / Trader** | `strategy/HYPOTHESIS.md` ➔ `reports/INFORME_FUTUROS_100_USDT.md` ➔ `reports/PRELIMINARY_REPORT.md` |
| **Ingeniero de Software** | `architecture/DAS.md` ➔ `strategy/SCRUM_PLAN.md` ➔ Scripts en `scripts/` |
| **Operador / DevOps** | `README.md` (raíz) ➔ `architecture/DAS.md` ➔ `scripts/deploy_vps.sh` |
