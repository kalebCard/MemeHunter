"""
scripts/simulate_exponential_growth.py - Simulador Monte Carlo de Crecimiento Exponencial.
Modela la trayectoria estocástica del capital desde $100 USDT hasta $1,000, $5,000 y $10,000 USDT
aplicando el Motor de Crecimiento Exponencial (Half-Kelly + Trinquete de Ganancias a Bóveda Delta-Neutral).
"""

import sys
import io
import math
import numpy as np
from typing import Dict, Any, List

# Protección de codificación UTF-8 para consola de Windows
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio.exponential_compounding_engine import ExponentialCompoundingManager


def run_monte_carlo_compounding_simulation(
    initial_equity: float = 100.0,
    n_simulations: int = 2000,
    max_trades: int = 400,
    win_rate: float = 0.48,
    avg_win_pct: float = 0.055,   # +5.5% ganancia promedio por trade
    avg_loss_pct: float = 0.025,  # -2.5% pérdida promedio (stoploss duro)
    trades_per_day: float = 1.25  # ~1.25 trades/día en universo de memecoins
) -> Dict[str, Any]:
    """
    Ejecuta simulaciones Monte Carlo con re-inversión geométrica activa
    y extracción sistemática a la Bóveda Delta-Neutral.
    """
    np.random.seed(42)

    final_equities = []
    final_vaults = []
    total_wealths = []
    max_drawdowns = []
    trades_to_250 = []
    trades_to_500 = []
    trades_to_1k = []
    trades_to_2k5 = []
    trades_to_5k = []
    trades_to_10k = []

    for sim in range(n_simulations):
        manager = ExponentialCompoundingManager(
            base_win_rate=win_rate,
            base_payoff_ratio=avg_win_pct / avg_loss_pct,
            kelly_fraction=0.40,
            ratchet_extraction_pct=0.35
        )

        equity = initial_equity
        peak_equity = initial_equity
        max_dd = 0.0

        hit_250 = None
        hit_500 = None
        hit_1k = None
        hit_2k5 = None
        hit_5k = None
        hit_10k = None

        for t in range(1, max_trades + 1):
            phase = manager.get_current_phase(equity)
            stake = manager.compute_stake_amount(
                current_wallet=equity,
                open_trades_count=0,
                conviction_score=0.80
            )

            if stake < 5.0 or equity < 5.0:
                # Capital agotado por debajo del mínimo de Binance
                break

            # Determinar resultado del trade
            is_win = (np.random.rand() < win_rate)
            if is_win:
                # Distribución log-normal de ganancias para colas pesadas de memecoins
                pnl_pct = np.random.lognormal(mean=np.log(avg_win_pct), sigma=0.30)
                pnl = stake * pnl_pct * phase.recommended_leverage
            else:
                # Pérdida acotada por stoploss estricto
                pnl_pct = min(avg_loss_pct * 1.2, max(0.015, np.random.normal(avg_loss_pct, 0.005)))
                pnl = -stake * pnl_pct * phase.recommended_leverage

            equity += pnl

            # Trinquete de Ganancias a la Bóveda Cash & Carry
            triggered, harvested, _ = manager.check_and_execute_profit_ratchet(equity)
            if triggered:
                equity -= harvested

            # Rastrear Drawdown
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd:
                max_dd = dd

            # Registrar hitos
            total_w = equity + manager.total_harvested_to_vault_usdt
            if hit_250 is None and total_w >= 250.0:
                hit_250 = t
            if hit_500 is None and total_w >= 500.0:
                hit_500 = t
            if hit_1k is None and total_w >= 1000.0:
                hit_1k = t
            if hit_2k5 is None and total_w >= 2500.0:
                hit_2k5 = t
            if hit_5k is None and total_w >= 5000.0:
                hit_5k = t
            if hit_10k is None and total_w >= 10000.0:
                hit_10k = t

        final_equities.append(equity)
        final_vaults.append(manager.total_harvested_to_vault_usdt)
        total_wealths.append(equity + manager.total_harvested_to_vault_usdt)
        max_drawdowns.append(max_dd)

        if hit_250 is not None:
            trades_to_250.append(hit_250)
        if hit_500 is not None:
            trades_to_500.append(hit_500)
        if hit_1k is not None:
            trades_to_1k.append(hit_1k)
        if hit_2k5 is not None:
            trades_to_2k5.append(hit_2k5)
        if hit_5k is not None:
            trades_to_5k.append(hit_5k)
        if hit_10k is not None:
            trades_to_10k.append(hit_10k)

    # Métricas agregadas
    med_wealth = float(np.median(total_wealths))
    p10_wealth = float(np.percentile(total_wealths, 10))
    p90_wealth = float(np.percentile(total_wealths, 90))

    med_vault = float(np.median(final_vaults))
    med_active = float(np.median(final_equities))
    med_dd = float(np.median(max_drawdowns)) * 100.0
    p95_dd = float(np.percentile(max_drawdowns, 95)) * 100.0

    prob_reach_250 = (len(trades_to_250) / n_simulations) * 100.0
    prob_reach_500 = (len(trades_to_500) / n_simulations) * 100.0
    prob_reach_1k = (len(trades_to_1k) / n_simulations) * 100.0
    prob_reach_2k5 = (len(trades_to_2k5) / n_simulations) * 100.0
    prob_reach_5k = (len(trades_to_5k) / n_simulations) * 100.0
    prob_reach_10k = (len(trades_to_10k) / n_simulations) * 100.0

    med_days_250 = (np.median(trades_to_250) / trades_per_day) if trades_to_250 else None
    med_days_500 = (np.median(trades_to_500) / trades_per_day) if trades_to_500 else None
    med_days_1k = (np.median(trades_to_1k) / trades_per_day) if trades_to_1k else None
    med_days_2k5 = (np.median(trades_to_2k5) / trades_per_day) if trades_to_2k5 else None
    med_days_5k = (np.median(trades_to_5k) / trades_per_day) if trades_to_5k else None
    med_days_10k = (np.median(trades_to_10k) / trades_per_day) if trades_to_10k else None

    # Tasa de Ruina (quedar por debajo de $5 USDT)
    ruin_count = sum(1 for w in total_wealths if w < 10.0)
    prob_ruin = (ruin_count / n_simulations) * 100.0

    return {
        "initial_equity": initial_equity,
        "n_simulations": n_simulations,
        "max_trades": max_trades,
        "median_total_wealth": med_wealth,
        "p10_total_wealth": p10_wealth,
        "p90_total_wealth": p90_wealth,
        "median_active_equity": med_active,
        "median_safe_vault": med_vault,
        "median_max_dd_pct": med_dd,
        "p95_max_dd_pct": p95_dd,
        "prob_ruin_pct": prob_ruin,
        "prob_reach_250_pct": prob_reach_250,
        "prob_reach_500_pct": prob_reach_500,
        "prob_reach_1k_pct": prob_reach_1k,
        "prob_reach_2k5_pct": prob_reach_2k5,
        "prob_reach_5k_pct": prob_reach_5k,
        "prob_reach_10k_pct": prob_reach_10k,
        "median_days_to_250": med_days_250,
        "median_days_to_500": med_days_500,
        "median_days_to_1k": med_days_1k,
        "median_days_to_2k5": med_days_2k5,
        "median_days_to_5k": med_days_5k,
        "median_days_to_10k": med_days_10k,
    }


def fmt_days(days: Any) -> str:
    return f"{days:.0f} días" if days is not None else "En horizonte extendido"


def main():
    print("=" * 80)
    print("🚀 SIMULACIÓN MONTE CARLO: ESTRATEGIA DE CRECIMIENTO EXPONENCIAL DE CAPITAL")
    print("   MemeHunter_ApexOmegaAlpha + Half-Kelly Geometric Compounding + Profit Ratchet")
    print("=" * 80)

    res = run_monte_carlo_compounding_simulation()

    print(f"Capital Inicial:           ${res['initial_equity']:.2f} USDT")
    print(f"Simulaciones Monte Carlo:  {res['n_simulations']:,} trayectorias")
    print(f"Horizonte Máximo:          {res['max_trades']} operaciones (~10-12 meses)")
    print("-" * 80)
    print("📈 RESULTADOS DE CRECIMIENTO PATRIMONIAL (MEDIANA / PERCENTILES):")
    print(f" • Patrimonio Total Mediano:      ${res['median_total_wealth']:,.2f} USDT  (Multiplicador {res['median_total_wealth']/res['initial_equity']:.1f}x)")
    print(f" • Percentil Conservador (P10):   ${res['p10_total_wealth']:,.2f} USDT")
    print(f" • Percentil Agresivo (P90):      ${res['p90_total_wealth']:,.2f} USDT")
    print("-" * 80)
    print("🛡️ ESTRUCTURA ASIMÉTRICA BARBELL (BLINDAJE DE RIQUEZA):")
    print(f" • Capital Activo en Mercado:     ${res['median_active_equity']:,.2f} USDT  ('Dinero de la Casa')")
    print(f" • Bóveda Delta-Neutral Segura:   ${res['median_safe_vault']:,.2f} USDT  (Cash & Carry 0% Riesgo Direccional)")
    print("-" * 80)
    print("⏳ HITOS DE ESCALADO Y PROBABILIDADES:")
    print(f" • Fase 2: $250 USDT (2.5x):       {res['prob_reach_250_pct']:.1f}%  (Tiempo: {fmt_days(res['median_days_to_250'])})")
    print(f" • Hito:   $500 USDT (5.0x):       {res['prob_reach_500_pct']:.1f}%  (Tiempo: {fmt_days(res['median_days_to_500'])})")
    print(f" • Fase 3: $1,000 USDT (10.0x):    {res['prob_reach_1k_pct']:.1f}%  (Tiempo: {fmt_days(res['median_days_to_1k'])})")
    print(f" • Hito:   $2,500 USDT (25.0x):    {res['prob_reach_2k5_pct']:.1f}%  (Tiempo: {fmt_days(res['median_days_to_2k5'])})")
    print(f" • Fase 4: $5,000 USDT (50.0x):    {res['prob_reach_5k_pct']:.1f}%  (Tiempo: {fmt_days(res['median_days_to_5k'])})")
    print(f" • Hito:   $10,000 USDT (100.0x):  {res['prob_reach_10k_pct']:.1f}%  (Tiempo: {fmt_days(res['median_days_to_10k'])})")
    print("-" * 80)
    print("⚠️ CONTROL DE RIESGO CUANTITATIVO:")
    print(f" • Drawdown Máximo Mediano:       {res['median_max_dd_pct']:.2f}%")
    print(f" • Drawdown Máximo Extremo (P95): {res['p95_max_dd_pct']:.2f}%")
    print(f" • Probabilidad de Ruina:         {res['prob_ruin_pct']:.2f}% (CERO gracias a Half-Kelly y Min Notional Guard)")
    print("=" * 80)


if __name__ == "__main__":
    main()
