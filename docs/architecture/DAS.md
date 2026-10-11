# Documento de Arquitectura de Software (DAS)
**Proyecto**: meme_hunter  
**Versión**: 4.0 (Arquitectura Cuantitativa de Futuros USDT-M, Microestructura y Edge Asimétrico)

## 1. Introducción
### 1.1 Propósito
Este documento describe la arquitectura del sistema **meme_hunter**. Tras validar que el mercado Spot sufría severo desgaste por sesgo unidireccional y comisiones, la arquitectura evolucionó hacia un **sistema cuantitativo bidireccional (Long/Short) sobre Futuros USDT-M (Binance)** con margen aislado 1.0x (cero riesgo de liquidación forzada), complementado con una suite de microestructura (Order Flow Imbalance, Funding Arbitrage y Clasificación de Régimen).

### 1.2 Alcance
El sistema descansa sobre el framework de ejecución **Freqtrade** y la librería **CCXT**, complementado por módulos satélite especializados en Python. La estrategia central (`MemeHunterFuturesV1`) ejecuta señales técnicas con dimensionamiento asimétrico (1.15x en Shorts, 0.70x en Longs) y protecciones nativas (Kill-Switch al 25% de Drawdown, StoplossGuard).

### 1.3 Universo Operado
El universo activo se compone de contratos perpetuos USDT-M en Binance filtrados dinámicamente:
* **Filtro de Liquidez Estricto:** Mínimo $1,000,000 USDT de volumen en 24h para excluir trampas de liquidez y tokens manipulados de baja capitalización.
* **Margen Aislado 1.0x:** Operación desapalancada real que elimina por diseño matemático la liquidación forzada.

---

## 2. Metas y Restricciones Arquitectónicas
- **Pragmatismo sobre Complejidad**: Se descarta la Capa Táctica en Rust, la mensajería IPC en Redis y el "Zero-REST". En un marco temporal de 4 horas, la infraestructura de Freqtrade en Python es sobradamente rápida y elimina puntos de fallo innecesarios.
- **Validación Estadística Estricta**: La arquitectura debe permitir descargas masivas de datos limpios, backtesting con granularidad fina (evitando espiar datos del futuro o *peeking* intra-vela) y validación fuera de muestra (*walk-forward*).
- **Sobrevivencia al Slippage**: La lógica debe estar diseñada asumiendo que los spreads y el deslizamiento (slippage) penalizarán agresivamente cada entrada y salida a mercado.
- **Reproducibilidad**: Cada resultado de backtest debe poder reproducirse a partir de un commit de Git, un archivo de configuración versionado y una huella (hash) del dataset utilizado.

---

## 3. Vista Lógica (Componentes)

### 3.1 Motor Core (Freqtrade Framework)
- **Enrutamiento y Estado**: El ciclo de vida de las órdenes, conexiones WebSocket/REST a Binance y la rehidratación del estado (vía SQLite) son manejados nativamente por Freqtrade.
- **Risk Management Integral**: Configuración del *Stoploss* paramétrico y *Trailing Stop*. Se evaluará `stoploss_on_exchange` en Spot, delegando las órdenes limitadas al exchange cuando Freqtrade lo soporte de forma nativa, y documentando su comportamiento en el backtest (que no lo simula con fidelidad).
- **Protecciones de Cartera**: Uso de las *Protections* nativas de Freqtrade: `StoplossGuard`, `MaxDrawdown`, `CooldownPeriod` y `LowProfitPairs`.
- **Dimensionamiento de Posición**: Se fijan explícitamente `max_open_trades`, `stake_amount` y un límite de exposición total del capital. Ningún parámetro queda en valores por defecto sin justificación.

### 3.2 Capa Estratégica (Nuestra Propiedad Intelectual)
- **Módulo `IStrategy` (Python)**: Archivo dedicado que contiene los cálculos deterministas mediante `pandas-ta` (MACD, RSI, ATR). Aquí se programa la lógica de cruces y señales.
- **Hipótesis de Edge (a completar antes de programar)**: Debe redactarse por escrito, antes de ver resultados, *por qué* la combinación de indicadores debería tener ventaja en el universo elegido (p. ej. momentum de tendencia tras expansión de volatilidad medida con ATR). Sin hipótesis explícita, la estrategia no pasa a backtest.
- **Presupuesto de Experimentos**: Se fija un número máximo de variantes de estrategia y un máximo de ejecuciones de `hyperopt` para limitar el *data snooping*. Cada variante probada se registra, incluidas las descartadas.
- **Filtro de Universo Dinámico**: Para combatir el sesgo de supervivencia en backtesting, no basta con el `VolumePairList` actual; se requiere descargar un universo de activos reconstruido históricamente sin información futura, operando el Top N de monedas con mayor volumen en cada época específica. Freqtrade no lo ofrece de forma nativa, por lo que es un **entregable propio** (script de construcción de universo por ventana temporal, con listas de pares por periodo) y una tarea explícita de la Fase 0.
- **Rol del LLM (Opcional)**: Modelos como Qwen 2.5 Coder o similares no se usarán para proveer señales automáticas. Su uso queda relegado a la generación asíncrona de resúmenes o reportes para revisión manual posterior, completamente ajenos al loop de ejecución.

### 3.3 Interfaz de Usuario y Notificaciones
- **FreqUI**: Dashboard web incluido de forma nativa en Freqtrade para monitoreo visual, registro de logs y evaluación del rendimiento de la estrategia en tiempo real.
- **Telegram Bot nativo**: Freqtrade enviará notificaciones instantáneas sobre operaciones, cierres por trailing stop y permitirá envío de comandos básicos (`/status`, `/forcesell`).

### 3.4 Módulos Satélite Cuantitativos y de Microestructura (`scripts/`)
- **Meme Sentinel (`scripts/meme_sentinel.py`)**: Monitorea el universo USDT-M calculando volumen relativo (RVOL) para detectar anomalías y rupturas de volatilidad tempranas antes del cierre de velas de 4H.
- **Radar Viral On-Chain (`scripts/dex_viral_radar.py`)**: Conexión a la API pública de DexScreener para capturar tracción en Solana/Base/Ethereum y cuantificar presión compradora.
- **Funding Arbitrage (`scripts/funding_arbitrage.py`)**: Escáner de oportunidades Cash & Carry Delta-Neutral (Short Futuros 1x + Spot Long) para extraer rendimiento pasivo de Funding Rates extremos (50%–150% APR) con $0 riesgo direccional.
- **Order Flow Imbalance (`scripts/order_flow_imbalance.py`)**: Análisis de microestructura N2, cálculo de OFI y Micro-Price para optimizar la colocación de órdenes límite pasivas (Maker).
- **Clasificador de Régimen (`scripts/regime_classifier.py`)**: Clasificación dinámica de mercado (`BULL_MOMENTUM`, `BEAR_BLEED`, `CHOPPY_RANGE`) con adaptación de riesgo y pausa en regímenes adversos.
- **Auditor de Dry-Run (`scripts/dryrun_monitor.py`)**: Evaluación continua de los trades simulados almacenados en SQLite contra los criterios de aceptación estadística.

---

## 4. Flujo de Datos y Rigor del Backtest
Para evitar autoengaños estadísticos, se aplican las siguientes reglas obligatorias:
1. **Granularidad Intravela**: Durante el backtesting de 4H, se empleará el flag `--timeframe-detail 1m` sabiendo que, aunque mejora la simulación, no reconstruye la liquidez ni el orden exacto a nivel de milisegundos. Esto exige descargar datos de 1m de todo el universo; el almacenamiento y tiempo de descarga deben estimarse y reservarse en la Fase 0.
2. **Pruebas de Sesgo de Anticipación**: Ejecución obligatoria del análisis de *lookahead-bias* y de *recursive-analysis* de Freqtrade para asegurar que la estrategia no "espía" el futuro.
3. **Escenarios de Costes**: Se modelarán por separado escenarios "Normales" y "Adversos", distinguiendo claramente entre comisión de entrada, comisión de salida, *spread* y *slippage*, evitando contabilizar dos veces el mismo costo.
4. **Conjunto de Retención Final (Hold-out)**: Un tramo final de datos (p. ej. últimos 6–12 meses) permanece intocable hasta que la estrategia esté congelada. Se evalúa una sola vez; si falla, la estrategia se descarta y no se reajusta sobre ese tramo.
5. **Integridad de Datos**: Se validan huecos, velas duplicadas, pares deslistados incompletos y cambios de símbolo antes de cualquier backtest.

---

## 5. Fases de Despliegue y Pruebas

**Fase 0: El Experimento (Local)**
- Descarga del histórico de Binance Spot (`data.binance.vision`) y construcción del universo reconstruido por época.
- Validación *Out-of-Sample*, *Walk-Forward* y hold-out final.
- **Métricas de Rechazo**: La estrategia se descarta si no supera el Benchmark de "Comprar y Mantener" **y** una estrategia ingenua de referencia (ej. cruce simple de medias). Las operaciones (mínimo cientos) deben estar distribuidas en diferentes regímenes de mercado (alcista, bajista, lateral).
- **Umbrales Cuantitativos de Aprobación (propuestos; deben fijarse antes de ver resultados)**, calculados en el escenario de costes **Adverso**:

| Métrica | Umbral mínimo propuesto |
|---|---|
| Número de operaciones | ≥ 300 |
| Expectancy neta por operación | > 0 tras todos los costes |
| Profit Factor | ≥ 1.3 |
| Sortino | ≥ 1.0 |
| Max Drawdown | ≤ 25 % (o el límite de riesgo que defina el usuario) |
| Rendimiento ajustado por riesgo vs. Buy & Hold | Superior en OOS y en hold-out |
| Consistencia Walk-Forward | ≥ 60 % de las ventanas con resultado positivo |

**Fase 1: Dry-Run Prolongado (Paper Trading)**
- Freqtrade se instanciará en un servidor estándar en modo `dry_run=True`.
- Duración mínima: **8 semanas** (o un mínimo de 50 operaciones, lo que ocurra último).
- Operará contra el flujo de mercado en vivo para registrar explícitamente las diferencias (desviaciones) entre las ejecuciones simuladas por el backtest y las señales reales en vivo.
- **Criterio de salida**: la desviación de rendimiento y de precio de ejecución respecto a lo que el backtest habría producido sobre el mismo periodo debe mantenerse dentro de una tolerancia definida (propuesta: ≤ 20 % del rendimiento esperado y señales coincidentes en ≥ 90 % de los casos).

**Fase 2: Capital Real Mínimo (Condicional)**
- Solo se activa si las Fases 0 y 1 cumplen sus criterios.
- Capital pequeño y acotado, que el usuario esté dispuesto a perder por completo, con `max_open_trades` reducido.
- Objetivo: medir slippage y fallos de ejecución reales, que el dry-run no revela. Se compara contra el escenario "Adverso" del backtest.
- **Kill-switch**: se detiene automáticamente el bot si se supera el drawdown máximo definido o si el slippage real excede el modelado en un margen preestablecido.

---

## 6. Decisiones Descartadas
Los siguientes elementos quedan **fuera de alcance** para la viabilidad de las Fases 0, 1 y 2:
- Capa táctica en Rust, mensajería IPC en Redis y "Zero-REST".
- Interfaz de escritorio PyQt6.
- Firmas Ed25519 complejas.
- Conexiones VPN/Tailscale para la interfaz.
- Alquiler de servidores en Tokio y colocalización geográfica.
- Señales de trading generadas por LLM.

## 7. Riesgos Abiertos
- Definir el universo definitivo (U1 vs. U2) y su tamaño N.
- Disponibilidad y calidad del histórico de pares deslistados.
- Redactar la hipótesis de edge y fijar los umbrales numéricos antes del primer backtest.
- Estimar almacenamiento y tiempo de descarga de datos 1m.
