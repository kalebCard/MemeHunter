"""
telegram_messenger.py - Notificador Ejecutivo en Telegram para Hermes (Sprint 52: PB-187).

Permite a Hermes comunicarse en primera persona como Alter Ego del operador:
- Envía reportes de cambio de régimen
- Notifica rebalanceos de capital entre bots
- Emite alertas de riesgo / circuit breaker
"""

import os
import logging
from typing import Optional, Dict, Any

from client.telegram_ai_copilot import TelegramBotClient
from portfolio.secrets_vault import get_secret

logger = logging.getLogger("HermesTelegramMessenger")


class HermesTelegramMessenger:
    """
    Emisor de reportes ejecutivos de Hermes hacia Telegram.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        self.token = (
            token or 
            get_secret("FREQTRADE__TELEGRAM__TOKEN") or 
            get_secret("TELEGRAM_BOT_TOKEN") or 
            os.getenv("FREQTRADE__TELEGRAM__TOKEN") or 
            os.getenv("TELEGRAM_BOT_TOKEN") or ""
        )
        self.chat_id = (
            chat_id or 
            get_secret("FREQTRADE__TELEGRAM__CHAT_ID") or 
            get_secret("ALLOWED_CHAT_ID") or 
            os.getenv("FREQTRADE__TELEGRAM__CHAT_ID") or 
            os.getenv("ALLOWED_CHAT_ID") or ""
        )
        self.client = TelegramBotClient(self.token) if self.token else None

    def send_executive_report(self, text: str) -> Dict[str, Any]:
        """Envía el informe ejecutivo formateado en Markdown a Telegram."""
        if not self.client or not self.chat_id:
            logger.info("Telegram no configurado o credenciales ausentes en Hermes. Reporte emitido solo en consola.")
            return {"ok": False, "reason": "no_credentials"}

        res = self.client.send_message(chat_id=self.chat_id, text=text, parse_mode="Markdown")
        if not res.get("ok"):
            # Fallback sin parse_mode si falla el formato Markdown
            res = self.client.send_message(chat_id=self.chat_id, text=text, parse_mode="")
        return res
