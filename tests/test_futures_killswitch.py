"""Tests sin red para el kill-switch de MemeHunterFuturesV1 (PB-15)."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "user_data" / "strategies"))
import MemeHunterFuturesV1 as mod  # noqa: E402

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def make(tmp_path, runmode="dry_run", wallet=1000):
    return mod.MemeHunterFuturesV1({
        "runmode": runmode, "dry_run_wallet": wallet, "user_data_dir": str(tmp_path),
        "stake_currency": "USDT",
    })


def closed_trades(profits):
    return [SimpleNamespace(close_profit_abs=p, close_date_utc=datetime(2026, 1, i + 1, tzinfo=timezone.utc))
            for i, p in enumerate(profits)]


def set_trades(monkeypatch, profits, open_profits=None):
    if open_profits is None:
        open_profits = []
    def proxy(is_open=False):
        if is_open:
            return [SimpleNamespace(current_profit_abs=p) for p in open_profits]
        return closed_trades(profits)
    monkeypatch.setattr(mod.Trade, "get_trades_proxy", staticmethod(proxy))


def enter(s, side="long"):
    return s.confirm_trade_entry("BTC/USDT:USDT", "limit", 1, 1, "GTC", NOW, "tag", side)


def test_compute_drawdown():
    assert mod.compute_drawdown([], 1000) == 0.0
    assert mod.compute_drawdown([100, -110], 1000) == pytest.approx(0.10)  # 1100 -> 990
    # Es el drawdown ACTUAL: 1000 -> 1100 -> 990 -> 1090 se recupera a 0.9% del pico
    assert mod.compute_drawdown([100, -110, 100], 1000) == pytest.approx(10 / 1100)
    assert mod.compute_drawdown([50, 50], 1000) == 0.0
    assert mod.compute_drawdown([-500], 0) == 0.0  # sin capital base no divide por cero
    # PB-25: Drawdown con equidad flotante
    assert mod.compute_drawdown([], 1000, open_profit_abs=-260) == pytest.approx(0.26)
    assert mod.compute_drawdown([200], 1000, open_profit_abs=-360) == pytest.approx(360 / 1200)


def test_allows_entry_below_threshold(tmp_path, monkeypatch):
    set_trades(monkeypatch, [-200])  # 20% < 25%
    assert enter(make(tmp_path)) is True
    assert not (tmp_path / mod.KILL_SWITCH_FLAG).exists()


def test_blocks_and_latches_in_dry_run(tmp_path, monkeypatch):
    set_trades(monkeypatch, [-260])  # 26% >= 25%
    s = make(tmp_path)
    assert enter(s) is False
    assert (tmp_path / mod.KILL_SWITCH_FLAG).exists()
    # Aunque el equity se recupere, el latch sigue bloqueando hasta borrar el archivo
    set_trades(monkeypatch, [])
    assert enter(s) is False
    (tmp_path / mod.KILL_SWITCH_FLAG).unlink()
    assert enter(s) is True


def test_blocks_on_open_unrealized_drawdown(tmp_path, monkeypatch):
    # PB-25: 0 pérdida cerrada, pero -270 en posiciones vivas flotantes (27% DD)
    set_trades(monkeypatch, [], open_profits=[-150, -120])
    s = make(tmp_path)
    assert enter(s) is False


def test_blocks_on_adverse_funding_rate(tmp_path, monkeypatch):
    # PB-24: Guardián de Funding Rate
    set_trades(monkeypatch, [])
    s = make(tmp_path)
    mock_exchange = SimpleNamespace(get_funding_rate=lambda pair: -0.0008)
    s.exchange = mock_exchange
    # Short debe ser bloqueado por funding sangrante (-0.08% < -0.05%)
    assert enter(s, side="short") is False
    # Long se permite normalmente
    assert enter(s, side="long") is True


def test_backtest_blocks_without_writing_flag(tmp_path, monkeypatch):
    set_trades(monkeypatch, [-300])
    s = make(tmp_path, runmode="backtest")
    assert enter(s) is False
    assert not (tmp_path / mod.KILL_SWITCH_FLAG).exists()


def test_backtest_ignores_stale_flag_file(tmp_path, monkeypatch):
    (tmp_path / mod.KILL_SWITCH_FLAG).write_text("x")
    set_trades(monkeypatch, [])
    assert enter(make(tmp_path, runmode="backtest")) is True


def test_peak_based_not_start_based(tmp_path, monkeypatch):
    # sube a 1400 y cae a 1000: DD 28.6% desde el pico aunque no pierda vs. capital inicial
    set_trades(monkeypatch, [400, -400])
    assert enter(make(tmp_path)) is False
