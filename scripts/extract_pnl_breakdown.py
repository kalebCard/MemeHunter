"""
Auditoría y Desglose Granular de Rendimiento:
Genera la tabla diaria, mensual y anual certificada de la última simulación de 100 USDT (MemeHunterFuturesV5_Leverage).
"""

import sys
import json
import zipfile
from pathlib import Path
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def parse_last_backtest():
    backtest_dir = Path("user_data/backtest_results")
    with open(backtest_dir / ".last_result.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    zip_name = meta.get("latest_backtest")
    zip_path = backtest_dir / zip_name
    
    with zipfile.ZipFile(zip_path, "r") as z:
        candidates = [n for n in z.namelist() if n.endswith(".json") and not n.endswith("_config.json")]
        data = json.loads(z.read(candidates[0]))
        
    strat_name = list(data["strategy"].keys())[0]
    trades = data["strategy"][strat_name]["trades"]
    df = pd.DataFrame(trades)
    
    # Parse dates
    df['close_date'] = pd.to_datetime(df['close_timestamp'], unit='ms')
    df['date'] = df['close_date'].dt.date
    df['year_month'] = df['close_date'].dt.to_period('M')
    df['year'] = df['close_date'].dt.year
    df['day_name'] = df['close_date'].dt.day_name()
    
    # 1. Rendimiento Anual
    annual = df.groupby('year').agg(
        trades=('profit_abs', 'count'),
        profit_usdt=('profit_abs', 'sum'),
        win_rate=('profit_abs', lambda x: (x > 0).mean() * 100),
        best_trade=('profit_abs', 'max'),
        worst_trade=('profit_abs', 'min')
    ).reset_index()
    
    # 2. Rendimiento Mensual
    monthly = df.groupby('year_month').agg(
        trades=('profit_abs', 'count'),
        profit_usdt=('profit_abs', 'sum'),
        win_rate=('profit_abs', lambda x: (x > 0).mean() * 100),
        best_trade=('profit_abs', 'max'),
        worst_trade=('profit_abs', 'min')
    ).reset_index()
    
    # 3. Rendimiento por Día de la Semana
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_dow = df.groupby('day_name').agg(
        trades=('profit_abs', 'count'),
        profit_usdt=('profit_abs', 'sum'),
        win_rate=('profit_abs', lambda x: (x > 0).mean() * 100),
        avg_profit=('profit_abs', 'mean')
    ).reindex(day_order).reset_index()
    
    # 4. Estadísticas Diarias
    daily_pnl = df.groupby('date')['profit_abs'].sum()
    total_days = (df['close_date'].max() - df['close_date'].min()).days
    winning_days = (daily_pnl > 0).sum()
    losing_days = (daily_pnl < 0).sum()
    flat_days = total_days - len(daily_pnl)
    
    print("==================================================================")
    print(f" RESUMEN CERTIFICADO DE RENDIMIENTO: {strat_name} (100 USDT)")
    print(f" Archivo: {zip_name} | Operaciones Totales: {len(df)}")
    print("==================================================================\n")
    
    print("--- 1. RENDIMIENTO ANUAL ---")
    print(annual.to_string(index=False))
    print("\n--- 2. RENDIMIENTO MENSUAL (2024) ---")
    monthly['cumulative_usdt'] = monthly['profit_usdt'].cumsum()
    monthly['capital_at_end'] = 100.0 + monthly['cumulative_usdt']
    monthly['return_pct'] = (monthly['profit_usdt'] / (monthly['capital_at_end'] - monthly['profit_usdt'])) * 100
    print(monthly.to_string(index=False))
    
    print("\n--- 3. RENDIMIENTO POR DÍA DE LA SEMANA (ESTACIONALIDAD) ---")
    print(daily_dow.to_string(index=False))
    
    print("\n--- 4. ESTADÍSTICAS DIARIAS GENERALES ---")
    print(f"Total Días de Backtest: {total_days} días")
    print(f"Días con Ganancia Neta: {winning_days} días")
    print(f"Días con Pérdida Neta: {losing_days} días")
    print(f"Días Sin Operaciones / Neutros: {flat_days} días")
    print(f"Mejor Día: +{daily_pnl.max():.2f} USDT")
    print(f"Peor Día: {daily_pnl.min():.2f} USDT")
    print(f"Ganancia Diaria Promedio (en días con actividad): +{daily_pnl.mean():.2f} USDT")
    print(f"Ganancia Diaria Promedio (global anual): +{df['profit_abs'].sum() / total_days:.2f} USDT/día")

if __name__ == "__main__":
    parse_last_backtest()
