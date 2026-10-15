"""
hermes_runner.py - Daemon Autónomo de Ejecución Continua de Hermes (Sprint 52: PB-180).

Ejecuta el ciclo de supervisión, detección de régimen y gobernanza
de forma ininterrumpida como servicio en segundo plano o contenedor Docker:
- Ciclos de monitoreo cada N segundos (por defecto 300s / 5 minutos).
- Detecta cambios de régimen y alerta proactivamente en Telegram.
- Aplica salvaguardas de riesgo y rebalanceos de forma 100% desatendida.
"""

import os
import sys
import time
import signal
import threading
import logging
from typing import Optional

try:
    from meme_hunter.hermes.hermes_operator import HermesOperator
    from meme_hunter.hermes.telegram_messenger import HermesTelegramMessenger
except (ImportError, ModuleNotFoundError):
    from src.meme_hunter.hermes.hermes_operator import HermesOperator
    from src.meme_hunter.hermes.telegram_messenger import HermesTelegramMessenger

try:
    from client.telegram_ai_copilot import TelegramAiCopilotService
except ImportError:
    TelegramAiCopilotService = None

# Configurar logging institucional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [HermesDaemon]: %(message)s"
)
logger = logging.getLogger("HermesRunner")

running = True


def _handle_exit(signum, frame):
    global running
    logger.info(f"Señal de terminación recibida ({signum}). Deteniendo Hermes de forma segura...")
    running = False


signal.signal(signal.SIGINT, _handle_exit)
signal.signal(signal.SIGTERM, _handle_exit)


def run_daemon(interval_sec: Optional[int] = None):
    """Bucle principal de ejecución del Alter Ego."""
    interval = int(interval_sec or os.getenv("HERMES_INTERVAL_SEC", "300"))
    logger.info("=" * 60)
    logger.info("🧠 INICIANDO DAEMON AUTÓNOMO HERMES (ALTER EGO OPERATIVO)")
    logger.info(f"• Intervalo de sondeo: {interval} segundos")
    logger.info(f"• Memoria persistente: storage/hermes_memory.json")
    logger.info("=" * 60)

    operator = HermesOperator()
    messenger = HermesTelegramMessenger()
    last_regime = None

    # Iniciar listener interactivo de Telegram solo si está explícitamente habilitado
    # (Evita conflicto HTTP 409 de getUpdates cuando el servicio 'telegram_copilot' corre en paralelo)
    enable_tg_listener = os.getenv("HERMES_ENABLE_TELEGRAM_LISTENER", "false").lower() in ("true", "1", "yes")
    if TelegramAiCopilotService and enable_tg_listener:
        try:
            copilot = TelegramAiCopilotService()
            if copilot.is_configured():
                def _telegram_polling_loop():
                    logger.info("🤖 Listener interactivo de Telegram Copilot & Hermes (@Atutaskbot) iniciado.")
                    while running:
                        try:
                            copilot.poll_once()
                        except Exception as poll_err:
                            logger.warning(f"Excepción en polling de Telegram: {poll_err}")
                        time.sleep(1.0)
                    logger.info("Hilo interactivo de Telegram detenido ordenadamente.")

                tg_thread = threading.Thread(target=_telegram_polling_loop, daemon=True, name="TelegramListener")
                tg_thread.start()
            else:
                logger.warning("TelegramAiCopilotService no tiene token configurado.")
        except Exception as e:
            logger.error(f"No se pudo iniciar el listener de Telegram: {e}")

    # Iniciar worker de I+D Proactivo en segundo plano
    if hasattr(operator, "proactive_hunter") and operator.proactive_hunter:
        operator.proactive_hunter.start_worker()

    # Notificar inicio en Telegram si hay credenciales
    startup_msg = "🧠 *Hermes Activado:* He iniciado mi servicio de supervisión continua, I+D proactivo y chat interactivo sobre la arena multi-bot de Meme Hunter."
    messenger.send_executive_report(startup_msg)

    while running:
        try:
            logger.info("Iniciando ciclo autónomo de evaluación...")
            res = operator.run_cycle()
            regime = res["regime_info"].get("regime")
            confidence = res["regime_info"].get("confidence", 0.0)
            trades_cnt = res["portfolio"].get("total_open_trades", 0)
            stake_active = res["portfolio"].get("total_stake_active_usdt", 0.0)

            logger.info(
                f"Ciclo completado. Régimen: {regime} ({confidence*100:.0f}%) | "
                f"Trades vivos: {trades_cnt} | Stake activo: {stake_active:.2f} USDT"
            )

            # Si el régimen cambió respecto al ciclo anterior, notificar a Telegram
            if last_regime is not None and regime != last_regime:
                alert_text = (
                    f"⚠️ *CAMBIO DE RÉGIMEN DETECTADO POR HERMES*\n\n"
                    f"El mercado ha transitado de `{last_regime}` a *{regime}*.\n\n"
                    f"{res['explanation']}"
                )
                messenger.send_executive_report(alert_text)
                logger.info(f"Alerta de cambio de régimen enviada a Telegram ({last_regime} -> {regime}).")

            last_regime = regime

        except Exception as e:
            logger.error(f"Excepción en ciclo de Hermes: {e}", exc_info=True)

        # Esperar intervalo con verificación periódica de señal
        sleep_elapsed = 0
        while running and sleep_elapsed < interval:
            time.sleep(1)
            sleep_elapsed += 1

    if hasattr(operator, "proactive_hunter") and operator.proactive_hunter:
        operator.proactive_hunter.stop_worker()

    logger.info("Daemon Hermes detenido ordenadamente.")


if __name__ == "__main__":
    interval_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    run_daemon(interval_arg)
