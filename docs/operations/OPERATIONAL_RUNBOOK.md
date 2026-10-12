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

## 4. 📊 Batería de Validación Previa a Producción

Antes de desplegar cualquier cambio o ajuste de parámetros, ejecutar la suite completa de tests:
```powershell
python -m pytest tests/test_advanced_metrics.py tests/test_fractional_diff.py tests/test_triple_barrier_metalabeling.py tests/test_profit_ratchet.py tests/test_delta_neutral_vault.py tests/test_regime_classifier.py tests/test_futures_v7_quantum.py -v
```
**Criterio de pase obligatorio:** 21/21 tests pasando al 100%.
