"""
fat_tail_montecarlo.py - Simulación Monte Carlo No-IID con Bloques, Regímenes y Mechas Hostiles (PB-65).

Diferencias críticas frente al bootstrap tradicional:
1. Block Bootstrap (Moving Block Bootstrap): preserva la autocorrelación, rachas consecutivas y clustering de volatilidad.
2. Inyección de Stress Shock / Mechas de Short Squeeze: simula mechas intra-vela de +40% a +80% en memecoins delgadas.
3. Micro-Capital de 100 USDT con apalancamiento: audita la probabilidad real de liquidación o activación del Kill-Switch (25% DD).
"""

import sys
import json
import zipfile
import random
from pathlib import Path
import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BACKTEST_DIR = Path("user_data/backtest_results")


def load_trades_from_zip(zip_path: Path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            if name.endswith('.json') and not name.endswith('.meta.json'):
                data = json.loads(z.read(name).decode('utf-8'))
                if "strategy" in data:
                    for strat, strat_data in data["strategy"].items():
                        return strat, strat_data.get("trades", [])
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict) and "trades" in v:
                            return k, v["trades"]
    return None, []


def block_bootstrap_simulation(
    trades: list,
    starting_balance: float = 100.0,
    max_open_trades: int = 4,
    leverage: float = 1.5,
    block_size: int = 10,
    num_simulations: int = 5000,
    shock_prob_per_trade: float = 0.015,  # 1.5% de probabilidad de sufrir squeeze hostil
    shock_loss_pct: float = -0.35         # Pérdida de -35% en equity por squeeze forzado
):
    df = pd.DataFrame(trades)
    df['open_timestamp'] = pd.to_datetime(df['open_timestamp'], unit='ms', utc=True)
    df = df.sort_values('open_timestamp').reset_index(drop=True)

    profit_ratios = df['profit_ratio'].values
    n = len(profit_ratios)

    if n < block_size * 2:
        block_size = max(2, n // 10)

    num_blocks = int(np.ceil(n / block_size))

    # Métricas a recopilar
    final_equities = []
    max_drawdowns = []
    ruin_hits_50pct = 0
    kill_switch_hits_25pct = 0
    liquidation_hits = 0

    np.random.seed(42)
    random.seed(42)

    for sim_idx in range(num_simulations):
        # 1. Generar camino con Block Bootstrap
        sampled_sequence = []
        for _ in range(num_blocks):
            start_idx = np.random.randint(0, n - block_size + 1)
            block = profit_ratios[start_idx : start_idx + block_size]
            sampled_sequence.extend(block)
        sampled_sequence = sampled_sequence[:n]

        # 2. Simular evolución de cuenta con reinversión Anti-Freeze y Shocks
        equity = starting_balance
        peak = starting_balance
        max_dd = 0.0
        killed = False

        for r in sampled_sequence:
            # Tamaño por posición: micro-capital 4 slots
            stake = equity / max_open_trades

            # ¿Shock de short squeeze adverso?
            if np.random.rand() < shock_prob_per_trade:
                trade_pnl = stake * shock_loss_pct * leverage
            else:
                trade_pnl = stake * r * leverage

            equity += trade_pnl

            if equity > peak:
                peak = equity

            current_dd = (peak - equity) / peak if peak > 0 else 1.0
            if current_dd > max_dd:
                max_dd = current_dd

            if current_dd >= 0.25 and not killed:
                kill_switch_hits_25pct += 1
                killed = True

            if equity <= (starting_balance * 0.50):
                ruin_hits_50pct += 1
                break

            if equity <= 5.0:  # Cuenta pulverizada por debajo del notional mínimo
                liquidation_hits += 1
                break

        final_equities.append(max(0.0, equity))
        max_drawdowns.append(max_dd)

    final_equities = np.array(final_equities)
    max_drawdowns = np.array(max_drawdowns)

    var_95_dd = np.percentile(max_drawdowns, 95)
    var_99_dd = np.percentile(max_drawdowns, 99)
    median_final = np.median(final_equities)
    p5_final = np.percentile(final_equities, 5)
    p95_final = np.percentile(final_equities, 95)

    prob_kill_switch = (kill_switch_hits_25pct / num_simulations) * 100.0
    prob_ruin_50 = (ruin_hits_50pct / num_simulations) * 100.0
    prob_liquidation = (liquidation_hits / num_simulations) * 100.0

    print("=" * 75)
    print(f"[MONTE CARLO NO-IID: BLOCK BOOTSTRAP CON MECHAS DE SHOCK] (PB-65)")
    print("=" * 75)
    print(f"Configuracion: Capital Inicial: {starting_balance:.2f} USDT | Slots: {max_open_trades} | Leverage: {leverage}x")
    print(f"Muestra Base: {n} trades | Tamano de Bloque: {block_size} trades | Simulaciones: {num_simulations}")
    print(f"Riesgo de Mecha Adversa: 1.5% prob/trade con impacto -35% en slot")
    print("-" * 75)
    print("DISTRIBUCION DE CAPITAL FINAL:")
    print(f"  * Mediana (P50):                 {median_final:.2f} USDT (+{(median_final - starting_balance)/starting_balance*100:.1f}%)")
    print(f"  * Peor 5% (P5 - Escenario Hostil): {p5_final:.2f} USDT ({(p5_final - starting_balance)/starting_balance*100:.1f}%)")
    print(f"  * Mejor 5% (P95 - Rally Favorable): {p95_final:.2f} USDT (+{(p95_final - starting_balance)/starting_balance*100:.1f}%)")
    print("-" * 75)
    print("RIESGO DE COLA GORDA (DRAWDOWN & RUINA REAL):")
    print(f"  * Max Drawdown Promedio:         {np.mean(max_drawdowns)*100:.2f}%")
    print(f"  * VaR 95% Max Drawdown:          {var_95_dd*100:.2f}%")
    print(f"  * VaR 99% Max Drawdown:          {var_99_dd*100:.2f}%")
    print(f"  * Probabilidad de activar Kill-Switch (DD >= 25%): {prob_kill_switch:.2f}%")
    print(f"  * Probabilidad de Perdida Grave (Capital <= 50 USDT): {prob_ruin_50:.2f}%")
    print(f"  * Probabilidad de Liquidacion / Quiebra Total (< 5 USDT): {prob_liquidation:.2f}%")
    print("-" * 75)
    
    if prob_liquidation > 0.0 or prob_ruin_50 > 5.0:
        print("[DICTAMEN FORENSE]: Se desmiente el 0.0% de ruina. En condiciones reales no-IID")
        print("                  existe riesgo medible de liquidacion si no se respeta el Kill-Switch.")
    else:
        print("[DICTAMEN FORENSE]: El modelo soporta colas gordas manteniendo el riesgo de quiebra acotado.")
    print("=" * 75)


if __name__ == "__main__":
    latest_zip = BACKTEST_DIR / "backtest-result-2026-10-12_01-09-22.zip"
    strat, trades = load_trades_from_zip(latest_zip)
    block_bootstrap_simulation(trades, starting_balance=100.0, max_open_trades=4, leverage=1.5)
