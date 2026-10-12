import pytest
from dashboard.strategy_tester import validate_formula_ast, load_ohlcv_dataset, run_strategy_backtest


def test_validate_formula_ast_valid():
    res = validate_formula_ast("ts_decay_linear(returns, 5) * ts_rank(volume, 10)")
    assert res["valid"] is True
    assert res["depth"] >= 1
    assert "returns" in res["features_used"]
    assert "volume" in res["features_used"]


def test_validate_formula_ast_invalid():
    res = validate_formula_ast("import os; os.system('echo hacked')")
    assert res["valid"] is False
    assert "error" in res


def test_load_ohlcv_dataset():
    df = load_ohlcv_dataset("1000PEPE", "4h")
    assert not df.empty
    assert len(df) >= 30
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns


def test_run_strategy_backtest():
    formula = "ts_decay_linear(returns, 5) * ts_rank(volume, 10)"
    res = run_strategy_backtest(
        formula=formula,
        pair="1000PEPE",
        timeframe="4h",
        direction="short_only",
        leverage=1.5,
        stoploss_pct=0.10,
        trailing_stop_pct=0.04
    )
    assert res["success"] is True
    assert res["status"] == "success"
    assert "STUDIO_1000PEPE" in res["strategy_id"]
    m = res["metrics"]
    assert "sharpe_ratio" in m
    assert "net_return_pct" in m
    assert "max_drawdown_pct" in m
    assert "win_rate_pct" in m
    assert "total_trades" in m
    assert len(res["equity_curve"]) > 0
