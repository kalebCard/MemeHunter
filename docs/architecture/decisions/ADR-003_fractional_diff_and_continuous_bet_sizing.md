---
id: ADR-003
title: Diferenciación Fraccionaria y Bet Sizing Continuo de López de Prado
category: architecture/decisions
version: 1.0
status: APPROVED
last_updated: 2026-10-11
author: Quantitative Engineering Team
---

# ADR-003: Diferenciación Fraccionaria (FFD) y Dimensionamiento Continuo de Apuestas

## Contexto
En la auditoría forense de la estrategia `MemeHunterFuturesV5_Leverage` (Sprint 17), se descubrió que:
1. El apalancamiento 2.0x discreto asignado a "absorción de subasta" sólo se disparó en 2 operaciones de 215 ($N=2$), evidenciando un ajuste manual sobreajustado (*data snooping*).
2. Los indicadores tradicionales calculados sobre precios brutos violan los supuestos de estacionariedad, mientras que los retornos simples descartan la memoria de largo plazo de la tendencia macro.

## Decisión
1. **Diferenciación Fraccionaria FFD (`scripts/fractional_diff.py`):**
   - Emplear la expansión binomial de Hosking con ventana fija FFD ($d=0.40$), conservando más del 90% de correlación con la serie de precios mientras se garantiza estacionariedad formal (ADF test $p < 0.05$).
2. **Bet Sizing Continuo (`scripts/triple_barrier_metalabeling.py`):**
   - Desacoplar la señal direccional del dimensionamiento del trade.
   - En el hook `leverage()` de Freqtrade, calcular la probabilidad $p \in [0.50, 0.95]$ y aplicar la formulación continua derivada de Kelly y la función acumulada normal:
     $$m = 2 Z\left[\frac{p - 0.5}{\sqrt{p(1-p)}}\right] - 1$$
     $$\text{Apalancamiento} = 1.0 + m \times (2.0 - 1.0) \in [1.0x, 2.0x]$$

## Consecuencias
### Positivas
- Se elimina la asignación discreta arbitraria ($1.5x$ vs $1.75x$ vs $2.0x$).
- El apalancamiento modula suavemente en función de la confluencia estadística.
- La estrategia canónica `MemeHunterFuturesV7_Quantum` implementa esta arquitectura de forma nativa.
