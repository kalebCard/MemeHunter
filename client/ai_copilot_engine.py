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
4. CONTROL Y EJECUCIÓN AUTÓNOMA EN VIVO:
   - Cuentas con herramientas de despacho y ejecución en tiempo real sobre la API de Freqtrade y Binance.
   - Si el operador pide en lenguaje natural detener compras, parar el bot, reanudarlo, liquidar posiciones (por ID o por moneda como DOGE/PEPE), forzar compras, rebalancear o minar estrategias, confirma la instrucción sabiendo que el sistema ejecutará inmediatamente la orden real y adjuntará el comprobante de ejecución al pie del mensaje.
5. Explica el contexto de memecoins basándote en la desinflación macro post-pump y el sesgo asimétrico que genera rentabilidad.
6. Usa viñetas claras y emojis sobrios para facilitar la lectura en teléfonos móviles.
7. DISTINCIÓN CRÍTICA DE SALDOS (REAL vs SIMULADO):
   - El sistema corre en modo DRY-RUN (simulación sin riesgo de dinero real), donde los bots operan carteras de prueba virtuales (ej. ~100 USDT cada bot).
   - El usuario tiene sus fondos REALES en su cuenta de Binance (consultados vía API oficial).
   - Cuando el usuario pregunte por su saldo o dinero, DEBES distinguir con total claridad entre:
     a) SU SALDO REAL EN BINANCE (Billetera Spot y Billetera Futuros USDⓈ-M).
     b) EL SALDO SIMULADO DE LA ARENA MULTI-BOT (Ablation V5, Quantum V7, Mined Ensemble).
   - Si el usuario tiene fondos en Spot (ej. 10 USDT) pero 0 en Futuros, explícale cordialmente que Meme Hunter opera en el mercado de Futuros USDT-M, por lo que para operar en vivo solo debe transferir sus fondos de Spot a Futuros en Binance (sin comisiones).
8. BUCLE AUTÓNOMO DE INVESTIGACIÓN, REFINAMIENTO Y CUENTA SIMULADA:
   - Cuando el operador pida crear una nueva estrategia (ej. de 10 a 100 USDT, o bucle con backtesting), Hermes ejecuta un bucle iterativo donde sintetiza fórmulas con OpenRouter, las backtestea contra velas reales de 15m con slippage y comisiones, retroalimenta fallas y compila la estrategia ganadora en Bot 3 (:8083) con billetera simulada de 10 USDT.
9. REINICIO LIMPIO DE BOT 3 (MOONSHOT 10 A 100 USDT):
   - Si el operador pide reiniciar el bot de 10 a 100, comenzar de cero, nuevo intento, o limpiar la base de datos de Bot 3, Hermes detiene Bot 3, archiva la base de datos previa, restablece el balance virtual a 10.00 USDT e inyecta la estrategia récord ATH para un arranque limpio.
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
        hermes_context: Optional[Dict[str, Any]] = None,
        real_balance: Optional[Dict[str, Any]] = None,
        arena_balances: Optional[Dict[str, Any]] = None
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

        real_str = ""
        if real_balance and real_balance.get("has_keys"):
            spot_u = real_balance.get("spot_usdt_free", 0.0)
            fut_u = real_balance.get("futures_usdt_free", 0.0)
            assets = real_balance.get("other_assets", {})
            assets_str = ", ".join([f"{k}: {v}" for k, v in assets.items()]) if assets else "ninguno"
            real_str = (
                f"[BILLETERA REAL BINANCE DEL USUARIO (DINERO REAL)]\n"
                f"- Saldo Real Spot: {spot_u:.2f} USDT\n"
                f"- Saldo Real Futuros USDT-M: {fut_u:.2f} USDT (Transferir de Spot a Futuros para operar en vivo)\n"
                f"- Otros activos Spot: {assets_str}\n"
            )

        arena_str = ""
        if arena_balances and arena_balances.get("status") == "ok":
            tot = arena_balances.get("total_wallet", 0.0)
            fre = arena_balances.get("free_wallet", 0.0)
            usd = arena_balances.get("used_wallet", 0.0)
            bots_list = []
            for b_id, b_info in arena_balances.get("bots", {}).items():
                bots_list.append(f"  * {b_info['name']} (:{b_info['port']}): {b_info['total']:.2f} USDT (Libre: {b_info['free']:.2f})")
            bots_detail = "\n".join(bots_list)
            arena_str = (
                f"[ARENA MULTI-BOT SIMULADA (DRY-RUN PAPER TRADING)]\n"
                f"- Modo: DRY-RUN (Simulación sin riesgo real)\n"
                f"- Capital Simulado Total: {tot:.2f} USDT (Libre: {fre:.2f} USDT | Usado: {usd:.2f} USDT)\n"
                f"- Desglose por bot:\n{bots_detail}\n"
            )

        # Contexto del Maratón Cuantitativo Moonshot 10x
        marathon_str = ""
        try:
            lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mining", "factor_library.json")
            if os.path.exists(lib_path):
                with open(lib_path, "r", encoding="utf-8") as f:
                    factors = json.load(f)
                hermes_factors = [f for f in factors if "HERMES" in f.get("factor_id", "")]
                marathon_str = (
                    f"[MARATÓN Y EXPERIMENTO MOONSHOT 10X (10 A 100 USDT)]\n"
                    f"- Bucle Autónomo: ACTIVO en segundo plano (refinamiento continuo en 15m, 10x apalancamiento)\n"
                    f"- Factores Totales Minados: {len(factors)} ({len(hermes_factors)} por Hermes)\n"
                    f"- Bot 3 (:8083): Recibe inyecciones automáticas de cada factor prometedor (Sharpe > 1.60)\n"
                    f"- Diario Cuantitativo: docs/research/DIARIO_DE_ESTRATEGIAS.md activo\n"
                )
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.debug(f"Aviso al cargar factor_library: {e}")

        return (
            f"{real_str}"
            f"{arena_str}"
            f"{marathon_str}"
            f"{hermes_str}"
            f"[TELEMETRÍA EN VIVO]\n"
            f"- Estado de la Arena: {status_txt.upper()}\n"
            f"- Balance Referencia Bot 1: {total_balance:.2f} USDT (Disponible: {free_balance:.2f} USDT)\n"
            f"- PnL Cerrado Histórico: {total_pnl:+.2f} USDT ({profit_pct:+.2f}% | Win Rate: {win_rate:.1f}%)\n"
            f"- Posiciones Abiertas ({len(open_trades) if isinstance(open_trades, list) else 0}):\n"
            f"{trades_str}\n"
        )

    def extract_intent_heuristic(self, message: str) -> Dict[str, Any]:
        """Extrae la intención operativa usando análisis léxico/patrones regex enriquecidos."""
        msg = message.strip().lower()

        # 1. Kill switch de emergencia o liquidar todo
        if re.search(r"\b(kill\s*switch|emergencia|abortar|abort|liquidar\s+todo|vender\s+todo|vende\s+todo|cerrar\s+todo|cierra\s+todo|cerrar\s+todas|liquidar\s+todas|p[aá]nico)\b", msg):
            return {"action": "killswitch", "confidence": 0.98, "command": "/killswitch"}

        # 2. Detener compras (stopbuy)
        if re.search(r"\b(apagar?|apaga|det[eé]n(er)?|parar?|para|stop|pausar?|pausa|cancelar?|cancela|bloquear?|bloquea|no\s+compres|no\s+comprar)\s+(las\s+|m[aá]s\s+)?compras?\b", msg) or re.search(r"\b(stopbuy|bloquear\s+entradas|pausar\s+entradas)\b", msg):
            return {"action": "stopbuy", "confidence": 0.95, "command": "/stopbuy"}

        # 2.5. Detener entrenamiento / minado / refinamiento / maratón de alfas
        if re.search(r"\b(apagar?|apaga|det[eé]n(er)?|parar?|para|stop|pausar?|pausa|cancelar?|cancela|terminar?|termina|cortar?|corta)\s+(el\s+|la\s+)?(entrenamiento|minado|miner[ií]a|refinamiento|bucle|marat[oó]n|investigaci[oó]n|f[aá]brica|generaci[oó]n)\b", msg) or re.search(r"\b(stoptraining|stopmine|stopbucle|detenerentrenamiento|detenerminado|pararentrenamiento|pararminado)\b", msg):
            return {"action": "stop_training", "confidence": 0.98, "command": "/stoptraining"}

        # 3. Detener bot (stopbot)
        if re.search(r"\b(apagar?|apaga|det[eé]n(er)?|parar?|para|stop|pausar?|pausa)\s+(el\s+)?(bot|sistema|programa|arena|trading)\b", msg):
            return {"action": "stop", "confidence": 0.95, "command": "/stopbot"}

        # 4. Iniciar / reanudar bot o compras (startbot)
        if re.search(r"\b(iniciar?|inicia|arrancar?|arranca|reanudar?|reanuda|start|activar?|activa|despausar?)\s+(el\s+)?(bot|sistema|programa|trading|arena|compras?)\b", msg):
            return {"action": "start", "confidence": 0.95, "command": "/startbot"}

        # 5. Recargar configuración
        if re.search(r"\b(recargar?|recarga|reload|actualizar?\s+config|hot-reload)\b", msg):
            return {"action": "reload", "confidence": 0.90, "command": "/reload"}

        # 6. Consulta de estado / balance / profit
        if re.search(r"\b(balance|capital|saldo|fondos|cu[aá]nto\s+tengo|cu[aá]nto\s+hay|mi\s+dinero)\b", msg):
            return {"action": "query_balance", "confidence": 0.90, "command": "/balance"}
        if re.search(r"\b(profit|ganancias?|pnl|rendimiento|c[oó]mo\s+va\s+hoy|cu[aá]nto\s+ganamos)\b", msg):
            return {"action": "query_profit", "confidence": 0.90, "command": "/profit"}
        if re.search(r"\b(status|estado|posiciones|trades|operaciones)\b", msg):
            return {"action": "query_status", "confidence": 0.90, "command": "/status"}

        # 7. Venta forzada de trade (por ID numérico o por Símbolo de moneda)
        forcesell_id_match = re.search(
            r"\b(cerrar?|cierra|cerremos|vender?|vende|liquidar?|liquida|liquidemos|sal\s+de|salir\s+de|forcesell)\s+(el\s+|la\s+|las\s+|los\s+)?(trade\s+|posici[oó]n\s+|operaci[oó]n\s+)?#?(\d+)\b",
            msg
        )
        if forcesell_id_match:
            trade_id = forcesell_id_match.group(4)
            return {"action": "forcesell", "trade_id": trade_id, "confidence": 0.95, "command": f"/forcesell {trade_id}"}

        forcesell_sym_match = re.search(
            r"\b(cerrar?|cierra|cerremos|vender?|vende|liquidar?|liquida|liquidemos|sal\s+de|salir\s+de|forcesell)\s+(el\s+|la\s+|las\s+|los\s+)?(trade\s+|posici[oó]n\s+|operaci[oó]n\s+)?(de\s+)?([a-zA-Z0-9]+)\b",
            msg
        )
        if forcesell_sym_match:
            cand = forcesell_sym_match.group(5).upper()
            stop_words = {"TODO", "TODAS", "EL", "LA", "LOS", "LAS", "POSICION", "POSICIONES", "TRADE", "TRADES", "COMPRAS", "BOT", "SISTEMA", "UN", "UNA"}
            if cand not in stop_words and len(cand) >= 2:
                return {"action": "forcesell", "symbol": cand, "confidence": 0.95, "command": f"/forcesell {cand}"}

        # 8. Compra forzada / apertura manual
        buy_match = re.search(
            r"\b(comprar?|compra|buy|forcebuy|meter\s+long|abrir\s+long|entra\s+en|entrar\s+en)\s+([0-9\.]+\s+)?([a-zA-Z0-9]+)\b",
            msg
        )
        if buy_match:
            symbol = buy_match.group(3).upper()
            stop_words = {"UNA", "UNO", "UN", "ESTRATEGIA", "ALGO", "AHORA", "NUEVA", "BOT"}
            if symbol not in stop_words and len(symbol) >= 2:
                return {"action": "forcebuy", "symbol": symbol, "confidence": 0.95, "command": f"/forcebuy {symbol}/USDT:USDT"}

        # 9. Reiniciar Bot 3 / Moonshot 10 a 100 USDT (reset_moonshot)
        if (
            re.search(r"\b(reinici(?:ar?|a|ame)|reset(?:ea|ear)?|restablec(?:er|e)|limpiar?\s+base|borrar?\s+trades)\b.*\b(bot\s*3|10\s*(?:a|to)\s*100|moonshot|ensamble|ensemble)\b", msg)
            or re.search(r"\b(nuevo\s+intento|empezar?\s+de\s+cero|comenzar?\s+de\s+nuevo|borra\s+los\s+trades|reinicia\s+el\s+saldo)\b", msg)
            or msg in ["/resetbot3", "/reiniciarbot3", "/nuevointento", "/resetmoonshot"]
        ):
            return {"action": "reset_moonshot", "confidence": 0.98, "command": "/resetbot3"}

        # 10. Hermes / Régimen / Rebalance / Minería de Alphas
        if re.search(r"\b(crear?|crea|creame|generar?|genera|minar?|mina|inventar?|inventa|nueva\s+estrategia|nuevo\s+alpha|nuevo\s+factor|backtest|backtesting|optimiz|bucle|refinar?|refina|refinamiento|cuenta\s+simulada|billetera\s+simulada|plan\s+para\s+pasar)\b", msg):
            return {"action": "mine_strategy", "confidence": 0.95, "command": "/mine"}
        if msg in ["hermes", "alter ego", "/hermes", "/alterego"] or re.search(r"\b(informe\s+de\s+hermes|qu[eé]\s+dice\s+hermes|diagn[oó]stico\s+de\s+hermes|reporte\s+ejecutivo|alter\s*ego)\b", msg):
            return {"action": "query_hermes", "confidence": 0.95, "command": "/hermes"}
        if re.search(r"\b(regimen|r[eé]gimen|c[oó]mo\s+esta\s+el\s+mercado|tendencia|macro|funding)\b", msg):
            return {"action": "query_regime", "confidence": 0.95, "command": "/regime"}
        if re.search(r"\b(rebalancear?|rebalanceo|rebalance|ajustar?\s+capital|redistribuir|balancear)\b", msg):
            return {"action": "rebalance", "confidence": 0.95, "command": "/rebalance"}

        return {"action": "general_copilot_query", "confidence": 0.50, "command": None}

    def process_message(
        self,
        user_message: str,
        bot_state: Dict[str, Any],
        profit_data: Dict[str, Any],
        balance_data: Dict[str, Any],
        open_trades: List[Dict[str, Any]],
        hermes_context: Optional[Dict[str, Any]] = None,
        real_balance: Optional[Dict[str, Any]] = None,
        arena_balances: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Procesa el mensaje del operador, consulta a la IA o ejecuta fallback,
        y devuelve una tupla: (Respuesta en Markdown, Acción Sugerida si aplica).
        """
        context_str = self.build_context_summary(
            bot_state=bot_state,
            profit_data=profit_data,
            balance_data=balance_data,
            open_trades=open_trades,
            hermes_context=hermes_context,
            real_balance=real_balance,
            arena_balances=arena_balances
        )
        intent = self.extract_intent_heuristic(user_message)

        # Si OpenRouter tiene clave y está operativo, realizamos inferencia cognitiva
        prompt = (
            f"{context_str}\n"
            f"[CONSULTA DEL OPERADOR]:\n"
            f"\"{user_message}\"\n\n"
            f"Instrucción: Responde en español como el Copilot de Meme Hunter. "
            f"Si el usuario pregunta por su saldo o dinero, explica con claridad la diferencia entre sus fondos reales en Binance y el balance virtual de prueba de la arena en Dry-Run. "
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
        heuristic_reply = self._generate_heuristic_reply(
            user_message=user_message,
            intent=intent,
            context_str=context_str,
            open_trades=open_trades,
            hermes_context=hermes_context,
            profit_data=profit_data,
            balance_data=balance_data,
            real_balance=real_balance,
            arena_balances=arena_balances
        )
        return heuristic_reply, (intent if intent["action"] != "general_copilot_query" else None)

    def _generate_heuristic_reply(
        self,
        user_message: str,
        intent: Dict[str, Any],
        context_str: str,
        open_trades: List[Dict[str, Any]],
        hermes_context: Optional[Dict[str, Any]] = None,
        profit_data: Optional[Dict[str, Any]] = None,
        balance_data: Optional[Dict[str, Any]] = None,
        real_balance: Optional[Dict[str, Any]] = None,
        arena_balances: Optional[Dict[str, Any]] = None
    ) -> str:
        """Genera respuesta dinámica, conversacional y context-aware cuando el LLM está en modo offline."""
        msg_lower = user_message.lower().strip()
        action = intent.get("action")
        hermes_ctx = hermes_context or {}
        regime = hermes_ctx.get("regime", "RANGE_CHOP")
        confidence = hermes_ctx.get("confidence", 0.70)
        snap = hermes_ctx.get("snapshot", {})
        btc_price = snap.get("btc_price", 0.0)
        btc_chg = snap.get("btc_change_24h", 0.0)
        rationale = hermes_ctx.get("rationale", "Mercado en evaluación continua.")

        # 1. Comandos de control directos
        if action == "stopbuy":
            return (
                "🛡️ **Orden de Salvaguarda: Detener Compras**\n\n"
                "Ejecutando detención inmediata de nuevas compras en toda la arena multi-bot..."
            )
        elif action == "stop_training":
            return (
                "⏹️ **Orden Operativa: Detener Entrenamiento / Minado**\n\n"
                "Procediendo a finalizar de inmediato los procesos de investigación, minería de alfas y refinamiento en segundo plano..."
            )
        elif action == "stop":
            return (
                "🛑 **Orden de Salvaguarda: Detener Bot**\n\n"
                "Suspendiendo la ejecución de trading y cualquier proceso de entrenamiento activo..."
            )
        elif action == "start":
            return (
                "▶️ **Reanudación del Sistema Cuantitativo**\n\n"
                "Reanudando la operativa del bot de inmediato..."
            )
        elif action == "killswitch":
            return (
                "🚨 **ACTIVACIÓN DE EMERGENCIA: KILL-SWITCH 25%**\n\n"
                "Ejecutando protocolo de salvaguarda, bloqueo de compras y liquidación de emergencia..."
            )
        elif action == "forcesell":
            tid = intent.get("trade_id")
            sym = intent.get("symbol")
            if tid:
                return f"⚡ **Liquidación Forzada Ordenada**\n\nEjecutando orden de salida a mercado para el trade #{tid}..."
            elif sym:
                return f"⚡ **Liquidación de {sym} Ordenada**\n\nBuscando y liquidando posiciones abiertas de {sym} en la arena..."
            return "⚡ **Liquidación Forzada Ordenada**\n\nProcesando orden de salida a mercado..."
        elif action == "forcebuy":
            sym = intent.get("symbol", "BTC")
            pair = f"{sym}/USDT:USDT" if "/" not in sym else sym
            return f"⚡ **Apertura / Compra Forzada ({pair})**\n\nEnviando orden de entrada a mercado a Freqtrade..."
        elif action == "reset_moonshot":
            return (
                "🔄 **REINICIO DEL BOT 3 (MOONSHOT 10 A 100 USDT)**\n\n"
                "Ejecutando reinicio completo: deteniendo bot, archivando base de datos previa, "
                "reajustando saldo virtual limpio a 10.00 USDT e inyectando la estrategia récord ATH..."
            )

        # 2. Detección de Saludos y Conversación Amistosa
        if re.search(r"\b(hola|buen[oa]s|qu[eé]\s+tal|c[oó]mo\s+est[aá]s|hey|saludos)\b", msg_lower):
            trades_count = len(open_trades) if isinstance(open_trades, list) else 0
            return (
                f"👋 ¡Hola! Aquí **Hermes**, tu Alter Ego al mando de Meme Hunter.\n\n"
                f"Estoy monitoreando la arena en Binance Futures 24/7. Actualmente tenemos **{trades_count} posiciones abiertas** "
                f"bajo un régimen catalogado como **{regime}** (Confianza: {confidence*100:.0f}%).\n\n"
                f"• BTC cotiza en `${btc_price:,.1f}` (`{btc_chg:+.2f}%`).\n"
                f"• Mi meta es clara: **hacer crecer la cuenta en USDT y proteger las ganancias**.\n\n"
                f"¿Qué te gustaría revisar? Puedes preguntarme por una moneda específica (ej. *'cómo va ETH'*, *'cómo va SOL'*), "
                f"por las ganancias (*'cuánto llevamos'*), o usar comandos como `/hermes`, `/status` o `/regime`."
            )

        # 3. Detección de Búsqueda de Moneda Específica
        known_coins = ["BTC", "ETH", "SOL", "DOGE", "PEPE", "HYPE", "ZEC", "XAU", "XRP", "NEAR", "SOXL", "SNDK", "WAL", "BTW"]
        found_coin = None
        for c in known_coins:
            if re.search(rf"\b{c}\b", msg_lower, re.IGNORECASE):
                found_coin = c
                break

        if found_coin:
            matching_trades = [t for t in open_trades if found_coin in t.get("pair", "").upper()]
            if matching_trades:
                lines = []
                for t in matching_trades:
                    tid = t.get("trade_id", "?")
                    pair = t.get("pair", "")
                    prof = t.get("profit_pct", 0.0)
                    bot = t.get("origin_bot", "Bot")
                    is_short = t.get("is_short", False)
                    dir_str = "SHORT 📉" if is_short else "LONG 📈"
                    stake = t.get("stake_amount", 0.0)
                    lines.append(f"• Trade `#{tid}` (*{pair}* | {dir_str} en {bot}): `{prof:+.2f}%` (Margen: `{stake:.2f} USDT`)")
                trades_info = "\n".join(lines)
                return (
                    f"🔍 **Posición activa en {found_coin} en Binance Futures:**\n\n"
                    f"{trades_info}\n\n"
                    f"⚖️ **Táctica de Hermes:** Operando bajo régimen **{regime}**. Para forzar el cierre inmediato usa `/forcesell <id>`."
                )
            else:
                return (
                    f"ℹ️ **Moneda {found_coin}:** No tenemos ninguna posición abierta actualmente en `{found_coin}/USDT:USDT`.\n\n"
                    f"Los bots están filtrando pares con mayor volumen y asimetría bajo el régimen **{regime}**. "
                    f"Usa `/status` para ver todas las posiciones vivas en la arena."
                )

        # 4. Preguntas de Ganancias / Dinero / Balance
        if re.search(r"\b(ganancia|ganancias|plata|dinero|cu[aá]nto\s+llevamos|pnl|rentabilidad|balance|saldo|capital)\b", msg_lower):
            prof = profit_data or {}
            closed_pnl = prof.get("profit_closed_coin", 0.0)
            winrate = prof.get("winrate", 0.0) * 100.0 if prof.get("winrate", 0.0) <= 1.0 else prof.get("winrate", 0.0)

            # 1. Billetera Real de Binance
            real_info_lines = []
            if real_balance and real_balance.get("has_keys"):
                spot_u = real_balance.get("spot_usdt_free", 0.0)
                fut_u = real_balance.get("futures_usdt_free", 0.0)
                real_info_lines.append(f"• *Billetera Spot:* `{spot_u:.2f} USDT`")
                real_info_lines.append(f"• *Billetera Futuros (USDⓈ-M):* `{fut_u:.2f} USDT`")
                if fut_u == 0.0 and spot_u > 0.0:
                    real_info_lines.append("  _(⚠️ Tus fondos están en Spot. Para operar futuros en vivo, transfiérelos a Futuros en Binance sin comisión)_")
            else:
                real_info_lines.append("• *Billetera Binance:* `Sin credenciales directas`")

            real_block = "\n".join(real_info_lines)

            # 2. Arena Multi-Bot Simulación
            arena_info_lines = []
            if arena_balances and arena_balances.get("status") == "ok":
                tot_sim = arena_balances.get("total_wallet", 0.0)
                fre_sim = arena_balances.get("free_wallet", 0.0)
                usd_sim = arena_balances.get("used_wallet", 0.0)
                arena_info_lines.append(f"• *Total Cartera Simulación:* `{tot_sim:.2f} USDT` (Libre: `{fre_sim:.2f}` | Margen: `{usd_sim:.2f}`)")
                for b_id, b_data in arena_balances.get("bots", {}).items():
                    arena_info_lines.append(f"  - *{b_data['name']}* (:{b_data['port']}): `{b_data['total']:.2f} USDT` (Libre: `{b_data['free']:.2f}`)")
            else:
                bal = balance_data or {}
                arena_info_lines.append(f"• *Bot 1 (Ablation :8081):* `{bal.get('total', 0.0):.2f} USDT` (Libre: `{bal.get('free', 0.0):.2f}`)")

            arena_block = "\n".join(arena_info_lines)

            return (
                f"💰 **Reporte Oficial de Billeteras y Capital — Hermes Alter Ego**\n\n"
                f"🏦 **1. TU SALDO REAL EN BINANCE:**\n"
                f"{real_block}\n\n"
                f"🎮 **2. SALDO VIRTUAL DE LA ARENA (DRY-RUN PAPER TRADING):**\n"
                f"{arena_block}\n\n"
                f"📊 *PnL Realizado Histórico:* `{closed_pnl:+.2f} USDT` (Win Rate: `{winrate:.1f}%`)\n"
                f"🛡️ *Protección Activa:* Drawdown Kill Switch (25%) y Profit Ratchet vigilando cada trade."
            )

        # 5. Preguntas sobre Mercado / Tendencia / Bitcoin / Régimen
        if re.search(r"\b(mercado|tendencia|regimen|r[eé]gimen|bitcoin|btc|cae|sube|qu[eé]\s+pasa)\b", msg_lower):
            allocs = hermes_ctx.get("recommended_allocations", {})
            alloc_lines = [f"  - *{k}*: `{v*100:.0f}%`" for k, v in allocs.items()]
            alloc_str = "\n".join(alloc_lines) if alloc_lines else "  - Cartera balanceada estándar."
            return (
                f"📊 **Análisis Macro del Mercado — Hermes Agent**\n\n"
                f"• **Régimen Identificado:** `{regime}` (Confianza: {confidence*100:.0f}%)\n"
                f"• **BTC:** `${btc_price:,.1f}` (`{btc_chg:+.2f}%` en 24h)\n"
                f"• **Funding Rate Promedio:** `{snap.get('avg_funding_rate', 0):.6f}`\n\n"
                f"💡 **Diagnóstico:** {rationale}\n\n"
                f"⚖️ **Asignación de Capital Activa:**\n{alloc_str}"
            )

        # 6. Preguntas sobre los Bots / Estrategias
        if re.search(r"\b(bots?|estrategias?|ablation|quantum|ensemble|qui[eé]n\s+opera)\b", msg_lower):
            return (
                f"🤖 **Arena Multi-Bot — Estado de Estrategias**\n\n"
                f"Hermes coordina 3 campeones cuantitativos en simultáneo:\n\n"
                f"1. 🥇 **Ablation V5.2 (:8081):** Especialista en atrapar cascadas bajistas de memecoins tras pumps eufóricos.\n"
                f"2. 🥈 **Quantum V7.1 (:8082):** Motor de dimensionamiento fraccional de Kelly con mínima volatilidad de balance.\n"
                f"3. 🥉 **Mined Ensemble V8.0 (:8083):** Algoritmo de ensamble multi-factor para capturar tendencias continuas.\n\n"
                f"Régimen actual: **{regime}**. Hermes modula la exposición de cada uno cada 5 minutos."
            )

        # 7. Fallback Contextual Enriquecido (Conversacional, nunca repetitivo)
        trades_count = len(open_trades) if isinstance(open_trades, list) else 0
        return (
            f"🧠 **Hermes (Tu Alter Ego Operativo)**\n\n"
            f"Entendido: *\"{user_message}\"*\n\n"
            f"Estoy supervisando activamente la cartera en Binance Futures bajo el régimen **{regime}** con **{trades_count} posiciones abiertas**.\n\n"
            f"💡 **Comandos directos que puedes usar:**\n"
            f"• `/hermes` : Informe causal ejecutivo sobre la estrategia actual.\n"
            f"• `/status` : Lista detallada de trades y bots.\n"
            f"• `/regime` : Métricas macro de Binance Futures.\n"
            f"• `/rebalance` : Forzar rebalanceo de capital entre los 3 bots.\n"
            f"• O pregúntame por una moneda (ej. *'cómo va ETH'* o *'cuánto llevamos'*)."
        )
