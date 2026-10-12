"""
audit_seasonality.py - Análisis Cuantitativo de Estacionalidad y Ciclos Humanos.
Analiza la distribución temporal (días de semana, horas UTC, semanas del mes)
de las operaciones históricas para identificar anomalías de retorno y zonas de pérdida.
"""

import json
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np

BACKTEST_DIR = Path("user_data/backtest_results")
LAST_RESULT_POINTER = BACKTEST_DIR / ".last_result.json"


def load_latest_trades() -> pd.DataFrame:
    if not LAST_RESULT_POINTER.exists():
        raise FileNotFoundError("No se encontró .last_result.json")
    
    with open(LAST_RESULT_POINTER, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    zip_name = meta.get("latest_backtest")
    zip_path = BACKTEST_DIR / zip_name
    print(f"[INFO] Cargando resultados desde: {zip_path}")
    
    with zipfile.ZipFile(zip_path, "r") as z:
        # Buscar archivo de resultado json dentro del zip
        json_files = [name for name in z.namelist() if name.endswith(".json") and not name.endswith(".meta.json")]
        if not json_files:
            raise FileNotFoundError("No se encontró archivo de trades JSON dentro del zip.")
        
        with z.open(json_files[0]) as jf:
            data = json.load(jf)
            
    # Extraer trades de la primera estrategia en el archivo
    strategy_name = list(data.get("strategy", {}).keys())[0]
    trades_list = data["strategy"][strategy_name]["trades"]
    df = pd.DataFrame(trades_list)
    
    # Parsear fechas UTC
    df["open_timestamp"] = pd.to_datetime(df["open_timestamp"], unit="ms", utc=True)
    df["close_timestamp"] = pd.to_datetime(df["close_timestamp"], unit="ms", utc=True)
    
    return df, strategy_name


def audit_seasonality(df: pd.DataFrame, strategy_name: str):
    print("=" * 75)
    print(f"AUDITORIA DE ESTACIONALIDAD Y CICLOS HUMANOS: {strategy_name}")
    print(f"Total de operaciones auditadas: {len(df)}")
    print("=" * 75)
    
    # 1. Variables Temporales
    df["day_name"] = df["open_timestamp"].dt.day_name()
    df["day_of_week"] = df["open_timestamp"].dt.dayofweek # 0=Monday, 6=Sunday
    df["hour_utc"] = df["open_timestamp"].dt.hour
    df["day_of_month"] = df["open_timestamp"].dt.day
    
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # --- A. CICLO SEMANAL ---
    print("\n[1] RENDIMIENTO POR DIA DE LA SEMANA (Dia de Apertura)")
    day_stats = df.groupby("day_name").agg(
        trades=("profit_abs", "count"),
        total_pnl=("profit_abs", "sum"),
        win_rate=("profit_ratio", lambda x: (x > 0).mean() * 100),
        avg_profit_pct=("profit_ratio", lambda x: x.mean() * 100),
        stoploss_count=("exit_reason", lambda x: (x == "stop_loss").sum())
    ).reindex(days_order)
    
    print(day_stats.to_string())
    
    # --- B. VENTANAS HORARIAS / SESIONES INSTITUCIONALES ---
    print("\n[2] RENDIMIENTO POR SESION GLOBAL (Horarios UTC)")
    def get_session(hour):
        if 0 <= hour < 8:
            return "1. Asia / Overnight (00:00 - 08:00 UTC)"
        elif 8 <= hour < 14:
            return "2. London Open (08:00 - 14:00 UTC)"
        elif 14 <= hour < 21:
            return "3. New York / US Session (14:00 - 21:00 UTC)"
        else:
            return "4. US Close / Asia Prep (21:00 - 24:00 UTC)"
            
    df["session"] = df["hour_utc"].apply(get_session)
    session_stats = df.groupby("session").agg(
        trades=("profit_abs", "count"),
        total_pnl=("profit_abs", "sum"),
        win_rate=("profit_ratio", lambda x: (x > 0).mean() * 100),
        avg_profit_pct=("profit_ratio", lambda x: x.mean() * 100),
        stoploss_count=("exit_reason", lambda x: (x == "stop_loss").sum())
    )
    print(session_stats.to_string())
    
    # --- C. CICLO MENSUAL / CALENDARIO SALARIAL & EXPIRY ---
    print("\n[3] RENDIMIENTO POR FASE DEL MES (Calendario Humano / Payday & Bleed)")
    def get_month_phase(day):
        if 1 <= day <= 7:
            return "Fase 1: Inyeccion Salarial Inicio de Mes (Dias 1-7)"
        elif 8 <= day <= 14:
            return "Fase 2: Consolidacion Media (Dias 8-14)"
        elif 15 <= day <= 20:
            return "Fase 3: Quincena / Segundo Flujo (Dias 15-20)"
        else:
            return "Fase 4: Agotamiento de Liquidez & Expiry (Dias 21-31)"
            
    df["month_phase"] = df["day_of_month"].apply(get_month_phase)
    phase_stats = df.groupby("month_phase").agg(
        trades=("profit_abs", "count"),
        total_pnl=("profit_abs", "sum"),
        win_rate=("profit_ratio", lambda x: (x > 0).mean() * 100),
        avg_profit_pct=("profit_ratio", lambda x: x.mean() * 100),
        stoploss_count=("exit_reason", lambda x: (x == "stop_loss").sum())
    )
    print(phase_stats.to_string())
    
    # --- D. RESUMEN DE LA VENTAJA ESTADÍSTICA (EDGE) ---
    print("\n[4] CONCLUSIONES CLAVE DE LA AUDITORIA:")
    best_day = day_stats["total_pnl"].idxmax()
    worst_day = day_stats["total_pnl"].idxmin()
    print(f"  * Mejor dia de la semana para Shorts: {best_day} (+{day_stats.loc[best_day, 'total_pnl']:.2f} USDT)")
    print(f"  * Peor dia de la semana para Shorts : {worst_day} ({day_stats.loc[worst_day, 'total_pnl']:.2f} USDT)")
    
    best_session = session_stats["total_pnl"].idxmax()
    worst_session = session_stats["total_pnl"].idxmin()
    print(f"  * Mejor sesion horaria: {best_session} (+{session_stats.loc[best_session, 'total_pnl']:.2f} USDT)")
    print(f"  * Peor sesion horaria : {worst_session} ({session_stats.loc[worst_session, 'total_pnl']:.2f} USDT)")
    print("=" * 75)


if __name__ == "__main__":
    df_trades, name = load_latest_trades()
    audit_seasonality(df_trades, name)
