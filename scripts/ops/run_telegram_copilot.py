#!/usr/bin/env python3
"""
run_telegram_copilot.py - Entrypoint y Centinela del Copilot Cuantitativo en Telegram.

Uso:
    python scripts/ops/run_telegram_copilot.py --poll     # Inicia el bucle de polling continuo
    python scripts/ops/run_telegram_copilot.py --test     # Envía un ping de prueba y audita credenciales
    python scripts/ops/run_telegram_copilot.py --query "Mensaje de prueba" # Ejecuta una consulta directa al AI Copilot
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Inyectar el directorio raíz al path de importación de Python
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Garantizar compatibilidad con consola Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from client.telegram_ai_copilot import TelegramAiCopilotService, TelegramBotClient


def main():
    parser = argparse.ArgumentParser(description="Meme Hunter — AI Telegram Copilot Runner")
    parser.add_argument("--poll", action="store_true", help="Inicia el bucle de polling continuo en Telegram")
    parser.add_argument("--test", action="store_true", help="Verifica la conexión con Telegram y Freqtrade")
    parser.add_argument("--query", type=str, default="", help="Prueba una consulta directa de IA con telemetría viva")
    args = parser.parse_args()

    copilot = TelegramAiCopilotService()

    if args.query:
        print("🧠 Probando inferencia del Copilot de IA...")
        reply = copilot.dispatch_command(args.query, chat_id=copilot.allowed_chat_id or "local")
        print("\n" + "=" * 60)
        print("RESPUESTA DEL AI COPILOT:")
        print("=" * 60)
        print(reply)
        return 0

    if args.test or not args.poll:
        print("=" * 60)
        print("🤖 MEME HUNTER — AUDITORÍA DEL COPILOT DE TELEGRAM")
        print("=" * 60)
        print(f"• Token Configurado     : {'✅ Sí' if copilot.is_configured() else '❌ No (Configurar FREQTRADE__TELEGRAM__TOKEN)'}")
        print(f"• Chat ID Autorizado    : {copilot.allowed_chat_id or 'No fijado (permisivo en pruebas)'}")

        ping_res = copilot.ft_client.ping()
        print(f"• API Freqtrade (:8081) : {'✅ En Línea' if ping_res.get('status') == 'ok' else '❌ Desconectada'}")

        if copilot.is_configured() and copilot.tg_client:
            me_res = copilot.tg_client.get_me()
            if me_res.get("ok"):
                bot_user = me_res.get("result", {}).get("username", "N/A")
                print(f"• Identidad Telegram Bot: @{bot_user} (✅ Conectado)")
            else:
                print(f"• Fallo de Autenticación Telegram: {me_res.get('description')}")

        if not args.poll:
            print("\nPara iniciar el servicio en escucha activa:")
            print("  python scripts/ops/run_telegram_copilot.py --poll")
            return 0

    if args.poll:
        if not copilot.is_configured():
            print("❌ Error: No se puede iniciar el polling sin un token de Telegram válido.")
            print("Exporta FREQTRADE__TELEGRAM__TOKEN o configúralo en tu archivo .env")
            return 1

        print("🚀 Copilot de IA en Telegram activo y escuchando mensajes...", flush=True)
        print("Presiona Ctrl+C para detener.", flush=True)
        try:
            while True:
                copilot.poll_once()
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n⏹️ Servicio del Copilot de Telegram detenido.", flush=True)
            return 0


if __name__ == "__main__":
    sys.exit(main())
