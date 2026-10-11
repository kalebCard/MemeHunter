# Plan de Desarrollo Scrum: meme_hunter (Alpha & Asymmetric Edge)

Este documento organiza el desarrollo del sistema **meme_hunter** transformado en un **verdadero cazador de memecoins con ventaja asimétrica y modelos cuantitativos de última generación**, superando la dependencia de indicadores tradicionales rezagados.

---

## 1. Visión del Producto y Grandes Épicas

**Visión:** Construir un sistema cuantitativo autónomo y asimétrico que combine **Microestructura de Alta Velocidad (Order Flow)**, **Inteligencia On-Chain/Sentimiento (Social Velocity)** y **Machine Learning Adaptativo (FreqAI)** para capturar rallies explosivos en memecoins y arbitrar anomalías de liquidez/funding con estricto control de ruina y apalancamiento de capital (Copy-Trading / Fondos PAMM).

### Épicas del Proyecto
* **Épica 1: Infraestructura y Datos de Base (Completada ✅).** Descarga y formateo de datasets históricos de Binance sin sesgo de supervivencia ni lookahead.
* **Épica 2: Validación Estadística y Motor Base de Futuros (Completada ✅).** Estrategia `MemeHunterFuturesV1` validada (+56.82%), Monte Carlo bootstrap, tests de estrés y Kill-Switch de DD (25%).
* **Épica 3: Simulación en Vivo & Monitoreo Disciplinado (En Curso 🔄).** Dry-Run continuo en Docker monitoreado por `dryrun_monitor.py`.
* **Épica 4 (Novedosa): Inteligencia de Mercado Alternativa & Meme Social Spike.** Detección de volumen anormal temprano, ballenas y picos de menciones en tiempo real.
* **Épica 5 (Novedosa): Microestructura & Captura de Ineficiencias (Funding Arbitrage & OFI).** Señales de desequilibrio en el libro de órdenes (Order Flow Imbalance) y arbitraje de tasas de financiación delta-neutral.
* **Épica 6 (Novedosa): Régimen Adaptativo con FreqAI (Reinforcement Learning).** Modelos de aprendizaje automático para adaptar el tamaño de posición y régimen de mercado.
* **Épica 7: Escalabilidad de Capital & Monetización Institucional.** Infraestructura en VPS cloud 24/7, integración a plataformas de Copy-Trading (Binance/Bybit) para multiplicar retornos mediante Profit Share.
* **Épica 8: Hardening de Producción Real & Robustez ante Fricciones de Mercado (Completada ✅).** Mitigación de costos de financiación (funding bleed), ruido intra-vela en trailing stop, drawdown flotante no realizado y riesgo de short squeeze.
* **Épica 9 (Crítica): Certificación de Alta Fidelidad & Desmitificación de Backtest.** Eliminación del sesgo intra-vela de trailing stop (`--timeframe-detail 1m`), modelado de *funding fees*, sustitución de blacklists sobreajustadas por clasificadores dinámicos y validación exclusiva en memecoins reales.

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
| PB-13 | Integrar notificaciones por Telegram con alertas de Kill-Switch. | 3 | 2 | ⏳ Pendiente (.env) |
| PB-14 | Monitoreo y evaluación estadística de Dry-Run continuo (8 semanas). | 3 | 8 | 🔄 En Ejecución |
| **PB-15** | **Módulo Meme Sentinel: Detección de volumen inusual y picos de volatilidad temprana.** | 4 | 8 | ✅ Completado |
| **PB-16** | **Integración de Sentimiento y Radar Viral Web3 con DexScreener API.** | 4 | 13 | ✅ Completado |
| **PB-17** | **Motor de Arbitraje de Funding Rate Delta-Neutral (Futuros vs Spot).** | 5 | 8 | ✅ Completado |
| **PB-18** | **Microestructura Nivel 2: Order Book Imbalance (OFI) y Micro-Price.** | 5 | 13 | ✅ Completado |
| **PB-19** | **Clasificador Cuantitativo de Régimen de Mercado y Adaptación Dinámica de Riesgo.** | 6 | 13 | ✅ Completado |
| **PB-20** | **Aprovisionamiento en VPS Ubuntu 24/7 con `deploy_vps.sh` y hardening de seguridad.** | 7 | 5 | 📋 Backlog |
| **PB-21** | **Conexión a Copy-Trading (Binance / Bybit) para escala de capital vía Profit Share.** | 7 | 8 | 📋 Backlog |
| **PB-22** | **Interés Compuesto Dinámico (Sizing Geométrico / Compounding en Futuros).** | 7 | 5 | 📋 Priorizado |
| **PB-23** | **Blindaje de Salidas Técnicas & Trailing Dinámico (Solución Round-Trip & Ruido 4H).** | 8 | 8 | ✅ Completado |
| **PB-24** | **Filtro Guardián de Tasa de Financiación (Funding Rate Bleed Guard en Shorts/Longs).** | 8 | 5 | ✅ Completado |
| **PB-25** | **Kill-Switch Integral de Equidad Total (Drawdown Realizado + Flotante Unrealized).** | 8 | 5 | ✅ Completado |
| **PB-26** | **Optimización de Ejecución y Slippage (Políticas de órdenes límite/market de emergencia).** | 8 | 5 | ✅ Completado |
| **PB-27** | **Gestión de Riesgo Asimétrico y Squeeze Guard (Mitigación de Liquidación en Shorts).** | 8 | 5 | ✅ Completado |
| **PB-28** | **Backtest de Alta Fidelidad con `--timeframe-detail 1m` (Eliminación de sesgo intra-vela en Trailing).** | 9 | 8 | 📋 Planificado (Siguiente Paso) |
| **PB-29** | **Reemplazo de Blacklist Estático (`BLEEDING_LONG_BLACKLIST`) por Filtro de Régimen Dinámico.** | 9 | 5 | ✅ Completado |
| **PB-30** | **Reconstrucción y Backtest sobre Universo Real de Memecoins (Top 30 Binance USDT-M).** | 9 | 8 | ✅ Completado |
| **PB-31** | **Modelo de Descuento de Funding Fees Vela a Vela en Simulaciones Históricas de Futuros.** | 9 | 5 | ✅ Completado |
| **PB-32** | **Protocolo Obligatorio de Certificación en Dry-Run Real (4-8 Semanas en Docker).** | 9 | 8 | 🔄 En Curso (Innegociable) |

---

## 3. Planificación de Sprints

### Sprint 1 al 3: Fundación y Validación Cuantitativa (Completados ✅)
* Dataset sin sesgo de supervivencia en 68 pares.
* Validación del motor bidireccional en futuros: +56.82% de rendimiento neto con Longs y Shorts aislados 1.0x.
* Simulación de Monte Carlo y blindaje contra ruina. Kill-Switch implementado y validado en tests unitarios.

### Sprint 4: Estabilización Operativa y Dry-Run Dual (Actual 🔄)
**Objetivo:** Monitorear la microestructura real de Binance en modo simulado y auditar la ejecución de órdenes.
* **PB-12 ✅:** Contenedor `meme_hunter_futures` desplegado en Docker con interfaz FreqUI (puerto 8081).
* **PB-13:** Configuración de credenciales de Telegram en `.env` para monitoreo remoto y alertas en tiempo real.
* **PB-14 🔄:** Auditoría continua con `scripts/dryrun_monitor.py`.
  * **Resultados en vivo registrados:** 1 trade cerrado en `MAGIC/USDT:USDT` con **+9.31% de beneficio** (+9.22 USDT) por trailing stop, 7 posiciones abiertas bajo gestión.
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

### Sprint 8: Hardening de Producción Real & Robustez de Mercado (Completado ✅)
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

### Sprint 9: Certificación de Alta Fidelidad & Desmitificación de Backtests (En Curso / Prioridad Crítica 🔬)
**Objetivo:** Demoler los sesgos optimistas identificados en la simulación histórica y certificar la estrategia bajo condiciones de mercado 100% realistas.
* **PB-28 (Backtest con Datos de 1 Minuto):**
  * Descargar datos OHLCV de 1m para todo el universo y re-ejecutar el backtest con `--timeframe-detail 1m`.
  * Eliminar la presunción optimista de Freqtrade sobre el recorrido intra-vela del Trailing Stop.
* **PB-29 (Eliminación de Sesgo de Retrospectiva):**
  * Eliminar el cableado estático `BLEEDING_LONG_BLACKLIST = {'SUI', 'TIA', 'SOL'}` en `MemeHunterFuturesV1.py`.
  * Sustituirlo por filtros cuantitativos dinámicos de régimen (e.g. pendiente negativa de EMA 200, ADX > 25 bajista, o el clasificador de `scripts/regime_classifier.py`).
* **PB-30 (Universo Real de Memecoins):**
  * Ejecutar el backtest sobre el Top 30 real de memecoins en Binance USDT-M (`PEPE`, `WIF`, `BONK`, `FLOKI`, `BOME`, `NEIRO`), en lugar de Layer-1s clásicos (`BTC`, `ETH`, `SOL`).
* **PB-31 (Deducción de Tasas de Financiación):**
  * Cuantificar e incorporar el impacto del *Funding Rate* negativo acumulado durante las 815 operaciones en Short del histórico.
* **PB-32 (Protocolo Innegociable de Dry-Run en Vivo):**
  * Certificar el rendimiento durante un mínimo de **4 a 8 semanas continuas en Docker** con `scripts/dryrun_monitor.py` antes de autorizar el paso a capital real.

---

### Sprint 10: Crecimiento Exponencial, Despliegue Cloud y Multiplicador de Capital (Planificado 🚀)
**Objetivo:** Crecimiento financiero exponencial y gestión de capital externo mediante infraestructura probada y blindada.
* **PB-22:** Implementar **Interés Compuesto Dinámico (Sizing Geométrico)** en `config_futures.json` y estrategia para reinversión óptima de beneficios.
* **PB-20:** Despliegue en VPS (DigitalOcean / Hetzner / AWS) con el script `scripts/deploy_vps.sh` y firewall reforzado.
* **PB-21:** Publicación de la estrategia en el programa de Lead Trader de Binance o Bybit:
  * Mantener un Drawdown < 15% y Sortino > 1.5 para posicionarse en el Top Ranking de Copy Trading.
  * Monetizar mediante **Profit Sharing** (10% - 15% de los beneficios generados a los seguidores).

---

## 4. Definición de Hecho (DoD)
1. Código probado con tests unitarios (`pytest tests`).
2. **Cero sesgo intra-vela:** Ningún backtest con Trailing Stop se considerará válido sin `--timeframe-detail 1m`.
3. **Cero sesgo de retrospectiva:** Prohibición estricta de listas negras cableadas (*hardcoded blacklists*) específicas de símbolos.
4. **Certificación en Vivo:** Mínimo de 4 a 8 semanas de operación ininterrumpida en Dry-Run evaluadas por `dryrun_monitor.py` antes de asignar capital real.
5. Control estricto de margen, funding rate y distancia a liquidación en derivados.
6. Todo cambio versionado y sincronizado en GitHub: [kalebCard/MemeHunter](https://github.com/kalebCard/MemeHunter).
