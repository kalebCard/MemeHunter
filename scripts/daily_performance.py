"""
Meme Hunter - Daily Performance & Return Distribution Analyzer
Evaluates day-by-day PnL, win/loss day ratios, daily Sharpe/Sortino,
streaks, day-of-week seasonality, and monthly return matrices.
"""

import sys
import os
import json
import zipfile
import math
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def load_latest_backtest(backtest_dir: Path):
    last_result_file = backtest_dir / ".last_result.json"
    if not last_result_file.exists():
        raise FileNotFoundError(f"No se encontró .last_result.json en {backtest_dir}")
    
    with open(last_result_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    zip_name = meta.get("latest_backtest")
    if not zip_name:
        raise ValueError("No se encontró 'latest_backtest' en .last_result.json")
    
    zip_path = backtest_dir / zip_name
    if not zip_path.exists():
        raise FileNotFoundError(f"Archivo zip {zip_path} no existe.")
    
    with zipfile.ZipFile(zip_path, "r") as z:
        candidates = [n for n in z.namelist() if n.endswith(".json") and not n.endswith("_config.json") and not n.endswith("_MemeHunterV2.json")]
        if not candidates:
            raise FileNotFoundError("No se encontró el JSON principal de backtest dentro del ZIP.")
        main_json = candidates[0]
        data = json.loads(z.read(main_json))
        
    return data, zip_path.name


def analyze_daily_performance(data: dict, zip_name: str, backtest_dir: Path, starting_capital: float = 100.0):
    strat_dict = data.get("strategy", {})
    strat_name = list(strat_dict.keys())[0] if strat_dict else "MemeHunterFuturesV1"
    strat_data = strat_dict.get(strat_name, {})
    trades = strat_data.get("trades", [])
    original_balance = float(strat_data.get("starting_balance", 1000.0))
    scale_factor = starting_capital / original_balance if original_balance > 0 else 1.0
    starting_balance = starting_capital
    
    if not trades:
        print("[!] No hay trades en este backtest.")
        return
    
    df_trades = pd.DataFrame(trades)
    df_trades['profit_abs'] = df_trades['profit_abs'] * scale_factor
    df_trades['close_dt'] = pd.to_datetime(df_trades['close_date'])
    df_trades['close_day'] = df_trades['close_dt'].dt.date
    df_trades['open_dt'] = pd.to_datetime(df_trades['open_date'])
    df_trades['open_day'] = df_trades['open_dt'].dt.date
    
    start_date = df_trades['open_day'].min()
    end_date = df_trades['close_day'].max()
    all_days = pd.date_range(start=start_date, end=end_date, freq='D').date
    
    # Agrupar PnL por día de cierre
    daily_grouped = df_trades.groupby('close_day').agg(
        pnl_abs=('profit_abs', 'sum'),
        trades_count=('profit_abs', 'count'),
        wins_count=('profit_abs', lambda x: (x > 0).sum()),
        losses_count=('profit_abs', lambda x: (x <= 0).sum()),
        long_pnl=('profit_abs', lambda x: x[df_trades.loc[x.index, 'is_short'] == False].sum()),
        short_pnl=('profit_abs', lambda x: x[df_trades.loc[x.index, 'is_short'] == True].sum()),
    )
    
    # Crear serie completa de todos los días calendario
    df_calendar = pd.DataFrame(index=all_days)
    df_calendar.index.name = 'date'
    df_calendar = df_calendar.join(daily_grouped).fillna(0.0)
    df_calendar['trades_count'] = df_calendar['trades_count'].astype(int)
    df_calendar['wins_count'] = df_calendar['wins_count'].astype(int)
    df_calendar['losses_count'] = df_calendar['losses_count'].astype(int)
    
    # Equity curve y retornos diarios
    df_calendar['cum_pnl'] = df_calendar['pnl_abs'].cumsum()
    df_calendar['equity'] = starting_balance + df_calendar['cum_pnl']
    df_calendar['prev_equity'] = df_calendar['equity'].shift(1).fillna(starting_balance)
    df_calendar['daily_return_pct'] = (df_calendar['pnl_abs'] / df_calendar['prev_equity']) * 100.0
    
    # Métricas globales
    total_calendar_days = len(df_calendar)
    active_days = df_calendar[df_calendar['trades_count'] > 0]
    num_active_days = len(active_days)
    num_flat_days = total_calendar_days - num_active_days
    
    green_days = df_calendar[df_calendar['pnl_abs'] > 0]
    red_days = df_calendar[df_calendar['pnl_abs'] < 0]
    zero_days = df_calendar[df_calendar['pnl_abs'] == 0]
    
    num_green_days = len(green_days)
    num_red_days = len(red_days)
    
    total_net_pnl = df_calendar['pnl_abs'].sum()
    final_balance = starting_balance + total_net_pnl
    total_return_pct = (total_net_pnl / starting_balance) * 100.0
    
    # Estadísticas diarias
    mean_daily_pnl = df_calendar['pnl_abs'].mean()
    median_daily_pnl = df_calendar['pnl_abs'].median()
    std_daily_pnl = df_calendar['pnl_abs'].std()
    
    mean_daily_return_pct = df_calendar['daily_return_pct'].mean()
    median_daily_return_pct = df_calendar['daily_return_pct'].median()
    std_daily_return_pct = df_calendar['daily_return_pct'].std()
    
    # Sólo en días activos
    mean_active_pnl = active_days['pnl_abs'].mean() if num_active_days > 0 else 0
    mean_active_return_pct = active_days['daily_return_pct'].mean() if num_active_days > 0 else 0
    
    avg_green_pnl = green_days['pnl_abs'].mean() if num_green_days > 0 else 0
    avg_green_return_pct = green_days['daily_return_pct'].mean() if num_green_days > 0 else 0
    avg_red_pnl = red_days['pnl_abs'].mean() if num_red_days > 0 else 0
    avg_red_return_pct = red_days['daily_return_pct'].mean() if num_red_days > 0 else 0
    
    daily_win_rate_calendar = (num_green_days / total_calendar_days) * 100.0
    daily_win_rate_active = (num_green_days / num_active_days * 100.0) if num_active_days > 0 else 0
    
    # Profit factor diario
    gross_daily_profit = green_days['pnl_abs'].sum()
    gross_daily_loss = abs(red_days['pnl_abs'].sum())
    daily_profit_factor = (gross_daily_profit / gross_daily_loss) if gross_daily_loss > 0 else float('inf')
    
    # Win / Loss Ratio promedio diario
    win_loss_ratio = abs(avg_green_pnl / avg_red_pnl) if avg_red_pnl != 0 else float('inf')
    
    # Extremos
    best_day = df_calendar.loc[df_calendar['pnl_abs'].idxmax()]
    worst_day = df_calendar.loc[df_calendar['pnl_abs'].idxmin()]
    
    # VaR diario (percentil 5% y 1%)
    daily_var_95 = np.percentile(df_calendar['daily_return_pct'], 5)
    daily_var_99 = np.percentile(df_calendar['daily_return_pct'], 1)
    
    # Rachas (Streaks)
    signs = np.sign(df_calendar['pnl_abs'].values)
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    cur_w = 0
    cur_l = 0
    for s in signs:
        if s > 0:
            cur_w += 1
            cur_l = 0
            if cur_w > max_win_streak:
                max_win_streak = cur_w
        elif s < 0:
            cur_l += 1
            cur_w = 0
            if cur_l > max_loss_streak:
                max_loss_streak = cur_l
        else:
            cur_w = 0
            cur_l = 0
            
    # Ratios anualizados de Sharpe y Sortino diario
    rf_daily = 0.0  # asumimos 0% risk free para crypto
    daily_sharpe = (mean_daily_return_pct / std_daily_return_pct * math.sqrt(365)) if std_daily_return_pct > 0 else 0
    
    downside_returns = df_calendar['daily_return_pct'][df_calendar['daily_return_pct'] < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
    daily_sortino = (mean_daily_return_pct / downside_std * math.sqrt(365)) if downside_std > 0 else 0
    
    # Desglose por día de la semana
    df_calendar_dt = df_calendar.copy()
    dt_idx = pd.to_datetime(df_calendar_dt.index)
    df_calendar_dt['weekday'] = dt_idx.day_name()
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_es = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    
    dow_stats = df_calendar_dt.groupby('weekday').agg(
        pnl=('pnl_abs', 'sum'),
        mean_pnl=('pnl_abs', 'mean'),
        win_rate=('pnl_abs', lambda x: (x > 0).sum() / len(x) * 100.0),
        trades=('trades_count', 'sum')
    ).reindex(weekday_order)
    
    # Desglose mensual
    df_calendar_dt['year_month'] = dt_idx.to_period('M')
    monthly_pnl = df_calendar_dt.groupby('year_month').agg(
        pnl=('pnl_abs', 'sum'),
        trades=('trades_count', 'sum'),
        green_days=('pnl_abs', lambda x: (x > 0).sum()),
        red_days=('pnl_abs', lambda x: (x < 0).sum()),
        total_days=('pnl_abs', 'count')
    )
    
    # Imprimir Reporte Visual
    print("=" * 80)
    print(f"📊 REPORTE DE RENDIMIENTO DIARIO Y CONSISTENCIA TEMPORAL")
    print(f"Estrategia: {strat_name} | Archivo: {zip_name}")
    print(f"Periodo: {start_date} al {end_date} ({total_calendar_days} días naturales)")
    print("=" * 80)
    
    print("\n1. 📈 RENDIMIENTO DIARIO Y EXPECTATIVA MATEMÁTICA:")
    print(f"   • Retorno Total del Periodo:       +{total_net_pnl:.2f} USDT (+{total_return_pct:.2f}%)")
    print(f"   • Rendimiento Promedio por Día:    +{mean_daily_pnl:.2f} USDT/día (+{mean_daily_return_pct:.3f}%/día)")
    print(f"   • Rendimiento Mediano por Día:     +{median_daily_pnl:.2f} USDT/día")
    print(f"   • Rendimiento en Días Activos:     +{mean_active_pnl:.2f} USDT/día (+{mean_active_return_pct:.3f}%/día)")
    print(f"   • Proyección Mensual Promedio:     +{mean_daily_pnl * 30.4:.2f} USDT/mes (+{mean_daily_return_pct * 30.4:.2f}%/mes)")
    print(f"   • Proyección Anual Promedio:       +{mean_daily_pnl * 365:.2f} USDT/año (+{mean_daily_return_pct * 365:.2f}%/año)")

    print("\n2. ⚖️ PROBABILIDAD DE DÍAS VERDES VS ROJOS:")
    print(f"   • Días Totales Calendario:         {total_calendar_days} días")
    print(f"   • Días con Operaciones (Activos):  {num_active_days} días ({num_active_days/total_calendar_days*100:.1f}%)")
    print(f"   • Días sin Operaciones (Neutros):  {num_flat_days} días ({num_flat_days/total_calendar_days*100:.1f}%)")
    print(f"   • Días Verdes (Ganadores):         🟢 {num_green_days} días ({daily_win_rate_calendar:.1f}% del total / {daily_win_rate_active:.1f}% de los activos)")
    print(f"   • Días Rojos (Perdedores):         🔴 {num_red_days} días ({num_red_days/total_calendar_days*100:.1f}% del total / {num_red_days/num_active_days*100:.1f}% de los activos)")
    print(f"   • Profit Factor Diario:            {daily_profit_factor:.2f} (Ganancias brutas / Pérdidas brutas)")
    print(f"   • Ganancia Media en Día Verde:     🟢 +{avg_green_pnl:.2f} USDT (+{avg_green_return_pct:.2f}%)")
    print(f"   • Pérdida Media en Día Rojo:       🔴 {avg_red_pnl:.2f} USDT ({avg_red_return_pct:.2f}%)")
    print(f"   • Ratio Ganancia/Pérdida (W/L):    {win_loss_ratio:.2f}x (En promedio gana {win_loss_ratio:.2f}x lo que pierde en un día)")

    print("\n3. ⚡ DÍAS EXTREMOS Y GESTIÓN DE RIESGO DIARIO:")
    print(f"   • Mejor Día Histórico:             🚀 +{best_day['pnl_abs']:.2f} USDT (+{best_day['daily_return_pct']:.2f}%) [{df_calendar['pnl_abs'].idxmax()}]")
    print(f"   • Peor Día Histórico:              💥 {worst_day['pnl_abs']:.2f} USDT ({worst_day['daily_return_pct']:.2f}%) [{df_calendar['pnl_abs'].idxmin()}]")
    print(f"   • VaR Diario al 95% (Peor 5% días): {daily_var_95:.2f}% (Máxima pérdida esperada en 95 de cada 100 días)")
    print(f"   • VaR Diario al 99% (Peor 1% días): {daily_var_99:.2f}% (Estrés extremo en 99 de cada 100 días)")
    print(f"   • Mayor Racha de Días Verdes:      🟢 {max_win_streak} días consecutivos en positivo")
    print(f"   • Mayor Racha de Días Rojos:       🔴 {max_loss_streak} días consecutivos en negativo")

    print("\n4. 🏆 RATIOS DE CALIDAD DIARIOS (Riesgo vs Retorno Anualizado):")
    print(f"   • Sharpe Ratio Diario Anualizado:  {daily_sharpe:.2f}  (Excelente si > 1.0, Institucional si > 1.5)")
    print(f"   • Sortino Ratio Diario Anualizado: {daily_sortino:.2f}  (Mide retorno castigando sólo la volatilidad negativa)")

    print("\n5. 📅 RENDIMIENTO POR DÍA DE LA SEMANA (Seasonality):")
    print(f"   {'Día':<12} | {'PnL Total':<12} | {'Media/Día':<12} | {'% Ganador':<10} | {'Trades':<8}")
    print("   " + "-" * 62)
    for dow, row in dow_stats.iterrows():
        dow_name = weekday_es.get(dow, dow)
        pnl_str = f"+{row['pnl']:.2f}" if row['pnl'] >= 0 else f"{row['pnl']:.2f}"
        print(f"   {dow_name:<12} | {pnl_str:>8} USDT | {row['mean_pnl']:>8.2f} USDT | {row['win_rate']:>8.1f}% | {int(row['trades']):>6}")

    print("\n6. 🗓️ DESGLOSE MENSUAL CONSOLIDADO (Mes a Mes):")
    print(f"   {'Mes':<10} | {'PnL USDT':<12} | {'Retorno Est':<12} | {'Días 🟢':<8} | {'Días 🔴':<8} | {'Trades':<8}")
    print("   " + "-" * 66)
    
    green_months = 0
    red_months = 0
    for ym, row in monthly_pnl.iterrows():
        pnl_val = row['pnl']
        if pnl_val > 0:
            green_months += 1
            sign_icon = "🟢"
            pnl_txt = f"+{pnl_val:.2f}"
        else:
            red_months += 1
            sign_icon = "🔴"
            pnl_txt = f"{pnl_val:.2f}"
            
        ret_est = (pnl_val / starting_balance) * 100.0
        ret_txt = f"+{ret_est:.2f}%" if ret_est >= 0 else f"{ret_est:.2f}%"
        print(f"   {sign_icon} {str(ym):<7} | {pnl_txt:>8} USDT | {ret_txt:>10} | {int(row['green_days']):>6} d | {int(row['red_days']):>6} d | {int(row['trades']):>6}")

    total_months = len(monthly_pnl)
    print("   " + "-" * 66)
    print(f"   Consistencia Mensual: {green_months}/{total_months} meses en positivo ({green_months/total_months*100:.1f}%)")
    print("=" * 80 + "\n")

    # Guardar reporte estructurado en JSON
    output_path = backtest_dir / "daily_performance.json"
    report_dict = {
        "strategy": strat_name,
        "backtest_file": zip_name,
        "total_calendar_days": total_calendar_days,
        "active_days": num_active_days,
        "flat_days": num_flat_days,
        "total_net_pnl_usdt": round(float(total_net_pnl), 2),
        "total_return_pct": round(float(total_return_pct), 2),
        "mean_daily_pnl_usdt": round(float(mean_daily_pnl), 3),
        "mean_daily_return_pct": round(float(mean_daily_return_pct), 4),
        "daily_win_rate_calendar_pct": round(float(daily_win_rate_calendar), 2),
        "daily_win_rate_active_pct": round(float(daily_win_rate_active), 2),
        "daily_profit_factor": round(float(daily_profit_factor), 2),
        "win_loss_ratio": round(float(win_loss_ratio), 2),
        "avg_green_day_usdt": round(float(avg_green_pnl), 2),
        "avg_red_day_usdt": round(float(avg_red_pnl), 2),
        "best_day": {
            "date": str(df_calendar['pnl_abs'].idxmax()),
            "pnl_usdt": round(float(best_day['pnl_abs']), 2),
            "return_pct": round(float(best_day['daily_return_pct']), 2)
        },
        "worst_day": {
            "date": str(df_calendar['pnl_abs'].idxmin()),
            "pnl_usdt": round(float(worst_day['pnl_abs']), 2),
            "return_pct": round(float(worst_day['daily_return_pct']), 2)
        },
        "var_95_pct": round(float(daily_var_95), 2),
        "var_99_pct": round(float(daily_var_99), 2),
        "max_win_streak_days": int(max_win_streak),
        "max_loss_streak_days": int(max_loss_streak),
        "annualized_sharpe": round(float(daily_sharpe), 2),
        "annualized_sortino": round(float(daily_sortino), 2),
        "monthly_consistency_pct": round(float(green_months / total_months * 100.0), 2)
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
        
    print(f"[+] Reporte exportado a: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - Daily Performance Analyzer")
    parser.add_argument("--capital", type=float, default=100.0, help="Capital inicial (USDT)")
    args = parser.parse_args()
    
    workspace = Path(__file__).parent.parent
    backtest_dir = workspace / "user_data" / "backtest_results"
    data, zip_name = load_latest_backtest(backtest_dir)
    analyze_daily_performance(data, zip_name, backtest_dir, args.capital)


if __name__ == "__main__":
    main()
