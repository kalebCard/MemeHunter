"""
tests/test_profit_ratchet.py - Tests unitarios del Daemon de Trinquete (PB-68).
Valida:
1. Detección de hito de duplicación (+100%) y ejecución de cosecha (Harvesting).
2. Reseteo de base operativa e inmunización del capital transferido.
3. Activación matemática del Kill-Switch ante Drawdown >= 25%.
"""

import pytest
from pathlib import Path
from scripts.ops.profit_ratchet_daemon import ProfitRatchetDaemon


def test_ratchet_harvest_cycle(tmp_path):
    state_file = tmp_path / "ratchet_state_1.json"
    dummy_db = tmp_path / "dummy1.sqlite"

    daemon = ProfitRatchetDaemon(
        db_path=dummy_db,
        starting_capital=1000.0,
        harvest_target_pct=1.0,  # Hito al llegar a $2,000 (+100%)
        harvest_ratio=0.60,      # 60% a bóveda, 40% reinversión
        kill_switch_dd=0.25,
        dry_run=True,
        state_file=state_file
    )

    # Simular una ganancia que lleva el equity a $2,100 (+1,100 de profit)
    res = daemon.check_and_ratchet(external_unrealized_pnl=1100.0)

    assert res["status"] == "HARVESTED"
    # Ganancia total = 1,100 -> 60% cosechado = 660, 40% reinvertido = 440
    assert daemon.total_harvested == 660.0
    assert daemon.base_capital == 1440.0
    assert daemon.cycle_count == 1


def test_ratchet_kill_switch_trigger(tmp_path):
    state_file = tmp_path / "ratchet_state_2.json"
    dummy_db = tmp_path / "dummy2.sqlite"

    daemon = ProfitRatchetDaemon(
        db_path=dummy_db,
        starting_capital=1000.0,
        kill_switch_dd=0.25,
        dry_run=True,
        state_file=state_file
    )

    # Simular caída de equidad a $700 (Drawdown = 30% > 25%)
    res = daemon.check_and_ratchet(external_unrealized_pnl=-300.0)

    assert res["status"] == "KILLED"
    assert res["drawdown"] == 0.30
