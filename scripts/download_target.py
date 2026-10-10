#!/usr/bin/env python3
"""
PB-04 - Descarga Selectiva del Universo Dinámico (1m, 4h).
En lugar de descargar datos intradiarios de 757 pares, lee `universe.json`
y descarga el histórico completo de 4h y 1m solo para las monedas que alguna vez
formaron parte del Top 30.
"""
import json
import subprocess
import sys
from pathlib import Path
import logging

LOG = logging.getLogger("download_target")

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    universe_file = Path("/freqtrade/user_data/data/binance_vision/universe.json")
    if not universe_file.exists():
        LOG.error("%s no encontrado. Ejecuta build_universe.py primero.", universe_file)
        sys.exit(1)
    
    data = json.loads(universe_file.read_text())
    pairs = set()
    for month_pairs in data.values():
        pairs.update(month_pairs)
    
    symbols = [p.replace("/", "") for p in pairs]
    LOG.info("Encontrados %d pares unicos en el universo historico.", len(symbols))
    if not symbols:
        LOG.warning("El universo esta vacio.")
        sys.exit(0)
    
    cmd = [
        "python", "scripts/binance_vision.py", "download",
        "--symbols"
    ] + symbols + [
        "--interval", "4h", "1m",
        "--start", "2020-01"
    ]
    
    LOG.info("Ejecutando descarga para intervalos 4h y 1m...")
    subprocess.run(cmd, check=True)
    LOG.info("Descarga completada con exito.")

if __name__ == "__main__":
    main()
