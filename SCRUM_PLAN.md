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
| **PB-15** | **Módulo Meme Sentinel: Detección de volumen inusual y picos de volatilidad temprana.** | 4 | 8 | 📋 Backlog |
| **PB-16** | **Integración de Sentimiento y Narrativa Web3 (Telegram/X API o DEX aggregators).** | 4 | 13 | 📋 Backlog |
| **PB-17** | **Motor de Arbitraje de Funding Rate Delta-Neutral (Futuros vs Spot).** | 5 | 8 | 📋 Backlog |
| **PB-18** | **Microestructura Nivel 2: Order Flow Imbalance (OFI) y Cumulative Volume Delta (CVD).** | 5 | 13 | 📋 Backlog |
| **PB-19** | **Integración FreqAI: Modelos predictivos LightGBM / CatBoost para cambio de régimen.** | 6 | 13 | 📋 Backlog |
| **PB-20** | **Aprovisionamiento en VPS Ubuntu 24/7 con `deploy_vps.sh` y hardering de seguridad.** | 7 | 5 | 📋 Backlog |
| **PB-21** | **Conexión a Copy-Trading (Binance / Bybit) para escala de capital vía Profit Share.** | 7 | 8 | 📋 Backlog |

---

## 3. Planificación de Sprints

### Sprint 1 al 3: Fundación y Validación Cuantitativa (Completados ✅)
* Dataset sin sesgo de supervivencia en 68 pares.
* Validación del motor bidireccional en futuros: +56.82% de rendimiento neto con Longs y Shorts aislados 1.0x.
* Simulación de Monte Carlo y blindaje contra ruina. Kill-Switch implementado y validado en tests unitarios.

### Sprint 4: Estabilización Operativa y Dry-Run Dual (Actual 🔄)
**Objetivo:** Monitorear la microestructura real de Binance en modo simulado y mantener activo el bot.
* **PB-12 ✅:** Contenedor `meme_hunter_futures` activo en Docker con FreqUI en puerto 8081.
* **PB-13:** Configurar credenciales de Telegram en `.env` para monitoreo remoto.
* **PB-14 🔄:** Auditoría continua con `scripts/dryrun_monitor.py`. (Semana 1 en curso).
* **PB-15 (Kill-Switch) ✅:** Latch en `user_data/KILL_SWITCH` si el drawdown realizado supera el 25%.

---

### Sprint 5: Módulo de Detección Temprana ("Meme Sentinel")
**Objetivo:** Capturar memecoins antes de que las velas de 4H reflejen el movimiento explosivo.
* **PB-15:** Crear sub-proceso que audite en tiempo real todas las monedas USDT-M de Binance filtrando:
  - Spike de volumen en velas de 1m/5m superior a 5x la media móvil de 24h.
  - Expansión de rango verdadero (True Range) sin retroceso inmediato.
* **PB-16:** Probar integración de fuentes de datos sociales o de DEX (Pump.fun / Raydium / DexScreener trends) para anticipar qué meme listado en futuros entrará en tendencia viral.

---

### Sprint 6: Microestructura y Captura de Funding Rate
**Objetivo:** Generar ingresos sin riesgo direccional o capturar rebotes con ventaja de libro de órdenes.
* **PB-17:** Diseñar estrategia Delta-Neutral que capture tasas de financiación desorbitadas en memecoins en momentos de euforia (apertura simultánea Spot Long + Futuros Short 1x).
* **PB-18:** Inyectar features de Order Flow Imbalance (OFI) para determinar si las órdenes pasivas (Maker) serán ejecutadas a favor antes de que cambie el spread.

---

### Sprint 7: Régimen Adaptativo con FreqAI
**Objetivo:** Eliminar los parámetros estáticos (RSI 56/76) y dejar que la IA ajuste el riesgo.
* **PB-19:** Configurar pipeline de FreqAI para entrenar clasificadores de régimen de mercado:
  - Régimen Alcista Explosivo (Full momentum).
  - Régimen de Invierno/Sangrado (Prioridad Shorts).
  - Régimen Lateral/Choppy (Pausa de operativa para proteger capital).

---

### Sprint 8: Despliegue Cloud y Multiplicador de Capital (Copy-Trading)
**Objetivo:** El camino real hacia el crecimiento financiero exponencial: gestionar capital externo de forma automatizada.
* **PB-20:** Despliegue en VPS (DigitalOcean / Hetzner / AWS) con el script `scripts/deploy_vps.sh`.
* **PB-21:** Publicación de la estrategia en el programa de Lead Trader de Binance o Bybit:
  - Mantener un Drawdown < 15% y Sortino > 1.5 para posicionarse en el Top Ranking de Copy Trading.
  - Monetizar mediante **Profit Sharing** (10% - 15% de los beneficios generados a los seguidores).

---

## 4. Definición de Hecho (DoD)
1. Código probado con tests unitarios (`pytest tests`).
2. Sin riesgo de liquidación forzada (Apalancamiento estricto 1.0x o estrategias delta-neutrales).
3. Todo cambio versionado y sincronizado en GitHub: [kalebCard/MemeHunter](https://github.com/kalebCard/MemeHunter).
