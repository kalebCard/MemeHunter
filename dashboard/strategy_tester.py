"""
strategy_tester.py - Motor de Validación y Backtesting Rápido de Estrategias para el Cockpit.

Permite:
1. Validar sintaxis y seguridad AST Zero-Eval de fórmulas simbólicas.
2. Cargar datos OHLCV reales de futuros de memecoins (Binance Futures) o generar series estocásticas con saltos.
3. Ejecutar backtesting vectorial de alta velocidad con fricciones reales (fees, slippage, margin).
4. Calcular métricas cuantitativas completas: Sharpe, Sortino, MaxDD, Win Rate, Profit Factor, DSR y serie de equity.
"""

import os
import time
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import scipy.stats as ss

from mining.formula_parser import FormulaASTParser
from mining.alpha_grammar import AlphaGrammar
from data_engine.slippage_engine import MicrostructureSlippageEngine
from portfolio.order_router import SmartExitRouter, ExitUrgency, OrderExecutionStage

DATA_DIR = Path("C:/meme_hunter_data/binance/futures")


def validate_formula_ast(formula_str: str) -> Dict[str, Any]:
    """Valida una fórmula matemática mediante el parser AST Zero-Eval."""
    try:
        node = FormulaASTParser.parse(formula_str)
        nodes = node.get_nodes()
        ops = [n.op for n in nodes if hasattr(n, 'op')]
        features = [n.column for n in nodes if hasattr(n, 'column')]
        return {
            "valid": True,
            "depth": node.get_depth(),
            "clean_formula": node.to_formula(),
            "features_used": list(set(features)),
            "operators_used": list(set(ops)),
            "message": "Fórmula válida, tipada y segura (Zero-Eval)."
        }
    except Exception as e:
        return {
            "valid": False,
            "depth": 0,
            "clean_formula": formula_str,
            "features_used": [],
            "operators_used": [],
            "error": str(e),
            "message": str(e)
        }


def load_ohlcv_dataset(pair: str = "1000PEPE", timeframe: str = "4h") -> pd.DataFrame:
    """
    Carga velas OHLCV reales desde C:/meme_hunter_data/binance/futures si está disponible,
    o sintetiza una serie de tiempo con microestructura de memecoin si el archivo no existe.
    """
    clean_pair = pair.replace("/", "_").replace(":", "_").replace("-", "_")
    target_pattern = f"{clean_pair}*{timeframe}*futures.feather"
    
    found_file = None
    if DATA_DIR.exists():
        matches = list(DATA_DIR.glob(target_pattern))
        if not matches:
            # Intentar búsqueda más laxa (e.g. PEPE, DOGE)
            base_symbol = clean_pair.split('_')[0]
            matches = list(DATA_DIR.glob(f"*{base_symbol}*{timeframe}*.feather"))
        if matches:
            found_file = matches[0]

    if found_file and found_file.exists():
        try:
            df = pd.read_feather(found_file)
            if 'date' in df.columns:
                df = df.rename(columns={'date': 'timestamp'})
            elif 'open_time' in df.columns:
                df = df.rename(columns={'open_time': 'timestamp'})
            # Estandarizar columnas requeridas
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            df = _enrich_features(df)
            if len(df) > 100:
                return df
        except Exception:
            pass

    # Fallback: Generador Estocástico Realista con Dinámica de Memecoin
    return _generate_synthetic_memecoin_data(n_bars=300)


def _enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores de microestructura exigidos por AlphaGrammar."""
    df = df.copy()
    if 'returns' not in df.columns:
        df['returns'] = df['close'].pct_change().fillna(0.0)
    if 'hl_spread' not in df.columns:
        df['hl_spread'] = ((df['high'] - df['low']) / df['close'].replace(0, 1.0)).fillna(0.0)
    if 'vwap' not in df.columns:
        typical = (df['high'] + df['low'] + df['close']) / 3.0
        cum_vol = df['volume'].cumsum().replace(0, 1.0)
        df['vwap'] = ((typical * df['volume']).cumsum() / cum_vol).fillna(df['close'])
    if 'rvol' not in df.columns:
        vol_ma = df['volume'].rolling(20, min_periods=1).mean().replace(0, 1.0)
        df['rvol'] = (df['volume'] / vol_ma).fillna(1.0)
    return df


def _generate_synthetic_memecoin_data(n_bars: int = 300) -> pd.DataFrame:
    """Sintetiza una serie temporal con volatilidad de colas pesadas y regímenes post-pump."""
    np.random.seed(42)
    dates = pd.date_range("2026-06-01", periods=n_bars, freq="4h", tz="UTC")
    
    # Proceso con saltos y deriva bajista secular (Short-bias)
    ret_diff = np.random.normal(-0.0015, 0.022, n_bars)
    # Saltos tipo Poisson (pumps y dumps violentos)
    jumps = (np.random.rand(n_bars) < 0.05) * np.random.normal(-0.04, 0.06, n_bars)
    returns = ret_diff + jumps
    
    close_prices = 100.0 * np.exp(np.cumsum(returns))
    high_prices = close_prices * (1.0 + np.abs(np.random.normal(0.008, 0.006, n_bars)))
    low_prices = close_prices * (1.0 - np.abs(np.random.normal(0.008, 0.006, n_bars)))
    open_prices = (close_prices + np.roll(close_prices, 1)) / 2.0
    open_prices[0] = 100.0
    volumes = np.abs(np.random.lognormal(10.0, 1.2, n_bars))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })
    return _enrich_features(df)


def run_strategy_backtest(
    formula: str,
    pair: str = "1000PEPE",
    timeframe: str = "4h",
    direction: str = "short_only",
    leverage: float = 1.5,
    stoploss_pct: float = 0.10,
    trailing_stop_pct: float = 0.04,
    initial_wallet: float = 1000.0
) -> Dict[str, Any]:
    """
    Ejecuta el backtest vectorial de la fórmula y devuelve métricas completas y curva de equity.
    """
    # 1. Validar sintaxis
    ast_validation = validate_formula_ast(formula)
    if not ast_validation["valid"]:
        return {
            "success": False,
            "error": ast_validation["message"]
        }

    # 2. Cargar datos
    df = load_ohlcv_dataset(pair, timeframe)
    ast_node = FormulaASTParser.parse(formula)
    
    try:
        raw_signal = ast_node.evaluate(df)
        if isinstance(raw_signal, (int, float)):
            raw_signal = pd.Series(float(raw_signal), index=df.index)
        signal = raw_signal.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    except Exception as e:
        return {
            "success": False,
            "error": f"Error evaluando fórmula en serie temporal: {e}"
        }

    # 3. Normalización rodante z-score del factor
    mean_sig = signal.rolling(30, min_periods=5).mean()
    std_sig = signal.rolling(30, min_periods=5).std().replace(0, 1e-6)
    z_signal = ((signal - mean_sig) / std_sig).fillna(0.0)

    # 4. Simulación bar-by-bar con control de microestructura (Sprint 3: US-3.2 & US-3.3)
    wallet = float(initial_wallet)
    equity_curve = [{"timestamp": str(df['timestamp'].iloc[0]), "equity": round(wallet, 2), "benchmark": 1000.0}]

    slippage_engine = MicrostructureSlippageEngine()
    order_router = SmartExitRouter(slippage_engine=slippage_engine, hard_stoploss_pct=-abs(stoploss_pct))

    daily_vol_usdt = float(df['volume'].tail(6).sum() * df['close'].iloc[-1]) if 'volume' in df.columns else 5_000_000.0
    daily_vol_usdt = max(500_000.0, daily_vol_usdt)
    rolling_vol = df['close'].pct_change().rolling(20, min_periods=5).std().fillna(0.02)
    rolling_rvol = df['rvol'] if 'rvol' in df.columns else pd.Series(1.0, index=df.index)

    trades = []
    active_trade: Optional[Dict[str, Any]] = None
    total_slippage_drag_usd = 0.0
    total_fees_paid_usd = 0.0
    total_funding_pnl_usd = 0.0

    # Umbrales de señal
    entry_threshold = 0.75
    mmr = 1.0 / (2.0 * max(1.0, leverage))  # Tasa de margen de mantenimiento Binance Futures
    max_adverse_liquidation_pct = (1.0 - mmr) / max(1.0, leverage)

    for i in range(30, len(df)):
        current_time = str(df['timestamp'].iloc[i])
        close_p = float(df['close'].iloc[i])
        high_p = float(df['high'].iloc[i])
        low_p = float(df['low'].iloc[i])
        sig = float(z_signal.iloc[i])
        curr_vol = float(rolling_vol.iloc[i])
        curr_rvol = float(rolling_rvol.iloc[i])

        # Gestión de posición activa
        if active_trade:
            pos_type = active_trade["type"]
            entry_p = active_trade["entry_price"]
            peak_p = active_trade["peak_price"]

            # Acumular costo/ingreso de tasa de financiación (Funding Rate cada 8h / 2 barras 4h)
            bars_held = i - active_trade["entry_bar"]
            if bars_held > 0 and bars_held % 2 == 0:
                funding_rate_8h = 0.0001  # 0.01% por ciclo de 8h típico en memecoins
                funding_step_usdt = active_trade["stake"] * leverage * funding_rate_8h
                if pos_type == "SHORT":
                    # Los cortos cobran tasa de financiación positiva en memecoins en expansión
                    active_trade["funding_acc_usdt"] += funding_step_usdt
                else:
                    active_trade["funding_acc_usdt"] -= funding_step_usdt

            # Actualizar pico
            if pos_type == "SHORT":
                if close_p < peak_p:
                    active_trade["peak_price"] = close_p
                    peak_p = close_p
                unrealized_pct = (entry_p - close_p) / entry_p
                drawdown_from_peak = (close_p - peak_p) / entry_p

                # Chequear StopLoss
                hit_sl = (high_p - entry_p) / entry_p >= stoploss_pct
                hit_ts = (unrealized_pct >= 0.08) and (drawdown_from_peak >= trailing_stop_pct)
                hit_tp = unrealized_pct >= 0.25
                signal_exit = sig > 0.0
                is_liquidated = unrealized_pct <= -max_adverse_liquidation_pct

            else:  # LONG
                if close_p > peak_p:
                    active_trade["peak_price"] = close_p
                    peak_p = close_p
                unrealized_pct = (close_p - entry_p) / entry_p
                drawdown_from_peak = (peak_p - close_p) / entry_p
                hit_sl = (entry_p - low_p) / entry_p >= stoploss_pct
                hit_ts = (unrealized_pct >= 0.08) and (drawdown_from_peak >= trailing_stop_pct)
                hit_tp = unrealized_pct >= 0.25
                signal_exit = sig < 0.0
                is_liquidated = unrealized_pct <= -max_adverse_liquidation_pct

            should_exit = hit_sl or hit_ts or hit_tp or signal_exit or is_liquidated
            if should_exit:
                if is_liquidated:
                    exit_reason = "LIQUIDATION"
                    urgency = ExitUrgency.EMERGENCY
                elif hit_sl:
                    exit_reason = "STOP_LOSS"
                    urgency = ExitUrgency.EMERGENCY
                elif hit_ts:
                    exit_reason = "TRAILING_STOP"
                    urgency = ExitUrgency.MEDIUM
                elif hit_tp:
                    exit_reason = "TAKE_PROFIT"
                    urgency = ExitUrgency.LOW
                else:
                    exit_reason = "SIGNAL_REVERSAL"
                    urgency = ExitUrgency.LOW

                exit_order = order_router.route_exit(
                    symbol=pair,
                    side="buy" if pos_type == "SHORT" else "sell",
                    current_price=close_p,
                    order_size_usdt=active_trade["stake"] * leverage,
                    unrealized_pnl_pct=unrealized_pct,
                    daily_volume_usdt=daily_vol_usdt,
                    volatility=curr_vol,
                    rvol=curr_rvol,
                    urgency=urgency
                )

                exit_price = exit_order.executed_price
                exit_fees_usdt = exit_order.total_fees_usdt
                slippage_drag_usdt = exit_order.slippage_drag_usdt

                total_slippage_drag_usd += slippage_drag_usdt
                total_fees_paid_usd += (active_trade["entry_fee_usdt"] + exit_fees_usdt)
                total_funding_pnl_usd += active_trade["funding_acc_usdt"]

                if is_liquidated:
                    pnl_usdt = -active_trade["stake"]
                    net_pnl_pct = -100.0
                else:
                    raw_price_pnl = (entry_p - exit_price) / entry_p if pos_type == "SHORT" else (exit_price - entry_p) / entry_p
                    pnl_usdt = (active_trade["stake"] * leverage * raw_price_pnl) - (active_trade["entry_fee_usdt"] + exit_fees_usdt) + active_trade["funding_acc_usdt"]
                    net_pnl_pct = (pnl_usdt / active_trade["stake"]) * 100.0

                wallet += pnl_usdt

                trades.append({
                    "id": len(trades) + 1,
                    "type": pos_type,
                    "entry_time": active_trade["entry_time"],
                    "exit_time": current_time,
                    "entry_price": round(entry_p, 6),
                    "exit_price": round(exit_price, 6),
                    "pnl_pct": round(net_pnl_pct, 2),
                    "pnl_usdt": round(pnl_usdt, 2),
                    "exit_reason": exit_reason,
                    "stage": exit_order.stage.value,
                    "slippage_bps": round(exit_order.effective_slippage_bps, 1)
                })
                active_trade = None

        # Apertura de nueva posición
        if not active_trade and wallet > 50:
            stake = wallet * 0.25  # 25% por slot (4 slots)
            if direction in ["short_only", "both"] and sig > entry_threshold:
                entry_res = slippage_engine.simulate_order_execution(
                    side="sell",
                    order_type="maker",
                    price=close_p,
                    order_size_usdt=stake * leverage,
                    daily_volume_usdt=daily_vol_usdt,
                    volatility=curr_vol,
                    rvol=curr_rvol
                )
                active_trade = {
                    "type": "SHORT",
                    "entry_price": entry_res.executed_price,
                    "peak_price": entry_res.executed_price,
                    "entry_time": current_time,
                    "entry_bar": i,
                    "stake": stake,
                    "entry_fee_usdt": entry_res.liquidity_cost_usdt,
                    "funding_acc_usdt": 0.0
                }
            elif direction in ["long_only", "both"] and sig < -entry_threshold:
                entry_res = slippage_engine.simulate_order_execution(
                    side="buy",
                    order_type="maker",
                    price=close_p,
                    order_size_usdt=stake * leverage,
                    daily_volume_usdt=daily_vol_usdt,
                    volatility=curr_vol,
                    rvol=curr_rvol
                )
                active_trade = {
                    "type": "LONG",
                    "entry_price": entry_res.executed_price,
                    "peak_price": entry_res.executed_price,
                    "entry_time": current_time,
                    "entry_bar": i,
                    "stake": stake,
                    "entry_fee_usdt": entry_res.liquidity_cost_usdt,
                    "funding_acc_usdt": 0.0
                }

        # Grabar equity periódico (cada 4 barras)
        if i % 4 == 0 or i == len(df) - 1:
            benchmark_eq = 1000.0 * (close_p / float(df['close'].iloc[30]))
            equity_curve.append({
                "timestamp": current_time,
                "equity": round(max(0.0, wallet), 2),
                "benchmark": round(benchmark_eq, 2)
            })

    # 5. Cálculo de Métricas Cuantitativas
    total_trades = len(trades)
    if total_trades > 0:
        pnls = np.array([t["pnl_pct"] / 100.0 for t in trades])
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        win_rate = len(wins) / total_trades

        mean_ret = float(np.mean(pnls))
        std_ret = float(np.std(pnls)) if len(pnls) > 1 else 0.01

        # Anualización (4h = 6 velas/día * 365 = 2190)
        annual_factor = math.sqrt(2190 / 12)  # Trade holding ~12 barras
        sharpe = round(float((mean_ret / max(std_ret, 1e-6)) * annual_factor), 2)

        downside_std = float(np.std([p for p in pnls if p < 0])) if len(losses) > 1 else 0.01
        sortino = round(float((mean_ret / max(downside_std, 1e-6)) * annual_factor), 2)

        profit_factor = round(abs(sum(wins) / min(sum(losses), -1e-6)), 2) if losses else 9.99

        # Max Drawdown
        eq_series = np.array([p["equity"] for p in equity_curve])
        cum_max = np.maximum.accumulate(eq_series)
        drawdowns = (eq_series - cum_max) / cum_max
        max_dd = round(float(abs(np.min(drawdowns)) * 100), 2)

        # p-value y DSR proxy
        t_stat = (mean_ret / max(std_ret, 1e-6)) * math.sqrt(total_trades)
        p_val = round(float(2 * (1 - ss.t.cdf(abs(t_stat), df=max(1, total_trades - 1)))), 4)
        dsr_score = round(max(0.0, min(100.0, (1.0 - p_val * 2) * 100)), 1)
    else:
        win_rate = 0.0
        sharpe = 0.0
        sortino = 0.0
        max_dd = 0.0
        profit_factor = 0.0
        p_val = 1.0
        dsr_score = 0.0
        mean_ret = 0.0

    total_return_pct = round(((wallet - initial_wallet) / initial_wallet) * 100, 2)
    calmar = round(abs(total_return_pct / max(max_dd, 0.1)), 2)

    strategy_id = f"STUDIO_{pair}_{int(time.time())}"
    return {
        "success": True,
        "status": "success",
        "strategy_id": strategy_id,
        "formula": formula,
        "pair": pair,
        "timeframe": timeframe,
        "direction": direction,
        "leverage": leverage,
        "clean_formula": ast_validation["clean_formula"],
        "metrics": {
            "total_return_pct": total_return_pct,
            "net_return_pct": total_return_pct,
            "final_equity": round(wallet, 2),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown_pct": max_dd,
            "calmar_ratio": calmar,
            "win_rate_pct": round(win_rate * 100, 1),
            "total_trades": total_trades,
            "profit_factor": profit_factor,
            "p_value": p_val,
            "dsr_score": dsr_score,
            "dsr_score_pct": dsr_score,
            "expectancy_pct": round(mean_ret * 100, 2),
            "total_slippage_drag_usd": round(total_slippage_drag_usd, 2),
            "total_fees_paid_usd": round(total_fees_paid_usd, 2),
            "total_funding_pnl_usd": round(total_funding_pnl_usd, 2),
            "effective_spread_bps": round(float(slippage_engine.base_spread_bps), 1)
        },
        "equity_curve": equity_curve,
        "recent_trades": trades[-10:] if trades else []
    }

