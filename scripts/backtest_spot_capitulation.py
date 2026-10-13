"""
scripts/backtest_spot_capitulation.py
-------------------------------------
Simulador de Backtesting de Alta Fidelidad para MemeHunterSpot_CapitulationAlpha.
Evalúa el rendimiento de la estrategia sobre el histórico real de 1H en Binance
para los 10 principales pares memecoin (PEPE, BONK, FLOKI, SHIB, BOME, DOGE, MEW, NEIRO, POPCAT, WIF).
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))

from MemeHunterSpot_CapitulationAlpha import MemeHunterSpot_CapitulationAlpha

DATA_DIR = Path("C:/meme_hunter_data/binance/futures")


class MockTrade:
    def __init__(self, pair: str, open_rate: float, open_date: datetime, stake_amount: float):
        self.pair = pair
        self.open_rate = open_rate
        self.open_date_utc = open_date
        self.stake_amount = stake_amount
        self.highest_rate = open_rate
        self.lowest_rate = open_rate
        self.max_profit_ratio = 0.0
        self.current_stoploss_ratio = -0.045
        self.exit_reason = None
        self.close_rate = 0.0
        self.close_date = None
        self.pnl_ratio = 0.0
        self.pnl_net_usdt = 0.0
        self.is_open = True


def run_spot_backtest(
    initial_wallet: float = 100.0,
    max_open_trades: int = 3,
    fee_rate: float = 0.00075  # 0.075% tarifa Binance Spot usando BNB (0.15% roundtrip)
) -> Dict[str, Any]:
    strategy = MemeHunterSpot_CapitulationAlpha()
    
    # Pares disponibles en 1h
    pair_files = sorted(list(DATA_DIR.glob("*1h-futures.feather")))
    if not pair_files:
        raise FileNotFoundError("No se encontraron archivos 1h en C:/meme_hunter_data/binance/futures")

    # Cargar y preprocesar datos
    datasets = {}
    for pfile in pair_files:
        raw_name = pfile.name.replace("_USDT_USDT-1h-futures.feather", "").replace("1000", "")
        pair_name = f"{raw_name}/USDT"
        df = pd.read_feather(pfile)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calcular indicadores y señales
        df = strategy.populate_indicators(df, {"pair": pair_name})
        df = strategy.populate_entry_trend(df, {"pair": pair_name})
        df = strategy.populate_exit_trend(df, {"pair": pair_name})
        datasets[pair_name] = df

    # Unificar línea temporal para simular portafolio realista
    all_timestamps = sorted(list(set.union(*[set(df['date']) for df in datasets.values()])))
    # Filtrar solo periodos con warmup suficiente (después del índice 50)
    all_timestamps = all_timestamps[50:]

    wallet = initial_wallet
    open_trades: List[MockTrade] = []
    closed_trades: List[MockTrade] = []
    equity_curve = []

    # Mapas de acceso rápido por timestamp y par
    df_by_pair = {pair: df.set_index('date') for pair, df in datasets.items()}

    for current_time in all_timestamps:
        # 1. Gestionar trades abiertos en la vela actual
        still_open = []
        for trade in open_trades:
            pair_df = df_by_pair[trade.pair]
            if current_time not in pair_df.index:
                still_open.append(trade)
                continue

            candle = pair_df.loc[current_time]
            c_open = candle['open']
            c_high = candle['high']
            c_low = candle['low']
            c_close = candle['close']

            trade.highest_rate = max(trade.highest_rate, c_high)
            trade.lowest_rate = min(trade.lowest_rate, c_low)

            hours_elapsed = (current_time - trade.open_date_utc).total_seconds() / 3600.0
            peak_profit = (trade.highest_rate - trade.open_rate) / trade.open_rate
            trade.max_profit_ratio = max(trade.max_profit_ratio, peak_profit)

            # Actualizar stoploss según custom_stoploss
            current_profit_close = (c_close - trade.open_rate) / trade.open_rate
            sl_ratio = strategy.custom_stoploss(
                trade.pair, trade, current_time, c_close, current_profit_close
            )
            trade.current_stoploss_ratio = sl_ratio

            # A. Chequear si el Low de la vela perforó el Stoploss
            low_profit = (c_low - trade.open_rate) / trade.open_rate
            if low_profit <= trade.current_stoploss_ratio:
                trade.is_open = False
                exit_price = trade.open_rate * (1.0 + trade.current_stoploss_ratio)
                trade.close_rate = max(c_low, exit_price)
                trade.close_date = current_time
                if trade.current_stoploss_ratio > 0.0:
                    trade.exit_reason = "custom_stoploss_breakeven_or_lock"
                else:
                    trade.exit_reason = "hard_stoploss"
                closed_trades.append(trade)
                # Actualizar wallet
                gross_pnl = (trade.close_rate - trade.open_rate) / trade.open_rate
                net_pnl = gross_pnl - (fee_rate * 2.0)
                pnl_usdt = trade.stake_amount * net_pnl
                wallet += trade.stake_amount + pnl_usdt
                continue

            # B. Chequear si el High de la vela alcanzó la matriz ROI
            # ROI: 0h: 8.0%, 1h: 6.0%, 4h: 4.0%, 8h: 2.0%, 12h: 1.0%
            roi_target = 0.080
            if hours_elapsed >= 12.0:
                roi_target = 0.010
            elif hours_elapsed >= 8.0:
                roi_target = 0.020
            elif hours_elapsed >= 4.0:
                roi_target = 0.040
            elif hours_elapsed >= 1.0:
                roi_target = 0.060

            if peak_profit >= roi_target:
                trade.is_open = False
                trade.close_rate = trade.open_rate * (1.0 + roi_target)
                trade.close_date = current_time
                trade.exit_reason = f"roi_target_{int(roi_target*100)}pct"
                closed_trades.append(trade)
                gross_pnl = roi_target
                net_pnl = gross_pnl - (fee_rate * 2.0)
                pnl_usdt = trade.stake_amount * net_pnl
                wallet += trade.stake_amount + pnl_usdt
                continue

            # C. Chequear custom_exit (Time-Stop o Early Weakness Airbag)
            exit_signal_reason = strategy.custom_exit(
                trade.pair, trade, current_time, c_close, current_profit_close
            )
            if exit_signal_reason:
                trade.is_open = False
                trade.close_rate = c_close
                trade.close_date = current_time
                trade.exit_reason = exit_signal_reason
                closed_trades.append(trade)
                gross_pnl = (c_close - trade.open_rate) / trade.open_rate
                net_pnl = gross_pnl - (fee_rate * 2.0)
                pnl_usdt = trade.stake_amount * net_pnl
                wallet += trade.stake_amount + pnl_usdt
                continue

            # D. Salida Técnica (populate_exit_trend: EMA50 recuperada o RSI >= 65)
            if candle.get('exit_long', 0) == 1 and current_profit_close > 0.015:
                trade.is_open = False
                trade.close_rate = c_close
                trade.close_date = current_time
                trade.exit_reason = "technical_exit_exhaustion"
                closed_trades.append(trade)
                gross_pnl = current_profit_close
                net_pnl = gross_pnl - (fee_rate * 2.0)
                pnl_usdt = trade.stake_amount * net_pnl
                wallet += trade.stake_amount + pnl_usdt
                continue

            still_open.append(trade)

        open_trades = still_open

        # 2. Buscar nuevas entradas si hay slots disponibles
        available_slots = max_open_trades - len(open_trades)
        if available_slots > 0 and wallet >= 10.0:
            stake_per_trade = wallet / (len(open_trades) + available_slots)
            open_pairs = {t.pair for t in open_trades}

            for pair, df in datasets.items():
                if pair in open_pairs or available_slots <= 0:
                    continue
                if current_time not in df_by_pair[pair].index:
                    continue

                candle = df_by_pair[pair].loc[current_time]
                if candle.get('enter_long', 0) == 1:
                    entry_rate = candle['close']
                    new_trade = MockTrade(
                        pair=pair,
                        open_rate=entry_rate,
                        open_date=current_time,
                        stake_amount=stake_per_trade
                    )
                    open_trades.append(new_trade)
                    wallet -= stake_per_trade
                    available_slots -= 1

        # Registrar equity
        floating_equity = sum([
            t.stake_amount * (1.0 + (df_by_pair[t.pair].loc[current_time]['close'] - t.open_rate) / t.open_rate)
            if current_time in df_by_pair[t.pair].index else t.stake_amount
            for t in open_trades
        ])
        total_equity = wallet + floating_equity
        equity_curve.append({"date": current_time, "equity": total_equity})

    # Liquidar trades abiertos al final
    for trade in open_trades:
        last_candle = df_by_pair[trade.pair].iloc[-1]
        trade.close_rate = last_candle['close']
        trade.close_date = df_by_pair[trade.pair].index[-1]
        trade.exit_reason = "end_of_dataset"
        gross_pnl = (trade.close_rate - trade.open_rate) / trade.open_rate
        net_pnl = gross_pnl - (fee_rate * 2.0)
        pnl_usdt = trade.stake_amount * net_pnl
        wallet += trade.stake_amount + pnl_usdt
        closed_trades.append(trade)

    # 3. Métricas Estadísticas
    pnls = [
        ((t.close_rate - t.open_rate) / t.open_rate) - (fee_rate * 2.0)
        for t in closed_trades
    ]
    pnl_series = pd.Series(pnls)

    total_trades = len(closed_trades)
    winning_trades = sum(1 for p in pnls if p > 0)
    losing_trades = sum(1 for p in pnls if p <= 0)
    win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    final_equity = wallet
    total_net_return_pct = ((final_equity - initial_wallet) / initial_wallet) * 100.0

    eq_df = pd.DataFrame(equity_curve)
    eq_df['peak'] = eq_df['equity'].cummax()
    eq_df['drawdown'] = (eq_df['peak'] - eq_df['equity']) / eq_df['peak']
    max_drawdown_pct = eq_df['drawdown'].max() * 100.0

    # Desglose por motivo de salida
    reasons = {}
    for t in closed_trades:
        r = t.exit_reason
        reasons[r] = reasons.get(r, 0) + 1

    # Sharpe y Sortino
    if len(pnl_series) > 1 and pnl_series.std() > 0:
        trades_per_year = total_trades / (len(all_timestamps) / (24 * 365.25))
        sharpe = (pnl_series.mean() / pnl_series.std()) * np.sqrt(trades_per_year)
        downside = pnl_series[pnl_series < 0]
        sortino = (pnl_series.mean() / downside.std()) * np.sqrt(trades_per_year) if len(downside) > 1 and downside.std() > 0 else sharpe
    else:
        sharpe, sortino = 0.0, 0.0

    return {
        "initial_wallet": initial_wallet,
        "final_equity": round(final_equity, 2),
        "total_net_return_pct": round(total_net_return_pct, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "exit_reasons": reasons,
        "start_date": str(all_timestamps[0]),
        "end_date": str(all_timestamps[-1]),
        "days_tested": round(len(all_timestamps) / 24.0, 1)
    }


if __name__ == "__main__":
    print("Iniciando Backtesting de MemeHunterSpot_CapitulationAlpha...")
    results = run_spot_backtest()
    print("\n" + "="*60)
    print(" RESULTADOS OFICIALES DE BACKTESTING - BINANCE SPOT ")
    print("="*60)
    for k, v in results.items():
        if k != "exit_reasons":
            print(f" {k:<25}: {v}")
    print("\nDesglose de Salidas por Motivo:")
    for r, count in results["exit_reasons"].items():
        print(f" - {r:<35}: {count} trades ({round(count/results['total_trades']*100, 1)}%)")
    print("="*60)
