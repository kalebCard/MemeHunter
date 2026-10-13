#!/usr/bin/env python3
"""
scripts/scan_live_signals.py - Escáner en Vivo de Señales de Capitulación (MemeHunter_ApexOmegaAlpha v7.6.1).
Consulta el feed público de Binance para los 10 pares de memecoins líderes y evalúa
en tiempo real si existen condiciones de capitulación o rebote elástico.
"""

import sys
import io
import time
import urllib.request
import urllib.parse
import os
from pathlib import Path
import pandas as pd
import numpy as np

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))

from MemeHunter_ApexOmegaAlpha import MemeHunter_ApexOmegaAlpha

try:
    import ccxt
except ImportError:
    ccxt = None

def send_telegram_alert(text: str):
    token = os.environ.get("FREQTRADE__TELEGRAM__TOKEN")
    chat_id = os.environ.get("FREQTRADE__TELEGRAM__CHAT_ID")
    if not token or not chat_id:
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("FREQTRADE__TELEGRAM__TOKEN="):
                    token = line.split("=", 1)[1].strip()
                elif line.startswith("FREQTRADE__TELEGRAM__CHAT_ID="):
                    chat_id = line.split("=", 1)[1].strip()
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "MemeHunterBot/1.0"})
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass

PAIRS_SPOT = [
    "DOGE/USDT",
    "SHIB/USDT",
    "PEPE/USDT",
    "WIF/USDT",
    "BONK/USDT",
    "FLOKI/USDT",
    "BOME/USDT",
    "NEIRO/USDT",
    "MEW/USDT",
    "POPCAT/USDT"
]

def scan_live_market():
    print("=" * 80)
    print("🏹 MEME HUNTER: ESCÁNER EN VIVO DE CAPITULACIÓN & MICROESTRUCTURA (v7.6.1)")
    print("   Estrategia: MemeHunter_ApexOmegaAlpha | Timeframe: 1h | Exchange: Binance")
    print("=" * 80)

    if ccxt is None:
        print("❌ Error: Librería ccxt no disponible.")
        return

    exchange = ccxt.binance({
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })

    strategy = MemeHunter_ApexOmegaAlpha()
    results = []

    print(f"\nConsultando velas 1h recientes para los {len(PAIRS_SPOT)} pares líderes...")

    for pair in PAIRS_SPOT:
        try:
            ohlcv = exchange.fetch_ohlcv(pair, timeframe="1h", limit=60)
            if not ohlcv or len(ohlcv) < 30:
                continue

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            
            df = strategy.populate_indicators(df, {"pair": pair})
            df = strategy.populate_entry_trend(df, {"pair": pair})

            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]

            price = last_row["close"]
            drop = last_row.get("drop_from_recent_high", 0.0) * 100.0
            rsi = last_row.get("rsi", 50.0)
            vol_ratio = last_row.get("vol_ratio", 1.0)
            z_score = last_row.get("z_score_dist", 0.0)
            
            enter_long = int(last_row.get("enter_long", 0))
            enter_tag = str(last_row.get("enter_tag", ""))
            
            # Chequear también si la vela previa disparó entrada
            if enter_long == 0 and int(prev_row.get("enter_long", 0)) == 1:
                enter_long = 1
                enter_tag = str(prev_row.get("enter_tag", "")) + " (Vela Previa)"

            if enter_long == 1:
                alert_text = (
                    f"🚨 *MEME HUNTER: DISPARO ACTIVO*\n"
                    f"• *Par:* `{pair}`\n"
                    f"• *Señal:* `{enter_tag}`\n"
                    f"• *Precio:* `${price:.6f}`\n"
                    f"• *Caída 16h:* `{drop:.2f}%`\n"
                    f"• *RSI:* `{rsi:.1f}` | *Vol/SMA20:* `{vol_ratio:.2f}x`\n"
                    f"• *Z-Score:* `{z_score:.2f}`\n"
                    f"🎯 *Take Profit:* +3.5% (4h) / +6.0% | *Stoploss:* -3.0%"
                )
                send_telegram_alert(alert_text)

            status = "🟢 DISPARO ACTIVO" if enter_long == 1 else ("🟡 EN ZONA DE PÁNICO" if rsi < 30 or drop < -10 else "⚪ NEUTRAL")

            results.append({
                "pair": pair,
                "price": price,
                "drop_pct": drop,
                "rsi": rsi,
                "vol_ratio": vol_ratio,
                "z_score": z_score,
                "status": status,
                "tag": enter_tag
            })

        except Exception as e:
            # En caso de que algún par no tenga formato estándar en spot
            continue

    print("-" * 80)
    print(f"{'Par':<12} {'Precio':<12} {'Caída 16h':<10} {'RSI (14)':<9} {'Vol/SMA20':<10} {'Z-Score':<8} {'Estado'}")
    print("-" * 80)

    for r in results:
        print(f"{r['pair']:<12} ${r['price']:<11.6f} {r['drop_pct']:>6.2f}%    {r['rsi']:>5.1f}     {r['vol_ratio']:>5.2f}x      {r['z_score']:>6.2f}   {r['status']}")
        if r['tag']:
            print(f"   └──> Señal Detectada: [{r['tag']}]")

    print("=" * 80)
    print("💡 Interpretación Operativa:")
    print(" • Si 'DISPARO ACTIVO': Entrada Limit inmediata al Bid con gestión de riesgo Half-Kelly.")
    print(" • Si 'EN ZONA DE PÁNICO': Monitorear la vela actual para confirmación de giro verde.")
    print("=" * 80)

if __name__ == "__main__":
    scan_live_market()
