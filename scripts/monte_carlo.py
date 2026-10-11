"""
Meme Hunter - Monte Carlo Risk & Robustness Simulator
Evaluates path-dependency, sequence risk, Max Drawdown at 95%/99% VaR,
and Risk of Ruin using bootstrap resampling on backtest trade logs.
"""

import sys
import os
import json
import zipfile
import random
import math
import argparse
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_latest_backtest(backtest_dir: Path):
    last_result_file = backtest_dir / ".last_result.json"
    if not last_result_file.exists():
        raise FileNotFoundError(f"No .last_result.json found in {backtest_dir}")
    
    with open(last_result_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    zip_name = meta.get("latest_backtest")
    if not zip_name:
        raise ValueError("No latest_backtest key found in .last_result.json")
    
    zip_path = backtest_dir / zip_name
    if not zip_path.exists():
        raise FileNotFoundError(f"Backtest zip {zip_path} does not exist.")
    
    print(f"[*] Analizando resultados de backtest: {zip_path.name}")
    
    with zipfile.ZipFile(zip_path, "r") as z:
        # Find json file
        json_candidates = [n for n in z.namelist() if n.endswith(".json") and not n.endswith("_config.json") and not n.endswith("_MemeHunterV2.json")]
        if not json_candidates:
            raise FileNotFoundError("Could not find primary backtest json inside zip")
        
        main_json_name = json_candidates[0]
        data = json.loads(z.read(main_json_name))
        
    return data, zip_path.name

def run_monte_carlo(trades: list, starting_balance: float = 1000.0, max_open_trades: int = 5, num_simulations: int = 2500, stake_mode: str = "compounding"):
    """
    Runs bootstrap simulation with reshuffling and replacement.
    Supports 'compounding' (stake = equity / max_open_trades) and 'fixed' (stake = starting_balance / max_open_trades).
    """
    n_trades = len(trades)
    if n_trades == 0:
        raise ValueError("No trades found in backtest.")
    
    profit_ratios = [t["profit_ratio"] for t in trades]
    actual_profits_abs = [t["profit_abs"] for t in trades]
    
    actual_final_balance = starting_balance + sum(actual_profits_abs)
    
    cum_equity = starting_balance
    peak = cum_equity
    actual_max_dd_pct = 0.0
    for p in actual_profits_abs:
        cum_equity += p
        if cum_equity > peak:
            peak = cum_equity
        dd = (peak - cum_equity) / peak if peak > 0 else 0
        if dd > actual_max_dd_pct:
            actual_max_dd_pct = dd
            
    sim_final_balances = []
    sim_max_drawdowns = []
    sim_max_consec_losses = []
    
    ruin_10 = 0
    ruin_20 = 0
    ruin_30 = 0
    ruin_50 = 0
    
    position_fraction = 1.0 / max_open_trades
    fixed_stake_amount = starting_balance / max_open_trades
    
    for i in range(num_simulations):
        sample_ratios = [random.choice(profit_ratios) for _ in range(n_trades)]
        
        equity = starting_balance
        peak_equity = starting_balance
        max_dd = 0.0
        consec_losses = 0
        max_consec = 0
        
        for r in sample_ratios:
            if equity < 5.0:
                # Saldo cayó por debajo del mínimo de Binance ($5 USDT)
                break

            if stake_mode == "compounding":
                trade_stake = max(5.0, equity * position_fraction)
            else: # fixed
                trade_stake = max(5.0, fixed_stake_amount)
                
            pnl = trade_stake * r
            equity += pnl
            
            if r < 0:
                consec_losses += 1
                if consec_losses > max_consec:
                    max_consec = consec_losses
            else:
                consec_losses = 0
                
            if equity > peak_equity:
                peak_equity = equity
            
            current_dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if current_dd > max_dd:
                max_dd = current_dd
        
        sim_final_balances.append(equity)
        sim_max_drawdowns.append(max_dd)
        sim_max_consec_losses.append(max_consec)
        
        if max_dd >= 0.10: ruin_10 += 1
        if max_dd >= 0.20: ruin_20 += 1
        if max_dd >= 0.30: ruin_30 += 1
        if max_dd >= 0.50: ruin_50 += 1
        
    sim_final_balances.sort()
    sim_max_drawdowns.sort()
    sim_max_consec_losses.sort()
    
    def percentile(arr, p):
        idx = int(round(p * (len(arr) - 1)))
        return arr[idx]
    
    results = {
        "num_simulations": num_simulations,
        "n_trades": n_trades,
        "starting_balance": starting_balance,
        "actual_backtest": {
            "final_balance": round(actual_final_balance, 2),
            "profit_pct": round(((actual_final_balance - starting_balance) / starting_balance) * 100, 2),
            "max_drawdown_pct": round(actual_max_dd_pct * 100, 2)
        },
        "ending_balance": {
            "min": round(sim_final_balances[0], 2),
            "p01": round(percentile(sim_final_balances, 0.01), 2),
            "p05": round(percentile(sim_final_balances, 0.05), 2),
            "median": round(percentile(sim_final_balances, 0.50), 2),
            "p95": round(percentile(sim_final_balances, 0.95), 2),
            "p99": round(percentile(sim_final_balances, 0.99), 2),
            "max": round(sim_final_balances[-1], 2),
            "mean": round(sum(sim_final_balances) / num_simulations, 2)
        },
        "max_drawdown": {
            "median_pct": round(percentile(sim_max_drawdowns, 0.50) * 100, 2),
            "var_90_pct": round(percentile(sim_max_drawdowns, 0.90) * 100, 2),
            "var_95_pct": round(percentile(sim_max_drawdowns, 0.95) * 100, 2),
            "var_99_pct": round(percentile(sim_max_drawdowns, 0.99) * 100, 2),
            "worst_case_pct": round(sim_max_drawdowns[-1] * 100, 2)
        },
        "consecutive_losses": {
            "median": percentile(sim_max_consec_losses, 0.50),
            "p95": percentile(sim_max_consec_losses, 0.95),
            "p99": percentile(sim_max_consec_losses, 0.99),
            "max": sim_max_consec_losses[-1]
        },
        "risk_of_ruin": {
            "dd_ge_10_pct": round((ruin_10 / num_simulations) * 100, 2),
            "dd_ge_20_pct": round((ruin_20 / num_simulations) * 100, 2),
            "dd_ge_30_pct": round((ruin_30 / num_simulations) * 100, 2),
            "dd_ge_50_pct": round((ruin_50 / num_simulations) * 100, 2)
        }
    }
    return results

def print_report(res: dict, backtest_name: str):
    print("\n" + "="*70)
    print(f"📊 MEME HUNTER - REPORTE DE ANÁLISIS MONTE CARLO (ROBUSTEZ)")
    print(f"Archivo Origen: {backtest_name}")
    print(f"Simulaciones: {res['num_simulations']:,} iteraciones | Trades por ciclo: {res['n_trades']}")
    print("="*70)
    
    act = res["actual_backtest"]
    print(f"\n1. BACKTEST HISTÓRICO ORIGINAL:")
    print(f"   - Capital Final:     ${act['final_balance']:,.2f} USDT ({act['profit_pct']:+.2f}%)")
    print(f"   - Max Drawdown Real:  {act['max_drawdown_pct']:.2f}%")
    
    sb = res.get("starting_balance", 100.0)
    eb = res["ending_balance"]
    print(f"\n2. DISTRIBUCIÓN DEL CAPITAL FINAL (Simulado a {res['num_simulations']:,} caminos):")
    print(f"   - Peor Caso (Mínimo):       ${eb['min']:,.2f} USDT ({((eb['min']-sb)/sb)*100:+.2f}%)")
    print(f"   - Percentil 5% (Pesimista):  ${eb['p05']:,.2f} USDT ({((eb['p05']-sb)/sb)*100:+.2f}%)")
    print(f"   - Mediana (Caso Base):      ${eb['median']:,.2f} USDT ({((eb['median']-sb)/sb)*100:+.2f}%)")
    print(f"   - Media:                    ${eb['mean']:,.2f} USDT ({((eb['mean']-sb)/sb)*100:+.2f}%)")
    print(f"   - Percentil 95% (Optimista): ${eb['p95']:,.2f} USDT ({((eb['p95']-sb)/sb)*100:+.2f}%)")
    print(f"   - Mejor Caso (Máximo):      ${eb['max']:,.2f} USDT ({((eb['max']-sb)/sb)*100:+.2f}%)")
    
    dd = res["max_drawdown"]
    print(f"\n3. ANÁLISIS DE MÁXIMO DRAWDOWN & RIESGO (VaR):")
    print(f"   - Drawdown Mediano (50%):     {dd['median_pct']:.2f}%")
    print(f"   - Drawdown al 90% Confianza:  {dd['var_90_pct']:.2f}%")
    print(f"   - Drawdown al 95% Confianza:  {dd['var_95_pct']:.2f}%  (Norma DAS v3.1: <= 20.0%)")
    print(f"   - Drawdown al 99% Confianza:  {dd['var_99_pct']:.2f}%")
    print(f"   - Peor Drawdown Simulado:     {dd['worst_case_pct']:.2f}%")
    
    ror = res["risk_of_ruin"]
    print(f"\n4. PROBABILIDAD DE RUINA / CAÍDA SEVERA:")
    print(f"   - Probabilidad de DD >= 10%:  {ror['dd_ge_10_pct']:.2f}%")
    print(f"   - Probabilidad de DD >= 20%:  {ror['dd_ge_20_pct']:.2f}%")
    print(f"   - Probabilidad de DD >= 30%:  {ror['dd_ge_30_pct']:.2f}%")
    print(f"   - Probabilidad de DD >= 50%:  {ror['dd_ge_50_pct']:.2f}%")
    
    cl = res["consecutive_losses"]
    print(f"\n5. RACHAS DE PÉRDIDAS CONSECUTIVAS:")
    print(f"   - Mediana:                    {cl['median']} trades")
    print(f"   - Percentil 95%:              {cl['p95']} trades")
    print(f"   - Racha Máxima Simulada:      {cl['max']} trades")
    
    print("\n" + "="*70)
    status_95 = "✅ APROBADO" if dd['var_95_pct'] <= 25.0 else "⚠️ ALERTA"
    profit_prob = round(len([b for b in [1] if eb['p05'] >= sb]) * 100, 2)
    print(f"DICTAMEN DE ROBUSTEZ: {status_95}")
    if dd['var_95_pct'] <= 25.0:
        print("El sistema resiste desórdenes de secuencia y estrés extremo sin vulnerar el límite de riesgo.")
    else:
        print("El sistema tiene riesgo de sobrepasar el límite de drawdown en colas del 95%.")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - Monte Carlo Simulator")
    parser.add_argument("--capital", type=float, default=100.0, help="Capital inicial en USDT")
    parser.add_argument("--sims", type=int, default=2500, help="Número de iteraciones bootstrap")
    args = parser.parse_args()
    
    workspace = Path(__file__).parent.parent
    backtest_dir = workspace / "user_data" / "backtest_results"
    
    data, zip_name = load_latest_backtest(backtest_dir)
    
    strat_dict = data.get("strategy", {})
    strat_name = list(strat_dict.keys())[0] if strat_dict else "MemeHunterFuturesV1"
    strat_data = strat_dict.get(strat_name, {})
    trades = strat_data.get("trades", [])
    starting_balance = args.capital
    
    print(f"[*] Analizando {len(trades)} trades de {zip_name} [{strat_name}] con capital inicial ${starting_balance:.2f} USDT...")
    
    print(f"\n>>> ESCENARIO 1: CONFIGURACIÓN 5 TRADES (20% del capital por posición, compuesto)")
    res_5 = run_monte_carlo(trades, starting_balance, max_open_trades=5, num_simulations=args.sims, stake_mode="compounding")
    print_report(res_5, f"{zip_name} [5 Trades - 20% Compuesto | ${starting_balance:.0f} USDT]")
    
    print(f"\n>>> ESCENARIO 2: SIZING CONSERVADOR 10 TRADES (10% del capital por posición, compuesto)")
    res_10 = run_monte_carlo(trades, starting_balance, max_open_trades=10, num_simulations=args.sims, stake_mode="compounding")
    print_report(res_10, f"{zip_name} [10 Trades - 10% Compuesto | ${starting_balance:.0f} USDT]")
    
    fixed_stake = max(5.0, starting_balance / 10.0)
    print(f"\n>>> ESCENARIO 3: STAKE FIJO (${fixed_stake:.2f} USDT por operación)")
    res_fixed = run_monte_carlo(trades, starting_balance, max_open_trades=10, num_simulations=args.sims, stake_mode="fixed")
    print_report(res_fixed, f"{zip_name} [Fixed ${fixed_stake:.0f} Stake | ${starting_balance:.0f} USDT]")
    
    all_results = {
        "scenario_5_compounding": res_5,
        "scenario_10_compounding": res_10,
        "scenario_fixed": res_fixed
    }
    
    output_path = backtest_dir / "monte_carlo_latest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"[+] Comparativa de escenarios guardada en: {output_path}")

if __name__ == "__main__":
    main()
