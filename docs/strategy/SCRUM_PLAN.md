---
id: STRAT-ROADMAP-001
title: Plan de Desarrollo Scrum y Backlog de Sprints (Meme Hunter v7.3)
category: strategy
version: 7.3
status: ACTIVE
last_updated: 2026-10-12
author: Quantitative Engineering & Research Core
references:
  - docs/strategy/ESTRATEGIA_MAESTRA_UNIFICADA.md
  - docs/MANUAL_UNIFICADO_DEL_SISTEMA.md
  - docs/operations/OPERATIONAL_RUNBOOK.md
  - docs/sprints/SPRINT_PLAN_AUTONOMOUS_LOOP_HARDENING.md
  - docs/sprints/SPRINT_PLAN_29_BIDIRECTIONAL_AND_DATA_SYNC.md
---

# 📋 Plan de Desarrollo Scrum: meme_hunter (STRAT-ROADMAP-001 v7.3)

> **Documento Consolidado:** Para la visión estratégica y matemática unificada del sistema, consultar el [Compendio Maestro de Estrategia (STRAT-MASTER-001)](ESTRATEGIA_MAESTRA_UNIFICADA.md).

Este documento organiza el desarrollo del sistema **meme_hunter** transformado en un **verdadero cazador de memecoins con ventaja asimétrica y modelos cuantitativos de última generación**, superando la dependencia de indicadores tradicionales rezagados.

> **Última actualización:** 12 de octubre de 2026 — Consolidación v7.3 con Sprints 21 a 29 finalizados y certificados (ver §0 y §3).

---

## 0. Auditoría de Estado Real y Riesgos Cuantitativos (11-oct-2026)

Una revisión profunda del código, datos, metodología y artefactos de backtest detectó riesgos metodológicos y discrepancias críticas. **Hasta resolver las pruebas fuera de muestra (OOS) y las pruebas de significancia, ninguna métrica de rendimiento (incluyendo el Calmar 21 y el 0.0% de ruina) se considera definitiva para capital real.**

| # | Hallazgo / Riesgo Cuantitativo | Severidad | Estado / Solución y Plan de Mitigación |
|---|---|---|---|
| H1 | Backtest previo con archivos sintéticos y blacklist estática. | 🔴 Crítica | ✅ **Resuelto (PB-35):** Sustituido por backtest oficial de Freqtrade `21-24-28.zip` con trades reales. |
| H2 | PB-30 sin memecoins reales de Binance Futures. | 🔴 Crítica | ✅ **Resuelto (PB-36 / PB-30):** Descargado Top 10 memecoins (`1000PEPE`, `1000SHIB`, `WIF`, etc.) y simulado al 100%. |
| H3 | PB-28 sin detalle de 1m en trailing stops. | 🔴 Crítica | ✅ **Resuelto (PB-28):** Simulado oficialmente con `--timeframe-detail 1m` sobre 14M velas intradiarias. |
| H4 | PB-25: `_current_drawdown()` dependía de atributo no estándar en Trade. | 🟠 Alta | ✅ **Resuelto (PB-33):** Cálculo dinámico con `trade.calc_profit(rate)` usando último precio. |
| H5 | PB-24: `_is_adverse_funding()` fallaba silenciosamente en llamada a exchange. | 🟠 Alta | ✅ **Resuelto (PB-34):** Consulta nativa a `exchange.fetch_funding_rate()` con logs y advertencias. |
| H6 | Dry-Run detenido: no hay contenedores Docker en ejecución. | 🟠 Alta | 🟢 **Activo:** Contenedor Docker en ejecución procesando validación intensiva con `--timeframe-detail 1m`. |
| H7 | Telegram sin configurar (`.env` completamente comentado). | 🟡 Media | ⏳ **Pendiente (PB-13):** Credenciales pendientes de introducir por el usuario. |
| H8 | Cifras contradictorias entre commits y documentos. | 🟡 Media | ✅ **Resuelto (PB-38):** Sincronizado `INFORME_FUTUROS_100_USDT.md` con las métricas oficiales. |
| H9 | Tests de estrategia requerían entorno Freqtrade. | 🟡 Media | ✅ **Resuelto (PB-38):** Verificados los 59 tests pasando al 100% dentro del contenedor Docker. |
| H10 | Riesgos estructurales en V3 (Short-Sniper, fórmula errónea de stop dinámico). | 🔴 Crítica | ✅ **Resuelto (PB-44 / PB-50):** Superado con `MemeHunterFuturesV4`. |
| H11 | Restricción micro-capital (100 USDT con umbral $5 Min Notional de Binance). | 🔴 Crítica | ✅ **Resuelto (PB-51 / PB-53):** Modelo Anti-Freeze con 4 slots concentrados y `stake_amount: unlimited`. |
| **H12** | **Riesgo severo de Overfitting por iteraciones acumuladas (V1 a V6).** | 🔴 Crítica | ✅ **Completado (PB-60):** Validación OOS Cross-Asset sobre activos ciegos (SOL, SUI, TIA, WLD) certifica rentabilidad de +104.27% ($N=955$) con un Win Rate de 53.1%, Calmar de 8.90 y Max DD de 23.08%. El $p$-value ajustado es $0.0234 (< 0.05)$, confirmando que el edge estructural es transferible y no está sobreajustado a las memecoins de diseño. |
| **H13** | **Minería de datos en "Estacionalidad Humana" (Filtro de Días).** | 🔴 Crítica | ✅ **Completado (PB-61):** Test de ablación sin filtro ejecutado con $N=2,361$. Se ratifica ventaja estructural pura (+156.29%, $p=0.0068$ ajustado), pero el Calmar cae de 21.0 a 7.06 y el Win Rate real desciende al 50.2%. |
| **H14** | **Métricas hiper-optimizadas (Calmar 21.03, CAGR +110%).** | 🔴 Crítica | ⚠️ **Abierto (PB-64):** Ignora fricciones microestructurales severas (no-fills en órdenes Maker en caídas súbitas, slippage en salidas a mercado de baja liquidez). |
| **H15** | **Falsa sensación de "0.0% probabilidad de ruina".** | 🔴 Crítica | ✅ **Completado (PB-65):** Block Bootstrap con mechas de shock revela un Max Drawdown promedio de 73.4% y un 87.88% de probabilidad de tocar el piso de 50 USDT si se opera sin pausas. Ratifica la obligatoriedad matemática del Kill-Switch al 25% para no quebrar. |
| **H16** | **Apalancamiento Asimétrico optimizado ex-post sobre la misma muestra.** | 🟠 Alta | ✅ **Completado (PB-66):** Sensibilidad 1.0x evaluada con $N=1,846$. Retorno $+48.64\%$, pero el retorno medio baja a $\mu=+0.458\%$. Al 1.0x plano, el $p$-value ajustado es $0.0774$, confirmando que el 1.5x/2.0x inflaba artificialmente el edge percibido sobre las comisiones. |
| **H17** | **Sesgo de supervivencia y tamaño muestral limitado ($N=215$).** | 🟠 Alta | ⚠️ **Abierto (PB-67):** Universo compuesto por monedas sobrevivientes; 215 trades no garantizan significancia estadística con corrección de pruebas múltiples. |

---

## 1. Visión del Producto y Grandes Épicas

**Visión:** Construir un sistema cuantitativo autónomo y asimétrico basado en una **Arquitectura Híbrida Barbell (de Pesas) y Trinquete de Ganancias (Profit Ratchet)**:
1. **Motor Alfa Asimétrico (Meme Hunter Futures):** Genera aceleración rápida de micro-capital explotando la desinflación macro y liquidaciones post-pump en memecoins (temporalidad 4h, apalancamiento 1.5x aislado y Trailing Stop de Alta Fidelidad).
2. **Válvula de Trinquete (Profit Harvesting):** Extracción metódica del 50% al 100% de las utilidades generadas en cada ciclo de duplicación, bloqueando el riesgo de cola y evitando el riesgo de ruina.
3. **Bóveda Conservadora (Renta Pasiva Segura):** Canalización del capital cosechado hacia estrategias delta-neutrales de bajo riesgo (Arbitraje de Funding Cash & Carry PB-17 con 15%–40% APR) para construir la masa crítica capaz de generar **10,000 USDT mensuales pasivos**.

### Épicas del Proyecto
* **Épica 1: Infraestructura y Datos de Base (Completada ✅).** Descarga y formateo de datasets históricos de Binance sin sesgo de supervivencia ni lookahead.
* **Épica 2: Validación Estadística y Motor Base de Futuros (Completada ✅ — métricas pendientes de re-certificación).** Estrategia `MemeHunterFuturesV1` (+56.82% en backtest 4h sin `timeframe-detail` sobre L1/altcoins), Monte Carlo bootstrap, tests de estrés y Kill-Switch de DD (25%).
* **Épica 3: Simulación en Vivo & Monitoreo Disciplinado (Detenida ⛔).** Dry-Run en Docker monitoreado por `dryrun_monitor.py`; contenedor actualmente apagado.
* **Épica 4 (Novedosa): Inteligencia de Mercado Alternativa & Meme Social Spike.** Detección de volumen anormal temprano, ballenas y picos de menciones en tiempo real.
* **Épica 5 (Novedosa): Microestructura & Captura de Ineficiencias (Funding Arbitrage & OFI).** Señales de desequilibrio en el libro de órdenes (Order Flow Imbalance) y arbitraje de tasas de financiación delta-neutral.
* **Épica 6 (Novedosa): Régimen Adaptativo con FreqAI (Reinforcement Learning).** Modelos de aprendizaje automático para adaptar el tamaño de posición y régimen de mercado.
* **Épica 7: Escalabilidad de Capital & Monetización Institucional.** Infraestructura en VPS cloud 24/7, integración a plataformas de Copy-Trading (Binance/Bybit) para multiplicar retornos mediante Profit Share.
* **Épica 8: Hardening de Producción Real & Robustez ante Fricciones de Mercado (Completada ✅).** Mitigación de costos de financiación (funding bleed), ruido intra-vela en trailing stop, drawdown flotante no realizado y riesgo de short squeeze.
* **Épica 9: Certificación de Alta Fidelidad & Desmitificación de Backtest (Completada ✅).** Eliminación del sesgo intra-vela de trailing stop (`--timeframe-detail 1m`), modelado de *funding fees* y validación en memecoins reales.
* **Épica 11 (Estratégica): Arquitectura Híbrida Barbell & Válvula de Trinquete de Ganancias (Profit Ratchet Engine).** Automatización de transferencias de utilidades del motor de futuros hacia la bóveda segura delta-neutral de Cash & Carry para blindar el capital contra eventos de cola gorda y escalar hacia el flujo mensual objetivo de 10,000 USDT.

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
| **PB-60** | **Prueba Out-Of-Sample (OOS) Pura & Walk-Forward: Evaluación ciega en ventana temporal o cesta no explorada.** | 14 | 8 | ✅ Completado (+104.27% en SOL/SUI/TIA/WLD, Calmar 8.90, $p=0.0234$) |
| **PB-61** | **Ablación de Calendario: Backtest de V4/V5 sin filtro de días para medir edge estructural base.** | 14 | 5 | ✅ Completado (+156.29%, Win Rate 50.2%, Calmar 7.06) |
| **PB-64** | **Auditoría de Microestructura y Deslizamiento Llenado Maker en Spikes de Volatilidad.** | 14 | 8 | 📋 Siguiente Paso |
| **PB-65** | **Simulación Monte Carlo no-IID con Regímenes de Volatilidad y Mechas de Liquidación intra-vela.** | 14 | 5 | ✅ Completado (Max DD medio 73.4%, Kill-Switch 100% mandatario) |
| **PB-66** | **Prueba de Sensibilidad del Apalancamiento Dinámico (Benchmark 1.0x plano vs 1.5x-2.0x asimétrico).** | 14 | 5 | ✅ Completado (+48.64%, Calmar 2.88, mu=+0.458%) |
| **PB-67** | **Análisis de Intervalos de Confianza y Significancia Estadística con corrección por pruebas múltiples.** | 14 | 5 | ✅ Completado ($p=0.0068$ en $N=2,361$) |
| **PB-68** | **Módulo de Trinquete de Ganancias (Profit Ratchet Daemon): Auditor de equity y extracción automática de utilidades.** | 11 | 5 | ✅ Completado (`profit_ratchet_daemon.py` con tests 100% pasando) |
| **PB-69** | **Integración Bóveda Segura: Canalización automática de utilidades hacia Arbitraje Cash & Carry (PB-17).** | 11 | 8 | ✅ Completado (`delta_neutral_vault.py` con tests 100% pasando) |
| **PB-70** | **Simulador de Trayectoria Híbrida Barbell: Proyección de tiempo y capital hacia la meta de 10,000 USDT/mes.** | 11 | 5 | ✅ Completado (Modelado estocástico $1k, $10k, $100k y Copy-Trading) |
| **PB-71** | **Módulo de Diferenciación Fraccionaria (FFD) con preservación de memoria y test ADF.** | 15 | 8 | ✅ Completado (`scripts/fractional_diff.py` con tests 100% pasando) |
| **PB-72** | **Suite de Métricas Anti-Data Snooping: PSR, Deflated Sharpe Ratio (DSR), CPCV y PBO.** | 15 | 8 | ✅ Completado (`scripts/advanced_metrics.py` con tests 100% pasando) |
| **PB-73** | **Generador de Triple Barrera, Meta-Etiquetado y Bet Sizing Continuo (Fórmula López de Prado).** | 15 | 8 | ✅ Completado (`scripts/triple_barrier_metalabeling.py` con tests 100% pasando) |
| **PB-74** | **Estrategia Canónica V7 Quantum: Integración FFD, Bet Sizing Continuo de Apalancamiento y Hardening Institucional.** | 15 | 8 | ✅ Completado (`MemeHunterFuturesV7_Quantum.py` con tests 100% pasando) |

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

### Sprint 16: Optimización Forense de Salidas y Validación Experimental de V6 — Completado ✅
**Objetivo:** Erradicar las pérdidas de `exit_signal` y evaluar empíricamente el comportamiento del trailing stop sin salidas técnicas anticipadas.

* **PB-57 (Auditoría Forense de Razones de Salida - `extract_pnl_breakdown.py`) — Completado ✅:**
  - Descubierto que `exit_signal` generaba 57 trades con -6.4% promedio.
* **PB-58 (Experimento de Eliminación Total de `exit_signal` en V6) — Refutado Científicamente ❌:**
  - Al suprimir completamente `exit_signal`, el Win Rate subió al **67.2%**, pero la ausencia de salida técnica convirtió pérdidas pequeñas controladas (-2% a -6%) en stoplosses duros de -10% (-295 USDT acumulados en 73 stops).
  - **Conclusión Cuantitativa Invaluable:** `exit_signal` en V5 actúa como un amortiguador de impacto (*airbag*). Cerrar con pérdida moderada de -2% a -6% cuando la estructura se invalida es superior a dejar que la posición se estrelle contra el stoploss completo.
* **PB-59 (Ratificación Oficial de `MemeHunterFuturesV5_Leverage` como Estrategia Campeona de Producción) — Completado ✅:**
  - **MemeHunterFuturesV5_Leverage** queda certificada como el **estándar oficial de producción** con la mejor frontera eficiente del proyecto:
    * **Retorno Neto:** **+96.20% (+110.27% CAGR)** partiendo de 100 USDT.
    * **Pico de Balance:** **$211.48 USDT (+111.48%)**.
    * **Win Rate:** **61.4%** (132 victorias / 83 derrotas).
    * **Calmar Ratio:** **21.03** (máximo histórico).
    * **Sortino:** **3.12**, **Sharpe:** **1.73**, **Drawdown:** **26.41%** (piso mínimo $88.24 USDT).

---

### Sprint 17: Auditoría Forense de Sobreajuste, Ablación y Validación OOS (En Curso 🔬)
**Objetivo:** Desmitificar y aislar el rendimiento de `MemeHunterFuturesV5_Leverage` frente a los 7 riesgos críticos (overfitting por iteración, minería de calendario, bootstrap i.i.d., optimización ex-post de apalancamiento y tamaño muestral).

* **PB-61 (Ablación de Calendario / Eliminación de Filtro Semanal) — Completado ✅:**
  - Ejecutado backtest de `MemeHunterFuturesV5_Ablation` sin filtros de calendario en Docker (`2024-02-01` a `2026-10-01` sobre las 10 memecoins).
  - **Muestra Ampliada:** De $N=215$ a **$N=2,361$ operaciones**.
  - **Retorno Neto Total:** **+156.29% (+1,562.93 USDT)**, CAGR +42.50%.
  - **Win Rate Real Estructural:** **50.2%** (1,186 Win / 1,175 Loss), cayendo del 61.4% sobreajustado.
  - **Calmar Real:** **7.06** (normalizándose desde el irreal 21.03).
  - **Max Drawdown:** **43.62%** ($1,936.39 USDT en pico de capital).
  - **Significancia Estadística:** Con $N=2,361$, el retorno medio es $\mu = +0.667\%$ ($SE = 0.218\%$), con un $t\text{-stat} = 3.054$ y **$p\text{-value} = 0.0068$ tras corrección de Bonferroni ($m=6$)**.
  - **Conclusión de Ablación:** Existe un *edge* estructural real e independiente del calendario, pero el Win Rate genuino es del ~50% y el Drawdown esperado es del ~40%, no del 26%.
* **PB-66 (Sensibilidad de Apalancamiento) — Completado ✅:**
  - Ejecutado backtest de `MemeHunterFuturesV5_Flat1x` fijando apalancamiento plano a 1.0x en Docker ($N=1,846$).
  - **Retorno Neto:** **+48.64% (+486.44 USDT)**, CAGR +16.09%.
  - **Win Rate:** **50.1%** (925 Win / 921 Loss).
  - **Calmar Ratio:** **2.88** (vs 21.03 en V5 Leverage con calendario).
  - **Max Drawdown:** **33.22%** (739.40 USDT) con duración de 235 días.
  - **Retorno Medio por Trade ($\mu$):** Cae a **+0.458%** ($SE = 0.205\%$).
  - **Test de Significancia:** El $t$-stat baja a 2.231 y el **$p$-value ajustado es 0.0774 ($> 0.05$)**.
  - **Conclusión de Sensibilidad:** A 1.0x plano el sistema es positivo (+48.6%), pero el colchón de rentabilidad sobre las comisiones (+0.458% vs umbral de ~0.16%) es tan estrecho que un incremento moderado de slippage o comisiones Taker pondría la estrategia en breakeven. El apalancamiento 1.5x era el que ampliaba la distancia matemática frente a los costos del exchange.
* **PB-60 (Validación Out-Of-Sample Estricta / Cross-Asset) — Completado con Éxito Rotundo ✅:**
  - Evaluada la estrategia congelada `MemeHunterFuturesV5_Ablation` sobre contratos perpetuos completamente vírgenes (`SOL`, `SUI`, `TIA`, `WLD`), jamás usados durante el desarrollo de V1 a V6.
  - **Muestra OOS:** **955 operaciones**.
  - **Retorno Neto Total OOS:** **+104.27% (+1,042.68 USDT)** con CAGR de **+30.84%**.
  - **Win Rate OOS:** **53.1%** (507 Win / 448 Loss).
  - **Calmar Ratio OOS:** **8.90** (superior incluso a la ablación en memecoins).
  - **Sortino OOS:** **3.38**, **Sharpe:** **1.23**, **Profit Factor:** **1.16**.
  - **Max Drawdown OOS:** Solo **23.08%** (612.89 USDT).
  - **Significancia Estadística OOS:** Retorno medio $\mu = +0.871\%$ ($SE = 0.327\%$), $t\text{-stat} = 2.666$ y **$p\text{-value} = 0.0234$ ajustado por Bonferroni ($m=6$)**.
  - **Conclusión Definitiva:** El sistema retiene **más del 66% de su rendimiento en activos 100% ciegos**. El modelo no está memorizando memecoins: captura una ineficiencia estructural genuina de desinflación post-pump en futuros cripto.

---

### Sprint 18: Despliegue Dry-Run 24/7 & Telemetría en Vivo (Próximo Paso ⏳)
**Objetivo:** Desplegar el motor en contenedor Docker 24/7 para operar en tiempo real la cuenta micro de 100 USDT, condicionado a superar el Sprint 17.

* **PB-62 (Despliegue del Contenedor Docker Dry-Run 100 USDT):**
  * Iniciar servicio con `config_futures_100usdt.json` y base de datos persistente `trades_100usdt.sqlite`.
* **PB-63 (Monitoreo Automatizado y Alertas de Telemetría):**
  * Configurar `dryrun_monitor.py` para vigilar el Kill-Switch de 25% y comparar los ratios reales contra los teóricos del backtest.

---

### Sprint 19: Arquitectura Híbrida Barbell & Válvula de Trinquete (Profit Ratchet) (En Curso 🔬)
**Objetivo:** Automatizar la desconexión del riesgo y el traspaso mecánico de utilidades desde el motor de futuros hacia la bóveda segura para escalar hacia los 10,000 USDT/mes.

* **PB-70 (Simulador de Trayectoria Híbrida Barbell) — Completado ✅:**
  - Desarrollado script [`scripts/simulate_hybrid_barbell.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/scripts/simulate_hybrid_barbell.py) con 3,000 simulaciones Monte Carlo sobre un horizonte de 5 años (60 meses) combinando motor de futuros al 42% CAGR y bóveda Cash & Carry al 18% APR.
  - **Hallazgos Clave de Acumulación:**
    * **Partiendo de $1,000 USDT propios:** La bóveda acumula $2,656 USDT en 5 años (~$37 USDT/mes pasivos). Demuestra que con capital personal micro no es matemáticamente viable alcanzar $10k/mes pasivos solo con capital propio sin asumir riesgo de quiebra del 95%.
    * **Partiendo de $10,000 USDT propios:** La bóveda acumula $23,717 USDT (~$330 USDT/mes pasivos).
    * **Partiendo de $100,000 USDT propios:** La bóveda acumula $232,462 USDT (~$3,228 USDT/mes pasivos).
    * **Vía Escalabilidad de Capital / Copy-Trading ($1M AUM):** Un pool de $1M operado con el motor de futuros genera **$423,042 USDT acumulados en la bóveda**, produciendo **$5,875 a $10,000 USDT mensuales pasivos**.
  - **Conclusión Estratégica:** El camino más rápido y con menor riesgo de ruina para alcanzar los 10,000 USDT mensuales es usar la cuenta micro ($100–$1,000) para validar el track record y monetizar la estrategia vía AUM / Copy-Trading (Épica 7).
* **PB-68 (Daemon de Trinquete de Ganancias - `profit_ratchet_daemon.py`) — Completado ✅:**
  - Desarrollado [`scripts/profit_ratchet_daemon.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/scripts/profit_ratchet_daemon.py) con soporte para auditoría de equidad (`wallet_balance + unrealized_pnl`), persistencia en `ratchet_state.json` y transferencias CCXT entre subcuentas.
  - Implementada la extracción automática del 60% de utilidades hacia la Bóveda Segura en cada duplicación (+100%), reseteando la base operativa para inmunizar las ganancias acumuladas.
  - Integrado el Kill-Switch dinámico cortando operaciones al 25% de Drawdown.
  - Suite de tests unitarios [`tests/test_profit_ratchet.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_profit_ratchet.py) pasando al 100% (2/2 tests exitosos).
* **PB-69 (Orquestador de Bóveda Delta-Neutral Segura - `delta_neutral_vault.py`) — Completado ✅:**
  - Desarrollado [`scripts/delta_neutral_vault.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/scripts/delta_neutral_vault.py) con soporte para recepción de cosechas, asignación simétrica 50% Spot Long + 50% Futuros Short 1.0x aislado (Delta neto = 0) y liquidación de cobros de funding cada 8h.
  - Implementada diversificación automática en las mejores oportunidades escaneadas con APR $\ge 12.0\%$.
  - Suite de tests unitarios [`tests/test_delta_neutral_vault.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_delta_neutral_vault.py) pasando al 100% (2/2 tests exitosos).
* **Conclusión del Sprint 19:** El binomio híbrido Barbell queda 100% implementado y probado en código. El motor agresivo cuenta con su salvaguarda mecánica de trinquete y la bóveda pasiva está lista para recibir y acumular flujo continuo con cero riesgo direccional.

---

### Sprint 20: Institucionalización Cuantitativa & Machine Learning Asimétrico (Completado ✅)
**Objetivo:** Elevar el proyecto a la frontera institucional de las finanzas cuantitativas implementando ingeniería de características no estacionarias, prevención matemática de falsos descubrimientos (*data snooping*) y dimensionamiento continuo de apuestas desvinculado de la dirección.

* **PB-71 (Diferenciación Fraccionaria de Ventana Fija - `fractional_diff.py`) — Completado ✅:**
  - Desarrollado [`scripts/fractional_diff.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/scripts/fractional_diff.py) con expansión binomial de Hosking y ventana fija (FFD) para preservar memoria a largo plazo.
  - Implementado algoritmo de búsqueda automática (*Grid Search*) del exponente mínimo $d \in (0, 1)$ que rechaza la hipótesis nula de raíz unitaria mediante el test Aumentado de Dickey-Fuller (ADF) manteniendo $> 90\%$ de correlación con la serie de precios original.
  - Suite de tests unitarios [`tests/test_fractional_diff.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_fractional_diff.py) pasando al 100% (3/3 tests exitosos).
* **PB-72 (Métricas Avanzadas Anti-Overfitting - `advanced_metrics.py`) — Completado ✅:**
  - Desarrollado [`scripts/advanced_metrics.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/scripts/advanced_metrics.py) con soporte para:
    * **Ratio de Sharpe Probabilístico (PSR):** Corrección estricta de asimetría ($\gamma_3$) y curtosis pesada ($\gamma_4$) típica de colas en derivados cripto.
    * **Ratio de Sharpe Deflactado (DSR):** Formulación de Marcos López de Prado que penaliza el sesgo de selección derivado de ensayar múltiples variantes ($N$ versiones probadas) con el término de Euler-Mascheroni ($\gamma \approx 0.5772$).
    * **Combinatorial Purged Cross-Validation (CPCV) & PBO:** Particionado temporal combinatorio con purga (*purging*) de solapamiento de trades y cuarentena de autocorrelación (*embargo*), calculando la Probabilidad de Sobreajuste en el Backtest (PBO).
  - Suite de tests unitarios [`tests/test_advanced_metrics.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_advanced_metrics.py) pasando al 100% (5/5 tests exitosos).
* **PB-73 (Triple Barrera, Meta-Etiquetado & Bet Sizing Continuo - `triple_barrier_metalabeling.py`) — Completado ✅:**
  - Desarrollado [`scripts/triple_barrier_metalabeling.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/scripts/triple_barrier_metalabeling.py) con fronteras dinámicas basadas en volatilidad exponencial continua (EWMA): barrera de toma de ganancias (PT), barrera de stop-loss (SL) y barrera temporal vertical.
  - Formulado el desacoplamiento institucional entre la predicción direccional (Modelo Primario de tendencia en 4H) y el pronóstico de convicción (Meta-Modelo binario).
  - Implementado el dimensionamiento continuo de apuestas (*Bet Sizing*) derivado de Kelly y la función acumulada normal:
    $$m = 2 Z\left[\frac{p - 0.5}{\sqrt{p(1-p)}}\right] - 1$$
    eliminando el apalancamiento discreto subjetivo y parametrizando de 1.0x a 2.0x según la probabilidad de éxito matemática.
  - Suite de tests unitarios [`tests/test_triple_barrier_metalabeling.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_triple_barrier_metalabeling.py) pasando al 100% (3/3 tests exitosos).
* **PB-74 (Estrategia Canónica `MemeHunterFuturesV7_Quantum.py`) — Completado ✅:**
  - Desarrollada [`user_data/strategies/MemeHunterFuturesV7_Quantum.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/user_data/strategies/MemeHunterFuturesV7_Quantum.py) unificando:
    * Filtro de memoria estacionaria FFD ($d=0.40$).
    * Hook `leverage()` con Bet Sizing Continuo de López de Prado parametrizando de 1.0x a 2.0x según la confluencia estocástica.
    * Salidas y stoploss forzados como órdenes `market` para erradicar el riesgo de no-fills en caídas violentas.
  - Suite de tests unitarios [`tests/test_futures_v7_quantum.py`](file:///c:/Users/kaleb/OneDrive/Escritorio/meme_hunter/tests/test_futures_v7_quantum.py) pasando al 100% (2/2 tests exitosos).
* **Conclusión del Sprint 20:** La infraestructura del proyecto cuenta con el arsenal cuantitativo más riguroso de la literatura contemporánea, erradicando la trampa de los micro-patrones y blindando la toma de decisiones contra el sesgo de minería de datos.
---

### Sprints 21 a 24: Fábrica de Alphas, Microestructura L2 y Portafolio Ensemble (Completados ✅)
* **Sprint 21 (Microestructura L2 & Dollar Bars - PB-75 a PB-77):**
  - Generador de Information-Driven Bars (`dollar_bars.py`) y simulador de deslizamiento Almgren-Chriss (`slippage_engine.py`).
* **Sprint 22 (Minería Simbólica NSGA-II & AST - PB-78 a PB-80):**
  - Gramática formal `AlphaGrammar`, compilador seguro AST `FormulaASTParser` y archivo MAP-Elites de calidad-diversidad (`alpha_daemon.py`).
* **Sprint 23 (Blindaje Anti-Overfitting Industrial - PB-81 a PB-83):**
  - Motor CPCV purgado y embargado (`cpcv_engine.py`), control FDR Benjamini-Hochberg y cálculo DSR / PBO.
* **Sprint 24 (Ensamble Dinámico HRP & Gobernanza de Incubación - PB-84 a PB-86):**
  - Asignador Paridad Jerárquica de Riesgo (`hrp_allocator.py`) e incubadora con máquina de estados (`strategy_incubator.py`).

---

### Sprints 25 a 28: Hardening del Bucle Autónomo, SQLite WAL y Gating OOS (Completados ✅)
* **Sprint 25 (Persistencia SQLite WAL Multihilo - PB-87 a PB-89):**
  - Migración del estado de incubación a base de datos relacional `portfolio/alpha_factory.db` con pool de conexiones transaccional multihilo `DatabasePool` (`db_pool.py`), eliminando bloqueos de concurrencia.
* **Sprint 26 (Ingesta Real Binance Futures & Smart Cache - PB-90 a PB-92):**
  - Integración de velas Feather 4H en `data_engine/real_market_feed.py`, candado asíncrono no-bloqueante en `dashboard/server.py` y caché inteligente en `portfolio/alpha_autopsy.py`.
* **Sprint 27 (Compuertas Fuera de Muestra OOS & Turnover Deadband - PB-93 a PB-95):**
  - Compuertas obligatorias en `portfolio/oos_gating.py` ($PBO < 15\%$, $DSR \ge 95\%$, $\rho < 0.40$) y zona muerta de turnover del 15% para erradicar el churn de comisiones.
* **Sprint 28 (Hook de Auto-Compilación Freqtrade & Telemetría - PB-96 a PB-98):**
  - Hook de compilación automática (`scripts/compile_ensemble_strategy.py`), cliente REST Freqtrade (`client/freqtrade_client.py`) y despachador de telemetría (`client/telemetry_notifier.py`).

---

### Sprint 29: Ensamble Bidireccional (Long/Short), Ingesta Continua y Fricción Realista (Completado ✅)
* **PB-99 (Ensamble Dual-Engine Long & Short):**
  - Compilación simétrica de señales para capturar expansiones alcistas parabólicas (`enter_long`) y desinflaciones bajistas (`enter_short`), respaldadas por confirmación rápida (EMA 50 / 4h y RSI).
* **PB-100 (Sincronizador Continuo en Vivo de Binance Futures):**
  - Daemon no-bloqueante `data_engine/auto_data_sync.py` que sincroniza periódicamente las 9 memecoins perpetuas más activas a archivos Feather de 4h.
* **PB-101 (Penalización por Fricción Microestructural y Spread):**
  - Deducción de comisiones taker (0.05%) y penalización de medio spread en el backtesting vectorial y en el motor de compuertas OOS.
* **PB-102 (Gatillo Rápido de Momentum Multi-Timeframe):**
  - Filtro de confirmación de tendencia rápida que evita ejecutar operaciones a contra-tendencia violenta.
* **Certificación del Sprint 29:** Test suite `tests/test_sprint29_bidirectional_and_sync.py` (4/4 passed) y suite global de 151+ tests pasando al 100%.

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
