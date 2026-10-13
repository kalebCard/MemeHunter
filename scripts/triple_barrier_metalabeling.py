"""
Meme Hunter - Backward Compatibility Shim
Canonical Location: scripts/research/triple_barrier_metalabeling.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_TARGET = Path(__file__).resolve().parent / "research" / "triple_barrier_metalabeling.py"

if __name__ == "__main__":
    import runpy
    runpy.run_path(str(_TARGET), run_name="__main__")
else:
    from scripts.research.triple_barrier_metalabeling import *
