import zipfile
import json
import pandas as pd
import numpy as np

def test_realistic_tight_stoploss():
    z = zipfile.ZipFile('user_data/backtest_results/backtest-result-2026-10-11_18-46-09.zip')
    data = json.loads(z.read('backtest-result-2026-10-11_18-46-09.json'))
    trades = data['strategy']['MemeHunterFuturesV1']['trades']
    df = pd.DataFrame(trades).sort_values('open_date')
    
    # Excluir Longs en altcoins sangrantes (SUI, TIA, SOL)
    df_clean = df[~((df['pair'].isin(['SUI/USDT:USDT', 'TIA/USDT:USDT', 'SOL/USDT:USDT'])) & (~df['is_short']))]

    # Modelo conservador:
    # 1. No asumimos ganancias extra de trailing. Los ganadores mantienen exactamente su PnL original.
    # 2. Únicamente evaluamos el impacto de recortar la pérdida máxima en stop_loss:
    #    Si el stop pasa de -15% a -10% o -11%, evaluamos cuántos ganadores tuvieron una excursión adversa >= 10%.
    
    for stop_cut in [0.09, 0.10, 0.11, 0.12, 0.15]:
        adjusted = []
        premature_stopped_winners = 0
        
        for _, r in df_clean.iterrows():
            is_short = r['is_short']
            adv = (r['max_rate'] - r['open_rate'])/r['open_rate'] if is_short else (r['open_rate'] - r['min_rate'])/r['open_rate']
            p_ratio = r['profit_ratio']
            
            if r['exit_reason'] == 'stop_loss':
                # El stop loss fue acotado a -stop_cut
                p_ratio = -stop_cut
            elif p_ratio > 0 and adv >= stop_cut:
                # Este trade ganó originalmente, pero si el stop hubiera sido más ajustado, se habría cerrado en pérdida
                premature_stopped_winners += 1
                p_ratio = -stop_cut
                
            adjusted.append({
                'is_short': is_short,
                'profit_ratio': p_ratio
            })
            
        adj_df = pd.DataFrame(adjusted)
        
        # Simulación de curva de capital
        cap = 100.0
        peak = cap
        max_dd = 0.0
        equity = [cap]
        for _, tr in adj_df.iterrows():
            mult = 1.35 if tr['is_short'] else 0.45
            stake = max(5.0, min(cap, cap * 0.10 * mult))
            pnl = stake * tr['profit_ratio']
            cap += pnl
            peak = max(peak, cap)
            dd = (peak - cap) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            equity.append(cap)
            
        ret = ((cap - 100.0) / 100.0) * 100
        rets = np.diff(equity) / equity[:-1]
        down_rets = rets[rets < 0]
        sortino = (np.mean(rets) / np.std(down_rets) * np.sqrt(365 * 6)) if len(down_rets) > 0 and np.std(down_rets) > 0 else 0
        
        print(f"Stop Loss: -{stop_cut*100:.1f}% | Ganadores cortados antes: {premature_stopped_winners} | Retorno: +{ret:.2f}% | Max DD: {max_dd*100:.2f}% | Sortino: {sortino:.2f} | Saldo: ${cap:.2f}")

if __name__ == "__main__":
    test_realistic_tight_stoploss()
