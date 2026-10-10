# Plan de Desarrollo Scrum: meme_hunter

Este documento organiza el desarrollo del bot de trading **meme_hunter** (basado en la Arquitectura DAS v3.1) utilizando la metodología Scrum. Dado que el proyecto prioriza la validación empírica antes del despliegue real, los Sprints están enfocados en entregar valor medible (resultados estadísticos) lo antes posible.

---

## 1. Visión del Producto y Épicas

**Visión:** Construir un sistema de trading automatizado basado en Freqtrade que demuestre rentabilidad matemática en un universo específico de criptomonedas (Líquido o Memes) antes de arriesgar capital real.

**Épicas (Grandes bloques de trabajo):**
1. **Épica 1: Infraestructura de Datos (Fundación).** Conseguir datos limpios, de alta granularidad y sin sesgo de supervivencia.
2. **Épica 2: Desarrollo y Backtesting de Estrategia.** Definir la hipótesis, programar indicadores y validar rigurosamente en backtest.
3. **Épica 3: Simulación en Vivo (Paper Trading).** Despliegue seguro en la nube operando contra mercado real sin capital.
4. **Épica 4: Paso a Producción (Capital Real).** Gestión estricta de riesgo y ejecución real con capital acotado.

---

## 2. Product Backlog (Priorizado)

| ID | Historia de Usuario / Tarea Técnica | Épica | Estimación (Puntos) |
|---|---|---|---|
| PB-01 ✅ | Inicializar proyecto Freqtrade y repositorio Git. | 1 | 2 |
| PB-02 ✅ | Desarrollar script para descargar y formatear datos de `data.binance.vision`. | 1 | 5 |
| PB-03 ✅ | Desarrollar filtro de Universo Dinámico (Top N histórico sin sesgo). | 1 | 8 |
| PB-04 ✅ | Descargar dataset completo (1m y 4h/1d) y auditar calidad. | 1 | 3 |
| PB-05 ✅ | Redactar Hipótesis de Edge y umbrales numéricos de aceptación. | 2 | 2 |
| PB-06 ✅ | Programar `IStrategy` inicial (MACD, RSI, ATR). | 2 | 5 |
| PB-07 ✅ | Configurar protecciones nativas (Stoploss, MaxDrawdown, etc.). | 2 | 3 |
| PB-08 ✅ | Ejecutar análisis *lookahead-bias* y *recursive-analysis*. | 2 | 3 |
| PB-09 | Realizar backtest sobre U1 (Líquido) y evaluar contra Benchmark. | 2 | 5 |
| PB-10 | Realizar optimización controlada (`hyperopt`) si es necesario. | 2 | 5 |
| PB-11 | Validar estrategia en datos Hold-Out (Prueba final). | 2 | 3 |
| PB-12 | Configurar servidor remoto para Dry-Run. | 3 | 5 |
| PB-13 | Integrar bot de Telegram para notificaciones. | 3 | 2 |
| PB-14 | Monitorear y evaluar Dry-Run (8 semanas) vs Backtest. | 3 | 8 |
| PB-15 | Implementar "Kill-Switch" y lógica de límite dinámico de riesgo. | 4 | 5 |
| PB-16 | Configurar API Keys de producción y lanzar Fase 2. | 4 | 3 |

---

## 3. Planificación de Sprints (Sprints de 1-2 semanas)

### Sprint 1: Fundación y Datos Sin Sesgo
**Objetivo del Sprint:** Tener el entorno listo y el dataset histórico (sin sesgo de supervivencia) preparado para backtesting.
*   **PB-01:** Inicializar proyecto Freqtrade y repositorio Git.
*   **PB-02:** Script de descarga de datos (`data.binance.vision`).
*   **PB-03:** Desarrollo del Universo Dinámico (Top N histórico).
*   **PB-04:** Descarga masiva y auditoría de datos.
*   **Entregable (Incremento):** Base de datos histórica validada y estructura de carpetas de Freqtrade lista.

**Progreso y hallazgos del Sprint 1:**
*   PB-01 y PB-02 terminados (decisiones: Docker con Freqtrade 2026.9 fijado, datos en `C:/meme_hunter_data`, histórico desde 2020-01, N=30).
*   PB-03 terminado: script `build_universe.py` genera un mapa temporal (mes a mes) del Top 30 sin lookahead bias. La estrategia `MemeHunterV1` carga este mapa y anula las señales de los pares que no están en el universo válido para el mes en curso. Freqtrade procesa pares inactivos correctamente con `allow_inactive: true`.
*   PB-04 terminado: Se excluyó `LUNAUSDT` (y estables) mediante blacklist rígida para evitar anomalías. Se escribió el script `download_target.py` que descarga 1m y 4h selectivamente solo para el Top 30.

### Sprint 2: Primera Estrategia y Validación Inicial
**Objetivo del Sprint:** Programar la lógica base y correr los primeros backtests rigurosos.
*   **PB-05 ✅:** Redactar Hipótesis de Edge (`HYPOTHESIS.md`).
*   **PB-06 ✅:** Programar `IStrategy` inicial (`MemeHunterV1.py`).
*   **PB-07 ✅:** Configurar protecciones nativas (Cooldown, StoplossGuard, MaxDrawdown, LowProfitPairs).
*   **PB-08 ✅:** Ejecutar `lookahead-analysis` y `recursive-analysis` de Freqtrade.
*   **Entregable (Incremento):** Estrategia codificada, robusta contra trampas lógicas, lista para PB-09.

**Progreso y hallazgos del Sprint 2:**
*   PB-05 y PB-06: La hipótesis se basa en Momentum (MACD) + Expansión de Volatilidad (ATR) + Filtro de Agotamiento (RSI). El Stop Loss es dinámico (2x ATR de la entrada).
*   PB-07: Freqtrade aceptó la configuración de protecciones.
*   PB-08: El `lookahead-analysis` arrojó "No bias detected". Las matemáticas son válidas.
*   *Test Preliminar:* Un dry-test en 2021 sobre BTC y LUNA confirmó que el pipeline funciona y el sistema genera ganancias marginales (Expectancy de 0.13), pero el Profit Factor (1.05) no alcanzó el objetivo. El siguiente paso en el Sprint 3 es ejecutar PB-09 con todos los datos y analizar si es necesaria la hiper-optimización (PB-10).

### Sprint 3: La Prueba de Fuego (Evaluación Estadística)
**Objetivo del Sprint:** Saber estadísticamente si la estrategia sirve o se descarta.
*   **PB-09:** Backtest completo en U1 y comparación vs Buy&Hold.
*   **PB-10:** Optimización de hiperparámetros acotada (opcional/limitada).
*   **PB-11:** Prueba final con el conjunto de retención (Hold-out).
*   **Entregable (Incremento):** Reporte cuantitativo de resultados. **Decisión GO/NO-GO para la Fase 1.**

### Sprint 4: Infraestructura Cloud y Dry-Run
**Objetivo del Sprint:** Desplegar el bot de forma segura en la nube para simulación en vivo.
*   *(Condicionado a aprobar el Sprint 3)*
*   **PB-12:** Instalar Freqtrade en VPS Linux.
*   **PB-13:** Conectar notificaciones por Telegram.
*   **PB-14 (Inicio):** Iniciar el Dry-Run.
*   **Entregable (Incremento):** Bot operando 24/7 en la nube generando señales y operaciones simuladas.

---

## 4. Definición de Hecho (Definition of Done - DoD)
Para que una tarea se considere terminada debe cumplir:
1. El código está en el repositorio Git (no hay nada "solo local").
2. Cumple con los criterios de aceptación del DAS (ej. escenarios de costes adversos aplicados en el backtest).
3. No rompe la ejecución básica de Freqtrade (`freqtrade backtesting` corre sin errores).
4. La documentación pertinente ha sido actualizada.

## 5. Ceremonias (Adaptación para IA-Humano)
Aunque el desarrollo lo hagamos nosotros dos (Tú y yo, el asistente), mantendremos el ritmo:
*   **Sprint Planning:** Al inicio de cada fase, confirmamos las tareas a realizar.
*   **Daily Async:** Cuando retomes el trabajo, te daré un resumen rápido de dónde nos quedamos.
*   **Sprint Review:** Al terminar un Sprint, revisamos los resultados (ej. el reporte de backtest) antes de avanzar.
*   **Retrospectiva:** Evaluamos si las reglas del DAS están funcionando o si necesitamos ajustar el enfoque.
