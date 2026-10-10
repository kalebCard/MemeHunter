# meme_hunter

Bot de trading sobre [Freqtrade](https://www.freqtrade.io/) cuyo objetivo es **validar empíricamente un edge** antes de arriesgar capital.

- Arquitectura: [DAS.md](DAS.md)
- Plan de trabajo: [SCRUM_PLAN.md](SCRUM_PLAN.md)
- Hipótesis Teórica: [HYPOTHESIS.md](HYPOTHESIS.md)
- Test Preliminar (2021): [PRELIMINARY_REPORT.md](PRELIMINARY_REPORT.md)

## Estructura

```
meme_hunter/
├── docker-compose.yml     # Imagen oficial freqtradeorg/freqtrade:stable
├── .env.example           # Plantilla de secretos (copiar a .env)
├── user_data/             # Versionado: config, estrategias, notebooks
│   ├── config.json
│   └── strategies/
└── (datos de mercado)     # C:/meme_hunter_data -> /freqtrade/user_data/data
```

> Los datos de mercado se guardan **fuera de OneDrive** (`C:/meme_hunter_data`) para evitar sincronizar decenas de GB.

## Requisitos

- Docker Desktop (backend WSL2)
- Git

## Uso rápido

```powershell
Copy-Item .env.example .env          # una sola vez
docker compose build                 # imagen meme_hunter (Freqtrade 2026.9 fijado + pytest)
docker compose run --rm freqtrade --version
```

### Datos históricos (incluye pares deslistados) — `scripts/binance_vision.py`

```powershell
# Alias para no repetir
function bv { docker compose run --rm --entrypoint python freqtrade scripts/binance_vision.py @args }

bv symbols                                              # catálogo completo de símbolos Spot
bv download --all-symbols --interval 1d                 # 1. todos los pares USDT diarios (para calcular Universo)
```

- Verifica el `sha256` de cada archivo mensual y guarda un manifest por símbolo.
- Es incremental: solo descarga los meses que faltan (`--force` para rehacer).

### Construcción del Universo y Descarga Selectiva

Para evitar descargar `1m` para pares ilíquidos y reducir tiempos:

```powershell
# 2. Construir el Top 30 histórico
docker compose run --rm --entrypoint python freqtrade scripts/build_universe.py

# 3. Descargar velas de alta resolución (4h, 1m) SOLO para el Top 30
docker compose run --rm --entrypoint python freqtrade scripts/download_target.py
```

### Tests

```powershell
docker compose run --rm --entrypoint python freqtrade -m pytest -c tests/pytest.ini tests
```

## Reglas del proyecto (resumen del DAS)

1. Nada pasa a dry-run sin superar los umbrales de la Fase 0.
2. Todo backtest se ejecuta con costes **adversos** y `--timeframe-detail 1m`.
3. El hold-out final se usa **una sola vez**.
4. Secretos solo en `.env`, nunca en `config.json`.
