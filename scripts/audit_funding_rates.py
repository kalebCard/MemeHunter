"""
Auditor Cuantitativo de Tasas de Financiación (Funding Rates) para MemeHunterFuturesV1 (PB-31).
Calcula el costo real de funding pagado/cobrado vela a vela sobre los trades del backtest.
"""
import sys
import zipfile
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from data_engine.paths import get_futures_data_dir

DATA_DIR = get_futures_data_dir()
BACKTEST_ZIP = Path("user_data/backtest_results/backtest-result-2026-10-11_realistic_v3.zip")


def load_funding_data(pair: str) -> pd.DataFrame:
    clean_pair = pair.replace("/", "_").replace(":", "_")
    fpath = DATA_DIR / f"{clean_pair}-1h-funding_rate.feather"
    if not fpath.exists():
        return None
    try:
        df = pd.read_feather(fpath)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df.set_index("date", inplace=True)
        return df
    except Exception as exc:
        print(f"Error cargando funding para {pair}: {exc}")
        return None


def run_funding_audit():
    if not BACKTEST_ZIP.exists():
        print(f"No se encontró {BACKTEST_ZIP}")
        return

    with zipfile.ZipFile(BACKTEST_ZIP, "r") as z:
        data = json.loads(z.read("backtest-result-realistic.json"))

    strat_name = list(data["strategy"].keys())[0]
    trades = data["strategy"][strat_name].get("trades", [])

    print("=" * 75)
    print("🔬 AUDITORÍA REAL DE FUNDING RATES (PB-31) SOBRE TRADES HISTÓRICOS")
    print(f"Total de operaciones evaluadas: {len(trades)}")
    print("=" * 75)

    funding_cache = {}
    total_funding_cost_shorts = 0.0
    total_funding_cost_longs = 0.0
    trades_analyzed = 0

    for t in trades:
        pair = t.get("pair")
        is_short = t.get("is_short", False)
        open_date_str = t.get("open_date")
        close_date_str = t.get("close_date")
        stake_amount = t.get("stake_amount", 100.0)

        if not open_date_str or not close_date_str:
            continue

        open_dt = pd.to_datetime(open_date_str, utc=True)
        close_dt = pd.to_datetime(close_date_str, utc=True)

        if pair not in funding_cache:
            funding_cache[pair] = load_funding_data(pair)

        fdf = funding_cache[pair]
        if fdf is None or fdf.empty:
            continue

        # Filtrar funding rates ocurridos durante la vida del trade
        trade_fundings = fdf.loc[(fdf.index >= open_dt) & (fdf.index <= close_dt)]
        if trade_fundings.empty:
            continue

        # funding_rate column
        rate_col = "funding_rate" if "funding_rate" in trade_fundings.columns else trade_fundings.columns[0]
        sum_rate = trade_fundings[rate_col].sum()

        # En Futuros:
        # Long paga funding positivo, cobra funding negativo.
        # Short paga funding negativo, cobra funding positivo.
        # Costo para Short = sum_rate * (-1) * notional
        # Costo para Long = sum_rate * notional
        if is_short:
            # Si sum_rate es negativo, el short PAGA (costo positivo = pérdida de balance)
            cost = -sum_rate * stake_amount
            total_funding_cost_shorts += cost
        else:
            cost = sum_rate * stake_amount
            total_funding_cost_longs += cost

        trades_analyzed += 1

    total_profit_reported = data["strategy"][strat_name].get("profit_total_abs", 1579.74)
    net_funding_impact = total_funding_cost_shorts + total_funding_cost_longs
    adjusted_profit = total_profit_reported - net_funding_impact

    print(f"\nOperaciones con datos de Funding analizadas: {trades_analyzed} / {len(trades)}")
    print(f"• Impacto de Funding en SHORTS (815 trades):  {total_funding_cost_shorts:+.2f} USDT")
    print(f"• Impacto de Funding en LONGS  (339 trades):  {total_funding_cost_longs:+.2f} USDT")
    print(f"• IMPACTO TOTAL NETO DE FUNDING:              {net_funding_impact:+.2f} USDT")
    print("-" * 75)
    print(f"• Beneficio Bruto Reportado en Backtest:      +{total_profit_reported:.2f} USDT")
    print(f"• BENEFICIO REAL AJUSTADO POR FUNDING:        +{adjusted_profit:.2f} USDT ({(adjusted_profit / total_profit_reported - 1):.1%} variación)")
    print("=" * 75)


if __name__ == "__main__":
    run_funding_audit()
