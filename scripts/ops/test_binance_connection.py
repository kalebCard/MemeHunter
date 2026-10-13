#!/usr/bin/env python3
"""
Test de Conexión Oficial con Binance Spot (DAS v3.1 §5)

Verifica:
1. Conectividad y latencia con api.binance.com.
2. Descarga de Order Book y Tickers en tiempo real (modo público / Dry-Run).
3. Autenticación, saldo disponible y permisos de cuenta (si hay API Keys en .env).
"""
import os
import sys
import time
import ccxt
from freqtrade.configuration import Configuration


def main():
    print("=" * 60)
    print("🔍 INICIANDO DIAGNÓSTICO DE CONEXIÓN CON BINANCE SPOT")
    print("=" * 60)

    # 1. Cargar configuración y variables de entorno FREQTRADE__*
    config_file = "user_data/config_live.json"
    if not os.path.exists(config_file):
        print(f"❌ Error: {config_file} no encontrado.")
        sys.exit(1)

    try:
        config = Configuration.from_files([config_file])
    except Exception as e:
        print(f"❌ Error al cargar configuración: {e}")
        sys.exit(1)

    exchange_config = config.get("exchange", {})
    api_key = exchange_config.get("key", "").strip()
    api_secret = exchange_config.get("secret", "").strip()
    dry_run = config.get("dry_run", True)

    print(f"• Exchange: {exchange_config.get('name', 'binance').upper()}")
    print(f"• Modo configurado: {'DRY-RUN (Simulación sin riesgo)' if dry_run else '⚠️ PRODUCCIÓN REAL (Dinero Real)'}")

    # 2. Inicializar cliente CCXT
    exchange_params = {
        "timeout": 10000,
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
        },
    }

    if api_key and api_secret:
        exchange_params["apiKey"] = api_key
        exchange_params["secret"] = api_secret
        print("• Credenciales detectadas: ✅ API Key y Secret configuradas")
    else:
        print("• Credenciales detectadas: ℹ️ Modo Público (Sin claves privadas)")

    client = ccxt.binance(exchange_params)

    # 3. Test de Conectividad y Latencia
    print("\n[1/3] Probando latencia de red con Binance...")
    t0 = time.time()
    try:
        server_time = client.fetch_time()
        latency_ms = (time.time() - t0) * 1000
        print(f"✅ Conexión exitosa. Latencia: {latency_ms:.1f} ms (Server Time UTC: {server_time})")
    except Exception as e:
        print(f"❌ Error al conectar con Binance: {e}")
        sys.exit(1)

    # 4. Test de Datos de Mercado en Vivo
    print("\n[2/3] Verificando Order Book y Tickers en tiempo real...")
    try:
        ticker = client.fetch_ticker("BTC/USDT")
        order_book = client.fetch_order_book("BTC/USDT", limit=5)
        best_bid = order_book["bids"][0][0] if order_book["bids"] else 0
        best_ask = order_book["asks"][0][0] if order_book["asks"] else 0
        spread_pct = ((best_ask - best_bid) / best_bid) * 100 if best_bid > 0 else 0

        print(f"• BTC/USDT Último Precio: ${ticker.get('last', 0):,.2f}")
        print(f"• Mejor Bid: ${best_bid:,.2f} | Mejor Ask: ${best_ask:,.2f}")
        print(f"• Spread Bid-Ask: {spread_pct:.4f}%")
        print("✅ Libro de órdenes y cotizaciones en vivo recibidos correctamente.")
    except Exception as e:
        print(f"❌ Error obteniendo datos de mercado: {e}")
        sys.exit(1)

    # 5. Test de Cuenta Privada (si hay claves)
    print("\n[3/3] Verificando estado de cuenta...")
    if api_key and api_secret:
        try:
            balance = client.fetch_balance()
            usdt_free = balance.get("USDT", {}).get("free", 0.0)
            usdt_total = balance.get("USDT", {}).get("total", 0.0)
            print("✅ Autenticación con Binance APROBADA.")
            print(f"• Saldo USDT Libre: ${usdt_free:,.2f}")
            print(f"• Saldo USDT Total: ${usdt_total:,.2f}")

            # Mostrar otras monedas con saldo positivo
            non_zero = {k: v["total"] for k, v in balance.items() if isinstance(v, dict) and v.get("total", 0) > 0}
            if non_zero:
                print(f"• Activos con saldo: {', '.join([f'{k}: {v:.4f}' for k, v in non_zero.items()])}")
        except Exception as e:
            print(f"❌ Fallo al autenticar con Binance API: {e}")
            print("⚠️ Revisa que tu API Key y Secret en el archivo .env sean correctas y que la IP tenga permiso.")
            sys.exit(1)
    else:
        print("ℹ️ No hay claves privadas en .env. El sistema operará en Dry-Run conectado al mercado en vivo.")
        print("💡 Para operar con fondos reales, edita el archivo .env con tus claves de Binance.")

    print("\n" + "=" * 60)
    print("🚀 EL SISTEMA ESTÁ LISTO PARA CONECTAR Y OPERAR CON BINANCE")
    print("=" * 60)


if __name__ == "__main__":
    main()
