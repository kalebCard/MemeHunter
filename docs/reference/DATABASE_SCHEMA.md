---
id: REF-DB-001
title: Especificación Canónica de Base de Datos SQLite WAL (v8.0)
category: reference
version: 8.0
status: ACTIVE
last_updated: 2026-10-13
author: Quantitative Architecture & Systems Engineering Core
---

# 📦 Especificación Canónica de Base de Datos SQLite WAL

El almacenamiento canónico de Meme Hunter se consolida exclusivamente en `storage/meme_hunter.db` bajo el modo **Write-Ahead Logging (WAL)**, eliminando de raíz el anti-patrón de múltiples archivos JSON concurrentes.

---

## ⚙️ Pragmas Obligatorios

| PRAGMA | Valor | Propósito |
| :--- | :--- | :--- |
| `busy_timeout` | `15000` | Espera hasta 15 segundos ante bloqueos de escritura antes de lanzar excepción |
| `journal_mode` | `WAL` | Permite concurrencia total: múltiples lectores y un escritor sin contención |
| `synchronous` | `NORMAL` | Máximo rendimiento sin comprometer la durabilidad transaccional |
| `foreign_keys` | `ON` | Integridad referencial estricta |

---

## 🗄️ Esquema de Tablas Canónicas

### 1. `strategies`
Almacena el estado y métricas de cada estrategia en la incubadora de alfas.
* `strategy_id` (TEXT, PK): Identificador único del factor.
* `name` (TEXT, NOT NULL): Nombre descriptivo de la estrategia.
* `status` (TEXT, NOT NULL): Estado en el ciclo (`SANDBOX`, `LIVE`, `ALPHA_DECAY`, `RETIRED`).
* `target_capital_weight` (REAL): Peso asignado por el optimizador HRP [0.0 a 1.0].
* `backtest_sharpe` (REAL): Ratio de Sharpe histórico en muestra.
* `live_sharpe` (REAL): Ratio de Sharpe observado en tiempo real.
* `days_in_stage` (INTEGER): Días transcurridos en el estado actual.
* `decay_zscore` (REAL): Puntuación Z de degradación de señal.
* `last_audit_date` (TEXT): Fecha ISO de la última auditoría.
* `updated_at` (TEXT, NOT NULL): Marca temporal ISO UTC de última modificación.
* *Índice:* `idx_strategies_status ON strategies(status)`

### 2. `portfolio_allocations`
Registro inmutable de asignaciones y ponderaciones de capital de HRP y Riskfolio.
* `id` (INTEGER, PK AUTOINCREMENT)
* `timestamp` (TEXT, NOT NULL): Fecha ISO UTC del rebalanceo.
* `strategy_id` (TEXT, FK -> strategies.strategy_id ON DELETE CASCADE)
* `weight` (REAL, NOT NULL): Ponderación asignada.
* `status` (TEXT, NOT NULL): Estado operativo al momento del rebalanceo.
* *Índices:* `idx_allocations_timestamp`, `idx_allocations_strategy`

### 3. `alpha_autopsies`
Dictámenes forenses cognitivos emitidos por agentes LLM (DeepSeek / Claude) al detectar fatiga de señal.
* `id` (INTEGER, PK AUTOINCREMENT)
* `factor_id` (TEXT, NOT NULL): Identificador del factor degradado.
* `formula` (TEXT, NOT NULL): Expresión matemática del alfa.
* `health_status` (TEXT, NOT NULL): Diagnóstico (`WARNING_DECAY`, `CRITICAL_BREAK`).
* `diagnosis` (TEXT, NOT NULL): Resumen clínico del fallo.
* `root_cause` (TEXT, NOT NULL): Causa raíz económica o de microestructura.
* `recommendation` (TEXT, NOT NULL): Directiva de ajuste o mutación.
* `confidence_score` (REAL): Nivel de certidumbre del LLM [0.0 a 1.0].
* `suggested_actions` (TEXT): Lista JSON de acciones sugeridas (`ISOLATE_FACTOR`, etc.).
* `timestamp` (TEXT, NOT NULL): Fecha ISO UTC del dictamen.
* *Índices:* `idx_autopsies_factor`, `idx_autopsies_timestamp`

### 4. `market_biases`
Almacén canónico de sesgos direccionales y clasificación de régimen con control de expiración (TTL). Sustituye a `market_bias.json`.
* `symbol` (TEXT, PK): Par operado (ej: `DOGE/USDT:USDT`).
* `posture` (TEXT, NOT NULL): Postura (`BEARISH_SHORT`, `BULLISH_LONG`, `NEUTRAL`).
* `confidence` (REAL): Convicción matemática [0.0 a 1.0].
* `valid_until_utc` (TEXT): Marca temporal ISO UTC de expiración del sesgo.
* `updated_at` (TEXT, NOT NULL): Fecha ISO UTC de registro.
* *Índice:* `idx_market_biases_updated`

### 5. `diversity_archive`
Celdas del mapa de diversidad MAP-Elites para evitar estancamiento evolutivo.
* `niche_id` (TEXT, PK): Identificador del nicho multidimensional.
* `feature_type` (TEXT, NOT NULL): Tipo de factor (Mom, Vol, Liq, Micro).
* `complexity_tier` (TEXT, NOT NULL): Nivel de complejidad AST.
* `fitness_score` (REAL): Puntuación de aptitud / IC Information Ratio.
* `factor_id` (TEXT): Identificador del factor alojado.
* `formula` (TEXT): Fórmual matemática.
* `factor_data` (TEXT): Metadatos adicionales en JSON.
* `updated_at` (TEXT, NOT NULL): Fecha ISO UTC de actualización.
* *Índice:* `idx_diversity_fitness`

### 6. `cycle_history`
Historial de iteraciones del bucle de orquestación autónoma.
* `id` (INTEGER, PK AUTOINCREMENT)
* `timestamp` (TEXT, NOT NULL): Marca temporal ISO UTC.
* `actions` (TEXT): Lista JSON de acciones ejecutadas.
* `quarantined` (TEXT): Lista JSON de factores puestos en cuarentena.
* `promoted` (TEXT): Lista JSON de factores promovidos a LIVE.
* `new_weights` (TEXT): Diccionario JSON con los nuevos pesos de portafolio.
* `goal_reached` (INTEGER): Bandera booleana (0 o 1).
* `cycle_cost_usd` (REAL): Coste en USD de las llamadas a API en la iteración.
* `accumulated_cost_usd` (REAL): Coste acumulado de la sesión.
* `active_strategies` (INTEGER): Total de estrategias en ejecución activa.
* *Índice:* `idx_cycle_timestamp`

### 7. `risk_events`
Auditoría inmutable de violaciones de compuertas y disparos de seguridad.
* `id` (INTEGER, PK AUTOINCREMENT)
* `event_type` (TEXT, NOT NULL): Tipo de evento (`KILL_SWITCH`, `PRE_TRADE_FRICTION`, `FIREWALL_GAP`).
* `severity` (TEXT, NOT NULL): Severidad (`WARNING`, `CRITICAL`, `FATAL`).
* `description` (TEXT, NOT NULL): Descripción circunstanciada del evento.
* `symbol` (TEXT): Par involucrado (opcional).
* `metric_value` (REAL): Valor observado.
* `threshold_value` (REAL): Umbral vulnerado.
* `timestamp_utc` (TEXT, NOT NULL): Fecha ISO UTC.
* *Índices:* `idx_risk_events_type`, `idx_risk_events_timestamp`
