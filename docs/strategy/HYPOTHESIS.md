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

## 5. Hipótesis V3: Alfa Asimétrico por Desinflado de Memecoins (Sprint 10)

La investigación empírica sobre las 10 principales memecoins de Binance Futures demostró que la hipótesis de *momentum alcista simétrico* falla en memecoins por una razón estructural de microestructura:
> **Las memecoins carecen de valor intrínseco o flujos de caja.** Tras un rally eufórico de 3 a 7 días impulsado por viralidad en redes, entran en un régimen secular de desinflado y distribución que dura semanas y meses, perdiendo entre un 80% y un 95% de su valor.

### 5.1 El Edge Asimétrico Comprobado
1. **Compras (Longs = Ruido y Trampas):** Intentar comprar rebotes o rupturas en memecoins expone el capital a falsas rupturas (*bull traps*) y sangrado continuo. En el backtest oficial de alta fidelidad, los Longs restaron capital constantemente (-48.11 USDT).
2. **Ventas en Corto (Shorts = Ventaja Estadística Pura):** Entrar en Short cuando el precio rompe a la baja la EMA 200 en velas de 4h (con MACD bajo cero y RSI entre 24 y 44) captura el colapso gravitacional natural de los tokens especulativos.
3. **Inmunidad a la Liquidación:** Al operar exclusivamente con **apalancamiento aislado 1.0x** y un stoploss duro del 10%, el sistema elimina el riesgo de liquidación catastrófica ante repuntes violentos (*short squeezes*).
4. **Validación Cuantitativa Oficial:**
   - La estrategia **`MemeHunterFuturesV1_ShortOnly`** generó **+63.24% de retorno neto (+632.40 USDT)** sobre 1,000 USDT base, con un **Calmar Ratio de 4.00**, **Sortino de 2.48** y **Sharpe de 1.11**, con 8 de los 10 pares ganadores (+719.85 USDT acumulados).

