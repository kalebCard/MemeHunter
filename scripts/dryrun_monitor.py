"""
Meme Hunter - Monitor del Dry-Run (PB-14)

Lee las bases SQLite de Freqtrade (solo lectura) y compara el dry-run contra los
criterios de aceptacion de SCRUM_PLAN.md:
  - Win rate dentro de +-10 pp del backtest (57.8%)
  - Edge neto medio por trade > 0.3%
  - Drawdown maximo < limite (P95 de Monte Carlo; configurable)

Uso:
    python scripts/monte_carlo.py   # (referencia del P95)
    python scripts/dryrun_monitor.py
    python scripts/dryrun_monitor.py --db user_data/tradesv3.live.sqlite --wallet 1000
"""
import argparse
import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DBS = {
    "Futuros": ROOT / "user_data" / "tradesv3.futures.sqlite",
    "Spot": ROOT / "user_data" / "tradesv3.live.sqlite",
}

BACKTEST_WIN_RATE = 0.578
WIN_RATE_TOLERANCE = 0.10
MIN_EDGE = 0.003
MIN_TRADES_FOR_VERDICT = 30


def load_trades(db: Path):
    uri = f"file:{db.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT pair, is_open, is_short, open_date, close_date, close_profit, "
            "close_profit_abs, exit_reason FROM trades ORDER BY open_date"
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def max_drawdown(profits_abs, wallet: float) -> float:
    """Drawdown maximo (fraccion) de la curva de equity acumulada sobre `wallet`."""
    equity = peak = wallet
    worst = 0.0
    for p in profits_abs:
        equity += p
        peak = max(peak, equity)
        worst = max(worst, (peak - equity) / peak if peak > 0 else 0.0)
    return worst


def evaluate(trades, wallet: float, dd_limit: float):
    closed = [t for t in trades if not t["is_open"] and t["close_profit"] is not None]
    open_ = [t for t in trades if t["is_open"]]
    result = {"closed": len(closed), "open": len(open_)}
    if not closed:
        return result

    ratios = [t["close_profit"] for t in closed]
    abs_ = [t["close_profit_abs"] or 0.0 for t in closed]
    wins = sum(1 for r in ratios if r > 0)
    result.update(
        win_rate=wins / len(closed),
        edge=sum(ratios) / len(ratios),
        pnl_abs=sum(abs_),
        pnl_pct=sum(abs_) / wallet,
        drawdown=max_drawdown(abs_, wallet),
        longs=sum(1 for t in closed if not t["is_short"]),
        shorts=sum(1 for t in closed if t["is_short"]),
    )
    result["checks"] = {
        "win_rate": abs(result["win_rate"] - BACKTEST_WIN_RATE) <= WIN_RATE_TOLERANCE,
        "edge": result["edge"] > MIN_EDGE,
        "drawdown": result["drawdown"] < dd_limit,
    }
    result["enough_data"] = len(closed) >= MIN_TRADES_FOR_VERDICT
    return result


def report(name: str, res: dict, dd_limit: float):
    print(f"\n=== {name} ===")
    print(f"Trades cerrados: {res['closed']} | abiertos: {res['open']}")
    if "win_rate" not in res:
        print("Sin trades cerrados todavia: no hay metricas.")
        return
    mark = lambda ok: "OK " if ok else "FALLA"
    c = res["checks"]
    print(f"Long/Short cerrados: {res['longs']}/{res['shorts']}")
    print(f"PnL cerrado: {res['pnl_abs']:+.2f} USDT ({res['pnl_pct']:+.2%} de la cartera)")
    print(f"[{mark(c['win_rate'])}] Win rate: {res['win_rate']:.1%} "
          f"(objetivo {BACKTEST_WIN_RATE:.1%} +-{WIN_RATE_TOLERANCE:.0%})")
    print(f"[{mark(c['edge'])}] Edge medio/trade: {res['edge']:+.2%} (minimo {MIN_EDGE:.1%})")
    print(f"[{mark(c['drawdown'])}] Max drawdown: {res['drawdown']:.2%} (limite {dd_limit:.0%})")
    if not res["enough_data"]:
        print(f"(!) Muestra insuficiente: {res['closed']} < {MIN_TRADES_FOR_VERDICT} trades. "
              "Los resultados NO son concluyentes.")
    else:
        print("Veredicto parcial:", "CUMPLE" if all(c.values()) else "NO CUMPLE")


def main():
    ap = argparse.ArgumentParser(description="Monitor del dry-run vs criterios de aceptacion")
    ap.add_argument("--db", type=Path, help="Una sola base SQLite (por defecto: futuros y spot)")
    ap.add_argument("--wallet", type=float, default=1000.0, help="dry_run_wallet inicial (USDT)")
    ap.add_argument("--dd-limit", type=float, default=0.262,
                    help="Limite de drawdown (fraccion). Por defecto 26.2%% (max DD del hold-out); "
                         "sustituir por el P95 de monte_carlo.py")
    args = ap.parse_args()

    dbs = {args.db.stem: args.db} if args.db else DEFAULT_DBS
    for name, db in dbs.items():
        if not db.exists():
            print(f"\n=== {name} ===\nBase no encontrada: {db}")
            continue
        report(name, evaluate(load_trades(db), args.wallet, args.dd_limit), args.dd_limit)


if __name__ == "__main__":
    main()
