# 📔 Diario Cuantitativo de Estrategias y Bitácora de Aprendizaje
### Meme Hunter — Hermes Autonomous Quant Research Journal
*Registro institucional continuo de hipótesis económicas, fórmulas matemáticas, backtests y lecciones aprendidas.*

---

## 🧭 Metodología de la Bitácora
Cada iteración o experimento cuantitativo de Hermes se documenta bajo el estándar institucional:
1. **Hipótesis Económica:** Qué ineficiencia o anomalía de microestructura se busca explotar.
2. **Fórmula Simbólica:** Expresión matemática validada mediante el parser AST Zero-Eval.
3. **Métricas Empíricas:** Sharpe Ratio, Win Rate, Expectancy, Max Drawdown y Retorno en datos reales de memecoins (`1000PEPE`, `DOGE`, etc.).
4. **Autopsia & Lección Aprendida:** Diagnóstico técnico del modelo (por qué funcionó o qué sesgo provocó el fallo).
5. **Decisión Operativa:** Descarte, cuarentena, incubación en Sandbox o inyección en vivo a la Arena de Bots.

---

## 📑 Índice de Entradas y Factores Históricos

| ID del Factor / Estrategia | Fecha | Régimen | Sharpe | Win Rate | Veredicto | Despliegue |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| [`BASE_MOONSHOT_10X`](#1-base_moonshot_10x--breakout-de-momentum-con-volumen-anómalo) | 2026-10-15 | ALL_REGIMES | **+4.53** | **48.9%** | 🏆 Récord Base | Base de Bot 3 |
| [`HERMES_ALPHA_05`](#2-hermes_alpha_05--asimetría-de-rango-verdadero-vs-retornos) | 2026-10-15 | RANGE_CHOP | **+8.28** | **52.4%** | 🟢 Promovido | Incubadora HRP |
| [`HERMES_ALPHA_06`](#3-hermes_alpha_06--desbalance-de-volumen-vs-spread-retardado) | 2026-10-15 | RANGE_CHOP | **+3.70** | **50.0%** | 🟢 Promovido | Incubadora HRP |
| [`DIAGNÓSTICO_CHOP_15M`](#4-autopsia-de-régimen-range_chop-en-velas-de-15m) | 2026-10-15 | RANGE_CHOP | N/A | N/A | 💡 Lección Clave | Regla de Síntesis |

---

## 🔬 Entradas Detalladas

### 1. `BASE_MOONSHOT_10X` — Breakout de Momentum con Volumen Anómalo
* **Fecha:** 15 de Octubre de 2026
* **Objetivo Estratégico:** Multiplicar capital de 10 a 100 USDT en 1 semana (+900% ROI).
* **Timeframe:** 15m | **Apalancamiento:** 10.0x aislado.
* **Hipótesis Económica:** En memecoins de alta volatilidad, un quiebre de media móvil rápida (`EMA 8 > EMA 21`) acompañado de volumen explosivo (`RVOL > 1.8x`) sobre el VWAP intradiario indica entrada de liquidez institucional con inercia sostenida de 2 a 4 velas.
* **Fórmula / Lógica:**
  ```python
  long_cond = (
      (close > vwap) &
      (ema_8 > ema_21) &
      (close > ema_8) &
      (rvol > 1.8) &
      (rsi > 52) & (rsi < 75)
  )
  ```
* **Métricas Validadas:**
  * **Sharpe Ratio:** `+4.53`
  * **Win Rate:** `48.9%` (92 operaciones en backtesting PEPE/DOGE)
  * **Retorno Neto:** `+29.45%` (Pico de equity: **21.46 USDT**, +114.6%)
  * **Max Drawdown:** `45.11%` (protegido por Stop Loss duro en -4.5% = -45% de margen)
* **💡 Lección Aprendida:**
  El apalancamiento 10x no tolera stops amplios. Un stop loss de -4.5% combinado con un trailing stop dinámico (+5% activación / retroceso permitido de 2%) permite asegurar ganancias explosivas sin ser barrido prematuramente por el ruido de 15m.
* **Veredicto:** 🏆 **RÉCORD BASE HOMOLOGADO** — Base de referencia para el Bot 3.

---

### 2. `HERMES_ALPHA_05` — Asimetría de Rango Verdadero vs Retornos
* **Fecha:** 15 de Octubre de 2026 (Ciclo Nocturno)
* **Régimen de Mercado:** `RANGE_CHOP` (Rango lateral picado)
* **Hipótesis Económica:** Cuando el rango verdadero (`hl_spread`) se expande más rápido que los retornos direccionales brutos en presencia de volumen creciente, anticipa un breakout inminente por absorción de liquidez pasiva en el libro de órdenes.
* **Fórmula Simbólica:**
  $$\text{log}(\text{volume}) \times (\text{ts\_rank}(\text{hl\_spread}, 8) - \text{ts\_rank}(\text{returns}, 8))$$
* **Métricas Validadas:**
  * **Sharpe Proxy:** `+8.28`
  * **Information Coefficient (IC):** `0.0196` (t-stat > 2.0)
  * **Turnover:** `1.12`
  * **Profundidad AST:** 4 niveles
* **💡 Lección Aprendida:**
  La compresión logarítmica del volumen (`log(volume)`) amortigua el sesgo de picos aislados de volumen en memecoins, permitiendo que la señal sea representativa a lo largo de toda la sesión sin sobredisparos.
* **Veredicto:** 🟢 **PROMOVIDO A CALIDAD DIVERSIDAD (QualityDiversityArchive)**.

---

### 3. `HERMES_ALPHA_06` — Desbalance de Volumen vs Spread Retardado
* **Fecha:** 15 de Octubre de 2026 (Ciclo Nocturno)
* **Régimen de Mercado:** `RANGE_CHOP`
* **Hipótesis Económica:** Mide la aceleración del precio respecto a la apertura normalizada por la volatilidad del volumen relativo (`ts_std(rvol, 10)`). Detecta anomalías de liquidez donde pequeñas órdenes mueven excesivamente el precio por vacío en el libro.
* **Fórmula Simbólica:**
  $$\frac{\text{log}(\text{volume}) \times (\text{ts\_delay}(\text{close}, 3) - \text{open})}{\text{ts\_std}(\text{rvol}, 10) + 10^{-6}}$$
* **Métricas Validadas:**
  * **Sharpe Proxy:** `+3.70`
  * **Information Coefficient (IC):** `0.1302` (predictibilidad positiva consistente)
  * **IC IR (Information Ratio):** `0.6681`
* **💡 Lección Aprendida:**
  Normalizar por `ts_std(rvol, 10)` evita entrar en momentos de volatilidad errática y selecciona momentos donde el volumen es predecible y la liquidez es suficiente para no sufrir slippage en la salida.
* **Veredicto:** 🟢 **PROMOVIDO A LA INCUBADORA HRP**.

---

### 4. Autopsia de Régimen: `RANGE_CHOP` en Velas de 15m
* **Fecha:** 15 de Octubre de 2026
* **Diagnóstico Forense de Hermes:**
  Durante regímenes laterales de memecoins, las fórmulas basadas en momentum simple de cierre (`ts_delta(close, w)` o `close > close.shift(w)`) fallan sistemáticamente con Sharpes negativos (`-0.5` a `-1.5`) y Drawdowns superiores al 80%.
* **Causa Raíz:**
  En 15m, el "whipsaw" (amago y reversión) ocurre con frecuencia en memecoins debido a barridos de liquidez de creadores de mercado. Los breakouts de precio sin confirmación de volumen relativo sostenido son trampas de liquidez.
* **💡 Regla Cuantitativa Adoptada para Hermes:**
  1. Se prohíben fórmulas puramente lineales de precio.
  2. Todo candidato debe incorporar un término de volumen normalizado (`rvol` o `volume / vwap`).
  3. Los cruces deben filtrar con bandas de Bollinger o z-scores temporales (`ts_zscore`) para exigir que la anomalía sea estadísticamente significativa (> 2 desviaciones).

### HERMES_OPT_18 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 16:24:47 UTC` (Ciclo #107)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 8), 12) * ts_rank(rvol, 14) * log(abs(ts_delta(hl_spread, 6)) + 1) / (ts_std(returns, 16) + 1e-6) * ts_decay_linear(rvol, 10) * ts_rank(volume, 12)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+1.81`
  * **Win Rate:** `51.3%` (356 operaciones)
  * **Retorno Proyectado:** `+188.87%`
  * **Drawdown Máximo:** `50.4%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_OPT_19 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 16:24:50 UTC` (Ciclo #107)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 8), 12) * ts_rank(rvol, 14) * log(abs(ts_delta(hl_spread, 6)) + 1) / (ts_std(returns, 16) + 1e-6) * ts_decay_linear(rvol, 10) * ts_rank(volume, 14)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+1.86`
  * **Win Rate:** `51.4%` (353 operaciones)
  * **Retorno Proyectado:** `+193.84%`
  * **Drawdown Máximo:** `50.4%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_OPT_20 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 16:34:41 UTC` (Ciclo #115)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 8), 12) * ts_rank(rvol, 14) * log(abs(ts_delta(hl_spread, 6)) + 1) / (ts_std(returns, 16) + 1e-6) * ts_decay_linear(rvol, 10) * ts_rank(volume, 14) * ts_zscore(hl_spread, 10) * ts_zscore(ts_delta(volume, 10), 20)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+2.21`
  * **Win Rate:** `57.3%` (175 operaciones)
  * **Retorno Proyectado:** `+157.16%`
  * **Drawdown Máximo:** `50.7%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_OPT_21 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 16:34:56 UTC` (Ciclo #115)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 8), 12) * ts_rank(rvol, 14) * log(abs(ts_delta(hl_spread, 6)) + 1) / (ts_std(returns, 16) + 1e-6) * ts_decay_linear(rvol, 10) * ts_rank(volume, 14) * ts_zscore(ts_delta(volume, 10), 20) * ts_zscore(hl_spread, 10) * ts_zscore(ts_delta(volume, 10), 20)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+2.74`
  * **Win Rate:** `60.7%` (162 operaciones)
  * **Retorno Proyectado:** `+225.05%`
  * **Drawdown Máximo:** `43.8%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_OPT_22 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 17:20:55 UTC` (Ciclo #149)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 6), 10) * ts_rank(rvol, 12) * log(abs(ts_delta(hl_spread, 5)) + 1) / (ts_std(returns, 14) + 1e-6) * ts_decay_linear(rvol, 8) * ts_rank(volume, 12) * ts_zscore(hl_spread, 8) * ts_zscore(volume, 10) * ts_zscore(hl_spread, 12)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+2.88`
  * **Win Rate:** `59.0%` (156 operaciones)
  * **Retorno Proyectado:** `+244.59%`
  * **Drawdown Máximo:** `38.8%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_OPT_23 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 17:24:42 UTC` (Ciclo #152)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 6), 10) * ts_rank(rvol, 12) * log(abs(ts_delta(hl_spread, 5)) + 1) / (ts_std(returns, 14) + 1e-6) * ts_decay_linear(rvol, 8) * ts_rank(volume, 12) * ts_zscore(hl_spread, 8) * ts_zscore(volume, 10) * ts_zscore(hl_spread, 12) * ts_zscore(ts_delta(volume, 5), 10)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+3.15`
  * **Win Rate:** `63.8%` (140 operaciones)
  * **Retorno Proyectado:** `+275.38%`
  * **Drawdown Máximo:** `25.1%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_OPT_24 — ⚡ **MEJORA DE SESIÓN EN BOT 3**
* **Fecha de Registro:** `2026-10-15 17:24:48 UTC` (Ciclo #152)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 6), 10) * ts_rank(rvol, 12) * log(abs(ts_delta(hl_spread, 5)) + 1) / (ts_std(returns, 14) + 1e-6) * ts_decay_linear(rvol, 8) * ts_rank(volume, 12) * ts_zscore(hl_spread, 8) * ts_zscore(volume, 10) * ts_zscore(hl_spread, 12) * ts_zscore(ts_delta(volume, 5), 10) * ts_zscore(ts_delta(hl_spread, 5), 10)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+3.39`
  * **Win Rate:** `64.2%` (135 operaciones)
  * **Retorno Proyectado:** `+235.38%`
  * **Drawdown Máximo:** `38.4%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_ATH_25 — 🏆 **NUEVO RÉCORD GLOBAL (ATH)**
* **Fecha de Registro:** `2026-10-15 17:25:58 UTC` (Ciclo #153)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 5)) * ts_zscore(ts_delta(vwap, 6), 12) * ts_rank(rvol, 16) * log(abs(ts_delta(hl_spread, 6)) + 1) / (ts_std(returns, 18) + 1e-6) * ts_decay_linear(rvol, 10) * ts_rank(volume, 14) * ts_zscore(hl_spread, 10) * ts_zscore(volume, 12) * ts_zscore(hl_spread, 14) * ts_zscore(ts_delta(volume, 6), 12) * ts_zscore(ts_delta(hl_spread, 6), 12)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+4.55`
  * **Win Rate:** `61.0%` (140 operaciones)
  * **Retorno Proyectado:** `+373.03%`
  * **Drawdown Máximo:** `32.5%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---

### HERMES_ATH_26 — 🏆 **NUEVO RÉCORD GLOBAL (ATH)**
* **Fecha de Registro:** `2026-10-15 19:10:17 UTC` (Ciclo #238)
* **Régimen Detectado:** `RANGE_CHOP` | **Timeframe:** `15m` | **Apalancamiento:** `10x`
* **Fórmula Matemática:**
```python
sign(ts_delta(close, 4)) * ts_zscore(ts_delta(vwap, 6), 12) * ts_rank(hl_spread, 16) * log(abs(ts_delta(rvol, 5)) + 1) / (ts_std(returns, 20) + 1e-6) * ts_decay_linear(volume, 10) * ts_rank(volume, 12) * ts_zscore(hl_spread, 10) * ts_zscore(volume, 12) * ts_zscore(hl_spread, 14) * ts_zscore(ts_delta(volume, 6), 12) * ts_zscore(ts_delta(hl_spread, 6), 12)
```
* **Métricas de Backtest:**
  * **Sharpe Ratio:** `+4.67`
  * **Win Rate:** `57.3%` (135 operaciones)
  * **Retorno Proyectado:** `+357.60%`
  * **Drawdown Máximo:** `27.1%`
* **Acción Cuantitativa:** Compilado e inyectado en vivo a **Bot 3 (:8083)** en simulación con 10.00 USDT.

---
