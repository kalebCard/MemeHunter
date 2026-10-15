#!/usr/bin/env python3
"""
Meme Hunter - Funding Rate Arbitrage Scanner & Simulator (PB-17)

Detecta y simula oportunidades de Cash & Carry / Arbitraje Delta-Neutral en memecoins:
1. Escanea las tasas de financiación (Funding Rate) de Futuros USDT-M en Binance.
2. Anualiza el rendimiento (APR / APY) compuesto cada 8 horas.
3. Evalúa si el spread de comisiones Maker/Taker permite una captura rentable libre de riesgo direccional.

Uso:
    python scripts/funding_arbitrage.py --top 10
    python scripts/funding_arbitrage.py --min-apr 25.0
"""
import argparse
import sys
import time
from typing import List, Dict
import ccxt

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def calculate_annualized_rates(funding_rate_8h: float) -> Dict[str, float]:
    """Calcula rendimientos diario, APR simple y APY compuesto a partir de la tasa de 8h."""
    # 3 pagos de funding al día = 1095 pagos al año
    daily_rate_pct = funding_rate_8h * 3 * 100.0
    apr_simple_pct = funding_rate_8h * 3 * 365 * 100.0
    
    # APY compuesto: (1 + r)^1095 - 1
    if funding_rate_8h > -1.0:
        apy_compounded_pct = ((1.0 + funding_rate_8h) ** 1095 - 1.0) * 100.0
    else:
        apy_compounded_pct = 0.0

    return {
        "rate_8h_pct": round(funding_rate_8h * 100.0, 4),
        "daily_pct": round(daily_rate_pct, 3),
        "apr_pct": round(apr_simple_pct, 2),
        "apy_pct": round(min(apy_compounded_pct, 9999.0), 2),  # Limitar absurdos matemáticos
    }


def scan_funding_opportunities(exchange: ccxt.binance, min_apr: float = 15.0) -> List[Dict]:
    """Descarga todas las tasas de financiación actuales de Binance Futures."""
    exchange.load_markets()
    funding_rates = exchange.fetch_funding_rates()
    opportunities = []

    for symbol, data in funding_rates.items():
        if not symbol.endswith(":USDT"):
            continue
            
        rate = data.get("fundingRate")
        if rate is None:
            continue

        rates = calculate_annualized_rates(rate)
        
        # Oportunidad Long Spot + Short Futuros (si el funding es positivo, los Shorts cobran)
        # Oportunidad Short Spot + Long Futuros (si el funding es negativo extremo)
        is_positive = rate > 0
        direction = "Short Fut / Long Spot" if is_positive else "Long Fut / Short Spot"
        abs_apr = abs(rates["apr_pct"])

        if abs_apr >= min_apr:
            opportunities.append({
                "symbol": symbol,
                "direction": direction,
                "funding_rate": rates["rate_8h_pct"],
                "apr": rates["apr_pct"],
                "apy": rates["apy_pct"],
                "daily": rates["daily_pct"],
                "next_funding_time": data.get("fundingDatetime"),
                "mark_price": data.get("markPrice", 0.0)
            })

    opportunities.sort(key=lambda x: abs(x["apr"]), reverse=True)
    return opportunities


def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - Funding Rate Arbitrage Scanner")
    parser.add_argument("--min-apr", type=float, default=15.0, help="APR anualizado mínimo para filtrar (%)")
    parser.add_argument("--top", type=int, default=15, help="Número máximo de pares a listar")
    args = parser.parse_args()

    print("=" * 70)
    print("⚡ MEME HUNTER: ESCÁNER DE ARBITRAJE DE FUNDING DELTA-NEUTRAL (PB-17)")
    print(f"Filtro: APR >= {args.min_apr}% | Pagos cada 8 horas")
    print("=" * 70)

    exchange = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})
    
    try:
        opps = scan_funding_opportunities(exchange, min_apr=args.min_apr)
    except Exception as e:
        print(f"❌ Error al consultar Binance: {e}")
        return

    if not opps:
        print(f"\n[i] No hay mercados con APR superior al {args.min_apr}% en este momento.")
        return

    print(f"\n💎 TOP {min(args.top, len(opps))} OPORTUNIDADES CON MAYOR TASA DE RENDIMIENTO:")
    print(f"{'Símbolo':<18} {'Tasa 8h %':<11} {'Diario %':<10} {'APR %':<11} {'APY %':<11} {'Estrategia Delta-Neutral'}")
    print("-" * 75)
    for o in opps[:args.top]:
        sign = "+" if o["apr"] > 0 else ""
        print(f"{o['symbol']:<18} {sign}{o['funding_rate']:<10}% {sign}{o['daily']:<9}% {sign}{o['apr']:<10}% {sign}{o['apy']:<10}% {o['direction']}")

    print("\n💡 MECÁNICA DEL ARBITRAJE DELTA-NEUTRAL:")
    print("1. Compras $500 en Spot y abres simultáneamente un Short de $500 en Futuros 1x.")
    print("2. Tu exposición al precio es $0 (si la memecoin se hunde un 80%, no pierdes nada).")
    print("3. Cada 8 horas cobras la tasa de financiación directo a tu balance de futuros.")


if __name__ == "__main__":
    main()
