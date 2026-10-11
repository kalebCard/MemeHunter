"""Tests sin red para scripts/dryrun_monitor.py."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dryrun_monitor as dm  # noqa: E402


def make_db(path, rows):
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE trades (pair TEXT, is_open INT, is_short INT, open_date TEXT, "
        "close_date TEXT, close_profit REAL, close_profit_abs REAL, exit_reason TEXT)"
    )
    con.executemany("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


def row(i, ratio, is_open=0, short=0):
    return (f"P{i}/USDT", is_open, short, f"2026-10-{i % 28 + 1:02d}", None,
            None if is_open else ratio, None if is_open else ratio * 100, "roi")


def test_max_drawdown_basic():
    # 1000 -> 1100 (pico) -> 990 -> 1090: caida 10% desde el pico
    assert dm.max_drawdown([100, -110, 100], 1000) == pytest.approx(0.10)
    assert dm.max_drawdown([50, 50], 1000) == 0.0


def test_load_and_evaluate_counts_open_separately(tmp_path):
    db = tmp_path / "t.sqlite"
    make_db(db, [row(1, 0.05), row(2, -0.02), row(3, 0, is_open=1)])
    res = dm.evaluate(dm.load_trades(db), 1000, 0.262)
    assert res["closed"] == 2 and res["open"] == 1
    assert res["win_rate"] == 0.5
    assert res["edge"] == pytest.approx(0.015)
    assert not res["enough_data"]


def test_empty_db_has_no_metrics(tmp_path):
    db = tmp_path / "t.sqlite"
    make_db(db, [row(1, 0, is_open=1)])
    res = dm.evaluate(dm.load_trades(db), 1000, 0.262)
    assert res == {"closed": 0, "open": 1}


def test_checks_pass_and_fail(tmp_path):
    good = tmp_path / "good.sqlite"
    make_db(good, [row(i, 0.02 if i % 5 else -0.01) for i in range(40)])  # 80% win
    r = dm.evaluate(dm.load_trades(good), 1000, 0.262)
    assert r["enough_data"] and r["checks"]["edge"] and r["checks"]["drawdown"]
    assert not r["checks"]["win_rate"]  # 80% fuera de 57.8% +-10pp

    bad = tmp_path / "bad.sqlite"
    make_db(bad, [row(i, -0.01) for i in range(10)])
    r = dm.evaluate(dm.load_trades(bad), 1000, 0.262)
    assert not r["checks"]["edge"] and not r["checks"]["win_rate"]


def test_shorts_counted(tmp_path):
    db = tmp_path / "t.sqlite"
    make_db(db, [row(1, 0.01, short=1), row(2, 0.01)])
    r = dm.evaluate(dm.load_trades(db), 1000, 0.262)
    assert (r["longs"], r["shorts"]) == (1, 1)
