"""
Script lanzador para el MemeHunter Alpha Cockpit Visual Dashboard.
Sprint 3: Monitoreo Visual e Interfaz de Control Cuantitativo.
"""

import os
import sys

# Agregar path raíz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# Configurar encoding UTF-8 seguro para Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

from dashboard.server import run_server

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    run_server(port)

