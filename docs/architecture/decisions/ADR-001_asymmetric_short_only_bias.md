---
id: ADR-001
title: Asymmetric Short-Only Bias en Memecoins
category: architecture/decisions
version: 1.0
status: APPROVED
last_updated: 2026-10-11
author: Quantitative Engineering Team
---

# ADR-001: Sesgo Asimétrico Short-Only en Memecoins

## Contexto
Durante las fases iniciales del proyecto (Sprint 1 a 3), el sistema operaba bajo un paradigma bidireccional tradicional (Long/Short simétrico) en Binance Futures y Spot. La investigación empírica sobre las 10 principales memecoins (`PEPE`, `DOGE`, `SHIB`, `WIF`, etc.) reveló un problema estructural de microestructura:
- Las memecoins carecen de flujos de caja y valor fundamental intrínseco.
- Tras un pico eufórico de 3 a 7 días, ingresan en regímenes seculares de desinflación gravitacional que duran semanas o meses, perdiendo entre el 80% y 95% de su valor pico.
- Las compras (Longs) introducían ruido estocástico, falsos rebotes y generaron pérdidas continuas (-48.11 USDT netos en el backtest de alta fidelidad).

## Decisión
Se decide **eliminar el 100% de las señales Long** en el universo de memecoins y focalizar el motor de futuros exclusivamente en el lado **Short**:
1. Apertura de posiciones cortas ante rupturas bajistas bajo la EMA 200 en velas de 4H confirmadas por MACD negativo y RSI en zona de desinflación.
2. Inmunidad a la liquidación: empleo exclusivo de **margen aislado 1.0x - 1.5x** con stoploss duro al -10%, ubicando el precio de liquidación a más de +50% del precio de entrada.

## Consecuencias
### Positivas
- Multiplicación de la rentabilidad neta por **11.3X** (`MemeHunterFuturesV1_ShortOnly` alcanzó +63.24% neto vs +5.57% de la versión bidireccional).
- Reducción drástica del *churn* de comisiones y eliminación de *bull traps*.
- 8 de los 10 pares del universo resultaron masivamente rentables (+719.85 USDT acumulados).

### Negativas / Mitigaciones
- En activos con alta capitalización e institucionalización como `DOGE`, las fases alcistas sostenidas pueden generar rachas de stoplosses. Mitigación: filtro de régimen macro (`regime_classifier.py`) y confirmación de memoria estacionaria FFD.
