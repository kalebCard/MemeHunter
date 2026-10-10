# meme_hunter

Bot de trading sobre [Freqtrade](https://www.freqtrade.io/) cuyo objetivo es **validar empíricamente un edge** antes de arriesgar capital.

- Arquitectura: [DAS.md](DAS.md)
- Plan de trabajo: [SCRUM_PLAN.md](SCRUM_PLAN.md)

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
docker compose pull                  # actualizar imagen
docker compose run --rm freqtrade --version
docker compose run --rm freqtrade list-exchanges
```

## Reglas del proyecto (resumen del DAS)

1. Nada pasa a dry-run sin superar los umbrales de la Fase 0.
2. Todo backtest se ejecuta con costes **adversos** y `--timeframe-detail 1m`.
3. El hold-out final se usa **una sola vez**.
4. Secretos solo en `.env`, nunca en `config.json`.
