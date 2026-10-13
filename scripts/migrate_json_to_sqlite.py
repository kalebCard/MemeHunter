"""
Meme Hunter - Backward Compatibility Shim
Canonical Location: scripts/ops/migrate_json_to_sqlite.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_TARGET = Path(__file__).resolve().parent / "ops" / "migrate_json_to_sqlite.py"

if __name__ == "__main__":
    import runpy
    runpy.run_path(str(_TARGET), run_name="__main__")
else:
    from scripts.ops.migrate_json_to_sqlite import *
