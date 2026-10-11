#!/usr/bin/env python3
"""
Meme Hunter - Meme Sentinel (PB-15)
Detector temprano de anomalías de volumen y aceleración de volatilidad en memecoins.

Analiza en tiempo real los mercados de futuros USDT-M de Binance buscando:
1. Spikes de volumen relativo (RVOL) en velas cortas (1m / 5m) frente a la media.
2. Expansión explosiva de rango verdadero (ATR / Price Velocity).
3. Ranking de candidatos ordenados por puntuación de momentum anómalo.

Uso:
    python scripts/meme_sentinel.py --top 10
    python scripts/meme_sentinel.py --min-volume-spike 3.0 --timeframe 5m
"""
import argparse
import sys
import time
from typing import List, Dict
import ccxt
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_usdt_futures_markets(exchange: ccxt.binance) -> List[str]:
    """Obtiene todos los pares activos de Futuros USDT-M."""
    exchange.load_markets()
    symbols = []
    for symbol, market in exchange.markets.items():
        if (
            market.get("linear")
            and market.get("quote") == "USDT"
            and market.get("active")
            and not symbol.startswith("BTC")  # Excluir majors de análisis de memes
            and not symbol.startswith("ETH")
        ):
            symbols.append(symbol)
    return symbols


def analyze_symbol(exchange: ccxt.binance, symbol: str, timeframe: str = "5m", limit: int = 30, min_24h_volume_usdt: float = 1000000.0) -> Dict:
    """Calcula RVOL y expansión de rango descartando tokens con volumen 24h insuficiente."""
    try:
        # 1. Filtro de liquidez 24h: evitar trampas ilíquidas donde no se puede salir
        ticker = exchange.fetch_ticker(symbol)
        quote_vol_24h = ticker.get("quoteVolume", 0.0) or 0.0
        if quote_vol_24h < min_24h_volume_usdt:
            return None

        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if len(ohlcv) < 15:
            return None
        
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        # Última vela cerrada vs velas previas
        current_candle = df.iloc[-1]
        past_candles = df.iloc[:-1]
        
        avg_volume = past_candles["volume"].mean()
        if avg_volume <= 0:
            return None
            
        rvol = current_candle["volume"] / avg_volume
        
        # Cambio porcentual de precio en la vela actual
        price_change_pct = ((current_candle["close"] - current_candle["open"]) / current_candle["open"]) * 100.0
        
        # Rango de la vela (High - Low) relativo
        candle_range_pct = ((current_candle["high"] - current_candle["low"]) / current_candle["open"]) * 100.0
        
        score = rvol * abs(price_change_pct)
        
        return {
            "symbol": symbol,
            "rvol": round(rvol, 2),
            "price_change_pct": round(price_change_pct, 2),
            "range_pct": round(candle_range_pct, 2),
            "close": current_candle["close"],
            "volume_candle_usdt": round(current_candle["volume"] * current_candle["close"], 2),
            "volume_24h_usdt": round(quote_vol_24h, 2),
            "score": round(score, 2)
        }
    except Exception:
        return None


def scan_markets(min_spike: float = 2.5, timeframe: str = "5m", max_pairs: int = 40, min_24h_vol: float = 1000000.0) -> List[Dict]:
    exchange = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})
    symbols = get_usdt_futures_markets(exchange)
    
    # Priorizar tokens comúnmente asociados a memecoins y alta volatilidad
    meme_keywords = ["DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "BOME", "MEME", "POPCAT", "NEIRO", "TURBO", "1000"]
    priority_symbols = [s for s in symbols if any(k in s for k in meme_keywords)]
    other_symbols = [s for s in symbols if s not in priority_symbols]
    target_symbols = (priority_symbols + other_symbols)[:max_pairs]
    
    print(f"[*] Analizando {len(target_symbols)} mercados en Futuros ({timeframe}) | Filtro Vol 24h: >= ${min_24h_vol:,.0f}...")
    alerts = []
    
    for s in target_symbols:
        res = analyze_symbol(exchange, s, timeframe=timeframe, min_24h_volume_usdt=min_24h_vol)
        if res and res["rvol"] >= min_spike:
            alerts.append(res)
        time.sleep(exchange.rateLimit / 1000.0)  # Respetar rate limits
        
    alerts.sort(key=lambda x: x["score"], reverse=True)
    return alerts


def main():
    parser = argparse.ArgumentParser(description="Meme Sentinel - Detector Temprano de Anomalías")
    parser.add_argument("--min-volume-spike", type=float, default=2.0, help="Multiplicador de volumen mínimo (RVOL)")
    parser.add_argument("--min-volume-24h", type=float, default=1000000.0, help="Volumen mínimo de 24h en USDT para evitar trampas")
    parser.add_argument("--timeframe", type=str, default="5m", help="Timeframe de detección rápida (1m, 5m, 15m)")
    parser.add_argument("--top", type=int, default=10, help="Número de alertas a mostrar")
    args = parser.parse_args()

    print("=" * 75)
    print(f"🐕 MEME SENTINEL: ESCÁNER DE VOLUMEN Y EXPLOSIONES TEMPRANAS")
    print(f"Timeframe: {args.timeframe} | Filtro RVOL: >= {args.min_volume_spike}x | Vol 24h >= ${args.min_volume_24h:,.0f}")
    print("=" * 75)

    alerts = scan_markets(min_spike=args.min_volume_spike, timeframe=args.timeframe, min_24h_vol=args.min_volume_24h)

    if not alerts:
        print("\n[i] No se detectaron anomalías por encima del umbral en este ciclo.")
        return

    print(f"\n🔥 TOP {min(args.top, len(alerts))} MEMECOINS CON ACTIVIDAD INUSUAL Y ALTA LIQUIDEZ:")
    print(f"{'Símbolo':<18} {'RVOL':<8} {'Var %':<8} {'Rango %':<9} {'Vol 24h USDT':<15} {'Score'}")
    print("-" * 75)
    for a in alerts[:args.top]:
        sign = "+" if a["price_change_pct"] > 0 else ""
        print(f"{a['symbol']:<18} {a['rvol']:<7}x {sign}{a['price_change_pct']:<7}% {a['range_pct']:<8}% ${a['volume_24h_usdt']:<14,.0f} {a['score']}")


if __name__ == "__main__":
    main()
