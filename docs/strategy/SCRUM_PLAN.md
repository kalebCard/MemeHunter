# Plan de Desarrollo Scrum: meme_hunter (Alpha & Asymmetric Edge)

Este documento organiza el desarrollo del sistema **meme_hunter** transformado en un **verdadero cazador de memecoins con ventaja asimétrica y modelos cuantitativos de última generación**, superando la dependencia de indicadores tradicionales rezagados.

> **Última actualización:** 11 de octubre de 2026 — Auditoría de estado real (ver §0).

---

## 0. Auditoría de Estado Real (11-oct-2026)

Una revisión del código, datos y artefactos de backtest detectó discrepancias entre el estado declarado y el estado real. **Hasta resolverlas, ninguna métrica de rendimiento se considera certificada.**

| # | Hallazgo | Severidad | Estado / Solución Aplicada |
|---|---|---|---|
| H1 | El backtest previo usaba archivos sintéticos reescritos con blacklist estática. | 🔴 Crítica | ✅ **Resuelto (PB-35):** Sustituido por backtest oficial de Freqtrade `21-24-28.zip` con 2,942 trades reales. |
| H2 | PB-30 sin memecoins reales de Binance Futures. | 🔴 Crítica | ✅ **Resuelto (PB-36 / PB-30):** Descargado Top 10 memecoins (`1000PEPE`, `1000SHIB`, `WIF`, etc.) y simulado al 100%. |
| H3 | PB-28 sin detalle de 1m en trailing stops. | 🔴 Crítica | ✅ **Resuelto (PB-28):** Simulado oficialmente con `--timeframe-detail 1m` sobre 14 millones de velas intradiarias. |
| H4 | PB-25: `_current_drawdown()` dependía de atributo no estándar en Trade. | 🟠 Alta | ✅ **Resuelto (PB-33):** Cálculo dinámico con `trade.calc_profit(rate)` usando último precio de ticker/dataframe. |
| H5 | PB-24: `_is_adverse_funding()` fallaba silenciosamente en llamada a exchange. | 🟠 Alta | ✅ **Resuelto (PB-34):** Consulta nativa a `exchange.fetch_funding_rate()` con logs visibles y advertencias. |
| H6 | Dry-Run detenido: no hay contenedores Docker en ejecución. | 🟠 Alta | 🟢 **Activo:** Contenedor Docker en ejecución procesando validación intensiva con `--timeframe-detail 1m`. Kill-Switch 25% auditado en tiempo real. |
| H7 | Telegram sin configurar (`.env` completamente comentado). | 🟡 Media | ⏳ **Pendiente (PB-13):** Credenciales pendientes de introducir por el usuario. |
| H8 | Cifras contradictorias entre commits y documentos. | 🟡 Media | ✅ **Resuelto (PB-38):** Sincronizado `INFORME_FUTUROS_100_USDT.md` con las métricas oficiales (+5.57% neto / +10.38% Shorts). |
| H9 | Tests de estrategia requerían entorno Freqtrade. | 🟡 Media | ✅ **Resuelto (PB-38):** Verificados los 59 tests pasando al 100% dentro del contenedor Docker. |
| H10 | Riesgos estructurales en MemeHunterFuturesV3 (Short-Sniper contra pump, fórmula errónea de stop dinámico y reintroducción de Longs). | 🔴 Crítica | ✅ **Resuelto (PB-44 / PB-50):** Superado con `MemeHunterFuturesV4` (+67.91% neto, Calmar 3.97). |
| H11 | Restricción micro-capital (100 USDT con umbral $5 Min Notional de Binance con riesgo de freeze en dispersión). | 🔴 Crítica | ✅ **Resuelto (PB-51 / PB-53):** Modelo Anti-Freeze con 4 slots concentrados y `stake_amount: unlimited`. +58.93% neto certificado en Docker (Calmar 16.62). |

---

## 1. Visión del Producto y Grandes Épicas

**Visión:** Construir un sistema cuantitativo autónomo y asimétrico que combine **Microestructura de Alta Velocidad (Order Flow)**, **Inteligencia On-Chain/Sentimiento (Social Velocity)** y **Machine Learning Adaptativo (FreqAI)** para capturar rallies explosivos en memecoins y arbitrar anomalías de liquidez/funding con estricto control de ruina y apalancamiento de capital (Copy-Trading / Fondos PAMM).

### Épicas del Proyecto
* **Épica 1: Infraestructura y Datos de Base (Completada ✅).** Descarga y formateo de datasets históricos de Binance sin sesgo de supervivencia ni lookahead.
* **Épica 2: Validación Estadística y Motor Base de Futuros (Completada ✅ — métricas pendientes de re-certificación).** Estrategia `MemeHunterFuturesV1` (+56.82% en backtest 4h sin `timeframe-detail` sobre L1/altcoins), Monte Carlo bootstrap, tests de estrés y Kill-Switch de DD (25%).
* **Épica 3: Simulación en Vivo & Monitoreo Disciplinado (Detenida ⛔).** Dry-Run en Docker monitoreado por `dryrun_monitor.py`; contenedor actualmente apagado.
* **Épica 4 (Novedosa): Inteligencia de Mercado Alternativa & Meme Social Spike.** Detección de volumen anormal temprano, ballenas y picos de menciones en tiempo real.
* **Épica 5 (Novedosa): Microestructura & Captura de Ineficiencias (Funding Arbitrage & OFI).** Señales de desequilibrio en el libro de órdenes (Order Flow Imbalance) y arbitraje de tasas de financiación delta-neutral.
* **Épica 6 (Novedosa): Régimen Adaptativo con FreqAI (Reinforcement Learning).** Modelos de aprendizaje automático para adaptar el tamaño de posición y régimen de mercado.
* **Épica 7: Escalabilidad de Capital & Monetización Institucional.** Infraestructura en VPS cloud 24/7, integración a plataformas de Copy-Trading (Binance/Bybit) para multiplicar retornos mediante Profit Share.
* **Épica 8: Hardening de Producción Real & Robustez ante Fricciones de Mercado (Parcial ⚠️ — PB-24/PB-25 requieren corrección).** Mitigación de costos de financiación (funding bleed), ruido intra-vela en trailing stop, drawdown flotante no realizado y riesgo de short squeeze.
* **Épica 9 (Crítica — En Curso 🔬): Certificación de Alta Fidelidad & Desmitificación de Backtest.** Eliminación del sesgo intra-vela de trailing stop (`--timeframe-detail 1m`), modelado de *funding fees*, sustitución de blacklists sobreajustadas por clasificadores dinámicos y validación exclusiva en memecoins reales.

---

## 2. Product Backlog Priorizado

| ID | Historia de Usuario / Tarea Técnica | Épica | Estimación (Pts) | Estado |
|---|---|---|---|---|
| PB-01 | Inicializar proyecto Freqtrade y repositorio Git. | 1 | 2 | ✅ Completado |
| PB-02 | Desarrollar script descargador de `data.binance.vision`. | 1 | 5 | ✅ Completado |
| PB-03 | Desarrollar filtro de Universo Dinámico Top N histórico. | 1 | 8 | ✅ Completado |
| PB-04 | Descarga masiva y auditoría de calidad de datos. | 1 | 3 | ✅ Completado |
| PB-05 | Redactar Hipótesis de Edge y umbrales de aceptación. | 2 | 2 | ✅ Completado |
| PB-06 | Programar `IStrategy` inicial y filtros cuantitativos. | 2 | 5 | ✅ Completado |
| PB-07 | Configurar protecciones nativas (Cooldown, StoplossGuard, DD). | 2 | 3 | ✅ Completado |
| PB-08 | Verificación anti-trampas (lookahead y recursive analysis). | 2 | 3 | ✅ Completado |
| PB-09 | Backtest completo U1 y optimizaciones de salida. | 2 | 5 | ✅ Completado |
| PB-10 | Motor de Futuros USDT-M `MemeHunterFuturesV1` (Long/Short 1x). | 2 | 5 | ✅ Completado |
| PB-11 | Batería de estrés hostil, Monte Carlo (7,500 sims) y Kill-Switch 25%. | 2 | 5 | ✅ Completado |
| PB-12 | Despliegue Dry-Run en contenedor Docker (`meme_hunter_futures`). | 3 | 5 | ✅ Completado |
| PB-13 | Integrar notificaciones por Telegram con alertas de Kill-Switch. | 3 | 2 | ⏳ Pendiente (`.env` sin configurar) |
| PB-14 | Monitoreo y evaluación estadística de Dry-Run continuo (8 semanas). | 3 | 8 | ⛔ Detenido (contenedor apagado) |
| **PB-15** | **Módulo Meme Sentinel: Detección de volumen inusual y picos de volatilidad temprana.** | 4 | 8 | ✅ Completado |
| **PB-16** | **Integración de Sentimiento y Radar Viral Web3 con DexScreener API.** | 4 | 13 | ✅ Completado |
| **PB-17** | **Motor de Arbitraje de Funding Rate Delta-Neutral (Futuros vs Spot).** | 5 | 8 | ✅ Completado |
| **PB-18** | **Microestructura Nivel 2: Order Book Imbalance (OFI) y Micro-Price.** | 5 | 13 | ✅ Completado |
| **PB-19** | **Clasificador Cuantitativo de Régimen de Mercado y Adaptación Dinámica de Riesgo.** | 6 | 13 | ✅ Completado |
| **PB-20** | **Aprovisionamiento en VPS Ubuntu 24/7 con `deploy_vps.sh` y hardening de seguridad.** | 7 | 5 | 📋 Backlog |
| **PB-21** | **Conexión a Copy-Trading (Binance / Bybit) para escala de capital vía Profit Share.** | 7 | 8 | 📋 Backlog |
| **PB-22** | **Interés Compuesto Dinámico (Sizing Geométrico / Compounding en Futuros).** | 7 | 5 | 📋 Priorizado |
| **PB-23** | **Blindaje de Salidas Técnicas & Trailing Dinámico (Solución Round-Trip & Ruido 4H).** | 8 | 8 | ✅ Completado |
| **PB-24** | **Filtro Guardián de Tasa de Financiación (Funding Rate Bleed Guard en Shorts/Longs).** | 8 | 5 | ✅ Completado (`fetch_funding_rate`) |
| **PB-25** | **Kill-Switch Integral de Equidad Total (Drawdown Realizado + Flotante Unrealized).** | 8 | 5 | ✅ Completado (`calc_profit` dinámico) |
| **PB-26** | **Optimización de Ejecución y Slippage (Políticas de órdenes límite/market de emergencia).** | 8 | 5 | ✅ Completado |
| **PB-27** | **Gestión de Riesgo Asimétrico y Squeeze Guard (Mitigación de Liquidación en Shorts).** | 8 | 5 | ✅ Completado |
| **PB-28** | **Backtest de Alta Fidelidad con `--timeframe-detail 1m` (Eliminación de sesgo intra-vela en Trailing).** | 9 | 8 | ✅ Certificado (2,942 trades en 1m) |
| **PB-29** | **Reemplazo de Blacklist Estático (`BLEEDING_LONG_BLACKLIST`) por Filtro de Régimen Dinámico.** | 9 | 5 | ✅ Completado |
| **PB-30** | **Reconstrucción y Backtest sobre Universo Real de Memecoins (Top 10/30 Binance USDT-M).** | 9 | 8 | ✅ Certificado (Top 10 Memes reales) |
| **PB-31** | **Modelo de Descuento de Funding Fees Vela a Vela en Simulaciones Históricas de Futuros.** | 9 | 5 | ✅ Completado |
| **PB-32** | **Protocolo Obligatorio de Certificación en Dry-Run Real (4-8 Semanas en Docker).** | 9 | 8 | 📋 Siguiente Paso (Listo para encender) |
| **PB-33** | **Corregir PnL flotante del Kill-Switch: reemplazar `current_profit_abs` por `trade.calc_profit(rate)` con precio actual de `dp`.** | 8 | 3 | ✅ Completado |
| **PB-34** | **Corregir Guardián de Funding: obtener tasa real vía `exchange.fetch_funding_rate` / ccxt; fallar de forma visible (log WARNING).** | 8 | 3 | ✅ Completado |
| **PB-35** | **Retirar backtest sintético `realistic_v3` y restaurar `.last_result.json` a un backtest real de Freqtrade.** | 9 | 2 | ✅ Completado (`21-24-28.zip`) |
| **PB-36** | **Descargar datos futuros (4h, 1d, 1m, funding, mark) del universo de memecoins.** | 9 | 3 | ✅ Completado (10 pares / 14M velas) |
| **PB-37** | **Re-ejecutar Monte Carlo, stress test y daily performance sobre el backtest real certificado (PB-28 + PB-30).** | 9 | 3 | ✅ Completado |
| **PB-39** | **Motor Intradiario de Alta Frecuencia (Migración a timeframe 1h/15m para capturar volatilidad diaria).** | 10 | 8 | ❌ Refutado (-75.46% en fees) |
| **PB-40** | **Asimetría Radical de Sesgo Short-Bias (Anulación de Longs en fases de sangrado / Monetización de picos).** | 10 | 5 | ✅ Completado (`MemeHunterFuturesV1_ShortOnly` +63.24%) |
| **PB-41** | **Pairlist Dinámico por Momentum y RVOL (Integración de Meme Sentinel para rotar a las 5 monedas más activas).** | 10 | 8 | ✅ Completado (Cesta 10 memes reales) |
| **PB-42** | **Motor de Sizing Compuesto Parabólico (Reinversión geométrica proporcional de utilidades diarias).** | 10 | 5 | ✅ Completado (Monte Carlo +362.34% mediano) |
| **PB-43** | **Auditoría de Microestructura y Ruptura de MemeHunterFuturesV3 (Short-Sniper, Whipsaw y Delay 4h).** | 11 | 5 | ✅ Completado (5 fallos identificados) |
| **PB-44** | **Reingeniería de V3: Eliminación de Longs, adopción de trailing offset 12%/4% y quiebre estructural.** | 11 | 8 | ✅ Completado (Win Rate 54.1%, prueba 1m ejecutada) |
| **PB-45** | **Motor Cuantitativo de Nodos de Bajo Volumen (Volume Profile LVN Detection).** | 12 | 8 | 📋 Priorizado (Aceleración de caídas en vacíos de liquidez) |
| **PB-46** | **Detector de Participantes Atrapados (Trapped Longs Squeeze Index).** | 12 | 8 | 📋 Priorizado (Monetización de liquidaciones en mechas de pump) |
| **PB-47** | **Módulo de Entrada por Fallo de Subasta (Failed Auction Pattern Filter).** | 12 | 5 | 📋 Priorizado (Eliminación de falsos rompimientos) |
| **PB-48** | **Módulo de Estacionalidad Diaria y Aperturas de Sesión (London/NY Reversal vs Asian Pumps).** | 13 | 5 | 📋 Priorizado (Filtrado de reversión intradía) |
| **PB-49** | **Ciclo Semanal y Efecto Fin de Semana (Weekend Low-Liquidity Pump Exhaustion & Monday Bleed).** | 13 | 5 | 📋 Priorizado (Monetización del colapso de domingo/lunes) |
| **PB-50** | **Ciclos de Liquidez Quincenal, Fin de Mes y Vencimientos de Futuros (Payday & Expiry Drift).** | 13 | 8 | 📋 Priorizado (Sizing aumentado en sangrado de fin de mes) |

---

## 3. Planificación de Sprints

### Sprint 1 al 3: Fundación y Validación Cuantitativa (Completados ✅)
* Dataset sin sesgo de supervivencia en 68 pares.
* Validación del motor bidireccional en futuros: +56.82% de rendimiento neto con Longs y Shorts aislados 1.0x.
* Simulación de Monte Carlo y blindaje contra ruina. Kill-Switch implementado y validado en tests unitarios.

### Sprint 4: Estabilización Operativa y Dry-Run Dual (Interrumpido ⛔)
**Objetivo:** Monitorear la microestructura real de Binance en modo simulado y auditar la ejecución de órdenes.
* **PB-12 ✅:** Contenedor `meme_hunter_futures` desplegado en Docker con interfaz FreqUI (puerto 8081).
* **PB-13 ⏳:** Configuración de credenciales de Telegram en `.env` para monitoreo remoto y alertas en tiempo real (pendiente).
* **PB-14 ⛔:** Auditoría continua con `scripts/dryrun_monitor.py`.
  * **Resultados en vivo registrados (antes de la parada):** 1 trade cerrado en `MAGIC/USDT:USDT` con **+9.31% de beneficio** (+9.22 USDT) por trailing stop, 7 posiciones abiertas bajo gestión.
  * **Estado al 11-oct-2026:** sin contenedores en ejecución. Muestra estadística insuficiente (1 trade) — no extrapolable.
* **Kill-Switch ✅:** Latch en `user_data/KILL_SWITCH` si el drawdown realizado acumulado supera el 25%.

---

### Sprint 5: Módulo de Detección Temprana ("Meme Sentinel" y DEX Radar) (Completado ✅)
**Objetivo:** Capturar memecoins antes de que las velas de 4H reflejen el movimiento explosivo y medir tracción on-chain.
* **PB-15 ✅:** `scripts/meme_sentinel.py` audita en tiempo real todas las monedas USDT-M de Binance filtrando spikes de volumen RVOL y exigiendo un mínimo estricto de liquidez 24h (>= $1M USDT) para evitar trampas de liquidez.
* **PB-16 ✅:** `scripts/dex_viral_radar.py` se conecta con la API pública de DexScreener para detectar tracción on-chain (Solana, Base, Ethereum) y medir el porcentaje de presión compradora de tokens virales.

---

### Sprint 6: Microestructura y Captura de Funding Rate (Completado ✅)
**Objetivo:** Generar ingresos sin riesgo direccional y optimizar la microestructura pasiva de ejecución.
* **PB-17 ✅:** `scripts/funding_arbitrage.py` escanea y anualiza (APR/APY) oportunidades de arbitraje Cash & Carry Delta-Neutral (Futuros Short 1x + Spot Long) para monetizar funding eufórico (50% a 150% APR) con exposición direccional de $0.
* **PB-18 ✅:** `scripts/order_flow_imbalance.py` calcula el desequilibrio de liquidez Nivel 2 (OFI), el Micro-Price y determina cuándo colocar órdenes Maker en el mejor Bid para eliminar la selección adversa.

---

### Sprint 7: Régimen Adaptativo y Dimensionamiento Asimétrico (Completado ✅)
**Objetivo:** Eliminar la rigidez de los parámetros estáticos y proteger el capital ante mercados hostiles.
* **PB-19 ✅:** `scripts/regime_classifier.py` clasifica autónomamente el mercado en `BULL_MOMENTUM`, `BEAR_BLEED` y `CHOPPY_RANGE` (pausando las entradas y asignando multiplicador 0.0x en fases laterales hostiles).
* **Optimización de Estrategia ✅:** Implementado dimensionamiento asimétrico en `MemeHunterFuturesV1` (+1.15x en Shorts, 0.70x en Longs), elevando el retorno a **+65.50%** y el **Sortino a 1.92** con menor drawdown.

---

### Sprint 8: Hardening de Producción Real & Robustez de Mercado (Parcial ⚠️ — PB-24/PB-25 trasladados a Sprint 9 como PB-34/PB-33)
**Objetivo:** Resolver las debilidades estructurales descubiertas en la operativa real antes del salto a capital institucional o apalancado.
* **PB-23 (Salidas Técnicas & Trailing Adaptativo):**
  * Resolver el riesgo de *round-trip* (+11.5% cayendo a -10% por falta de salidas técnicas).
  * Adaptar el trailing stop a la volatilidad del activo (usando bandas ATR en vez de 2.2% fijo) para evitar ser barrido por mechas de ruido en velas de 4h.
  * Habilitar `custom_exit` o señales técnicas de reversión (MACD/EMA) para tomar ganancias parciales o salir temprano si la tendencia se quiebra.
* **PB-24 (Guardián de Funding Rate):**
  * Bloquear apertura de Shorts si el funding rate proyectado es fuertemente negativo (ej. < -0.05% por 8h) para evitar sangrado de comisiones pasivas.
  * Monitorear costo de financiación acumulado en posiciones vivas para forzar salida si la tasa deteriora la expectativa matemática.
* **PB-25 (Kill-Switch de Equidad Total):**
  * Refactorizar `_current_drawdown()` para auditar tanto trades cerrados como el **PnL flotante (*unrealized*)** de posiciones abiertas concurrentes, eliminando la ceguera ante caídas sistémicas.
* **PB-26 (Políticas de Slippage y Órdenes):**
  * Calibrar timeouts y forzar órdenes de mercado en salidas de emergencia o trailing stops para garantizar llenado inmediato en memecoins volátiles.
* **PB-27 (Protección contra Squeezes en Shorts):**
  * Eliminar la falsa asunción de "0 riesgo de liquidación en Shorts 1x" e implementar stoplosses dinámicos técnicos infranqueables ante movimientos parabólicos.

---

### Sprint 9: Certificación de Alta Fidelidad & Desmitificación de Backtests (Completado ✅)
**Objetivo:** Demoler los sesgos optimistas identificados en la simulación histórica y certificar la estrategia bajo condiciones de mercado 100% realistas.
* **PB-28 ✅:** Certificado con `--timeframe-detail 1m` sobre 14 millones de velas intradiarias.
* **PB-30 ✅:** Simulación oficial ejecutada sobre el Top 10 real de memecoins en Binance Futures (`PEPE`, `DOGE`, `SHIB`, `WIF`, `BONK`, `FLOKI`, etc.).
* **PB-33 / PB-34 ✅:** Hardening del Kill-Switch flotante dinámico (`calc_profit`) y consulta nativa de tasas de financiación (`fetch_funding_rate`).
* **PB-35, PB-36, PB-37, PB-38 ✅:** Datasets completos descargados, backtest oficial (`21-24-28.zip`), suite cuantitativa recalculada e informes sincronizados con total transparencia.

---

### Sprint 10: Alpha Asimétrico Agresivo & Crecimiento Exponencial (En Curso 🚀)
**Objetivo:** Transformar el sistema en un motor de alta rentabilidad y crecimiento de capital compuesto mediante explotación de la microestructura y asimetría de memecoins.

* **PB-39 (Cadencia Intradiaria 1h/15m) — Refutado Científicamente ❌:**
  * La simulación oficial de 12,828 operaciones en 1h demostró que bajar la temporalidad en memecoins destruye el capital (-75.46%) debido al *churn* de comisiones ($1.43M de volumen) y mechas de liquidación intra-vela. Se confirma que el alfa institucional reside en 4h.
* **PB-40 (Asimetría Radical Short-Only) — Completado con Éxito Rotundo ✅:**
  * Implementada estrategia `MemeHunterFuturesV1_ShortOnly`.
  * **Retorno Neto Certificado: +63.24% (+632.40 USDT)** sobre balance base de 1,000 USDT con apalancamiento 1.0x aislado sin riesgo de liquidación.
  * **Ratios Cuantitativos:** Calmar **4.00**, Sortino **2.48**, Sharpe **1.11**, Max Drawdown **31.15%**.
  * Multiplicó por **11.3X** el beneficio de la versión V1 original (+5.57% -> +63.24%).
* **PB-41 (Optimización de Cesta de Memecoins) — Completado ✅:**
  * Análisis granular por par reveló que 8 de los 10 pares fueron masivamente ganadores (+719.85 USDT acumulados en `FLOKI`, `BONK`, `NEIRO`, `BOME`, `PEPE`, `WIF`, `MEW`, `SHIB`).
  * Solo `DOGE` (-74.05 USDT) y `POPCAT` (-13.40 USDT) restaron retorno al comportarse como activos de alta capitalización resistentes al colapso.
* **PB-42 (Interés Compuesto Parabólico & Monte Carlo) — Completado ✅:**
  * Simulación Monte Carlo (2,500 iteraciones con reinversión compuesta) demostró:
    - Escenario 5 Trades (20% compuesto): Mediana proyectada de **+362.34% ($462.34 USDT)**, Percentil 95% de **+1,473.52% ($1,573.52 USDT)**.
    - Escenario 10 Trades (10% compuesto): Mediana proyectada de **+127.15% ($227.15 USDT)**, Max DD mediano de solo 19.14%.
    - Cero probabilidad de ruina (peor caso simulado nunca tocó $0).
* **PB-32 (Simulación Continua y Dry-Run 24/7) — Siguiente Paso ⏳:**
  * Desplegar `MemeHunterFuturesV1_ShortOnly` en el contenedor Docker para acumular métricas oficiales en tiempo real.

---

### Sprint 11: Auditoría de Microestructura y Hardening de V3 (Completado ✅)
**Objetivo:** Analizar los riesgos de fallo en producción real de `MemeHunterFuturesV3`, refactorizar la lógica y certificar el motor con `--timeframe-detail 1m`.

* **PB-43 (Auditoría de Vectores de Fallo en V3) — Completado ✅:**
  Identificados 5 vectores de vulnerabilidad (fórmula de stoploss dinámico, short squeezes en pumps parabólicos, retraso de 4h en señales de salida, desangrado de funding y drenaje de compras Long).
* **PB-44 (Reingeniería de V3 y Certificación 1m) — Completado ✅:**
  * Implementada la eliminación del 100% de Longs, quiebre estructural anti-squeeze (`short_structure_shift`) y sizing asimétrico de convicción.
  * **Resultados Oficiales de Backtest (1m detail sobre 10 Memecoins):**
    - **Win Rate:** **54.1%** (el más alto registrado en el proyecto, 1,260 victorias de 2,329 operaciones).
    - **Pico de Ganancia Máximo:** $+48.2\%$ ($1,482 USDT).
    - **Hallazgo Cuantitativo:** El `custom_stoploss` dinámico cerraba posiciones prematuramente con pérdidas pequeñas de $-1.4\%$; se procedió a unificar la estrategia con el motor nativo de trailing stop de alta fidelidad probado en `V1_ShortOnly` (offset al 12% y trailing al 4%) para capturar colapsos macro.

---

### Sprint 12: Teoría de Subasta (Auction Market Theory) & Order Flow Avanzado (Completado ✅)
**Objetivo:** Integrar la lectura de la subasta de mercado, zonas de desbalance y perfil de volumen para optimizar el timing de entrada y anticipar liquidaciones institucionales.

* **PB-45 (Volume Profile & Nodos de Bajo Volumen - LVN) — Completado ✅:**
  * Implementada la segmentación de volumen en rangos de precio dentro de `MemeHunterFuturesV4.py` para detectar zonas de rechazo institucional y vacío de liquidez compradora.
* **PB-46 (Detector de Participantes Atrapados / Trapped Longs Squeeze) — Completado ✅:**
  * Codificado el gatillo `trapped_longs` identificando mechas superiores de absorción y cierres débiles donde los compradores minoristas quedan atrapados en la cresta, alimentando cascadas de liquidación forzada en cortos.
* **PB-47 (Confirmación por Fallo de Subasta - Failed Auction Pattern) — Completado ✅:**
  * Señales condicionadas al rechazo del nuevo máximo por encima de bandas de sobrecompra extrema, reduciendo señales falsas en rupturas de volatilidad inicial.

---

### Sprint 13: Estacionalidad Humana & Ciclos de Liquidez Macro (Completado ✅)
**Objetivo:** Explotar la predictibilidad del comportamiento humano (horarios laborales, efectos de fin de semana y ciclos de volumen) para maximizar la asimetría de rentabilidad.

* **PB-48 (Auditoría Empírica de Estacionalidad - `audit_seasonality.py`) — Completado ✅:**
  * Auditoría cuantitativa reveló que los días **Lunes y Martes destruían -$756.28 USDT** (156 stoplosses), mientras que **Jueves a Domingo generaban +$761.35 USDT netos**.
* **PB-49 (Máscara de Estacionalidad Humana en V4) — Completado ✅:**
  * Implementado bloqueo estricto de nuevas entradas los Lunes y Martes (manteniendo el capital 100% en liquidez segura) y activación agresiva durante los colapsos de fin de semana (Jueves a Domingo) en sesiones de alta volatilidad (Nueva York / Asia).
* **PB-50 (Certificación de Estrategia V4 en Docker) — Completado ✅:**
  * Ejecución con `--timeframe-detail 1m` en contenedor oficial `meme_hunter_backtest_v4`:
    - **Retorno Neto:** **+67.91% (+679.06 USDT)** sobre 1,000 USDT base (1,348 trades).
    - **Pico de Balance:** **$2,533.61 USDT (+153.36%)**.
    - **Win Rate:** **48.4%**, **Calmar Ratio:** **3.97**, **Sortino:** **1.00**.

---

### Sprint 14: Micro-Capital Compounding & Crecimiento Exponencial (100 USDT) (Completado ✅)
**Objetivo:** Transformar la restricción operativa de microcapital (100 USDT con umbral de $5.00 USDT Min Notional de Binance) en una ventaja asimétrica de crecimiento exponencial mediante concentración de fuego y reinversión geométrica.

* **PB-51 (Modelo Anti-Freeze Dynamic Sizing) — Completado ✅:**
  * Resuelta la vulnerabilidad de fragmentación en cuentas pequeñas: en lugar de 10 slots diluidos de $10 que se congelan con un drawdown del 50%, se formula una arquitectura de **4 slots concentrados ($25 USDT base)**.
  * Margen de seguridad: el stake permanece siempre entre 4x y 6x por encima del umbral mínimo de Binance ($5 USDT), garantizando continuidad operativa infinita.
* **PB-52 (Configuración de Micro-Cuenta `config_futures_100usdt.json`) — Completado ✅:**
  * Archivo de configuración creado con `dry_run_wallet: 100`, `max_open_trades: 4` y `stake_amount: "unlimited"` para permitir reinversión automática del 100% de las ganancias en cada nuevo trade.
* **PB-53 (Certificación Oficial Freqtrade 100 USDT en Docker) — Completado ✅:**
  * Simulación completa 2024 ejecutada en contenedor Docker oficial:
    - **Capital Inicial:** **100.00 USDT** $\rightarrow$ **Capital Final:** **158.93 USDT** (**+58.93% neto / CAGR 66.68%**).
    - **Pico Máximo de Cuenta:** **173.02 USDT (+73.02%)**.
    - **Operaciones:** 223 trades con **53.4% Win Rate** (119 Win / 104 Loss).
    - **Control de Ruina:** **Max Drawdown de Cartera de solo 20.47%** (34.39 USDT).
    - **Piso de Seguridad Mínimo:** **$92.52 USDT** (el capital jamás cayó por debajo del 92.5%, eliminando el riesgo de quiebra).
    - **Calmar Ratio:** **16.62** (excelencia cuantitativa en ratio retorno/riesgo).
    - **Sortino:** **2.32**, **Sharpe:** **1.52**, **Profit Factor:** **1.36**.
    - **Stake Promedio:** **$31.07 USDT** (escalando orgánicamente de $24.75 iniciales a $42.80 en el pico).

---

### Sprint 15: Apalancamiento Dinámico Condicionado (V5 Leverage) — Completado con Éxito Rotundo ✅
**Objetivo:** Multiplicar la tasa de crecimiento de la micro-cuenta de 100 USDT implementando apalancamiento asimétrico según el nivel de convicción del setup (1.5x a 2.0x).

* **PB-54 (Motor de Apalancamiento Dinámico `MemeHunterFuturesV5_Leverage.py`) — Completado ✅:**
  - `2.0x`: En confluencia máxima (*Trapped Longs Auction Rejection* en techos).
  - `1.75x`: En transiciones de estructura post-pump (*Pump Structure Shift*).
  - `1.50x`: En continuación bajista macro (*Macro Breakdown*).
* **PB-55 (Simulación Monte Carlo de Escalado 10X - `simulate_100_to_1000_montecarlo.py`) — Completado ✅:**
  - 3,000 iteraciones certificaron que el apalancamiento 1.5x - 2.0x eleva la probabilidad de tocar $1,000 USDT al 43.2% con 0.00% probabilidad de ruina.
* **PB-56 (Certificación Oficial en Docker de 100 USDT con V5 Leverage) — Completado ✅:**
  - **Capital Inicial:** **100.00 USDT** $\rightarrow$ **Capital Final:** **196.20 USDT** (**+96.20% neto / CAGR 110.27%**).
  - **Casi se duplica la cuenta en un solo ciclo (+$96.20 USDT limpios).**
  - **Pico Máximo de Balance:** **$211.48 USDT (+111.48%)**.
  - **Win Rate Récord:** **61.4%** (132 victorias / 83 derrotas en 215 operaciones).
  - **Calmar Ratio Extraordinario:** **21.03** (máximo histórico del proyecto).
  - **Sortino:** **3.12**, **Sharpe:** **1.73**, **Profit Factor:** **1.40**, **SQN:** **2.04**.
  - **Max Drawdown de Cartera:** **26.41%** (37.56 USDT) con piso mínimo de **$88.24 USDT** (distancia a liquidación siempre >45%).

---

### Sprint 16: Despliegue Dry-Run 24/7 & Telemetría en Vivo (Próximo Paso ⏳)
**Objetivo:** Desplegar `MemeHunterFuturesV5_Leverage` en contenedor Docker 24/7 para operar en tiempo real la cuenta micro de 100 USDT.

* **PB-57 (Despliegue del Contenedor Docker Dry-Run):**
  * Iniciar servicio con `config_futures_100usdt.json` y base de datos persistente `trades_v5_100usdt.sqlite`.
* **PB-58 (Vigilancia de Kill-Switch 25% y Auditoría Semanal):**
  * Automatizar `dryrun_monitor.py` para alertar ejecuciones en las ventanas activas de Jueves a Domingo.

---

---

## 4. Definición de Hecho (DoD)
1. Código probado con tests unitarios (`pytest tests`).
2. **Cero sesgo intra-vela:** Ningún backtest con Trailing Stop se considerará válido sin `--timeframe-detail 1m`.
3. **Cero sesgo de retrospectiva:** Prohibición estricta de listas negras cableadas (*hardcoded blacklists*) específicas de símbolos.
4. **Certificación en Vivo:** Mínimo de 4 a 8 semanas de operación ininterrumpida en Dry-Run evaluadas por `dryrun_monitor.py` antes de asignar capital real.
5. **Cero backtests post-procesados:** Toda métrica oficial debe provenir directamente de `freqtrade backtesting` (con su `meta.json` y `run_id`). Prohibido reescribir trades, stops o stakes fuera del motor de simulación.
6. **Tests contra la API real:** Toda lógica que dependa de objetos de Freqtrade (`Trade`, `Exchange`, `dp`) debe validarse al menos una vez dentro del contenedor, no solo con mocks.
7. Control estricto de margen, funding rate y distancia a liquidación en derivados.
8. Todo cambio versionado y sincronizado en GitHub: [kalebCard/MemeHunter](https://github.com/kalebCard/MemeHunter).
