#!/usr/bin/env python3
"""
Test de Conexión Oficial con Binance (Spot & Futures) (Meme Hunter v8.0)

Verifica:
1. Conectividad y latencia con api.binance.com y fapi.binance.com.
2. Descarga de Order Book y Tickers en tiempo real (público / Dry-Run).
3. Autenticación, saldo disponible y permisos de cuenta (si hay API Keys en .env).
"""
import os
import sys
import time
import json
from pathlib import Path
import ccxt

# Configurar encoding UTF-8 seguro para consolas de Windows
if sys.platform.startswith("win"):
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    root_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv(".env")
except ImportError:
    pass


def main():
    print("=" * 60)
    print("🔍 INICIANDO DIAGNÓSTICO DE CONEXIÓN CON BINANCE")
    print("=" * 60)

    # 1. Resolver API Keys desde variables de entorno (.env) o configuración
    api_key = (
        os.getenv("BINANCE_API_KEY", "").strip()
        or os.getenv("FREQTRADE__EXCHANGE__KEY", "").strip()
    )
    api_secret = (
        os.getenv("BINANCE_API_SECRET", "").strip()
        or os.getenv("FREQTRADE__EXCHANGE__SECRET", "").strip()
    )

    # Fallback: leer config_futures.json o config_live.json si están vacías en .env
    if not api_key:
        for cfg_name in ["user_data/config_futures.json", "user_data/config_live.json"]:
            if os.path.exists(cfg_name):
                try:
                    with open(cfg_name, "r", encoding="utf-8") as f:
                        cfg_data = json.load(f)
                    exch = cfg_data.get("exchange", {})
                    if exch.get("key"):
                        api_key = exch.get("key").strip()
                        api_secret = exch.get("secret", "").strip()
                        break
                except Exception:
                    pass

    dry_run_env = os.getenv("FREQTRADE__DRY_RUN", "true").lower()
    is_dry_run = dry_run_env in ("true", "1", "yes")

    print(f"• Exchange: BINANCE")
    print(f"• Modo configurado: {'DRY-RUN (Simulación sin riesgo de capital)' if is_dry_run else '⚠️ PRODUCCIÓN REAL (Dinero Real)'}")

    # 2. Inicializar cliente CCXT para Spot
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
        # Ocultar parte de la clave para mostrar en pantalla con seguridad
        masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
        print(f"• Credenciales detectadas: ✅ API Key configurada ({masked_key})")
    else:
        print("• Credenciales detectadas: ℹ️ Modo Público (Sin claves privadas en .env)")

    client = ccxt.binance(exchange_params)

    # 3. Test de Conectividad y Latencia de Red
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

    # 5. Test de Cuenta Privada y Saldos (si hay claves)
    print("\n[3/3] Verificando estado de cuenta y saldos...")
    if api_key and api_secret:
        try:
            balance = client.fetch_balance()
            usdt_free = balance.get("USDT", {}).get("free", 0.0)
            usdt_total = balance.get("USDT", {}).get("total", 0.0)
            print("✅ Autenticación con Binance APROBADA.")
            print(f"• Saldo USDT Libre (Spot): ${usdt_free:,.2f}")
            print(f"• Saldo USDT Total (Spot): ${usdt_total:,.2f}")

            # Mostrar otras monedas con saldo positivo
            non_zero = {k: v["total"] for k, v in balance.items() if isinstance(v, dict) and v.get("total", 0) > 0.0001}
            if non_zero:
                print(f"• Activos con saldo: {', '.join([f'{k}: {v:.4f}' for k, v in list(non_zero.items())[:5]])}")

            # Intentar verificar también Futuros si tiene permisos
            try:
                futures_client = ccxt.binance({
                    "timeout": 10000,
                    "enableRateLimit": True,
                    "apiKey": api_key,
                    "secret": api_secret,
                    "options": {"defaultType": "future"},
                })
                f_balance = futures_client.fetch_balance()
                f_usdt_free = f_balance.get("USDT", {}).get("free", 0.0)
                f_usdt_total = f_balance.get("USDT", {}).get("total", 0.0)
                print(f"• Saldo USDT Libre (Futuros USDT-M): ${f_usdt_free:,.2f}")
                print(f"• Saldo USDT Total (Futuros USDT-M): ${f_usdt_total:,.2f}")
                print("✅ Permisos de Binance Futures APROBADOS.")
            except Exception as fe:
                print(f"ℹ️ Verificación de Futuros: {fe} (Habilite permisos de Futuros si va a operar derivados)")

        except Exception as e:
            print(f"❌ Fallo al autenticar con Binance API: {e}")
            print("⚠️ Revisa que tu API Key y Secret en el archivo .env sean correctas y que la IP tenga permiso.")
            sys.exit(1)
    else:
        print("ℹ️ No hay claves privadas activas en .env. El sistema operará en Dry-Run conectado al mercado en vivo.")
        print("💡 Para operar con tus fondos, descomenta y coloca tus claves en el archivo .env.")

    print("\n" + "=" * 60)
    print("🚀 EL SISTEMA ESTÁ LISTO PARA CONECTAR Y OPERAR CON BINANCE")
    print("=" * 60)


if __name__ == "__main__":
    main()
