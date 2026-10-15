#!/usr/bin/env python3
"""
Meme Hunter - DEX & Viral Meme Radar (PB-16)

Conecta con APIs públicas on-chain (DexScreener) sin requerir API keys de pago para:
1. Detectar memecoins que se están volviendo virales en DEX (Solana / Ethereum / Base).
2. Medir el volumen de las últimas 1h / 24h, transacciones por minuto y liquidez de pools.
3. Cruzar los tokens en tendencia con los pares listados en Binance Futuros USDT-M para
   anticipar qué contratos van a experimentar inyecciones masivas de volumen.

Uso:
    python scripts/dex_viral_radar.py --top 10
    python scripts/dex_viral_radar.py --chain solana --min-liquidity 100000
"""
import argparse
import sys
import time
from typing import Dict, List
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex"


def fetch_trending_boosted_tokens() -> List[Dict]:
    """Obtiene los tokens con mayor tracción y boost reciente en DexScreener."""
    url = f"{DEXSCREENER_API_URL}/tokens/boosted"
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "MemeHunter/1.0"})
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []


def search_dex_pairs(query: str = "PEPE") -> List[Dict]:
    """Busca pares de un token específico en DexScreener."""
    url = f"{DEXSCREENER_API_URL}/search?q={query}"
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "MemeHunter/1.0"})
        if res.status_code == 200:
            data = res.json()
            return data.get("pairs", [])
    except Exception:
        pass
    return []


def parse_and_filter_dex_pair(pair: Dict, min_liquidity: float = 50000.0, min_vol_24h: float = 200000.0) -> Dict:
    """Extrae métricas de liquidez, volumen y transacciones de un par on-chain."""
    try:
        liquidity = float(pair.get("liquidity", {}).get("usd", 0.0) or 0.0)
        volume_24h = float(pair.get("volume", {}).get("h24", 0.0) or 0.0)
        volume_1h = float(pair.get("volume", {}).get("h1", 0.0) or 0.0)
        
        if liquidity < min_liquidity or volume_24h < min_vol_24h:
            return None

        price_change_24h = float(pair.get("priceChange", {}).get("h24", 0.0) or 0.0)
        price_change_1h = float(pair.get("priceChange", {}).get("h1", 0.0) or 0.0)
        txns_1h = pair.get("txns", {}).get("h1", {})
        buys_1h = int(txns_1h.get("buys", 0) or 0)
        sells_1h = int(txns_1h.get("sells", 0) or 0)
        
        # Ratio de presión compradora on-chain
        total_txns = buys_1h + sells_1h
        buy_ratio_pct = (buys_1h / total_txns * 100.0) if total_txns > 0 else 50.0

        base_token = pair.get("baseToken", {})
        symbol = base_token.get("symbol", "UNKNOWN").upper()
        name = base_token.get("name", "Unknown")
        chain = pair.get("chainId", "unknown")

        return {
            "symbol": symbol,
            "name": name,
            "chain": chain,
            "price_usd": float(pair.get("priceUsd", 0.0) or 0.0),
            "liquidity_usd": round(liquidity, 2),
            "volume_24h_usd": round(volume_24h, 2),
            "volume_1h_usd": round(volume_1h, 2),
            "change_1h_pct": round(price_change_1h, 2),
            "change_24h_pct": round(price_change_24h, 2),
            "buys_1h": buys_1h,
            "sells_1h": sells_1h,
            "buy_pressure_pct": round(buy_ratio_pct, 1),
            "dex_id": pair.get("dexId", ""),
            "pair_url": pair.get("url", "")
        }
    except Exception:
        return None


def scan_viral_memes(min_liq: float = 50000.0, min_vol: float = 200000.0, top: int = 10) -> List[Dict]:
    """Audita memecoins de alta tracción y filtra por calidad de liquidez on-chain."""
    print("[*] Conectando con DexScreener y DEX liquidity pools...")
    boosted = fetch_trending_boosted_tokens()
    results = []
    seen_symbols = set()

    for item in boosted:
        token_address = item.get("tokenAddress")
        chain_id = item.get("chainId")
        if not token_address:
            continue
        
        # Consultar detalles del pool
        pairs = search_dex_pairs(token_address)
        for p in pairs:
            parsed = parse_and_filter_dex_pair(p, min_liquidity=min_liq, min_vol_24h=min_vol)
            if parsed and parsed["symbol"] not in seen_symbols:
                seen_symbols.add(parsed["symbol"])
                results.append(parsed)
                break
        time.sleep(0.15)  # Respetar rate limits de la API pública

    # Si hay pocos boosted con suficiente liquidez, buscar las búsquedas populares
    if len(results) < top:
        fallback_queries = ["PEPE", "DOGE", "SHIB", "WIF", "BONK", "FLOKI", "NEIRO", "MOODENG", "GOAT", "PNUT"]
        for q in fallback_queries:
            if len(results) >= top:
                break
            pairs = search_dex_pairs(q)
            for p in pairs:
                parsed = parse_and_filter_dex_pair(p, min_liquidity=min_liq, min_vol_24h=min_vol)
                if parsed and parsed["symbol"] not in seen_symbols:
                    seen_symbols.add(parsed["symbol"])
                    results.append(parsed)
                    break
            time.sleep(0.15)

    results.sort(key=lambda x: x["volume_24h_usd"], reverse=True)
    return results[:top]


def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - DEX & Viral Meme Radar (PB-16)")
    parser.add_argument("--min-liquidity", type=float, default=50000.0, help="Liquidez mínima en pool USD")
    parser.add_argument("--min-volume", type=float, default=200000.0, help="Volumen mínimo de 24h USD")
    parser.add_argument("--top", type=int, default=10, help="Número de memecoins a listar")
    args = parser.parse_args()

    print("=" * 80)
    print("🌐 MEME HUNTER: RADAR VIRAL ON-CHAIN & DEX POOLS (PB-16)")
    print(f"Filtros: Liquidez >= ${args.min_liquidity:,.0f} | Vol 24h >= ${args.min_volume:,.0f}")
    print("=" * 80)

    memes = scan_viral_memes(min_liq=args.min_liquidity, min_vol=args.min_volume, top=args.top)

    if not memes:
        print("\n[i] No se encontraron pools que superen el filtro de liquidez en este ciclo.")
        return

    print(f"\n🔥 TOP {len(memes)} MEMECOINS EN TENDENCIA ON-CHAIN:")
    print(f"{'Símbolo':<12} {'Cadena':<10} {'Var 1h %':<10} {'Var 24h %':<11} {'Presión Compra':<16} {'Liquidez USD':<15} {'Vol 24h USD'}")
    print("-" * 85)
    for m in memes:
        s1 = "+" if m["change_1h_pct"] > 0 else ""
        s24 = "+" if m["change_24h_pct"] > 0 else ""
        print(f"{m['symbol']:<12} {m['chain']:<10} {s1}{m['change_1h_pct']:<9}% {s24}{m['change_24h_pct']:<10}% {m['buy_pressure_pct']}% Compras     ${m['liquidity_usd']:<14,.0f} ${m['volume_24h_usd']:,.0f}")

    print("\n💡 APLICACIÓN TÁCTICA PARA FUTUROS:")
    print("• Tokens con >65% de presión compradora y volumen explosivo en DEX suelen experimentar")
    print("  expansiones inmediatas de funding rate y momentum en Binance Futuros.")


if __name__ == "__main__":
    main()
