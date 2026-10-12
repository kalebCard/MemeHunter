# 🏗️ Plan de Implementación: Arquitectura Híbrida Barbell & Motor de Trinquete (Profit Ratchet)

**Documento:** PLAN_IMPLEMENTACION_HIBRIDO_BARBELL.md  
**Objetivo Estratégico:** Construir el puente automatizado entre la generación rápida de capital en Futuros y la acumulación en la Bóveda Segura Delta-Neutral para alcanzar **10,000 USDT mensuales pasivos**.

---

## 🎯 1. Diagrama de Arquitectura del Sistema

```mermaid
graph TD
    subgraph Generador Alpha (Riesgo Controlado)
        A[Capital Semilla: 1,000 USDT] --> B[Freqtrade Futures Engine]
        B -->|MemeHunterFuturesV5_Ablation 1.5x| C[Balance Dinámico de Futuros]
    end

    subgraph Válvula de Trinquete (Risk Isolation)
        C --> D{Profit Ratchet Daemon PB-68}
        D -->|Equity >= Hito +100%| E[Disparador de Extracción]
        E -->|Transferencia Interna CCXT| F[Subcuenta / Balance Spot Binance]
        D -->|Drawdown >= 25%| K[Kill-Switch Inmediato]
    end

    subgraph Bóveda Segura Delta-Neutral (Riesgo Direccional $0)
        F --> G[Funding Arbitrage Manager PB-69]
        G --> H[Short Futuros 1x + Long Spot]
        H --> I[Cobro de Funding Rates: 15% - 40% APR]
        I --> J[Reinversión Segura]
    end

    J -->|Crecimiento Acumulado hacia $800k+| L[Flujo Pasivo: 10,000 USDT/Mes]
```

---

## 📅 2. Fases del Plan de Implementación

### Fase 1: Creación del Simulador de Trayectoria Híbrida (PB-70)
* **Objetivo:** Proyectar con precisión matemática la curva de crecimiento del binomio (Motor Agresivo + Bóveda Segura) según el capital de arranque ($1,000 USDT vs $10,000 USDT) y las tasas de extracción.
* **Componentes:**
  * Crear [`scripts/simulate_hybrid_barbell.py`](scripts/simulate_hybrid_barbell.py).
  * Simular 3,000 trayectorias con las métricas empíricas certificadas en OOS (CAGR 30.8% a 42.5%, Win Rate 50%–53%, Max DD 23%–43%).
  * Evaluar diferentes frecuencias de trinquete:
    - Retiro del 100% de ganancias al duplicar (+100%).
    - Retiro del 50% de ganancias y 50% al compounding.
* **Entregable:** Script ejecutable con métricas de tiempo esperado para alcanzar los 10,000 USDT/mes.

---

### Fase 2: Desarrollo del Daemon de Trinquete de Ganancias (PB-68)
* **Objetivo:** Desarrollar un servicio desacoplado y autónomo que audite la API de Binance o la base de datos de Freqtrade y ejecute transferencias seguras entre contratos de futuros y balance spot.
* **Componentes:**
  * Crear [`scripts/profit_ratchet_daemon.py`](scripts/profit_ratchet_daemon.py).
  * Conexión segura mediante CCXT (`binance.transfer('USDT', amount, 'future', 'spot')`).
  * **Reglas del Daemon:**
    1. **Monitoreo de Equity Total:** Audita `wallet_balance + unrealized_pnl`.
    2. **Umbral de Trinquete:** Cuando el balance supera el hito (ej. $1,000 \rightarrow $2,000), ejecuta la transferencia de $1,000 al balance Spot de Binance.
    3. **Reset de Stake:** Asegura que Freqtrade mantenga siempre el `dry_run_wallet` o `stake_amount` calibrado al capital base, dejando inmunes las ganancias transferidas.
    4. **Centinela del Kill-Switch:** Si la equidad cae un 25% desde el último pico del ciclo, el daemon bloquea nuevas operaciones y notifica por Telegram.
* **Entregable:** Daemon Python con tests unitarios y soporte para dry-run.

---

### Fase 3: Integración de la Bóveda Segura Delta-Neutral (PB-69)
* **Objetivo:** Tomar el capital cosechado por el trinquete en Spot y ponerlo a rentar automáticamente mediante arbitraje Cash & Carry delta-neutral sin exposición al mercado.
* **Componentes:**
  * Refactorizar y automatizar [`scripts/funding_arbitrage.py`](scripts/funding_arbitrage.py).
  * Añadir lógica de ejecución pasiva de dos patas:
    - Pata 1: Compra Spot del activo con funding rate positivo alto (ej. +0.05% a +0.15% cada 8h).
    - Pata 2: Apertura de Short Perpetuo 1.0x aislado por el mismo valor nominal exacto.
  * **Propiedad matemática:** Exposición direccional $= 0$. La cuenta es inmune a que el activo caiga -50% o suba +50%; su único retorno es el cobro sistemático del funding cada 8 horas.
* **Entregable:** Módulo de asignación delta-neutral autónomo.

---

### Fase 4: Despliegue en Docker y Validación en Dry-Run (Sprint 18)
* **Objetivo:** Poner a correr la arquitectura completa en Docker bajo simulación en tiempo real (Paper Trading) durante 4 a 8 semanas antes de operar con dinero real.
* **Componentes:**
  * Configurar `docker-compose.hybrid.yml` integrando:
    1. Servicio `freqtrade-futures` (ejecutando `MemeHunterFuturesV5_Ablation`).
    2. Servicio `profit-ratchet-daemon` (vigilando hitos de equity y Kill-Switch).
    3. Servicio `funding-arbitrage-vault` (recibiendo fondos y gestionando Cash & Carry).
  * Monitoreo con [`scripts/dryrun_monitor.py`](scripts/dryrun_monitor.py).
* **Entregable:** Sistema híbrido multi-contenedor corriendo 24/7 en segundo plano.

---

## 📊 3. Matriz de Parámetros Operativos Recomendados

| Parámetro | Configuración Inicial ($1,000 USDT) | Configuración Escalada ($10,000 USDT) |
|---|:---:|:---:|
| **Capital Motor Futuros** | $1,000 USDT (4 slots de $250) | $2,000 USDT (4 slots de $500) |
| **Capital Bóveda Segura Inicial** | $0 USDT (se construye con cosechas) | $8,000 USDT (generando 15% APR base) |
| **Apalancamiento Futuros** | 1.5x aislado homogéneo | 1.5x aislado homogéneo |
| **Trailing Stop Futuros** | Offset +12.0% / Holgura 4.0% | Offset +12.0% / Holgura 4.0% |
| **Kill-Switch de Equidad** | 25% de Drawdown vivo | 25% de Drawdown vivo |
| **Gatillo de Trinquete** | Cada +1,000 USDT de ganancia neta | Cada +2,000 USDT de ganancia neta |
| **Destino de Transferencia** | Subcuenta Spot / Vault Cash & Carry | Subcuenta Spot / Vault Cash & Carry |

---

## 🏁 4. Criterios de Aceptación para Producción (DoD Híbrido)

1. ✅ El simulador de trayectoria demuestra que el trinquete reduce el riesgo de ruina a menos del 1.0% frente al 87.8% del compounding sin frenos.
2. ✅ El daemon de trinquete realiza transferencias automáticas sin interrumpir el funcionamiento de Freqtrade.
3. ✅ El Kill-Switch de 25% detiene de forma instantánea el motor agresivo si ocurre un cambio de régimen hostil.
4. ✅ La bóveda delta-neutral no asume riesgo direccional (delta neto $< 0.01$).
