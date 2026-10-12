---
id: OPS-001
title: Manual Operativo y Runbook de Producción
category: operations
version: 2.0
status: ACTIVE
last_updated: 2026-10-11
author: Quantitative DevOps Team
---

# 🛠️ Manual Operativo y Runbook de Producción (Ops Runbook)

Este documento centraliza los procedimientos de despliegue, monitoreo en vivo, gestión de emergencias y orquestación de la Arquitectura Híbrida Barbell.

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

### 1.2 Inicio del Motor de Futuros (Modo Dry-Run)
```powershell
# Levantar contenedor en segundo plano
docker compose -f docker-compose.futures.yml up -d

# Ver logs en tiempo real
docker compose -f docker-compose.futures.yml logs -f meme_hunter_futures
```
* **Dashboard Web (FreqUI):** [http://localhost:8081](http://localhost:8081)
* **Credenciales por defecto:** configuradas en `user_data/config_futures.json`.

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

## 4. 🎛️ Monitoreo Visual con Alpha Cockpit Dashboard

El **Cockpit Dashboard** opera de manera aislada y multihilo en el puerto **8088** para no colisionar con FreqUI (puerto 8080/8081).

### 4.1 Iniciar el Servidor del Dashboard
```powershell
# Iniciar en puerto estándar 8088
python scripts/start_dashboard.py
```
* **Acceso Local:** [http://localhost:8088](http://localhost:8088)
* **Autenticación:** Las llamadas a mutación (`/api/trigger-loop` y `/api/synthesize-alpha`) requieren un token Bearer seguro:
  - Token por defecto para desarrollo: `meme_hunter_dev_token_2026`
  - Variable de entorno de producción: `DASHBOARD_API_TOKEN`

### 4.2 Acceso Seguro en Servidores Remotos / VPS
Nunca expongas el puerto 8088 a internet directamente. Utiliza un túnel cifrado SSH:
```bash
ssh -L 8088:127.0.0.1:8088 usuario@<IP_DEL_VPS>
```
Luego navega localmente a `http://localhost:8088`.

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

## 6. 📊 Batería de Validación Previa a Producción (CI/CD)

Antes de desplegar cualquier cambio a producción, ejecutar la suite completa de pruebas en el entorno hermético Docker:
```bash
docker compose run --rm -e PYTHONPATH=/freqtrade --entrypoint pytest freqtrade tests/ -v
```
**Criterio de aceptación obligatorio:** **110/110 tests pasando al 100% (0 errores)**.

