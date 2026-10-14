---
id: OPS-001
title: Manual Operativo y Runbook de Producción (Meme Hunter v8.5)
category: operations
version: 8.5
status: ACTIVE
last_updated: 2026-10-14
author: Quantitative DevOps & Production Engineering Team
---

# 🛠️ Manual Operativo y Runbook de Producción (Ops Runbook v8.5)

Este documento centraliza los procedimientos de despliegue, monitoreo en vivo, gestión de emergencias, sincronización continua de datos, compilación de estrategias de ensamble y orquestación de la Arquitectura Híbrida Barbell.

---

## 1. 🚀 Despliegue Rápido de Contenedores Docker

### 1.1 Preparación de Archivos de Configuración
Antes de iniciar los servicios, genera tus credenciales a partir de las plantillas seguras:

```powershell
# Windows PowerShell
Copy-Item user_data/config_futures.example.json user_data/config_futures.json
Copy-Item .env.example .env
```

Edita `.env` con tus credenciales de Binance y Telegram:
```env
BINANCE_API_KEY=tu_api_key
BINANCE_API_SECRET=tu_api_secret
TELEGRAM_TOKEN=tu_token_bot
TELEGRAM_CHAT_ID=tu_chat_id
```

### 1.2 Inicio del Motor de Futuros y Diagnóstico (Vía CLI Unificado)
El método estándar recomendado para operar el sistema es a través del CLI centralizado:

```powershell
# 1. Verificar salud integral del sistema (2 segundos)
python scripts/ops/meme_cli.py health

# 2. Levantar el motor de futuros en Docker (Puerto 8081)
python scripts/ops/meme_cli.py futures start

# 3. Consultar datos de acceso a la interfaz web oficial
python scripts/ops/meme_cli.py frequi

# 4. Ver logs en tiempo real
python scripts/ops/meme_cli.py futures logs
```

* **🌐 Interfaz Web Oficial Única (FreqUI):** [http://localhost:8081](http://localhost:8081)
* **🔑 Credenciales de Acceso:** Usuario: `admin` | Clave: `MemeHunter2026!` (API URL: `http://localhost:8081`).
* **🔬 Módulos Cuantitativos Unificados en FreqUI:**
  - 🌐 `/dag`: Orquestación Multi-Agente & Controles HITL
  - 🔄 `/incubator`: Motor de Auto-Mejora, Autopsias DeepSeek-R1 & MAP-Elites
  - 🧪 `/studio`: Laboratorio Cuantitativo & Validador AST Zero-Eval
* **Estrategias en Producción:** `MemeHunter_MinedEnsemble` (Ensamble dinámico bidireccional auto-minado) y `MemeHunterFuturesV7_Quantum`.

---

## 2. 🛡️ Protocolo de Contingencia: Activación del Kill-Switch

### 2.1 Mecánica del Kill-Switch
El sistema audita el drawdown de equidad total (realizado + flotante). Si la cuenta cae un **25%**, se crea el archivo testigo:
```
user_data/KILL_SWITCH
```
Cuando este archivo existe:
1. Freqtrade bloquea el 100% de nuevas entradas en todos los pares.
2. Se envía una alerta de emergencia vía Telegram.
3. Las posiciones vivas continúan gestionándose hasta su cierre por trailing stop o stoploss.

### 2.2 Procedimiento de Desactivación y Reset
Solo tras analizar la causa de la anomalía en el mercado:
1. Verificar logs: `docker compose -f docker-compose.futures.yml logs --tail 200`.
2. Para reanudar la operativa, eliminar manualmente el testigo:
   ```powershell
   Remove-Item user_data/KILL_SWITCH
   ```

---

## 3. ⚖️ Orquestación de la Arquitectura Barbell

### 3.1 Válvula de Trinquete (`profit_ratchet_daemon.py`)
Monitorea la equidad viva de la cuenta y extrae utilidades hacia la subcuenta de Bóveda:
```powershell
# Ejecución en segundo plano o tarea programada cada 1 hora
python scripts/profit_ratchet_daemon.py --check-interval 3600
```

### 3.2 Bóveda Delta-Neutral (`delta_neutral_vault.py`)
Escanea en vivo las tasas de financiación más altas de Binance Futures y rebalancea las posiciones Cash & Carry:
```powershell
# Escanear oportunidades y reportar estado de la bóveda
python scripts/delta_neutral_vault.py --scan
```

---

## 4. 🔬 Módulos Cuantitativos y Laboratorio de I+D en FreqUI (:8081)
El antiguo Cockpit Dashboard secundario (puerto 8088) ha sido **completamente integrado dentro de FreqUI** (`http://localhost:8081`), eliminando la necesidad de múltiples puertos y procesos paralelos.

### 4.1 Acceso Directo a los Módulos Cuantitativos
1. **Centro de Control & Trading en Vivo:** [http://localhost:8081/trade](http://localhost:8081/trade)
2. **Orquestador Multi-Agente & HITL:** [http://localhost:8081/dag](http://localhost:8081/dag)
3. **Incubadora Autónoma & Autopsias IA:** [http://localhost:8081/incubator](http://localhost:8081/incubator)
4. **Quant Studio AST Zero-Eval:** [http://localhost:8081/studio](http://localhost:8081/studio)

### 4.2 Verificación de Salud Unificada y Acceso Remoto
```powershell
# Verificar la salud de FreqUI y el sistema completo
python scripts/ops/meme_cli.py health
```

Para acceder de forma segura a FreqUI desde tu máquina local a un VPS remoto:
```bash
ssh -L 8081:127.0.0.1:8081 usuario@<IP_DEL_VPS>
```
Luego navega localmente a `http://localhost:8081`.

---

## 5. 🤖 Operación del Motor Autónomo y Gobernanza de Costes

El motor auto-evolutivo (`portfolio/autonomous_orchestrator.py`) y el bucle en vivo (`scripts/run_live_alpha_loop.py`) ejecutan ciclos de diagnóstico, autopsia, síntesis de alfas y rebalanceo HRP con salvaguardas económicas estrictas.

### 5.1 Configuración de Variables de Entorno en `.env`
```env
# Meta Cuantitativa de Convergencia (Sharpe del Portafolio)
AUTONOMOUS_TARGET_SHARPE=2.50

# Límites Presupuestarios y de Parada (Circuit Breakers)
AUTONOMOUS_MAX_BUDGET_USD=1.00
AUTONOMOUS_MAX_CYCLES=10
OPENROUTER_MAX_DAILY_TOKENS=150000

# Proveedor Cognitivo de IA (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL_REASONING=deepseek/deepseek-r1
OPENROUTER_MODEL_SYNTHESIS=deepseek/deepseek-chat
```

> [!IMPORTANT]
> **Nota sobre Claves de API de OpenRouter:**
> Asegúrate de utilizar una **API Key estándar de inferencia** creada en [openrouter.ai/keys](https://openrouter.ai/keys) con crédito o balance. Las claves de tipo *Management / Provisioning* no tienen permisos para `/api/v1/chat/completions`. Si se detecta un error 401 o falta de clave, el sistema activará **automáticamente el modo fallback heurístico offline a coste $0.00 USD**, manteniendo el bucle 100% operativo sin interrupciones.

### 5.2 Comandos de Ejecución
```powershell
# 1. Bucle continuo conectado a streaming de Binance:
python scripts/run_live_alpha_loop.py

# 2. Demostración E2E de un ciclo completo:
python scripts/run_autonomous_engine_demo.py
```

### 5.3 Comportamiento al Alcanzar la Meta (*Target Sharpe*)
Cuando el Sharpe Ponderado del portafolio alcanza o supera `AUTONOMOUS_TARGET_SHARPE` (por defecto 2.50) con $\ge 2$ estrategias en `LIVE`:
* El orquestador marca `goal_reached = True`.
* Notifica el éxito en consola y en el Cockpit Web (`/api/status`).
* Frena la síntesis de nuevos factores para prevenir sobreajuste (*overfitting*) innecesario.
* Mantiene la monitorización de salud pasiva.

---

## 6. 🔄 Operaciones de Datos, Fábrica SQLite WAL y Ensamble (Sprints 25 a 29)

### 6.1 Sincronización Automática en Vivo de Binance Futures
Para actualizar los datos Feather de las 9 memecoins más activas de futuros sin congelar el sistema:
```powershell
# Ejecución directa o programada cada 4 horas
python data_engine/auto_data_sync.py
```
* **Destino:** `C:/meme_hunter_data/binance/futures/*.feather`
* **Pares sincronizados:** `DOGE`, `PEPE`, `WIF`, `MEW`, `POPCAT`, `NEIRO`, `BONK`, `FLOKI`, `SHIB`.

### 6.2 Compilación del Ensamble Cuantitativo Bidireccional
Para compilar los alfas aprobados en la fábrica hacia una estrategia de Freqtrade:
```powershell
python scripts/compile_ensemble_strategy.py
```
* **Salida generada:** `user_data/strategies/MemeHunter_MinedEnsemble.py`.
* **Características:** Motores simétricos `enter_long` y `enter_short`, confirmación rápida de EMA 50 y RSI, y stop loss calibrado al -5.0%.
* **Hot-Reload REST:** Si el contenedor Freqtrade está activo en el puerto 8081, el cliente REST (`client/freqtrade_client.py`) recarga la estrategia en vivo sin interrumpir las órdenes abiertas.

### 6.3 Mantenimiento de la Fábrica SQLite WAL (`portfolio/alpha_factory.db`)
El estado de la incubadora opera en modo SQLite WAL para máxima concurrencia multihilo.
```powershell
# Verificar integridad de la base de datos
python -c "from portfolio.db_pool import DatabasePool; print('Estrategias:', len(DatabasePool.get_instance().get_strategies()))"

# Forzar vaciado de WAL a disco (Checkpoint)
python -c "from portfolio.db_pool import DatabasePool; DatabasePool.get_instance().execute_write('PRAGMA wal_checkpoint(TRUNCATE);')"
```

### 6.4 Auditoría de Compuertas Fuera de Muestra (OOS Gating)
Antes de permitir la entrada de cualquier factor a producción:
```powershell
python -c "from portfolio.oos_gating import OOSGatingEngine; engine = OOSGatingEngine(); print('OOS Engine Listo')"
```
* **Criterios de paso:** $PBO < 15\%$, $DSR \ge 95\%$, Correlación $< 0.40$.

---

## 7. 📊 Batería de Validación y Certificación Continua (CI/CD)

Antes de desplegar cualquier cambio a producción, ejecutar la suite completa de pruebas:
```powershell
python -m pytest tests -v
```

En entornos con Docker activo:
```bash
docker compose run --rm -e PYTHONPATH=/freqtrade --entrypoint pytest freqtrade tests/ -v
```

**Criterio de aceptación obligatorio:** **151+ tests pasando al 100% (0 errores)**.

---

## 8. 📱 Operación y Control Remoto Vía Telegram AI Copilot (@Atutaskbot) (Sprints 50 y 51)

Meme Hunter v8.5 incorpora el servicio de **Copilot de Inteligencia Artificial en Telegram** ([`client/telegram_ai_copilot.py`](file:///c:/meme_hunter/client/telegram_ai_copilot.py) y [`client/ai_copilot_engine.py`](file:///c:/meme_hunter/client/ai_copilot_engine.py)), permitiendo al operador supervisar y controlar el sistema mediante lenguaje natural y comandos deterministas desde dispositivos móviles.

### 8.1 Arquitectura y Reglas Críticas de Despliegue
> [!WARNING]
> **Conflicto 409 de Long-Polling en Telegram:**
> La API de Telegram prohíbe terminantemente múltiples instancias escuchando el mismo token de bot simultáneamente.
> * En [`docker-compose.futures.yml`](file:///c:/meme_hunter/docker-compose.futures.yml), la variable `FREQTRADE__TELEGRAM__ENABLED=false` deshabilita el polling nativo de Freqtrade.
> * El contenedor Freqtrade se dedica exclusivamente a ejecutar las estrategias y servir la API REST en el puerto `:8081`.
> * El servicio `TelegramAiCopilotService` opera como el **único consumidor autorizado** del bot `@Atutaskbot`.

### 8.2 Despliegue y Ejecución del Daemon
```powershell
# 1. Auditoría rápida de conectividad (Telegram API + Freqtrade REST API)
python scripts/ops/run_telegram_copilot.py --test

# 2. Iniciar el Daemon de Polling Continuo en segundo plano
python scripts/ops/run_telegram_copilot.py --poll

# Alternativa mediante CLI Canónico
python scripts/ops/meme_cli.py telegram-ai --poll
```

### 8.3 Firewall de Seguridad por Chat ID
El servicio implementa un filtro estricto por lista blanca:
* Variable obligatoria en `.env`: `TELEGRAM_CHAT_ID=6730240181`.
* Cualquier mensaje originado desde un Chat ID no autorizado es rechazado inmediatamente con registro en log de seguridad.

### 8.4 Comandos Deterministas Disponibles
| Comando | Descripción |
| :--- | :--- |
| `/status` | Estado de salud, modo (Dry-Run / Live), versión y trades abiertos. |
| `/balance` | Resumen de balance USDT, saldo libre, bloqueado y equidad total. |
| `/daily` | Rendimiento del día actual y comparación vs benchmarks. |
| `/profit` | Resumen histórico de PnL acumulado, winrate y factor de beneficio. |
| `/whitelist` | Pares activos autorizados en el motor de futuros. |
| `/forcebuy <par>` | Orden forzada de entrada (ej: `/forcebuy SOL/USDT`). |
| `/reload` | Recarga en caliente de configuraciones y estrategias sin reiniciar contenedor. |
| `/help` | Menú interactivo de ayuda y lista de comandos. |

### 8.5 Control Semántico en Lenguaje Natural (HITL)
El motor `QuantAiCopilotEngine` procesa mensajes coloquiales y consulta telemetría viva para sintetizar respuestas enriquecidas:
* *"¿Cómo vamos hoy?"* $\rightarrow$ Consulta `/daily` y resume el PnL y trades.
* *"¿Cuánto saldo libre nos queda?"* $\rightarrow$ Consulta `/balance` e informa USDT disponible.
* *"Comprar 1 SOL"* / *"Entra en doge"* $\rightarrow$ Detecta intención semántica, extrae el par y ejecuta `forcebuy` previa confirmación.
* *"¿Hay algún riesgo activo?"* $\rightarrow$ Verifica estado del Kill-Switch (-25%), drawdown flotante y alarmas de volatilidad.



