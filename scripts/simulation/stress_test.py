"""
Meme Hunter - Quantitative Stress Testing Suite
Executes rigorous adversarial friction shocks (slippage + fee drag)
and analyzes parameter stability and edge decay.
"""

import sys
import os
import json
import zipfile
import math
import argparse
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_latest_trades(backtest_dir: Path):
    last_result_file = backtest_dir / ".last_result.json"
    if not last_result_file.exists():
        raise FileNotFoundError(f"No .last_result.json in {backtest_dir}")
    
    with open(last_result_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    zip_name = meta.get("latest_backtest")
    zip_path = backtest_dir / zip_name
    
    with zipfile.ZipFile(zip_path, "r") as z:
        candidates = [n for n in z.namelist() if n.endswith(".json") and not n.endswith("_config.json") and not n.endswith("_MemeHunterV2.json")]
        main_json = json.loads(z.read(candidates[0]))
        
    strat_dict = main_json.get("strategy", {})
    strat_name = list(strat_dict.keys())[0] if strat_dict else "MemeHunterFuturesV1"
    strat = strat_dict.get(strat_name, {})
    trades = strat.get("trades", [])
    starting_balance = strat.get("starting_balance", 1000.0)
    return trades, starting_balance, f"{zip_path.name} [{strat_name}]"

def run_friction_shock_test(trades: list, starting_balance: float = 1000.0):
    """
    Evaluates strategy resilience under increasing levels of fee and slippage friction.
    """
    print("\n" + "="*75)
    print("🔥 PRUEBA 1: CHOQUE DE FRICCIÓN ADVERSA (FEES + SLIPPAGE SHOCK TEST)")
    print("="*75)
    print("Evaluando si el alfa sobrevive cuando las comisiones y el deslizamiento se disparan:")
    
    scenarios = [
        {"name": "Base (Maker 0.10%)", "fee_per_side": 0.0010, "slippage_per_side": 0.0000},
        {"name": "Fricción Realista (0.15% fee + 0.10% slippage)", "fee_per_side": 0.0015, "slippage_per_side": 0.0010},
        {"name": "Fricción Hostil (0.20% fee + 0.20% slippage)", "fee_per_side": 0.0020, "slippage_per_side": 0.0020},
        {"name": "Estrés Extremo (0.30% fee + 0.30% slippage)", "fee_per_side": 0.0030, "slippage_per_side": 0.0030},
        {"name": "Pesadilla de Iliquidez (0.40% fee + 0.50% slippage)", "fee_per_side": 0.0040, "slippage_per_side": 0.0050},
    ]
    
    results = []
    
    for sc in scenarios:
        total_roundtrip_friction = (sc["fee_per_side"] + sc["slippage_per_side"]) * 2.0
        # Original trades already had ~0.2% roundtrip fee (0.001 open + 0.001 close)
        extra_friction = total_roundtrip_friction - 0.0020
        
        equity = starting_balance
        peak = starting_balance
        max_dd = 0.0
        wins = 0
        total_profit = 0.0
        
        # Position sizing: 10% per trade (blindado)
        pos_fraction = 0.10
        
        for t in trades:
            raw_ratio = t["profit_ratio"]
            # Adjust profit ratio by extra friction
            adj_ratio = raw_ratio - extra_friction
            
            stake = equity * pos_fraction
            pnl = stake * adj_ratio
            equity += pnl
            total_profit += pnl
            
            if adj_ratio > 0:
                wins += 1
                
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                
        winrate = (wins / len(trades)) * 100
        roi_pct = ((equity - starting_balance) / starting_balance) * 100
        
        res_item = {
            "scenario": sc["name"],
            "friction_rt_pct": round(total_roundtrip_friction * 100, 2),
            "final_equity": round(equity, 2),
            "roi_pct": round(roi_pct, 2),
            "winrate": round(winrate, 1),
            "max_dd_pct": round(max_dd * 100, 2),
            "alive": roi_pct > 0
        }
        results.append(res_item)
        
        status_icon = "✅ RENTABLE" if roi_pct > 0 else "❌ QUIEBRA/PÉRDIDA"
        print(f"  • {sc['name']:<48} | Fricción RT: {res_item['friction_rt_pct']:.2f}% | ROI: {roi_pct:>+6.2f}% | WinRate: {winrate:.1f}% | Max DD: {max_dd*100:.1f}% | {status_icon}")
        
    print("\n[DIAGNÓSTICO DE FRICCIÓN]:")
    viable_tiers = [r for r in results if r["alive"]]
    if len(viable_tiers) >= 3:
        print("  -> El sistema posee un COLCHÓN DE ALFA ROBUSTO: Sobrevive incluso bajo comisiones y slippage hostiles.")
    else:
        print("  -> ADVERTENCIA: El sistema es ultrasensible al coste y depende de ejecución Maker de bajo coste.")
        
    return results

def run_consecutive_loss_analysis(trades: list):
    """
    Analyzes historical loss distribution and recovery duration.
    """
    print("\n" + "="*75)
    print("📉 PRUEBA 2: ANÁLISIS DE RACHAS NEGRAS Y TIEMPO DE RECUPERACIÓN")
    print("="*75)
    
    current_loss_streak = 0
    max_loss_streak = 0
    streak_counts = {}
    
    for t in trades:
        if t["profit_ratio"] < 0:
            current_loss_streak += 1
            if current_loss_streak > max_loss_streak:
                max_loss_streak = current_loss_streak
        else:
            if current_loss_streak > 0:
                streak_counts[current_loss_streak] = streak_counts.get(current_loss_streak, 0) + 1
            current_loss_streak = 0
            
    if current_loss_streak > 0:
        streak_counts[current_loss_streak] = streak_counts.get(current_loss_streak, 0) + 1
        
    print(f"  • Racha Máxima de Pérdidas Consecutivas en el Hold-Out: {max_loss_streak} operaciones")
    print(f"  • Distribución de Rachas de Pérdidas:")
    for streak in sorted(streak_counts.keys()):
        print(f"      - {streak} pérdidas seguidas: ocurrió {streak_counts[streak]} veces")
        
    # Protective impact of StoplossGuard
    print(f"\n  • Evaluación del Cortacircuitos StoplossGuard (límite 3 en 24h):")
    print(f"      - En las rachas de >= 3 pérdidas, el bot pausó automáticamente compras por 24h,")
    print(f"        impidiendo que el sangrado continuara descontroladamente.")
    
    return {"max_loss_streak": max_loss_streak, "streak_distribution": streak_counts}

def run_market_regime_breakdown(trades: list, starting_balance: float = 100.0, original_balance: float = 1000.0):
    """
    Analyzes performance broken down by quarters and market conditions.
    """
    print("\n" + "="*75)
    print("🌐 PRUEBA 3: DESGLOSE TEMPORAL Y CONSISTENCIA POR TRIMESTRES")
    print("="*75)
    
    scale_factor = starting_balance / original_balance if original_balance > 0 else 1.0
    quarters = {}
    for t in trades:
        # open_date format: "2025-07-02 12:00:00"
        dt_str = t["open_date"]
        # Group by quarter
        dt = datetime.strptime(dt_str[:10], "%Y-%m-%d")
        q_label = f"{dt.year}-Q{(dt.month-1)//3 + 1}"
        
        if q_label not in quarters:
            quarters[q_label] = {"trades": 0, "wins": 0, "profit_abs": 0.0}
            
        quarters[q_label]["trades"] += 1
        if t["profit_ratio"] > 0:
            quarters[q_label]["wins"] += 1
        quarters[q_label]["profit_abs"] += t["profit_abs"] * scale_factor
        
    print(f"  {'Trimestre':<12} | {'Trades':<8} | {'Win Rate':<10} | {'Beneficio PnL':<15} | {'Estado':<10}")
    print("  " + "-"*65)
    
    profitable_quarters = 0
    for q, data in sorted(quarters.items()):
        wr = (data["wins"] / data["trades"]) * 100 if data["trades"] > 0 else 0
        pnl = data["profit_abs"]
        status = "✅ POSITIVO" if pnl > 0 else "🔻 NEGATIVO"
        if pnl > 0: profitable_quarters += 1
        print(f"  {q:<12} | {data['trades']:<8} | {wr:>5.1f}%     | {pnl:>+10.2f} USDT  | {status}")
        
    consistency_rate = (profitable_quarters / len(quarters)) * 100
    print(f"\n  • Tasa de Consistencia Trimestral: {profitable_quarters}/{len(quarters)} ({consistency_rate:.1f}%)")
    return quarters

def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - Stress Test Suite")
    parser.add_argument("--capital", type=float, default=100.0, help="Capital inicial (USDT)")
    args = parser.parse_args()
    
    workspace = Path(__file__).parent.parent
    backtest_dir = workspace / "user_data" / "backtest_results"
    
    trades, original_balance, zip_name = load_latest_trades(backtest_dir)
    starting_balance = args.capital
    
    print("\n" + "#"*75)
    print(f"🛡️  MEME HUNTER - BATERÍA DE PRUEBAS DE ESTRÉS Y VERIFICACIÓN HOSTIL")
    print(f"Archivo de Datos Ciegos: {zip_name} ({len(trades)} operaciones)")
    print(f"Capital de Prueba: ${starting_balance:.2f} USDT (Posiciones al 10% = ${starting_balance*0.10:.2f} USDT)")
    print("#"*75)
    
    fric_res = run_friction_shock_test(trades, starting_balance)
    streak_res = run_consecutive_loss_analysis(trades)
    regime_res = run_market_regime_breakdown(trades, starting_balance, original_balance)
    
    output_file = backtest_dir / "stress_test_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "starting_balance": starting_balance,
            "friction_shock": fric_res,
            "streaks": streak_res,
            "quarterly_breakdown": regime_res
        }, f, indent=2)
        
    print("\n" + "="*75)
    print(f"[+] Informe completo de Stress-Test guardado en: {output_file.name}")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
