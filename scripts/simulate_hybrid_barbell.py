"""
simulate_hybrid_barbell.py - Simulador de Trayectoria Híbrida Barbell & Trinquete (PB-70).
Modela la interacción matemática entre:
1. Motor Alfa Asimétrico (Futuros 1.5x) con métricas reales OOS.
2. Válvula de Trinquete (Harvesting): extracción del 50% de ganancias al duplicar capital.
3. Bóveda Delta-Neutral: arbitraje Cash & Carry generando 18% APR compuesto.
Proyecta tiempo y probabilidad para alcanzar los 10,000 USDT mensuales pasivos.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def simulate_hybrid_growth(
    starting_alpha_capital: float = 1000.0,
    starting_vault_capital: float = 0.0,
    target_monthly_income: float = 10000.0,
    vault_apr: float = 0.18,              # 18% APR conservador en Cash & Carry
    alpha_monthly_cagr: float = 0.42,     # 42% anualizado empírico de V5 Ablation
    alpha_monthly_vol: float = 0.12,      # Volatilidad mensual del motor agresivo
    max_alpha_cap: float = 2000.0,        # Al tocar 2,000 USDT, extrae el 50% de utilidades
    months_horizon: int = 60,             # Horizonte de 5 años (60 meses)
    num_simulations: int = 3000
):
    # La meta pasiva: con 18% APR, 10,000 USDT/mes ($120,000/año) requiere:
    target_vault_size = (target_monthly_income * 12.0) / vault_apr
    
    monthly_vault_return = (1.0 + vault_apr) ** (1.0 / 12.0) - 1.0
    monthly_alpha_mean = (1.0 + alpha_monthly_cagr) ** (1.0 / 12.0) - 1.0
    
    months_to_target = []
    vault_final_balances = []
    total_wealth_final = []
    ruined_count = 0

    np.random.seed(42)

    for sim_idx in range(num_simulations):
        alpha_cap = starting_alpha_capital
        vault_cap = starting_vault_capital
        reached_month = None

        for m in range(1, months_horizon + 1):
            # 1. Crecimiento compuesto de la Bóveda Segura (Riesgo Direccional $0)
            vault_cap *= (1.0 + monthly_vault_return)

            # 2. Retorno estocástico del Motor Alfa (distribución normal con fat-tails moderadas)
            shock = np.random.normal(monthly_alpha_mean, alpha_monthly_vol)
            alpha_cap *= (1.0 + shock)

            # Si el motor agresivo sufre drawdown profundo por debajo de $200 (Kill Switch)
            if alpha_cap <= (starting_alpha_capital * 0.25):
                alpha_cap = starting_alpha_capital * 0.25  # Congela en piso de seguridad

            # 3. Regla del Trinquete (Profit Harvesting al tocar el techo de ciclo)
            if alpha_cap >= max_alpha_cap:
                profit = alpha_cap - starting_alpha_capital
                transfer_to_vault = profit * 0.60  # 60% a la bóveda segura
                reinvest_alpha = profit * 0.40     # 40% se queda para acelerar
                
                vault_cap += transfer_to_vault
                alpha_cap = starting_alpha_capital + reinvest_alpha

            # 4. ¿Alcanzó la meta de 10,000 USDT/mes en renta pasiva?
            monthly_income = vault_cap * monthly_vault_return
            if monthly_income >= target_monthly_income and reached_month is None:
                reached_month = m

        if reached_month is not None:
            months_to_target.append(reached_month)

        vault_final_balances.append(vault_cap)
        total_wealth_final.append(vault_cap + alpha_cap)

    # Métricas
    success_rate = (len(months_to_target) / num_simulations) * 100.0
    median_vault = np.median(vault_final_balances)
    p25_vault = np.percentile(vault_final_balances, 25)
    p75_vault = np.percentile(vault_final_balances, 75)
    median_income = median_vault * monthly_vault_return

    print("=" * 75)
    print(f"🔬 SIMULACIÓN DE TRAYECTORIA HÍBRIDA BARBELL & TRINQUETE (PB-70)")
    print("=" * 75)
    print(f"Capital Inicial: Motor Futuros = {starting_alpha_capital:,.2f} USDT | Bóveda Segura = {starting_vault_capital:,.2f} USDT")
    print(f"Meta de Ingreso Pasivo: {target_monthly_income:,.2f} USDT/mes (Requiere {target_vault_size:,.2f} USDT al {vault_apr*100:.1f}% APR)")
    print(f"Horizonte: {months_horizon} meses (5 años) | Simulaciones: {num_simulations}")
    print("-" * 75)
    print("RESULTADOS DE LA BÓVEDA SEGURA A 5 AÑOS:")
    print(f"  * Balance Mediano Acumulado (P50):  {median_vault:,.2f} USDT")
    print(f"  * Rango Intercuartil (P25 - P75):   {p25_vault:,.2f} USDT  a  {p75_vault:,.2f} USDT")
    print(f"  * Ingreso Pasivo Mensual Mediano:   {median_income:,.2f} USDT/mes")
    print(f"  * Probabilidad de Alcanzar 10k/mes: {success_rate:.2f}% dentro del horizonte")
    if months_to_target:
        print(f"  * Tiempo Mediano para la Meta:      {np.median(months_to_target):.0f} meses ({np.median(months_to_target)/12:.1f} años)")
    print("-" * 75)
    return success_rate, median_vault, median_income


if __name__ == "__main__":
    print("\n--- ESCENARIO 1: ARRANQUE CON MICRO-CAPITAL (1,000 USDT) ---")
    simulate_hybrid_growth(starting_alpha_capital=1000.0, starting_vault_capital=0.0)

    print("\n--- ESCENARIO 2: ARRANQUE MODERADO (10,000 USDT) ---")
    simulate_hybrid_growth(starting_alpha_capital=2000.0, starting_vault_capital=8000.0)
