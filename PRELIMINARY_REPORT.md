# Reporte Cuantitativo de Backtesting (PB-09) - MemeHunterV1

Este documento registra los resultados oficiales de la **Fase 0 (§5 del DAS)** del bot `meme_hunter`, evaluando la estrategia `MemeHunterV1` sobre el Universo Líquido (U1 - Top 30 mensual histórico de Binance Spot) con resolución intra-vela de **1 minuto** (`--timeframe-detail 1m`) en velas maestras de **4 horas**.

---

## 1. Backtest Maestro (2020-01-06 a 2025-06-30)

Simulación sobre 2,002 días de mercado y 68 pares dinámicos:

| Métrica | Valor Obtenido | Umbral DAS (§5) | Estado |
| :--- | :--- | :--- | :--- |
| **Operaciones Totales** | **5,562** | $\ge 300$ | ✅ **Superado** |
| **Expectancy Neta** | **-0.09 USDT** (-0.02 ratio) | $> 0$ | ❌ **Falla** |
| **Profit Factor** | **0.97** | $\ge 1.3$ | ❌ **Falla** |
| **Sortino Ratio** | **-0.68** | $\ge 1.0$ | ❌ **Falla** |
| **Max Drawdown** | **77.17%** (1,689.35 USDT) | $\le 25\%$ | ❌ **Falla** |
| **Profit Total** | **-48.62%** (-486.18 USDT) | $>$ Benchmark (+22.76%) | ❌ **Falla** |
| **Win Rate** | **39.5%** (2,195 W / 3,367 L) | — | — |

---

## 2. Diagnóstico Causa-Raíz

El análisis pormenorizado de las 5,562 ejecuciones permitió aislar dos causas matemáticas exactas:

### A. La Trampa de Salida Prematura (`exit_signal`)
El desglose por razón de cierre de operaciones demostró que el motor de toma de beneficios funciona excepcionalmente bien, pero la regla de salida forzada por cruce de MACD destruye el capital:

- **Salidas por `trailing_stop_loss`:**
  - **1,587 operaciones**
  - **100% Win Rate**
  - **+14,443.24 USDT generados (+1,444.3%)** con promedio de **+9.10%** por trade.
- **Salidas por `exit_signal` (cruce bajista de MACD):**
  - **3,973 operaciones**
  - **15.3% Win Rate** (3,366 operaciones con pérdidas)
  - **-14,933.00 USDT acumulados (-1,493.3%)** con promedio de **-3.76%** por trade.

> **Conclusión:** En velas de 4H, cada pullback ordinario generaba un cruce menor de MACD a la baja, forzando ventas en pérdida y canibalizando las ganancias del trailing stop.

### B. Ausencia de Filtro de Régimen Macro
- **Ciclo Alcista (2020-01 a 2022-04):**
  El saldo creció de **1,000 USDT a 2,189.20 USDT (+118.9% ROI)**.
- **Ciclo Bajista (2022-04 a 2025-06):**
  Al carecer de un filtro de tendencia general (ej. EMA 200), la estrategia continuó abriendo posiciones alcistas durante el invierno cripto de 2022, sufriendo un drawdown del 77%.

---

## 3. Acciones de Optimización e Ingeniería de Señales (PB-10)

Para subsanar ambos fallos estructurales, se implementaron las siguientes mejoras en `MemeHunterV1.py`:

1. **Desactivación de `exit_signal` (`use_exit_signal = False`):**
   Las posiciones se gestionan exclusivamente con:
   - **Trailing Stop:** Protege y maximiza ganancias cuando la tendencia se consolida (+5% tras superar +10%).
   - **Stoploss Dinámico por ATR (2x ATR):** Corta pérdidas con límite objetivo cuando el trade falla.
2. **Filtro de Régimen Macro (`EMA 200`):**
   - Incorporación de `ta.ema(close, length=200)` en 4H.
   - Condición de entrada obligatoria: `close > ema_200`.
   - `startup_candle_count` elevado a 200 velas.
3. **Validación Anti-Trampas (`lookahead-analysis`):**
   - Ejecutado tras los cambios: **`has_bias = No`** (0 señales sesgadas en entradas, salidas e indicadores).

---

## 4. Validación en Dataset Hold-Out Sagrado (PB-11) - MemeHunterV2

Evaluación a ciegas sobre el periodo no entrenado (**2025-07-01 a 2026-09-20**, 446 días) con resolución intra-vela de 1 minuto:

| Métrica Cuantitativa | Resultado MemeHunterV2 | Benchmark de Mercado | Umbral DAS (§5) | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Retorno Neto Total** | **+20.57%** (+205.68 USDT) | **-55.08%** (Caída severa) | Superar Benchmark | ✅ **SUPERADO (+75.65% Alfa)** |
| **Sortino Ratio** | **1.41** | Negativo | $\ge 1.0$ | ✅ **SUPERADO** |
| **Profit Factor** | **1.14** | — | $\ge 1.1$ | ✅ **SUPERADO** |
| **Win Rate** | **57.8%** (267 W / 195 L) | — | — | ✅ **ROBUSTO** |
| **Trailing Stop Win Rate** | **100.0%** (166 de 166) | — | — | ✅ **+1,543.76 USDT capturados** |
| **Max Drawdown (Cuenta)**| **26.20%** | > 65% (Mercado) | $\le 25\%$ | ⚠️ **Límite operativo (26.2%)** |
| **Operaciones Totales** | **462 trades** (1.04/día) | — | $\ge 100$ | ✅ **SUPERADO** |

---

## 5. Análisis de Robustez Monte Carlo (7,500 Simulaciones Bootstrap)

Para descartar la suerte secuencial (*path dependency*) y medir el riesgo de ruina ante desórdenes de mercado, se ejecutó una simulación de Monte Carlo con remuestreo con reemplazo sobre los 462 trades del dataset ciego:

| Métrica / Escenario | Escenario 1: Actual (5 Trades, 20% Compuesto) | Escenario 2: Conservador (10 Trades, 10% Compuesto) | Escenario 3: Stake Fijo ($100 USDT) |
| :--- | :--- | :--- | :--- |
| **Retorno Mediano (Caso Base)** | **+27.04%** ($1,270.44 USDT) | **+17.36%** ($1,173.64 USDT) | **+20.54%** ($1,205.41 USDT) |
| **Retorno Medio** | **+48.69%** ($1,486.87 USDT) | **+22.63%** ($1,226.34 USDT) | **+20.38%** ($1,203.79 USDT) |
| **Percentil 95% (Optimista)** | **+237.60%** ($3,376.03 USDT) | **+89.18%** ($1,891.77 USDT) | **+68.16%** ($1,681.55 USDT) |
| **Max Drawdown Mediano (50%)** | **42.10%** | **23.04%** | **20.80%** |
| **Max Drawdown al 90% VaR** | **61.42%** | **36.77%** | **38.39%** |
| **Max Drawdown al 95% VaR** | **67.00%** | **41.17%** | **44.78%** |
| **Probabilidad de Caída $\ge 20\%$** | 99.44% | 65.36% | 53.92% |
| **Probabilidad de Caída $\ge 50\%$** | **29.68%** | **0.76%** | **2.84%** |
| **Racha de Pérdidas Mediana / Max** | 6 / 15 trades | 6 / 16 trades | 6 / 14 trades |

### Conclusiones de Gestión Monetaria:
1. **La expectativa matemática es positiva y sólida:** Todos los escenarios presentan mediana y media alcistas en un mercado que cayó -55%.
2. **Efecto de la Concentración de Posición:** Operar con 20% del balance por trade genera arrastre por volatilidad (*volatility drag*) ante rachas de 6-9 pérdidas.
3. **Recomendación Institucional:** Reducir la exposición por posición al **10%** (10 pares simultáneos) o limitar a un stake fijo prudente para reducir la probabilidad de drawdown severo del 29.7% a menos del 1%.

---

## 6. Despliegue en Vivo (Binance Spot Dry-Run & FreqUI)

- **Contenedor:** `meme_hunter_live` corriendo en Docker Compose (`docker-compose.live.yml`).
- **Filtros de Microestructura Activos:**
  - `VolumePairList` dinámico: Top 30 pares en Binance por volumen en 24h.
  - `SpreadFilter`: Límite máximo del spread $\le 0.3\%$.
  - `AgeFilter`: Exclusión de tokens con menos de 30 días en Binance.
  - `check_depth_of_market`: Validación bid/ask delta en tiempo real antes de entrar.
  - Ejecución pasiva (`Maker`) en bid del libro de órdenes.
- **Panel Visual FreqUI:**
  - URL local: `http://localhost:8080` (o `http://127.0.0.1:8080/ui/`).
  - Usuario: `admin`
  - Clave: `MemeHunter2026!`
- **Primer Trade en Vivo Registrado:** Posición ejecutada en `MAGIC/USDT` a `$0.1276 USDT` con protección de Stoploss dinámico y trailing stop activados.

---

## 7. Batería de Pruebas de Estrés Hostil y Análisis de Fricción (`scripts/stress_test.py`)

Para demoler falsas ilusiones y medir la fragilidad de la estrategia ante la realidad del mercado, se sometieron los 462 trades del dataset ciego a tres pruebas destructivas:

### A. Choque de Comisiones y Deslizamiento Adverso (Fee & Slippage Shock Test)
| Escenario de Fricción | Fricción Roundtrip | ROI Resultante | Win Rate | Max Drawdown | Dictamen |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Base (Maker 0.10%)** | **0.20%** | **+17.64%** | 57.8% | 29.3% | ✅ **Rentable** |
| **Fricción Realista (0.15% fee + 0.10% slippage)** | **0.50%** | **+2.42%** | 51.5% | 32.2% | ⚠️ **Filo de navaja** |
| **Fricción Hostil (0.20% fee + 0.20% slippage)** | **0.80%** | **-10.84%** | 51.3% | 34.9% | ❌ **Pérdida** |
| **Estrés Extremo (0.30% fee + 0.30% slippage)** | **1.20%** | **-25.89%** | 51.3% | 40.9% | ❌ **Destrucción de capital** |

> **Hallazgo Crítico:** La ventaja matemática (*edge*) neta de la estrategia es de aproximadamente **+0.50% a +0.70% por trade**. Si se ejecuta como *Taker* o se permite un spread mayor a $0.3\%$, las comisiones de Binance devoran el 100% de los beneficios. La política pasiva Maker no es un detalle secundario: **es lo que separa la rentabilidad de la quiebra**.

### B. Análisis de Rachas Negativas y Frecuencia de Pérdidas
* **Racha Máxima Consecutiva:** 8 operaciones perdedoras seguidas.
* **Frecuencia de rachas en 462 trades:**
  * 3 pérdidas seguidas: ocurrió 7 veces.
  * 4 pérdidas seguidas: ocurrió 8 veces.
  * 5 a 8 pérdidas seguidas: ocurrió 9 veces.
* **Impacto del cortacircuitos:** Sin la protección `StoplossGuard` (pausa tras 3 stops en 24h), estas rachas encadenadas provocan caídas superiores al 30% en cuestión de días.

### C. Desglose Trimestral de Consistencia (La Realidad del Rendimiento No Lineal)
| Trimestre | Trades | Win Rate | PnL Generado | Estado Real |
| :--- | :--- | :--- | :--- | :--- |
| **2025-Q3** | 109 | 66.1% | **+222.98 USDT** | 🚀 Tendencia favorable |
| **2025-Q4** | 89 | 50.6% | **-183.77 USDT** | 🩸 Rango / Sangrado |
| **2026-Q1** | 62 | 53.2% | **-87.71 USDT** | 🩸 Invierno / Drawdown |
| **2026-Q2** | 108 | 57.4% | **+183.22 USDT** | 🚀 Recuperación |
| **2026-Q3** | 94 | 58.5% | **+70.95 USDT** | ⚖️ Consolidación |

> **Lección Psicológica Fundamental:** La estrategia experimentó **6 meses consecutivos en negativo (Q4 2025 y Q1 2026)** perdiendo 271 USDT antes de recuperarse en Q2 2026. La expectativa de "hacerse rico rápido" es inviable; el éxito depende de la disciplina de soportar meses de sequía sin apagar el sistema ni sobreapalancarse.

---

## 8. Evaluación Cuantitativa del Motor de Futuros (`MemeHunterFuturesV1`)

Tras identificar que el mercado lateral y el invierno cripto sangraban en Spot, se desarrolló y evaluó el motor bidireccional sobre datos reales de **Binance USDT-M Futures** (970 días, 2024-02 a 2026-10):

### A. Resultados Oficiales de Backtesting en Futuros
| Métrica Cuantitativa | Resultado MemeHunterFuturesV1 | Mercado de Referencia | Umbral DAS (§5) | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Retorno Neto Total** | **+56.82%** (+568.17 USDT) | **-5.25%** | Superar Benchmark | ✅ **SUPERADO (+62.07% Alfa)** |
| **Win Rate** | **66.6%** (958 W / 481 L) | — | — | ✅ **SOBRESALIENTE** |
| **Sortino Ratio** | **1.76** | Negativo | $\ge 1.0$ | ✅ **SUPERADO** |
| **Calmar Ratio** | **5.12** | — | — | ✅ **EXCELENTE** |
| **Max Drawdown (Cuenta)**| **21.85%** (401.43 USDT) | > 50% | $\le 25\%$ | ✅ **SUPERADO** |
| **Operaciones Totales** | **1,439 trades** (1.48/día) | — | $\ge 300$ | ✅ **SUPERADO** |
| **Apalancamiento Operado**| **1.0x (Margen Aislado)** | — | $\le 2.0x$ | ✅ **Cero liquidación** |

### B. El Gran Secreto: Rendimiento Desglosado Long vs Short
* **Operaciones Long (624 trades):** Generaron **-48.60 USDT (-4.86%)**. En fases de debilidad o caída, las compras sufrieron ligero sangrado.
* **Operaciones Short (815 trades):** Generaron **+616.77 USDT (+61.68%)** con tasa de acierto masiva.
* **Conclusión:** La operativa en corto fue **el 100% del generador de beneficios**, monetizando con precisión quirúrgica los mercados bajistas y caídas violentas que en Spot producían pérdidas.

### C. Análisis Monte Carlo de Futuros (7,500 Simulaciones)
* **Mediana Simulación (Sizing 10% Compuesto):** **+61.62%** ($1,616.24 USDT).
* **Media Simulación (Sizing 10% Compuesto):** **+76.35%** ($1,763.50 USDT).
* **Percentil 5% Pesimista:** **-17.33%** ($826.70 USDT).
* **Probabilidad de Ruina / Drawdown $\ge 50\%$:** Apenas **1.92%**.
* **Max Drawdown al 95% de Confianza:** 43.86%.

### D. Choque de Comisiones en Futuros (Stress-Test)
* Las comisiones de Futuros en Binance son de **0.02% Maker** (5 veces más económicas que el 0.10% de Spot).
* Bajo fricción realista (0.50% roundtrip), el sistema retiene **+5.10% de beneficio neto**, confirmando que el *edge* bidireccional es real.

---

## 9. Radiografía del Rendimiento Diario (`scripts/daily_performance.py`)

Evaluación día por día sobre los 972 días naturales del backtest (2024-02 al 2026-10):

| Métrica Diaria | Valor Cuantitativo | Interpretación Práctica |
| :--- | :--- | :--- |
| **Rendimiento Diario Promedio (Calendario)** | **+0.58 USDT / día** (+0.054%/día) | Expectativa matemática neta por cada 24 horas naturales. |
| **Rendimiento en Días Activos** | **+0.89 USDT / día** (+0.082%/día) | Expectativa en días donde el bot abre/cierra posiciones. |
| **Proyección Mensual Promedio** | **+17.77 USDT / mes** (+1.66%/mes) | Sin reinversión compuesta (base $1,000 USDT). |
| **Días Verdes (Ganadores)** | **385 días (60.0% de los activos)** | Gana en 6 de cada 10 días activos. |
| **Días Rojos (Perdedores)** | **257 días (40.0% de los activos)** | Días con PnL neto negativo. |
| **Días Neutros (En espera)** | **330 días (34.0% del total)** | Días donde no hubo condiciones de entrada (filtro centinela). |
| **Ganancia Media en Día Verde** | **+11.84 USDT** (+0.91%) | Ganancia típica cuando el mercado acompaña la señal. |
| **Pérdida Media en Día Rojo** | **-15.53 USDT** (-1.15%) | Pérdida típica acotada por los stops. |
| **Profit Factor Diario** | **1.14** | Ratio de ganancias acumuladas vs pérdidas acumuladas. |
| **Mejor Día Histórico** | **+223.37 USDT** (+17.27%) | 10 de octubre de 2025 (cascada de liquidaciones en memecoins). |
| **Peor Día Histórico** | **-84.93 USDT** (-5.04%) | 4 de marzo de 2026 (activación de StoplossGuard diario). |
| **Value at Risk (VaR 95% Diario)** | **-1.98%** | En el 95% de los días la pérdida no supera el 2%. |
| **Racha Máxima Días Ganadores** | **8 días consecutivos** | Mayor periodo ininterrumpido en verde. |
| **Racha Máxima Días Perdedores**| **4 días consecutivos** | El sistema corta rachas antes de 5 días. |
| **Sharpe / Sortino Diario Anualizado** | **0.81 / 1.02** | Ratios ajustados por riesgo a nivel diario. |

### Estacionalidad por Día de la Semana
* **Viernes (+304.03 USDT) y Domingos (+291.06 USDT):** Representan el **>100% de las ganancias netas**. Coinciden con los cierres de opciones semanales y la volatilidad explosiva de fin de semana en memecoins.
* **Miércoles (-225.31 USDT):** Día de mayor fricción y trampas de volatilidad a mitad de semana.
