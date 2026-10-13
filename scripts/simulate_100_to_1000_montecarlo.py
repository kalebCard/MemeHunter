"""
Meme Hunter - Backward Compatibility Shim
Canonical Location: scripts/simulation/simulate_100_to_1000_montecarlo.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_TARGET = Path(__file__).resolve().parent / "simulation" / "simulate_100_to_1000_montecarlo.py"

if __name__ == "__main__":
    import runpy
    runpy.run_path(str(_TARGET), run_name="__main__")
else:
    from scripts.simulation.simulate_100_to_1000_montecarlo import *
