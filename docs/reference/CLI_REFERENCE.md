---
id: REF-CLI-001
title: Referencia Canónica del CLI (meme-hunter v8.5)
category: reference
version: 8.5
status: ACTIVE
last_updated: 2026-10-14
author: Quantitative Architecture & Systems Engineering Core
---

# 💻 Referencia Canónica del CLI (`meme-hunter` & `meme_cli.py`)

El proyecto dispone de dos niveles estandarizados de interfaces de línea de comandos:
1. **`meme-hunter`**: CLI institucional empaquetado (**Typer** y **Rich**) para orquestación de bajo nivel, bases de datos y compilación de alfas.
2. **`python scripts/ops/meme_cli.py`**: CLI de operaciones diarias y control de infraestructura en producción (Docker, FreqUI, Centinela de Salud y Telegram Copilot).

---

## 📋 Resumen de Comandos y Grupos (`meme-hunter`)

```bash
meme-hunter [OPTIONS] COMMAND [ARGS]...
```

| Comando / Grupo | Propósito Principal |
| :--- | :--- |
| `version` | Muestra diagnóstico del entorno, raíz y persistencia WAL |
| `serve` | Inicia el servidor Cockpit Web ASGI (FastAPI) |
| `db` | 📦 Gestión y auditoría de la base de datos canónica SQLite WAL |
| `run` | 🚀 Ejecución de bucles de mercado y daemons de producción |
| `mine` | ⛏️ Minería genética de factores y compilación de estrategias |
| `backtest` | 📊 Backtesting institucional y auditoría forense DSR / PBO |
| `sim` | 🎲 Simulaciones Monte Carlo y modelos de crecimiento |

---

## 1. Grupo `meme-hunter db`

### `meme-hunter db init`
Inicializa el esquema relacional canónico con todas las tablas e índices en modo WAL.
* **Destino:** `storage/meme_hunter.db`
* **Pragmas aplicados:** `busy_timeout = 15000`, `synchronous = NORMAL`, `journal_mode = WAL`.

### `meme-hunter db inspect`
Inspecciona visualmente el estado del almacenamiento: recuento de estrategias por estado (`LIVE`, `SANDBOX`, `ALPHA_DECAY`), sesgos vigentes, autopsias registradas y tamaño en disco.

### `meme-hunter db migrate`
Migra atómicamente registros históricos desde archivos JSON (`incubator_state.json`, `autopsies.json`, `cycle_history.json`, `market_bias.json`) hacia la base de datos SQLite WAL sin pérdida de datos.

---

## 2. Grupo `meme-hunter run`

### `meme-hunter run live [OPTIONS]`
Inicia el bucle de trading y la orquestación multi-agente en vivo.
* `--config PATH`: Ruta al archivo de configuración de Freqtrade (Default: `./user_data/config_futures.json`).
* `--loop-interval INT`: Intervalo de consulta en segundos (Default: `10`).

### `meme-hunter run ratchet [OPTIONS]`
Inicia el daemon autónomo de trinquete de ganancias (Profit Ratchet Daemon).
* `--threshold FLOAT`: Umbral de duplicación de cuenta (Default: `1.0` = +100%).
* `--extract-ratio FLOAT`: Porcentaje de beneficios cosechados hacia la bóveda (Default: `0.60` = 60%).

### `meme-hunter run vault`
Inicia el escáner de arbitraje Cash & Carry de la Bóveda Delta-Neutral ($\Delta = 0$).

---

## 3. Grupo `meme-hunter mine`

### `meme-hunter mine compile [OPTIONS]`
Compila dinámicamente el ensamble minado Long/Short validando cada factor contra el parser AST *Zero-Eval*.
* `--output PATH`: Destino del archivo de estrategia compilada (Default: `./user_data/strategies/MemeHunter_MinedEnsemble.py`).

---

## 4. Grupo `meme-hunter backtest`

### `meme-hunter backtest audit --zip-path PATH`
Audita un archivo ZIP oficial de backtest exportado por Freqtrade, certificando matemáticamente el DSR (Deflated Sharpe Ratio) y el PBO (Probability of Backtest Overfitting).

---

## 5. Grupo `meme-hunter sim`

### `meme-hunter sim montecarlo [OPTIONS]`
Ejecuta la simulación de colas pesadas (Fat-Tail Monte Carlo) bajo distribuciones de Student-t.
* `--iterations INT`: Número de simulaciones (Default: `10000`).
* `--drawdown-limit FLOAT`: Límite de Drawdown para el Kill Switch (Default: `0.25`).

---

## 6. Comando `meme-hunter serve`

```bash
meme-hunter serve --host 127.0.0.1 --port 8088
```
Inicia la factoría FastAPI ASGI con documentación Swagger OpenAPI (`/api/docs`) y WebSockets de telemetría reactiva en `/ws/telemetry`.

---

## 7. 🛠️ CLI Operativo de Producción (`python scripts/ops/meme_cli.py`)

Para el día a día operativo en VPS o entorno local sin lidiar con comandos complejos de Docker o scripts individuales:

```powershell
# 1. Auditoría de Salud Integral (2 segundos)
python scripts/ops/meme_cli.py health

# 2. Acceso y Credenciales a la Interfaz Web Oficial FreqUI (:8081)
python scripts/ops/meme_cli.py frequi

# 3. Control del Contenedor de Futuros Docker
python scripts/ops/meme_cli.py futures start     # Iniciar contenedor
python scripts/ops/meme_cli.py futures stop      # Detener contenedor
python scripts/ops/meme_cli.py futures logs      # Logs en tiempo real
python scripts/ops/meme_cli.py futures status    # Inspección de estado

# 4. Copilot de IA en Telegram (Sprint 50 & 51)
python scripts/ops/meme_cli.py telegram-ai --poll    # Iniciar daemon de escucha
python scripts/ops/meme_cli.py telegram-ai --test    # Auditar conectividad y APIs
python scripts/ops/meme_cli.py telegram-ai --query "¿Cómo vamos hoy?"  # Prueba ad-hoc

# 5. Ejecución Rápida de Pruebas Automatizadas
python scripts/ops/meme_cli.py test             # Suite completa
python scripts/ops/meme_cli.py test --fast      # Modo silencioso (-q)
```

