"""
telemetry_notifier.py - Telemetría y Alertas del Bucle Autónomo (Sprint 28: PB-98).

Provee despacho de alertas estructuradas y telemetría a través de:
1. Webhooks de Discord o Telegram (si están configurados).
2. Registro estructurado en SQLite WAL (`cycle_history`).
3. Auditoría en archivo append-only (`logs/autonomous_loop.jsonl`).
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from portfolio.db_schema import insert_cycle_history_db

logger = logging.getLogger("TelemetryNotifier")


class TelemetryNotifier:
    """
    Gestor de telemetría y alertas para eventos críticos de producción:
    - Promociones de factores validados por CPCV
    - Cuarentena de alphas en Alpha Decay
    - Rebalanceos y rotación de pesos HRP
    - Estado de Hot-Reload de Freqtrade
    """

    def __init__(
        self,
        discord_webhook_url: Optional[str] = None,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        log_jsonl_path: str = "logs/autonomous_loop.jsonl",
        db_path: str = "portfolio/alpha_factory.db"
    ):
        self.discord_webhook = discord_webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.tg_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.log_jsonl_path = log_jsonl_path
        self.db_path = db_path

    def notify_cycle_event(self, report_dict: Dict[str, Any]) -> None:
        """Registra el ciclo en SQLite WAL y despacha alertas remotas si hay cambios relevantes."""
        # 1. Registrar en SQLite WAL
        try:
            insert_cycle_history_db(report_dict, db_path=self.db_path)
        except Exception as e:
            logger.warning(f"No se pudo registrar historial de ciclo en SQLite: {e}")

        # 2. Append en logs JSONL
        try:
            os.makedirs(os.path.dirname(self.log_jsonl_path), exist_ok=True)
            with open(self.log_jsonl_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(report_dict, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"Error escribiendo log JSONL: {e}")

        # 3. Notificación remota si hubo promociones, cuarentenas o meta alcanzada
        promoted = report_dict.get("promoted", [])
        quarantined = report_dict.get("quarantined", [])
        goal_reached = report_dict.get("goal_reached", False)

        if promoted or quarantined or goal_reached:
            msg = self._format_alert_message(report_dict)
            self._send_discord_alert(msg)
            self._send_telegram_alert(msg)

    def _format_alert_message(self, report: Dict[str, Any]) -> str:
        lines = [
            "🚀 **Meme Hunter - Alerta del Bucle Autónomo**",
            f"⏱ Timestamp: `{report.get('cycle_timestamp', datetime.now(timezone.utc).isoformat())}`",
        ]
        if report.get("promoted"):
            lines.append(f"✅ **Factores Promovidos a LIVE:** {', '.join(report['promoted'])}")
        if report.get("quarantined"):
            lines.append(f"⚠️ **Factores Degradados a DECAY:** {', '.join(report['quarantined'])}")
        if report.get("goal_reached"):
            lines.append("🎯 **META CUANTITATIVA ALCANZADA:** Portafolio auto-optimizado al Sharpe objetivo.")

        new_w = report.get("new_weights", {})
        if new_w:
            w_str = ", ".join(f"{k}: {v:.1%}" for k, v in new_w.items())
            lines.append(f"⚖️ **Pesos HRP Vigentes:** {w_str}")

        return "\n".join(lines)

    def _send_discord_alert(self, message: str) -> None:
        if not self.discord_webhook:
            return
        try:
            payload = json.dumps({"content": message}).encode('utf-8')
            req = urllib.request.Request(
                self.discord_webhook,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "MemeHunter-Notifier/1.0"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=3.0)
        except Exception as e:
            logger.debug(f"Fallo enviando alerta a Discord: {e}")

    def _send_telegram_alert(self, message: str) -> None:
        if not self.tg_token or not self.tg_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            payload = json.dumps({"chat_id": self.tg_chat_id, "text": message, "parse_mode": "Markdown"}).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=3.0)
        except Exception as e:
            logger.debug(f"Fallo enviando alerta a Telegram: {e}")
