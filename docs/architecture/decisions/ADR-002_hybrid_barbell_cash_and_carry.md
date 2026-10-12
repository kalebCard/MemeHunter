---
id: ADR-002
title: Arquitectura Híbrida Barbell y Válvula de Trinquete (Profit Ratchet)
category: architecture/decisions
version: 1.0
status: APPROVED
last_updated: 2026-10-11
author: Quantitative Engineering Team
---

# ADR-002: Arquitectura Híbrida Barbell y Válvula de Trinquete

## Contexto
El análisis de viabilidad estocástica (`simulate_hybrid_barbell.py`) demostró que:
1. Partiendo de micro-capital (100–1,000 USDT), pretender vivir de rentas pasivas sin riesgo es matemáticamente imposible.
2. Por otro lado, mantener todo el capital reinvertido perpetuamente en futuros de memecoins expone la cuenta a eventos de cola gorda (*fat tails*), donde una anomalía sistémica o fallo de exchange puede borrar el capital acumulado tras años de esfuerzo.

## Decisión
Se adopta la **Arquitectura Híbrida Barbell (de Pesas)** con una **Válvula de Trinquete Mecánica**:
1. **Extremo Agresivo:** Motor de futuros operando con $100–$1,000 USDT base para acelerar capital al 40%–110% CAGR.
2. **Válvula de Trinquete (`profit_ratchet_daemon.py`):** Cada vez que la equidad se duplica (+100%), se extrae automáticamente el 60% de las utilidades y se transfieren al balance Spot/Bóveda, reseteando la base operativa para inmunizar las ganancias pasadas.
3. **Extremo Conservador (`delta_neutral_vault.py`):** El capital cosechado se canaliza hacia arbitraje Cash & Carry (Spot Long + Short Futuros 1.0x aislado), generando 15%–40% APR con exposición direccional neta de $\Delta = 0$.

## Consecuencias
### Positivas
- Se rompe el dilema entre "alto rendimiento pero riesgo de ruina" y "cero riesgo pero crecimiento microscópico".
- Las utilidades cosechadas quedan matemáticamente protegidas contra drawdowns en el motor de futuros.
- El flujo pasivo generado por la bóveda financia los costos operativos y construye la masa crítica patrimonial.
