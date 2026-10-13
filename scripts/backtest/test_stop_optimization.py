import zipfile
import json
import pandas as pd
import numpy as np

def test_tight_stops_and_trailing():
    z = zipfile.ZipFile('user_data/backtest_results/backtest-result-2026-10-11_18-46-09.zip')
    data = json.loads(z.read('backtest-result-2026-10-11_18-46-09.json'))
    trades = data['strategy']['MemeHunterFuturesV1']['trades']
    df = pd.DataFrame(trades).sort_values('open_date')
    
    # Excluir Longs en altcoins sangrantes (SUI, TIA, SOL)
    df_clean = df[~((df['pair'].isin(['SUI/USDT:USDT', 'TIA/USDT:USDT', 'SOL/USDT:USDT'])) & (~df['is_short']))]

    # Probamos cómo cambia el profit de cada trade si el stop loss se recorta
    # Si un trade tuvo adverse excursion >= cut_stop, su PnL pasa de ser peor a -cut_stop
    # O si tuvo trailing temprano (+5% activa BE o +8% captura +4%)
    
    results = []
    
    for stoploss_val in [0.10, 0.12, 0.15]:
        for trailing_trigger in [0.06, 0.08, 0.119]:
            # Simulamos cada trade ajustado
            adjusted_trades = []
            for _, r in df_clean.iterrows():
                p_ratio = r['profit_ratio']
                is_short = r['is_short']
                adv = (r['max_rate'] - r['open_rate'])/r['open_rate'] if is_short else (r['open_rate'] - r['min_rate'])/r['open_rate']
                fav = (r['open_rate'] - r['min_rate'])/r['open_rate'] if is_short else (r['max_rate'] - r['open_rate'])/r['open_rate']
                
                # Si tocó el stop loss ajustado
                if adv >= stoploss_val and r['exit_reason'] == 'stop_loss':
                    # Pierde exactamente stoploss_val en vez de 15% o más
                    p_ratio = -stoploss_val
                    
                # Si alcanzó el trigger de trailing stop más temprano
                if fav >= trailing_trigger and r['exit_reason'] in ['stop_loss', 'force_exit']:
                    # Logró asegurar al menos +2% o salir en breakeven
                    p_ratio = 0.02
                    
                adjusted_trades.append({
                    'pair': r['pair'],
                    'is_short': is_short,
                    'profit_ratio': p_ratio
                })
                
            adj_df = pd.DataFrame(adjusted_trades)
            
            # Simulamos capital sobre $100
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
            
            results.append({
                'stoploss': stoploss_val,
                'trailing_trigger': trailing_trigger,
                'ret_pct': ret,
                'max_dd_pct': max_dd * 100,
                'sortino': sortino,
                'final_cap': cap
            })
            
    res_df = pd.DataFrame(results).sort_values('ret_pct', ascending=False)
    print("=== MATRIZ DE OPTIMIZACIÓN DE STOP LOSS & TRAILING TRIGGER ===")
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    test_tight_stops_and_trailing()
