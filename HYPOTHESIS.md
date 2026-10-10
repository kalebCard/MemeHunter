# Hipótesis de Edge: Estrategia MemeHunterV1

Este documento formaliza la hipótesis detrás de la estrategia base, cumpliendo el requisito del DAS (§3.2) de evitar el *data snooping* (ajustar indicadores hasta ver qué funciona en el pasado).

## 1. Universo y Marco Temporal
- **Universo (U1)**: Top 30 monedas por volumen en Binance Spot (dinámico mensual).
- **Timeframe**: 4 horas (4h).

## 2. Hipótesis Teórica (El "Por qué")
**El mercado de criptomonedas exhibe un comportamiento de fuerte inercia (momentum) direccional.** A diferencia de los mercados de acciones tradicionales (que tienden a la reversión a la media a corto plazo), las altcoins de alto volumen experimentan tendencias parabólicas impulsadas por el sentimiento y la liquidez. 

Nuestra ventaja (edge) consiste en **capturar el "cuerpo central" de estas tendencias, entrando solo cuando hay confirmación de expansión de volatilidad, y cortando las pérdidas rápidamente**.

### 2.1 Lógica de los Indicadores
1.  **MACD (Moving Average Convergence Divergence)**: Define la dirección y el momentum primario. Buscamos el inicio de una tendencia alcista (cruce al alza).
2.  **ATR (Average True Range)**: Mide la volatilidad absoluta. Un MACD cruzando al alza en un mercado "muerto" (ATR bajo/contrayéndose) suele ser una señal falsa. Exigimos que el ATR esté **expandiéndose** (ej. ATR actual > SMA(ATR, 14)) para confirmar que hay interés real en el movimiento.
3.  **RSI (Relative Strength Index)**: Filtro de agotamiento. No queremos comprar una moneda que ya ha subido un 50% en línea recta. El RSI debe estar en zona neutral/alcista pero **no sobrecomprado** (ej. 50 < RSI < 70) en el momento de la entrada.

## 3. Reglas de Operación (Reglas Deterministas)

### Entrada (Long)
Una operación se abre si y solo si ocurren simultáneamente:
1.  **El par está en el Universo Válido** para el mes en curso.
2.  **Momentum**: MACD línea principal > Señal MACD (idealmente cruce reciente).
3.  **Volatilidad**: El ATR de 14 periodos es mayor que su media móvil de 14 periodos.
4.  **Agotamiento**: RSI(14) > 50 (tendencia alcista) pero RSI(14) < 70 (no sobrecomprado).

### Salida y Gestión de Riesgo (Exit / Stop)
-   **Stop Loss (Dinámico por Volatilidad)**: No usamos un % fijo. El Stop Loss inicial se coloca a `Precio de Entrada - (2 * ATR)`. Esto da espacio para respirar a las monedas volátiles y aprieta el stop en monedas lentas.
-   **Trailing Stop**: Una vez que la operación alcanza un ROI del `1 * ATR`, el trailing stop se activa para proteger ganancias (breakeven + comisiones).
-   **Salida por Señal**: Se vende inmediatamente si el MACD cruza a la baja, independientemente de si hay ganancias o pérdidas.

## 4. Criterios de Aprobación (Revisión de Fase 0)
Tras aplicar escenarios de costes **adversos** (slippage y spread amplios):
-   **Expectancy neta**: > 0 (Cada operación, en promedio, debe ganar dinero tras comisiones/slippage).
-   **Profit Factor**: ≥ 1.3
-   **Sortino Ratio**: ≥ 1.0 (Penaliza la volatilidad a la baja).
-   **Consistencia**: Debe superar el rendimiento de "Buy & Hold" de BTC en el mismo periodo.

Si el backtest en U1 (Líquido) de 2020 a 2026 no cumple estos criterios, la hipótesis es **rechazada**. No se optimizará obsesivamente (hyperopt) para forzar los números; se diseñará una Hipótesis V2.
