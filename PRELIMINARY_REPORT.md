# Reporte Preliminar (PB-09) - MemeHunterV1

Este es un *test en seco* (2021) ejecutado únicamente sobre 2 monedas (BTC/USDT y LUNA/USDT) para validar que el pipeline de análisis genera correctamente las métricas. 
El backtest real sobre todo el Universo (Top 30 mensual histórico) requiere que la descarga de datos termine.

## Resultados Brutos (2021)
| Métrica | Valor | Objetivo (Hipótesis) | Estado |
| :--- | :--- | :--- | :--- |
| **Trades Totales** | 150 | - | - |
| **Expectancy** | 0.13 | > 0 | ✅ Cumple |
| **Profit Factor** | 1.05 | ≥ 1.3 | ❌ Falla |
| **Sortino Ratio** | 0.23 | ≥ 1.0 | ❌ Falla |
| **Win Rate** | 46.0% | - | - |
| **Max Drawdown** | 16.47% | < 20% | ✅ Cumple |
| **Profit Neto** | 2.01% | > Benchmark | ❌ Falla (Mercado: +6665%)|

## Conclusiones Iniciales
1. **El motor funciona**: Freqtrade está calculando correctamente la expectancy, stoploss dinámico, protecciones de drawdown y operando pares inactivos (LUNA).
2. **Bajo Rendimiento**: La estrategia está sobreviviendo (Expectancy positiva de 0.13, gana dinero neto), pero el Profit Factor es muy bajo (apenas se gana más de lo que se pierde) y el ratio riesgo-recompensa (Sortino) es pobre en comparación a simplemente holdear. 
3. **Falta de Diversificación**: Al probar solo en 2 monedas, el bot sufre *Drawdowns* largos (103 días).

## Siguientes Pasos
Una vez finalice la descarga masiva (PB-04), actualizaremos la lista de monedas para que incluya las ~100 monedas del universo histórico. Con eso, ejecutaremos el **Backtest Maestro (2020-2026)**. Si las métricas siguen sin cumplir la Hipótesis, procederemos a PB-10 (Optimización `hyperopt`) para ajustar parámetros como el ROI, temporalidad del MACD o la ventana del ATR.
