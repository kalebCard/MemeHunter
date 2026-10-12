"""
test_atomic_io.py - Pruebas unitarias de persistencia atómica transaccional (US-4.1).
"""

import json
from pathlib import Path
import pytest
from portfolio.atomic_io import atomic_write_json


def test_atomic_write_json_creates_file(tmp_path: Path):
    target = tmp_path / "subfolder" / "state.json"
    data = {"system": "meme_hunter", "version": 7.1, "active": True}
    
    atomic_write_json(target, data)
    
    assert target.exists()
    assert not (tmp_path / "subfolder" / "state.json.tmp").exists()
    
    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data


def test_atomic_write_json_overwrites_cleanly(tmp_path: Path):
    target = tmp_path / "config.json"
    initial_data = {"count": 1}
    updated_data = {"count": 2, "status": "LIVE"}
    
    atomic_write_json(target, initial_data)
    atomic_write_json(target, updated_data)
    
    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == updated_data


def test_atomic_write_json_handles_complex_types(tmp_path: Path):
    from datetime import datetime, timezone
    target = tmp_path / "audit.json"
    now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    data = {"timestamp": now, "weights": {"A": 0.5, "B": 0.5}}
    
    atomic_write_json(target, data)
    assert target.exists()
    
    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert "2026-10-12" in loaded["timestamp"]
    assert loaded["weights"]["A"] == 0.5
