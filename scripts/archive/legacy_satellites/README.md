# 📦 Archivo Canónico de Módulos Satélite y Herramientas Prescindibles

Este directorio contiene las herramientas, descargadores auxiliares y scripts de experimentos que fueron archivados de la ruta de ejecución principal en el **Sprint 56 (PB-220)** bajo la filosofía de **"Arquitectura por Sustracción" (*Menos es Más*)**.

---

## 🗄️ Manifiesto de Módulos Archivados

| Archivo | Propósito Histórico | Motivo de Archivado (Tier 8 & 9) |
|---|---|---|
| `delta_neutral_vault.py` | Bóveda Cash & Carry ($\Delta=0$) para capturar tasas de financiamiento. | Diseñado para carteras institucionales $\ge 10,000\text{ USDT}$; prescindible para el micro-capital activo en futuros (100 USDT). |
| `funding_arbitrage.py` | Escáner de oportunidades de arbitraje entre Spot y Futuros. | Consume recursos de red sin formar parte del motor autónomo central de trading en Binance Futures. |
| `dex_viral_radar.py` | Radar on-chain DEX (Solana/Base) vía DexScreener. | Informativo sobre memecoins tempranas, pero no opera en contratos perpetuos de Binance Futures. |
| `binance_vision.py` | Descargador masivo de volcados mensuales ZIP desde Binance Vision. | Superado por `data_engine/auto_data_sync.py`, que sincroniza incrementalmente velas OHLCV en vivo sin gigabytes redundantes. |
| `backtest_spot_capitulation.py` | Estrategia en Spot de capitulación y mechas de sobreventa. | Refutado y superado; el sistema opera exclusivamente en derivados de futuros con ventaja asimétrica Short. |

---

## 🧭 Compatibilidad y Acceso

Estos módulos se preservan para fines de investigación académica, auditoría histórica y reproducibilidad de experimentos previos. 

Para invocarlos puntualmente:
```bash
python -m scripts.archive.legacy_satellites.delta_neutral_vault --scan
```
