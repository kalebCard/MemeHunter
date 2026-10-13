#!/usr/bin/env python3
"""
Meme Hunter - Order Book & Flow Imbalance (OFI) Analyzer (PB-18)

Mide la microestructura de nivel 2 (Order Book) en tiempo real en Binance Futuros:
1. Bid/Ask Depth Imbalance: Proporción de liquidez disponible en los primeros N niveles.
2. Micro-Price & Spread Pressure: Determina si el precio de equilibrio ponderado por volumen
   está empujando hacia arriba o hacia abajo.
3. Señal de Ejecución Maker: Indica si colocar una orden Maker pasiva tiene alta probabilidad
   de ser ejecutada a favor sin sufrir adverse selection (selección adversa).

Uso:
    python scripts/order_flow_imbalance.py --symbol DOGE/USDT:USDT --levels 10
    python scripts/order_flow_imbalance.py --symbol 1000PEPE/USDT:USDT --stream
"""
import argparse
import sys
import time
from typing import Dict, List
import ccxt

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def calculate_order_book_metrics(order_book: Dict, levels: int = 10) -> Dict:
    """Calcula el desequilibrio de liquidez (Imbalance), Micro-Price y Spread."""
    bids: List[List[float]] = order_book.get("bids", [])[:levels]
    asks: List[List[float]] = order_book.get("asks", [])[:levels]

    if not bids or not asks:
        return {}

    best_bid_price, best_bid_vol = bids[0][0], bids[0][1]
    best_ask_price, best_ask_vol = asks[0][0], asks[0][1]

    spread = best_ask_price - best_bid_price
    spread_pct = (spread / best_bid_price) * 100.0 if best_bid_price > 0 else 0.0

    total_bid_depth = sum(qty for _, qty in bids)
    total_ask_depth = sum(qty for _, qty in asks)
    total_depth = total_bid_depth + total_ask_depth

    # Imbalance: oscila entre -1.0 (100% presión vendedora) y +1.0 (100% presión compradora)
    imbalance = (total_bid_depth - total_ask_depth) / total_depth if total_depth > 0 else 0.0

    # Micro-price: precio medio ponderado por el volumen opuesto en el nivel 1
    # MicroPrice = (AskVol * BidPrice + BidVol * AskPrice) / (BidVol + AskVol)
    l1_vol = best_bid_vol + best_ask_vol
    if l1_vol > 0:
        micro_price = (best_ask_vol * best_bid_price + best_bid_vol * best_ask_price) / l1_vol
    else:
        micro_price = (best_bid_price + best_ask_price) / 2.0

    # Predicción de presión inmediata
    mid_price = (best_bid_price + best_ask_price) / 2.0
    price_pressure = "ALCISTA (Presión compradora)" if micro_price > mid_price else "BAJISTA (Presión vendedora)"

    # Recomendación de orden Maker
    if imbalance > 0.20:
        maker_action = "FAVORABLE LONG (Colocar Maker en Best Bid)"
    elif imbalance < -0.20:
        maker_action = "FAVORABLE SHORT (Colocar Maker en Best Ask)"
    else:
        maker_action = "NEUTRAL (Libro balanceado)"

    return {
        "best_bid": best_bid_price,
        "best_ask": best_ask_price,
        "mid_price": mid_price,
        "micro_price": micro_price,
        "spread_pct": round(spread_pct, 4),
        "total_bid_depth": round(total_bid_depth, 2),
        "total_ask_depth": round(total_ask_depth, 2),
        "imbalance": round(imbalance, 3),
        "pressure": price_pressure,
        "maker_recommendation": maker_action,
    }


def analyze_symbol_order_flow(exchange: ccxt.binance, symbol: str, levels: int = 10) -> Dict:
    order_book = exchange.fetch_order_book(symbol, limit=levels)
    return calculate_order_book_metrics(order_book, levels=levels)


def main():
    parser = argparse.ArgumentParser(description="Meme Hunter - Order Book & Flow Imbalance (PB-18)")
    parser.add_argument("--symbol", type=str, default="1000PEPE/USDT:USDT", help="Par de futuros a analizar")
    parser.add_argument("--levels", type=int, default=10, help="Profundidad de niveles del libro de órdenes")
    parser.add_argument("--stream", action="store_true", help="Monitorizar continuamente cada segundo")
    args = parser.parse_args()

    print("=" * 70)
    print(f"📊 MEME HUNTER: MICROESTRUCTURA Y ORDER FLOW IMBALANCE (PB-18)")
    print(f"Símbolo: {args.symbol} | Niveles analizados: {args.levels}")
    print("=" * 70)

    exchange = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})

    try:
        while True:
            metrics = analyze_symbol_order_flow(exchange, args.symbol, levels=args.levels)
            if not metrics:
                print("❌ No se pudo obtener el libro de órdenes.")
                break

            print(f"\n[Microestructura {args.symbol}]")
            print(f"• Spread: {metrics['spread_pct']:.4f}% | Mid: {metrics['mid_price']} | Micro-Price: {metrics['micro_price']:.6f}")
            print(f"• Liquidez Bids (Compras): {metrics['total_bid_depth']} | Liquidez Asks (Ventas): {metrics['total_ask_depth']}")
            print(f"• Order Book Imbalance: {metrics['imbalance']:+.3f}  [-1.0 a +1.0]")
            print(f"• Presión Inmediata: {metrics['pressure']}")
            print(f"• Acción Maker: {metrics['maker_recommendation']}")

            if not args.stream:
                break
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[i] Monitorización detenida por el usuario.")
    except Exception as e:
        print(f"❌ Error durante el análisis: {e}")


if __name__ == "__main__":
    main()
