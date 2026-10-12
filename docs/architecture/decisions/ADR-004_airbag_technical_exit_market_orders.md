---
id: ADR-004
title: Efecto Airbag en Salidas Técnicas y Órdenes Market contra Fricción
category: architecture/decisions
version: 1.0
status: APPROVED
last_updated: 2026-10-11
author: Quantitative Engineering Team
---

# ADR-004: Salidas Técnicas como Airbag y Ejecución Market Forzada

## Contexto
En el Sprint 16 se ejecutó un experimento científico (`MemeHunterFuturesV6_Apex`) eliminando completamente la señal técnica de salida (`exit_signal`) para dejar que las posiciones corrieran libremente hasta el Trailing Stop.
- **Resultado del experimento:** El Win Rate aumentó artificialmente al 67.2%, pero al no existir una salida temprana ante quiebre de estructura, las pérdidas pequeñas controladas (-2% a -6%) se convirtieron en stoplosses duros del -10% (-295 USDT acumulados en 73 operaciones).
- Además, el análisis de microestructura reveló que durante desplomes o mechas de alta volatilidad, las órdenes de salida `limit` sufren riesgo de *no-fill*, dejando la posición abierta a merced de liquidaciones.

## Decisión
1. **Preservar `exit_signal` como "Airbag Técnico":**
   - Forzar el cierre inmediato de la posición corta si el precio recupera la EMA 200 o si MACD y RSI quiebran al alza, asumiendo una pérdida leve controlada antes de tocar el stoploss completo.
2. **Forzar Órdenes `market` en Salidas:**
   - Calibrar la política de ejecución de Freqtrade para que las entradas sean `limit` (Maker al Bid para cobrar rebate o pagar 0.02% de comisión), pero las salidas de emergencia, stoploss y `exit_signal` sean estrictamente `market` para garantizar ejecución inmediata sin retraso.

## Consecuencias
### Positivas
- Se redujo el Max Drawdown sustancialmente.
- Se elimina el riesgo de no-fill en caídas de baja liquidez en Binance Futures.
- Modelo ratificado formalmente en `MemeHunterFuturesV5_Leverage` y `MemeHunterFuturesV7_Quantum`.
