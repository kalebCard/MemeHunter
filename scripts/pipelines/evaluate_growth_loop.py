import zipfile
import json
import pandas as pd
import numpy as np

def run_advanced_optimizer():
    z = zipfile.ZipFile('user_data/backtest_results/backtest-result-2026-10-11_18-46-09.zip')
    data = json.loads(z.read('backtest-result-2026-10-11_18-46-09.json'))
    trades = data['strategy']['MemeHunterFuturesV1']['trades']
    df = pd.DataFrame(trades).sort_values('open_date')
    
    # Excluir Longs en monedas sangrantes donde el edge en compra es negativo
    df_clean = df[~((df['pair'].isin(['SUI/USDT:USDT', 'TIA/USDT:USDT', 'SOL/USDT:USDT'])) & (~df['is_short']))]

    results = []
    
    for base_pct in [0.08, 0.10, 0.12]:
        for short_mult in [1.20, 1.30, 1.40]:
            for long_mult in [0.35, 0.50, 0.65]:
                cap = 100.0
                peak = cap
                max_dd = 0.0
                equity_curve = [cap]
                
                for _, r in df_clean.iterrows():
                    mult = short_mult if r['is_short'] else long_mult
                    stake = max(5.0, cap * base_pct * mult)
                    stake = min(stake, cap)
                    pnl = stake * r['profit_ratio']
                    cap += pnl
                    if cap > peak:
                        peak = cap
                    dd = (peak - cap) / peak if peak > 0 else 0
                    if dd > max_dd:
                        max_dd = dd
                    equity_curve.append(cap)
                    
                ret_pct = ((cap - 100.0) / 100.0) * 100
                rets = np.diff(equity_curve) / equity_curve[:-1]
                down_rets = rets[rets < 0]
                sortino = (np.mean(rets) / np.std(down_rets) * np.sqrt(365 * 6)) if len(down_rets) > 0 and np.std(down_rets) > 0 else 0
                sharpe = (np.mean(rets) / np.std(rets) * np.sqrt(365 * 6)) if np.std(rets) > 0 else 0
                
                # Calmar drawdown: solo configuraciones con Drawdown <= 35%
                results.append({
                    "base_pct": base_pct,
                    "short_mult": short_mult,
                    "long_mult": long_mult,
                    "final_cap": cap,
                    "ret_pct": ret_pct,
                    "max_dd_pct": max_dd * 100,
                    "sortino": sortino,
                    "sharpe": sharpe,
                    "score": ret_pct / (max_dd * 100)  # Calmar ratio
                })
                
    res_df = pd.DataFrame(results).sort_values('ret_pct', ascending=False)
    print("=== TOP 5 POR RETORNO PURO ===")
    print(res_df.head(5).to_string(index=False))
    
    print("\n=== TOP 5 POR RATIO CALMAR (RETORNO / DRAWDOWN) ===")
    print(res_df.sort_values('score', ascending=False).head(5).to_string(index=False))

    safe_df = res_df[res_df['max_dd_pct'] <= 35.0]
    print("\n=== TOP 5 CON CONTROL DE RIESGO ESTRICTO (MAX DD <= 35%) ===")
    print(safe_df.sort_values('ret_pct', ascending=False).head(5).to_string(index=False))

if __name__ == "__main__":
    run_advanced_optimizer()
