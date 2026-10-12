"""
statistical_significance.py - Auditoría forense de significancia estadística,
intervalos de confianza del retorno medio y corrección de múltiples pruebas (PB-67).
"""

import json
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

BACKTEST_DIR = Path("user_data/backtest_results")


def load_trades_from_zip(zip_path: Path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            if name.endswith('.json') and not name.endswith('.meta.json'):
                data = json.loads(z.read(name).decode('utf-8'))
                if "strategy" in data:
                    for strat, strat_data in data["strategy"].items():
                        trades = strat_data.get("trades", [])
                        return strat, trades
                # Alternativa formato directo
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict) and "trades" in v:
                            return k, v["trades"]
    return None, []


def analyze_trades(strat_name: str, trades: list):
    if not trades:
        print(f"No trades found for {strat_name}")
        return

    df = pd.DataFrame(trades)
    
    # Extraer beneficios porcentuales (profit_ratio o profit_pct)
    if 'profit_ratio' in df.columns:
        pnl = df['profit_ratio'].values
    elif 'profit_pct' in df.columns:
        pnl = df['profit_pct'].values / 100.0
    else:
        print("Columnas de profit no encontradas:", df.columns)
        return

    n = len(pnl)
    mean_pnl = np.mean(pnl)
    std_pnl = np.std(pnl, ddof=1)
    se = std_pnl / np.sqrt(n)

    # 1. Test t de Student clásico H0: mu <= 0
    t_stat = mean_pnl / se
    p_value_one_tailed = 1.0 - stats.t.cdf(t_stat, df=n - 1)
    ci_95 = stats.t.interval(0.95, df=n - 1, loc=mean_pnl, scale=se)
    ci_99 = stats.t.interval(0.99, df=n - 1, loc=mean_pnl, scale=se)

    # 2. Bootstrap no paramétrico (10,000 remuestreos)
    np.random.seed(42)
    boot_means = [np.mean(np.random.choice(pnl, size=n, replace=True)) for _ in range(10000)]
    boot_ci_95 = (np.percentile(boot_means, 2.5), np.percentile(boot_means, 97.5))
    boot_p_val = np.mean(np.array(boot_means) <= 0)

    # 3. Ajuste por Pruebas Múltiples (Family-Wise Error Rate / Bonferroni)
    # Asumiendo m = 6 iteraciones del modelo (V1, V2, V3, V4, V5, V6)
    m_tests = 6
    p_bonferroni = min(1.0, p_value_one_tailed * m_tests)

    print("=" * 70)
    print(f"[AUDITORIA DE SIGNIFICANCIA ESTADISTICA]: {strat_name}")
    print("=" * 70)
    print(f"Muestra de trades (N): {n}")
    print(f"Retorno Medio por Trade (mu): {mean_pnl * 100:.3f}%")
    print(f"Desviacion Estandar (sigma): {std_pnl * 100:.3f}%")
    print(f"Error Estandar (SE): {se * 100:.3f}%")
    print("-" * 70)
    print("INTERVALOS DE CONFIANZA DEL RETORNO MEDIO:")
    print(f"  * IC 95% Parametrico (t): [{ci_95[0]*100:.3f}%, {ci_95[1]*100:.3f}%]")
    print(f"  * IC 99% Parametrico (t): [{ci_99[0]*100:.3f}%, {ci_99[1]*100:.3f}%]")
    print(f"  * IC 95% Bootstrap:       [{boot_ci_95[0]*100:.3f}%, {boot_ci_95[1]*100:.3f}%]")
    print("-" * 70)
    print("CONTRASTE DE HIPOTESIS (H0: Edge <= 0):")
    print(f"  * t-Statistic: {t_stat:.3f}")
    print(f"  * p-Value crudo (1-tailed): {p_value_one_tailed:.4f}")
    print(f"  * p-Value ajustado por mineria de datos (Bonferroni m={m_tests}): {p_bonferroni:.4f}")
    print(f"  * Probabilidad Bootstrap de retorno nulo/negativo: {boot_p_val * 100:.2f}%")
    print("-" * 70)

    # Analisis de comisiones vs Edge
    fee_threshold = 0.0016  # 0.16%
    prob_sub_fee = np.mean(np.array(boot_means) <= fee_threshold)
    print(f"VULNERABILIDAD FRENTE A FRICCION:")
    print(f"  * Umbral minimo de comisiones/slippage estimado: {fee_threshold*100:.2f}%")
    print(f"  * Probabilidad de que el edge real sea devorado por comisiones: {prob_sub_fee*100:.2f}%")
    
    if ci_95[0] > fee_threshold and p_bonferroni < 0.05:
        print("\n[DICTAMEN]: El edge estadistico supera con significancia el ruido y los costos.")
    elif ci_95[0] > 0 and p_bonferroni < 0.05:
        print("\n[DICTAMEN]: Existe ventaja estadistica sobre 0, pero el limite inferior toca la zona de friccion.")
    else:
        print("\n[DICTAMEN]: NO SE PUEDE RECHAZAR EL AZAR TRAS CORREGIR POR MINERIA DE DATOS.")
    print("=" * 70)


if __name__ == "__main__":
    v5_zip = BACKTEST_DIR / "backtest-result-2026-10-12_00-40-07.zip"
    if not v5_zip.exists():
        print(f"No se encontró {v5_zip}")
    else:
        strat, trades = load_trades_from_zip(v5_zip)
        analyze_trades(strat, trades)
