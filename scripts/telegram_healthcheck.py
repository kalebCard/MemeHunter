"""
Meme Hunter - Telegram Bot Verification Script
Checks if the Telegram Bot Token and Chat ID are valid, sends a test ping,
and verifies permissions.
"""

import sys
import os
import urllib.request
import urllib.parse
import json
from pathlib import Path

def test_telegram(token: str, chat_id: str):
    print("[*] Verificando credenciales de Telegram Bot...")
    
    # 1. getMe
    get_me_url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        req = urllib.request.Request(get_me_url, headers={"User-Agent": "MemeHunterBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode())
            if not res_data.get("ok"):
                print("[-] Error de autenticación: Token de Telegram no válido.")
                return False
            bot_info = res_data.get("result", {})
            print(f"[+] Bot conectado exitosamente: @{bot_info.get('username')} ({bot_info.get('first_name')})")
    except Exception as e:
        print(f"[-] Error al contactar api.telegram.org: {e}")
        return False

    # 2. sendMessage Test
    send_msg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🛡️ *Meme Hunter Live* - Verificación de Notificaciones Exitosa.\nEl sistema de alertas en tiempo real está listo para operar.",
        "parse_mode": "Markdown"
    }
    try:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(send_msg_url, data=data, headers={"User-Agent": "MemeHunterBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode())
            if res_data.get("ok"):
                print(f"[+] Mensaje de prueba enviado exitosamente al Chat ID: {chat_id}")
                return True
            else:
                print(f"[-] Error al enviar mensaje: {res_data}")
                return False
    except Exception as e:
        print(f"[-] Error al enviar mensaje al Chat ID {chat_id}: {e}")
        print("[!] Asegúrate de haber iniciado el bot en Telegram enviándole un mensaje primero (/start).")
        return False

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Read from environment or .env
    token = os.environ.get("FREQTRADE__TELEGRAM__TOKEN")
    chat_id = os.environ.get("FREQTRADE__TELEGRAM__CHAT_ID")
    
    if not token or not chat_id:
        # Check .env file
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("FREQTRADE__TELEGRAM__TOKEN="):
                    token = line.split("=", 1)[1].strip()
                elif line.startswith("FREQTRADE__TELEGRAM__CHAT_ID="):
                    chat_id = line.split("=", 1)[1].strip()
    
    if not token or not chat_id:
        print("[!] No se encontraron variables de Telegram configuradas.")
        print("    Configura en .env:")
        print("    FREQTRADE__TELEGRAM__ENABLED=true")
        print("    FREQTRADE__TELEGRAM__TOKEN=<tu_bot_token>")
        print("    FREQTRADE__TELEGRAM__CHAT_ID=<tu_chat_id>")
        return 1
    
    success = test_telegram(token, chat_id)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
