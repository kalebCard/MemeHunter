#!/usr/bin/env python3
"""
PB-03 - Construcción del Universo Dinámico (Top N histórico).

Filtra y clasifica los pares de Binance Spot por su `quote_volume` (volumen en USDT)
mes a mes, usando exclusivamente datos del pasado (para evitar el sesgo de anticipación).
Genera un mapa temporal que la estrategia usará para decidir si un par era operable
en una fecha determinada.

Salida:
    /freqtrade/user_data/data/binance_vision/universe.json
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

LOG = logging.getLogger("build_universe")
DEFAULT_DATADIR = Path("/freqtrade/user_data/data")

def build_universe(datadir: Path, top_n: int = 30) -> dict[str, list[str]]:
    klines_dir = datadir / "binance_vision" / "klines" / "1d"
    if not klines_dir.exists():
        LOG.error("No se encontraron datos 1d en %s", klines_dir)
        return {}

    LOG.info("Leyendo históricos 1d para calcular volumen mensual...")
    monthly_volumes = []
    
    for feather_path in klines_dir.glob("*.feather"):
        pair_raw = feather_path.stem
        # Omitimos pares estables o con base fiat si lo preferimos,
        # aunque la whitelist final del config también filtrará
        if pair_raw.endswith("USDC") or pair_raw.endswith("FDUSD"):
            continue
            
        try:
            df = pd.read_feather(feather_path)
            if df.empty or "quote_volume" not in df.columns:
                continue
                
            # Agrupar por mes UTC. Usamos sum() para ver el volumen total movido ese mes.
            df["month"] = df["date"].dt.strftime("%Y-%m")
            monthly = df.groupby("month")["quote_volume"].sum().reset_index()
            monthly["pair"] = pair_raw
            monthly_volumes.append(monthly)
        except Exception as e:
            LOG.warning("No se pudo leer %s: %s", feather_path, e)
            
    if not monthly_volumes:
        return {}
        
    all_volumes = pd.concat(monthly_volumes, ignore_index=True)
    
    # Nos interesa que un par sea seleccionable para el mes M si durante el mes M-1
    # estuvo en el Top N. Así evitamos lookahead bias (usar el volumen de M para operar en M).
    # Ordenamos y sacamos el ranking.
    
    universe = {}
    months = sorted(all_volumes["month"].unique())
    
    for i in range(1, len(months)):
        prev_month = months[i - 1]
        curr_month = months[i]
        
        # Ranking del mes anterior
        rank = all_volumes[all_volumes["month"] == prev_month].sort_values("quote_volume", ascending=False)
        top_pairs = rank.head(top_n)["pair"].tolist()
        
        # Reformatear de BTCUSDT a BTC/USDT si termina en USDT (asumimos USDT por ahora)
        formatted_pairs = []
        for p in top_pairs:
            if p.endswith("USDT"):
                formatted_pairs.append(f"{p[:-4]}/USDT")
            else:
                formatted_pairs.append(p)  # fallback
                
        universe[curr_month] = formatted_pairs
        
    return universe

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datadir", type=Path, default=DEFAULT_DATADIR)
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    universe_map = build_universe(args.datadir, args.top_n)
    if not universe_map:
        return 1

    out_file = args.datadir / "binance_vision" / "universe.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(universe_map, indent=2))
    
    LOG.info("Universo dinámico (Top %d) construido para %d meses.", args.top_n, len(universe_map))
    LOG.info("Guardado en %s", out_file)
    return 0

if __name__ == "__main__":
    sys.exit(main())
