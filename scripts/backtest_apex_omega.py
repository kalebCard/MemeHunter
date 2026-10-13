"""
scripts/backtest_apex_omega.py
------------------------------
Simulador de Backtesting Institucional de Alta Fidelidad para MemeHunter_ApexOmegaAlpha.
Evalúa el rendimiento de la estrategia definitiva sobre los 10 principales pares memecoin
en Binance (PEPE, BONK, FLOKI, SHIB, BOME, DOGE, MEW, NEIRO, POPCAT, WIF).
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any
import numpy as np
import pandas as pd

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))

from MemeHunter_ApexOmegaAlpha import MemeHunter_ApexOmegaAlpha
from data_engine.paths import get_futures_data_dir

DATA_DIR = get_futures_data_dir()


class MockTrade:
    def __init__(self, pair: str, open_rate: float, open_date: datetime, stake_amount: float, side: str = "long"):
        self.pair = pair
        self.open_rate = open_rate
        self.open_date_utc = open_date
        self.stake_amount = stake_amount
        self.side = side
        self.highest_rate = open_rate
        self.lowest_rate = open_rate
        self.max_profit_ratio = 0.0
        self.current_stoploss_ratio = -0.030
        self.exit_reason = None
        self.close_rate = 0.0
        self.close_date = None
        self.pnl_ratio = 0.0
        self.pnl_net_usdt = 0.0
        self.is_open = True


def run_apex_omega_backtest(
    initial_wallet: float = 100.0,
    max_open_trades: int = 3,
    fee_rate: float = 0.00075,
    enforce_friction_gate: bool = True
) -> Dict[str, Any]:
    print("=" * 65)
    print("🚀 INICIANDO BACKTEST INSTITUCIONAL DE MEMEHUNTER_APEXOMEGAALPHA")
    print(f"💰 Capital Inicial: {initial_wallet:.2f} USDT | Slots Concurrentes: {max_open_trades}")
    print(f"⚡ Tarifa de Exchange: {fee_rate:.3%} (BNB Maker/Taker) | Filtro Rentabilidad: {enforce_friction_gate}")
    print("=" * 65)

    strategy = MemeHunter_ApexOmegaAlpha()
    strategy.enforce_profitability_gate = enforce_friction_gate

    pair_files = sorted(list(DATA_DIR.glob("*1h-futures.feather")))
    if not pair_files:
        raise FileNotFoundError(f"No se encontraron archivos en {DATA_DIR}")

    datasets: Dict[str, pd.DataFrame] = {}
    for pfile in pair_files:
        raw_name = pfile.name.replace("_USDT_USDT-1h-futures.feather", "").replace("1000", "")
        pair_name = f"{raw_name}/USDT"
        df = pd.read_feather(pfile)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.sort_values("date").reset_index(drop=True)

        df = strategy.populate_indicators(df, {"pair": pair_name})
        df = strategy.populate_entry_trend(df, {"pair": pair_name})
        df = strategy.populate_exit_trend(df, {"pair": pair_name})
        datasets[pair_name] = df

    all_timestamps = set()
    for df in datasets.values():
        all_timestamps.update(df["date"].tolist())
    timeline = sorted(list(all_timestamps))

    time_indices = {}
    for pair, df in datasets.items():
        time_indices[pair] = {ts: idx for idx, ts in enumerate(df["date"])}

    current_wallet = initial_wallet
    open_trades: List[MockTrade] = []
    closed_trades: List[MockTrade] = []
    rejected_friction_count = 0

    for current_time in timeline:
        # 1. Gestionar Trades Abiertos
        still_open: List[MockTrade] = []
        for trade in open_trades:
            df = datasets[trade.pair]
            t_idx = time_indices[trade.pair].get(current_time)
            if t_idx is None:
                still_open.append(trade)
                continue

            row = df.iloc[t_idx]
            cur_high = row["high"]
            cur_low = row["low"]
            cur_close = row["close"]

            if cur_high > trade.highest_rate:
                trade.highest_rate = cur_high
            if cur_low < trade.lowest_rate:
                trade.lowest_rate = cur_low

            cur_profit = (cur_close - trade.open_rate) / trade.open_rate

            # Trinquete Stoploss
            dyn_sl = strategy.custom_stoploss(trade.pair, trade, current_time, cur_close, cur_profit)
            trade.current_stoploss_ratio = dyn_sl

            # Custom Exit (Time-stop o debilidad)
            cust_exit = strategy.custom_exit(trade.pair, trade, current_time, cur_close, cur_profit)

            # Verificar condiciones de salida
            exit_triggered = False
            exit_rate = cur_close
            exit_reason = None

            # A. Stoploss alcanzado
            if cur_low <= trade.open_rate * (1.0 + dyn_sl):
                exit_triggered = True
                exit_rate = trade.open_rate * (1.0 + dyn_sl)
                exit_reason = "ratchet_stoploss" if dyn_sl > -0.020 else "hard_stoploss"

            # B. Take Profit de ROI Escalonado
            elif cur_high >= trade.open_rate * 1.060:
                exit_triggered = True
                exit_rate = trade.open_rate * 1.060
                exit_reason = "roi_target_6pct"

            elif cur_high >= trade.open_rate * 1.035 and (current_time - trade.open_date_utc).total_seconds() >= 4 * 3600:
                exit_triggered = True
                exit_rate = trade.open_rate * 1.035
                exit_reason = "roi_target_3_5pct"

            # C. Salida Técnica Airbag
            elif row.get("exit_long", 0) == 1:
                exit_triggered = True
                exit_rate = cur_close
                exit_reason = "airbag_technical_exit"

            # D. Time-Stop Anti-Bagholding
            elif cust_exit is not None:
                exit_triggered = True
                exit_rate = cur_close
                exit_reason = cust_exit

            if exit_triggered:
                trade.is_open = False
                trade.close_rate = exit_rate
                trade.close_date = current_time
                trade.exit_reason = exit_reason

                gross_pnl_ratio = (exit_rate - trade.open_rate) / trade.open_rate
                fees = (trade.open_rate * fee_rate) + (exit_rate * fee_rate)
                net_pnl_ratio = gross_pnl_ratio - (fee_rate * 2)

                trade.pnl_ratio = net_pnl_ratio
                trade.pnl_net_usdt = trade.stake_amount * net_pnl_ratio

                current_wallet += (trade.stake_amount + trade.pnl_net_usdt)
                closed_trades.append(trade)
            else:
                still_open.append(trade)

        open_trades = still_open

        # 2. Evaluar Nuevas Entradas
        for pair in datasets.keys():
            if len(open_trades) >= max_open_trades:
                break

            # Evitar duplicar par
            if any(t.pair == pair for t in open_trades):
                continue

            df = datasets[pair]
            t_idx = time_indices[pair].get(current_time)
            if t_idx is None:
                continue

            row = df.iloc[t_idx]
            if row.get("enter_long", 0) == 1:
                entry_price = row["close"]

                # Filtro pre-trade de rentabilidad
                if enforce_friction_gate and strategy.profitability_gate:
                    dec = strategy.profitability_gate.evaluate_entry(
                        symbol=pair,
                        current_price=entry_price,
                        spread_pct=0.0010
                    )
                    if not dec.is_approved:
                        rejected_friction_count += 1
                        continue

                available_slot_capital = current_wallet / (max_open_trades - len(open_trades))
                stake_size = min(available_slot_capital, current_wallet)

                if stake_size >= 5.0 and current_wallet >= stake_size:
                    current_wallet -= stake_size
                    new_trade = MockTrade(
                        pair=pair,
                        open_rate=entry_price,
                        open_date=current_time,
                        stake_amount=stake_size,
                        side="long"
                    )
                    open_trades.append(new_trade)

    # Resultados y Métricas Institucionales
    total_trades = len(closed_trades)
    winning_trades = [t for t in closed_trades if t.pnl_net_usdt > 0]
    losing_trades = [t for t in closed_trades if t.pnl_net_usdt <= 0]
    win_rate = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(t.pnl_net_usdt for t in winning_trades)
    gross_loss = abs(sum(t.pnl_net_usdt for t in losing_trades))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    # Curva de Equity y Drawdown
    equity_curve = [initial_wallet]
    running_eq = initial_wallet
    peaks = [initial_wallet]
    drawdowns = [0.0]

    for t in closed_trades:
        running_eq += t.pnl_net_usdt
        equity_curve.append(running_eq)
        current_peak = max(peaks[-1], running_eq)
        peaks.append(current_peak)
        dd = (current_peak - running_eq) / current_peak
        drawdowns.append(dd)

    max_drawdown_pct = max(drawdowns) * 100.0 if drawdowns else 0.0
    returns = [t.pnl_ratio for t in closed_trades]
    mean_ret = np.mean(returns) if returns else 0.0
    std_ret = np.std(returns) if returns else 1.0
    downside_std = np.std([r for r in returns if r < 0]) if any(r < 0 for r in returns) else 1e-4

    sharpe = (mean_ret / std_ret * np.sqrt(365 * 24)) if std_ret > 0 else 0.0
    sortino = (mean_ret / downside_std * np.sqrt(365 * 24)) if downside_std > 0 else 0.0

    final_equity = current_wallet + sum(t.stake_amount for t in open_trades)
    net_return_pct = ((final_equity - initial_wallet) / initial_wallet) * 100.0

    print("\n" + "=" * 65)
    print("📊 RESULTADOS OFICIALES MEMEHUNTER_APEXOMEGAALPHA (BINANCE)")
    print("=" * 65)
    print(f" • Capital Inicial       : ${initial_wallet:,.2f} USDT")
    print(f" • Capital Final         : ${final_equity:,.2f} USDT")
    print(f" • Retorno Neto          : {net_return_pct:+.2f}%")
    print(f" • Total de Trades       : {total_trades}")
    print(f" • Win Rate              : {win_rate:.2f}% ({len(winning_trades)} W / {len(losing_trades)} L)")
    print(f" • Profit Factor         : {profit_factor:.2f}")
    print(f" • Max Drawdown          : {max_drawdown_pct:.2f}%")
    print(f" • Sharpe Ratio Anual    : {sharpe:.2f}")
    print(f" • Sortino Ratio Anual   : {sortino:.2f}")
    print(f" • Órdenes Descartadas   : {rejected_friction_count} por filtro de fricción")
    print("=" * 65)

    # Desglose de Salidas
    exit_counts = {}
    for t in closed_trades:
        exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1

    print("\n📍 Desglose de Salidas por Mecanismo:")
    for reason, count in sorted(exit_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {reason:<26}: {count:3d} trades ({count/total_trades*100.0:.1f}%)")
    print("=" * 65 + "\n")

    return {
        "final_equity": final_equity,
        "net_return_pct": net_return_pct,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe": sharpe,
        "sortino": sortino
    }


if __name__ == "__main__":
    run_apex_omega_backtest()
