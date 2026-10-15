"""
ai_copilot_engine.py - Motor Cognitivo Cuantitativo para Copilot de Telegram (Sprint 50: PB-172).

Orquesta la cognición de IA para Meme Hunter integrando:
1. Cliente OpenRouter (DeepSeek-V3 / DeepSeek-R1 / Claude 3.5).
2. Telemetría viva del bot (estado, balances, PnL, trades abiertos).
3. Clasificación de intención operativa y sugerencia de acciones ejecutables.
4. Modo Resiliente Offline con análisis heurístico si no hay conectividad a OpenRouter.
"""

import os
import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple

from mining.llm_client import OpenRouterClient, OpenRouterModel

logger = logging.getLogger("QuantAiCopilotEngine")


COPILOT_SYSTEM_PROMPT = """Eres el Copilot Cuantitativo Oficial de Meme Hunter (Arquitectura Institucional v8.6).
Tu función es asistir al operador jefe en Telegram con telemetría en tiempo real, análisis de riesgo de futuros (USDT-M 4h) y control del ecosistema gobernado por HERMES AGENT (el Alter Ego autónomo).

DIRECTIVA PRIMARIA DE HERMES:
LA META PRINCIPAL ES GANAR DINERO EN BINANCE FUTURES (Maximizar el PnL neto y el crecimiento compuesto del balance en USDT).
Cada decisión de asignación de capital, detección de régimen de mercado y salvaguarda de riesgo tiene un único propósito: extraer beneficios consistentes del mercado, capitalizar las ineficiencias de las memecoins y blindar las ganancias acumuladas.

REGLAS DE OPERACIÓN INSTITUCIONAL:
1. Respuestas concisas, ejecutivas, profesionales y directas (formato Telegram Markdown compatible).
2. Tienes acceso al cerebro de HERMES AGENT, quien clasifica el régimen del mercado (BEAR_CASCADE, BULL_PARABOLIC, RANGE_CHOP, PANIC_VOLATILITY) y reasigna capital entre Ablation V5 (:8081), Quantum V7 (:8082) y Mined Ensemble (:8083) para maximizar el PnL según el entorno.
3. Protege las ganancias obtenidas: el Kill Switch de Drawdown está fijado al 25% y Hermes activa el Profit Ratchet para no devolver dinero ganado a Binance.
4. Si el usuario pide detener compras, parar el bot, vender posiciones, consultar a Hermes o rebalancear, identifica la acción operativa exacta.
5. Explica el contexto de memecoins basándote en la desinflación macro post-pump y el sesgo asimétrico que genera rentabilidad.
6. Usa viñetas claras y emojis sobrios para facilitar la lectura en teléfonos móviles.
"""


class QuantAiCopilotEngine:
    """
    Motor Cognitivo que interpreta mensajes en lenguaje natural del operador,
    fusiona la telemetría en vivo de Freqtrade y las decisiones de Hermes Agent.
    """

    def __init__(
        self,
        llm_client: Optional[OpenRouterClient] = None,
        model: Optional[str] = None
    ):
        self.llm_client = llm_client or OpenRouterClient()
        self.model = (
            model
            or os.environ.get("HERMES_LLM_MODEL")
            or os.environ.get("OPENROUTER_MODEL")
            or OpenRouterModel.NOUS_HERMES_3_70B
        )

    def build_context_summary(
        self,
        bot_state: Dict[str, Any],
        profit_data: Dict[str, Any],
        balance_data: Dict[str, Any],
        open_trades: List[Dict[str, Any]],
        hermes_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Sintetiza la telemetría y el diagnóstico de Hermes en un bloque compacto."""
        status_txt = bot_state.get("state", "desconocido") if isinstance(bot_state, dict) else "activo"
        total_pnl = profit_data.get("profit_closed_coin", 0.0) if isinstance(profit_data, dict) else 0.0
        profit_pct = profit_data.get("profit_closed_ratio_pct", 0.0) if isinstance(profit_data, dict) else 0.0
        win_rate = profit_data.get("winrate", 0.0) if isinstance(profit_data, dict) else 0.0
        total_balance = balance_data.get("total", 0.0) if isinstance(balance_data, dict) else 0.0
        free_balance = balance_data.get("free", 0.0) if isinstance(balance_data, dict) else 0.0

        trades_summary = []
        if isinstance(open_trades, list):
            for t in open_trades[:6]:
                pair = t.get("pair", "N/A")
                pnl = t.get("profit_pct", 0.0)
                dur = t.get("open_date_hum", "N/A")
                tid = t.get("trade_id", "?")
                origin = t.get("origin_bot", "bot_v5")
                trades_summary.append(f"  - Trade #{tid} ({pair} | {origin}): {pnl:+.2f}% | Duración: {dur}")

        trades_str = "\n".join(trades_summary) if trades_summary else "  - Ninguna posición abierta actualmente."

        hermes_str = ""
        if hermes_context:
            regime = hermes_context.get("regime", "N/A")
            conf = hermes_context.get("confidence", 0.0) * 100
            rationale = hermes_context.get("rationale", "")
            allocations = hermes_context.get("recommended_allocations", {})
            alloc_str = ", ".join([f"{k}: {v*100:.0f}%" for k, v in allocations.items()])
            hermes_str = (
                f"[CEREBRO AUTÓNOMO HERMES (ALTER EGO)]\n"
                f"- Régimen de Mercado: {regime} (Confianza: {conf:.0f}%)\n"
                f"- Asignación Activa: {alloc_str}\n"
                f"- Justificación Táctica: {rationale}\n"
            )

        return (
            f"{hermes_str}"
            f"[TELEMETRÍA EN VIVO]\n"
            f"- Estado de la Arena: {status_txt.upper()}\n"
            f"- Balance Total Cartera: {total_balance:.2f} USDT (Disponible: {free_balance:.2f} USDT)\n"
            f"- PnL Cerrado Histórico: {total_pnl:+.2f} USDT ({profit_pct:+.2f}% | Win Rate: {win_rate:.1f}%)\n"
            f"- Posiciones Abiertas ({len(open_trades) if isinstance(open_trades, list) else 0}):\n"
            f"{trades_str}\n"
        )

    def extract_intent_heuristic(self, message: str) -> Dict[str, Any]:
        """Extrae la intención operativa usando análisis léxico/patrones regex."""
        msg = message.strip().lower()

        # Detener bot o compras
        if re.search(r"\b(apagar|apaga|deten|detener|parar|para|stop)\s+(las\s+)?compras?\b", msg):
            return {"action": "stopbuy", "confidence": 0.95, "command": "/stopbuy"}
        if re.search(r"\b(apagar|apaga|deten|detener|parar|para|stop)\s+(el\s+)?(bot|sistema|programa)\b", msg):
            return {"action": "stop", "confidence": 0.95, "command": "/stopbot"}
        if re.search(r"\b(iniciar|inicia|arrancar|arranca|reanudar|reanuda|start)\s+(el\s+)?(bot|sistema|programa|trading)\b", msg):
            return {"action": "start", "confidence": 0.95, "command": "/startbot"}

        # Kill switch de emergencia
        if re.search(r"\b(kill\s*switch|emergencia|abortar|abort|liquidar\s+todo)\b", msg):
            return {"action": "killswitch", "confidence": 0.98, "command": "/killswitch"}

        # Recargar configuración
        if re.search(r"\b(recargar?|recarga|reload|actualizar?\s+config)\b", msg):
            return {"action": "reload", "confidence": 0.90, "command": "/reload"}

        # Consulta de estado / balance / profit
        if re.search(r"\b(balance|capital|saldo|fondos|cuanto\s+tengo)\b", msg):
            return {"action": "query_balance", "confidence": 0.90, "command": "/balance"}
        if re.search(r"\b(profit|ganancias?|pnl|rendimiento|como\s+va\s+hoy)\b", msg):
            return {"action": "query_profit", "confidence": 0.90, "command": "/profit"}
        if re.search(r"\b(status|estado|posiciones|trades|operaciones)\b", msg):
            return {"action": "query_status", "confidence": 0.90, "command": "/status"}

        # Venta forzada de trade
        forcesell_match = re.search(
            r"\b(cerrar|cierra|cerremos|vender|vende|liquidar|liquida|liquidemos|forcesell)\s+(el\s+)?(trade\s+)?#?(\d+)\b",
            msg
        )
        if forcesell_match:
            trade_id = forcesell_match.group(4)
            return {"action": "forcesell", "trade_id": trade_id, "confidence": 0.95, "command": f"/forcesell {trade_id}"}

        # Compra forzada / apertura manual
        buy_match = re.search(
            r"\b(compra|comprar|buy|forcebuy|meter\s+long|abrir\s+long)\s+([0-9\.]+\s+)?([a-zA-Z0-9]+)\b",
            msg
        )
        if buy_match:
            symbol = buy_match.group(3).upper()
            return {"action": "forcebuy", "symbol": symbol, "confidence": 0.95, "command": f"/forcebuy {symbol}/USDT:USDT"}

        # Hermes / Régimen / Rebalance
        if re.search(r"\b(hermes|alter\s*ego|orquestador)\b", msg):
            return {"action": "query_hermes", "confidence": 0.95, "command": "/hermes"}
        if re.search(r"\b(regimen|r[eé]gimen|como\s+esta\s+el\s+mercado|tendencia)\b", msg):
            return {"action": "query_regime", "confidence": 0.95, "command": "/regime"}
        if re.search(r"\b(rebalancear?|rebalanceo|rebalance|ajustar?\s+capital)\b", msg):
            return {"action": "rebalance", "confidence": 0.95, "command": "/rebalance"}

        return {"action": "general_copilot_query", "confidence": 0.50, "command": None}

    def process_message(
        self,
        user_message: str,
        bot_state: Dict[str, Any],
        profit_data: Dict[str, Any],
        balance_data: Dict[str, Any],
        open_trades: List[Dict[str, Any]],
        hermes_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Procesa el mensaje del operador, consulta a la IA o ejecuta fallback,
        y devuelve una tupla: (Respuesta en Markdown, Acción Sugerida si aplica).
        """
        context_str = self.build_context_summary(bot_state, profit_data, balance_data, open_trades, hermes_context)
        intent = self.extract_intent_heuristic(user_message)

        # Si OpenRouter tiene clave y está operativo, realizamos inferencia cognitiva
        prompt = (
            f"{context_str}\n"
            f"[CONSULTA DEL OPERADOR]:\n"
            f"\"{user_message}\"\n\n"
            f"Instrucción: Responde en español como el Copilot de Meme Hunter. "
            f"Si detectas una acción operativa como parar o cerrar trades, confírmala explícitamente."
        )

        try:
            res = self.llm_client.complete(
                prompt=prompt,
                system_prompt=COPILOT_SYSTEM_PROMPT,
                model=self.model,
                temperature=0.3,
                json_mode=False
            )
            ai_text = res.get("text") or res.get("raw_text")
            if ai_text and not ai_text.startswith("[ERROR"):
                return ai_text, (intent if intent["action"] != "general_copilot_query" else None)
        except Exception as e:
            logger.warning(f"Fallo en llamada a LLM, usando generador heurístico: {e}")

        # Generador de respuesta heurística enriquecida (Modo Offline Resiliente)
        heuristic_reply = self._generate_heuristic_reply(user_message, intent, context_str, open_trades)
        return heuristic_reply, (intent if intent["action"] != "general_copilot_query" else None)

    def _generate_heuristic_reply(
        self,
        user_message: str,
        intent: Dict[str, Any],
        context_str: str,
        open_trades: List[Dict[str, Any]]
    ) -> str:
        """Genera respuesta determinista cuando el LLM está en modo offline."""
        action = intent.get("action")

        if action == "stopbuy":
            return (
                "🛡️ **Orden de Salvaguarda: Detener Compras**\n\n"
                "He detectado tu orden para inhibir nuevas entradas.\n"
                "Para confirmar y ejecutar en el bot, envía:\n"
                "`/stopbuy`"
            )
        elif action == "stop":
            return (
                "🛑 **Orden de Salvaguarda: Detener Bot**\n\n"
                "Para suspender la ejecución completa del bot de trading de inmediato, envía:\n"
                "`/stopbot`"
            )
        elif action == "start":
            return (
                "▶️ **Reanudación del Sistema Cuantitativo**\n\n"
                "Para reanudar la operativa del bot en Binance Futures, envía:\n"
                "`/startbot`"
            )
        elif action == "killswitch":
            return (
                "🚨 **ACTIVACIÓN DE EMERGENCIA: KILL-SWITCH 25%**\n\n"
                "Esta acción detendrá el motor y asegurará el capital remanente.\n"
                "Ejecuta de inmediato:\n"
                "`/killswitch`"
            )
        elif action == "forcesell":
            tid = intent.get("trade_id", "?")
            return (
                f"⚠️ **Confirmación de Salida Forzada**\n\n"
                f"¿Deseas liquidar de inmediato la posición #{tid} a mercado?\n"
                f"Ejecuta:\n"
                f"`/forcesell {tid}`"
            )
        elif action == "forcebuy":
            sym = intent.get("symbol", "BTC")
            pair = f"{sym}/USDT:USDT" if "/" not in sym else sym
            return (
                f"⚡ **Solicitud de Apertura / Compra Forzada ({pair})**\n\n"
                f"El motor cuantitativo Meme Hunter opera derivados USDT-M aislados con sesgo asimétrico.\n\n"
                f"Para confirmar la orden de apertura a mercado en Freqtrade, ejecuta:\n"
                f"`/forcebuy {pair}`\n\n"
                f"💡 *Nota:* Comprueba en `/balance` que dispongas de margen libre para nuevos slots."
            )
        elif action == "query_hermes":
            return (
                f"🧠 **Consulta al Alter Ego Autónomo Hermes**\n\n"
                f"{context_str}\n"
                f"💡 Usa `/hermes` para ver la explicación causal detallada o `/rebalance` para forzar rebalanceo."
            )
        elif action == "query_regime":
            return (
                f"📊 **Consulta de Régimen de Mercado**\n\n"
                f"{context_str}\n"
                f"💡 Usa `/regime` para el desglose macro directo de Binance Futures."
            )
        elif action == "rebalance":
            return (
                f"⚖️ **Rebalanceo de Cartera Solicitado**\n\n"
                f"Hermes ajusta los pesos de Ablation, Quantum y Ensemble según el régimen activo.\n\n"
                f"Para ejecutar el rebalanceo ahora, envía:\n"
                f"`/rebalance`"
            )
        elif action in ("query_status", "query_profit", "query_balance"):
            return (
                f"📊 **Reporte Cuantitativo en Tiempo Real**\n\n"
                f"{context_str}\n"
                f"💡 Puedes usar `/status`, `/profit` o `/balance` para reportes tabulares detallados."
            )
        else:
            trades_count = len(open_trades) if isinstance(open_trades, list) else 0
            return (
                f"🤖 **Meme Hunter AI Copilot**\n\n"
                f"He recibido tu consulta: *\"{user_message}\"*\n\n"
                f"**Resumen Operativo:**\n"
                f"- Posiciones vivas: {trades_count}\n"
                f"- Comandos rápidos disponibles: `/hermes`, `/regime`, `/status`, `/profit`, `/balance`, `/stopbuy`, `/stopbot`, `/reload`.\n"
                f"- Para consultar a la IA directamente usa `/ai <tu pregunta>`."
            )
