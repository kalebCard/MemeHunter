import sys
import os
sys.path.insert(0, os.path.abspath("."))
from client.multi_bot_orchestrator import MultiBotOrchestratorClient
from client.binance_account_client import BinanceAccountClient

orch = MultiBotOrchestratorClient()
print("=== TELEMETRÍA MULTI-BOT ===")
status = orch.get_aggregated_status()
print("Total open trades:", status.get("total_open_trades"))
print("Stake active USDT:", status.get("total_stake_active_usdt"))
print("\nBots:")
for b_id, b_info in status.get("bots", {}).items():
    print(f"  {b_id} ({b_info.get('name')}): {b_info.get('open_trades')} trades, online={b_info.get('is_online')}")

print("\n=== BALANCES SIMULADOS ARENA ===")
balances = orch.get_aggregated_balances()
print("Total Wallet Simulado:", balances.get("total_wallet"))
for b_id, b_info in balances.get("bots", {}).items():
    print(f"  {b_id} (:{b_info.get('port')}): Total={b_info.get('total')} USDT (Libre: {b_info.get('free')}, Usado: {b_info.get('used')})")

print("\n=== TRADES ABIERTOS ===")
trades = status.get("trades", [])
for t in trades:
    print(f"  #{t.get('trade_id')} {t.get('pair')} ({t.get('origin_bot')}): PnL={t.get('profit_pct'):+.2f}% | Duración={t.get('open_date_hum')}")

print("\n=== PROFIT CERRADO BOT 1 (Ablation :8081) ===")
p1 = orch.clients["bot_v5_ablation"].get_profit()
if p1.get("status") == "ok":
    d = p1.get("data", {})
    print(f"  PnL Cerrado: {d.get('profit_closed_coin', 0.0):+.2f} USDT ({d.get('profit_closed_ratio_pct', 0.0):+.2f}%) | Trades: {d.get('trade_count')} | WinRate: {d.get('winrate', 0.0)*100:.1f}%")

print("\n=== PROFIT CERRADO BOT 2 (Quantum :8082) ===")
p2 = orch.clients["bot_v7_quantum"].get_profit()
if p2.get("status") == "ok":
    d = p2.get("data", {})
    print(f"  PnL Cerrado: {d.get('profit_closed_coin', 0.0):+.2f} USDT ({d.get('profit_closed_ratio_pct', 0.0):+.2f}%) | Trades: {d.get('trade_count')} | WinRate: {d.get('winrate', 0.0)*100:.1f}%")

print("\n=== PROFIT CERRADO BOT 3 (Ensemble :8083) ===")
p3 = orch.clients["bot_mined_ensemble"].get_profit()
if p3.get("status") == "ok":
    d = p3.get("data", {})
    print(f"  PnL Cerrado: {d.get('profit_closed_coin', 0.0):+.2f} USDT ({d.get('profit_closed_ratio_pct', 0.0):+.2f}%) | Trades: {d.get('trade_count')} | WinRate: {d.get('winrate', 0.0)*100:.1f}%")

print("\n=== SALDO REAL BINANCE ===")
binance = BinanceAccountClient()
real = binance.get_real_balances()
print(f"  Spot USDT: {real.get('spot_usdt_free', 0.0):.2f} USDT")
print(f"  Futures USD-M: {real.get('futures_usdt_free', 0.0):.2f} USDT")
