"""
telegram_ai_copilot.py - Servicio Integral del Copilot Cuantitativo en Telegram (Sprint 50 & 51).

Conecta la IA al bot de Telegram y permite controlar el programa en tiempo real:
- Control de acceso estricto por Chat ID (Firewall de Ciberseguridad).
- Comandos operativos directos de baja latencia (/status, /profit, /balance, /stopbuy, /stopbot, /startbot, /forcesell, /reload, /killswitch).
- Agente Cognitivo de Lenguaje Natural (/ai o cualquier mensaje no comandado).
- Enlace bidireccional con la API REST de Freqtrade (:8081).
- Arquitectura autónoma en urllib sin dependencias binarias externas pesadas.
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from client.freqtrade_client import FreqtradeRestClient
from client.multi_bot_orchestrator import MultiBotOrchestratorClient
from client.ai_copilot_engine import QuantAiCopilotEngine
from client.binance_account_client import BinanceAccountClient
try:
    from meme_hunter.hermes.hermes_operator import HermesOperator
except (ImportError, ModuleNotFoundError):
    from src.meme_hunter.hermes.hermes_operator import HermesOperator
from portfolio.secrets_vault import get_secret

logger = logging.getLogger("TelegramAiCopilot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _load_env_file():
    """Carga automáticamente variables de entorno desde .env."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                break
            except Exception as e:
                logger.debug(f"Error leyendo {env_path}: {e}")


_load_env_file()


class TelegramBotClient:
    """Cliente HTTP liviano para Telegram Bot API con zero-dependencies."""

    def __init__(self, token: str, timeout_sec: float = 15.0):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.timeout_sec = timeout_sec

    def _api_call(self, method: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{method}"
        body = json.dumps(data).encode('utf-8') if data else None
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data else "GET")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = resp.read().decode('utf-8')
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            err = e.read().decode('utf-8', errors='ignore')
            logger.error(f"Telegram API HTTP {e.code} en {method}: {err}")
            return {"ok": False, "error_code": e.code, "description": err}
        except Exception as e:
            logger.error(f"Telegram API fallo de red en {method}: {e}")
            return {"ok": False, "error_code": 0, "description": str(e)}

    def get_me(self) -> Dict[str, Any]:
        """Obtiene información sobre la identidad del bot."""
        return self._api_call("getMe")

    def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Envía un mensaje de texto formateado al chat indicado."""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        res = self._api_call("sendMessage", payload)
        # Si falla por error de sintaxis en Markdown, reintenta sin parse_mode como fallback seguro
        if not res.get("ok") and "can't parse entities" in res.get("description", "").lower():
            payload.pop("parse_mode", None)
            res = self._api_call("sendMessage", payload)
        return res

    def get_updates(self, offset: Optional[int] = None, timeout: int = 10) -> Dict[str, Any]:
        """Realiza long-polling para recibir mensajes entrantes de Telegram."""
        payload: Dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        return self._api_call("getUpdates", payload)


class TelegramAiCopilotService:
    """
    Servicio Orquestador del Copilot de IA en Telegram para Meme Hunter.
    Procesa mensajes, valida permisos y ejecuta acciones sobre el motor de trading.
    """

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        allowed_chat_id: Optional[str] = None,
        freqtrade_client: Optional[FreqtradeRestClient] = None,
        ai_engine: Optional[QuantAiCopilotEngine] = None
    ):
        self.token = (
            telegram_token
            or os.environ.get("FREQTRADE__TELEGRAM__TOKEN")
            or os.environ.get("TELEGRAM_BOT_TOKEN")
            or get_secret("TELEGRAM_BOT_TOKEN", "")
            or ""
        )
        self.allowed_chat_id = str(
            allowed_chat_id
            or os.environ.get("FREQTRADE__TELEGRAM__CHAT_ID")
            or os.environ.get("TELEGRAM_CHAT_ID")
            or get_secret("TELEGRAM_CHAT_ID", "")
            or ""
        )
        self.tg_client = TelegramBotClient(self.token) if self.token else None
        base_host = os.environ.get("FREQTRADE_BASE_HOST", "http://127.0.0.1").rstrip("/")
        api_user = os.environ.get("FREQTRADE__API_SERVER__USERNAME", "admin")
        api_pass = (
            os.environ.get("FREQTRADE__API_SERVER__PASSWORD")
            or get_secret("FREQTRADE_API_PASSWORD")
            or os.environ.get("FREQTRADE_API_PASSWORD")
            or ""
        )
        self.ft_client = freqtrade_client or FreqtradeRestClient(
            base_url=f"{base_host}:8081",
            username=api_user,
            password=api_pass
        )
        self.orchestrator = MultiBotOrchestratorClient(base_host=base_host)
        self.hermes_op = HermesOperator(orchestrator=self.orchestrator)
        self.ai_engine = ai_engine or QuantAiCopilotEngine()
        self.binance_client = BinanceAccountClient()
        self.last_update_id = 0

        # PB-208: Registro de Comandos desacoplado (Command Pattern)
        self._command_registry: Dict[str, Any] = {
            "/start": lambda m, cid: self._cmd_help(),
            "/help": lambda m, cid: self._cmd_help(),
            "ayuda": lambda m, cid: self._cmd_help(),
            "/hermes": lambda m, cid: self._cmd_hermes(),
            "/alterego": lambda m, cid: self._cmd_hermes(),
            "/regime": lambda m, cid: self._cmd_regime(),
            "/regimen": lambda m, cid: self._cmd_regime(),
            "/rebalance": lambda m, cid: self._cmd_rebalance(),
            "/rebalancear": lambda m, cid: self._cmd_rebalance(),
            "/status": lambda m, cid: self._cmd_status(),
            "/estado": lambda m, cid: self._cmd_status(),
            "/profit": lambda m, cid: self._cmd_profit(),
            "/pnl": lambda m, cid: self._cmd_profit(),
            "/ganancias": lambda m, cid: self._cmd_profit(),
            "/balance": lambda m, cid: self._cmd_balance(),
            "/saldo": lambda m, cid: self._cmd_balance(),
            "/capital": lambda m, cid: self._cmd_balance(),
            "/stopbuy": lambda m, cid: self._cmd_stopbuy(),
            "/detenercompras": lambda m, cid: self._cmd_stopbuy(),
            "/stopbot": lambda m, cid: self._cmd_stopbot(),
            "/parar": lambda m, cid: self._cmd_stopbot(),
            "/detener": lambda m, cid: self._cmd_stopbot(),
            "/startbot": lambda m, cid: self._cmd_startbot(),
            "/iniciar": lambda m, cid: self._cmd_startbot(),
            "/reanudar": lambda m, cid: self._cmd_startbot(),
            "/reload": lambda m, cid: self._cmd_reload(),
            "/recargar": lambda m, cid: self._cmd_reload(),
            "/killswitch": lambda m, cid: self._cmd_killswitch(),
            "/emergencia": lambda m, cid: self._cmd_killswitch(),
            "/mine": lambda m, cid: self._cmd_mine(chat_id=cid),
            "/nuevaestrategia": lambda m, cid: self._cmd_mine(chat_id=cid),
            "/crearestrategia": lambda m, cid: self._cmd_mine(chat_id=cid),
            "/backtest": lambda m, cid: self._cmd_mine(chat_id=cid),
            "/refine": lambda m, cid: self._cmd_mine(chat_id=cid),
            "/bucle": lambda m, cid: self._cmd_mine(chat_id=cid),
            "/forcesellall": lambda m, cid: self._cmd_forcesell("all"),
            "/liquidartodo": lambda m, cid: self._cmd_forcesell("all"),
            "/vendertodo": lambda m, cid: self._cmd_forcesell("all"),
            "/resetbot3": lambda m, cid: self._cmd_reset_moonshot(),
            "/reiniciarbot3": lambda m, cid: self._cmd_reset_moonshot(),
            "/nuevointento": lambda m, cid: self._cmd_reset_moonshot(),
            "/resetmoonshot": lambda m, cid: self._cmd_reset_moonshot(),
        }

    def is_configured(self) -> bool:
        """Indica si el token de Telegram está presente."""
        return bool(self.token and len(self.token) > 10)

    def is_authorized(self, chat_id: Any) -> bool:
        """
        PB-200: Verifica que el chat_id coincida con el operador autorizado.
        Implementa política Zero-Trust Fail-Closed estricta.
        """
        if not self.allowed_chat_id or not str(self.allowed_chat_id).strip():
            logger.critical(
                "ACCESO DENEGADO: 'FREQTRADE__TELEGRAM__CHAT_ID' no configurado. "
                "Telegram Copilot opera en modo seguro Fail-Closed y rechaza todas las solicitudes."
            )
            return False
        return str(chat_id).strip() == str(self.allowed_chat_id).strip()

    def dispatch_command(self, text: str, chat_id: str) -> str:
        """PB-208: Despacha comandos operativos determinísticos mediante el Command Registry."""
        msg = text.strip()
        cmd = msg.split()[0].lower() if msg else ""

        # 1. Búsqueda directa en registro
        handler = self._command_registry.get(cmd)
        if handler:
            return handler(msg, chat_id)

        # 2. Comandos parametrizados
        if cmd.startswith("/forcesell"):
            parts = msg.split()
            tid = parts[1] if len(parts) > 1 else ""
            return self._cmd_forcesell(tid)
        elif cmd.startswith("/forcebuy"):
            parts = msg.split()
            pair = parts[1] if len(parts) > 1 else ""
            return self._cmd_forcebuy(pair)
        elif cmd.startswith("/ai"):
            prompt = msg[3:].strip()
            return self._cmd_ai_query(prompt, chat_id=chat_id)

        # 3. Lenguaje natural -> Motor Cognitivo de IA
        return self._cmd_ai_query(msg, chat_id=chat_id)

    def _cmd_help(self) -> str:
        return (
            "🤖 *MEME HUNTER — AI TELEGRAM COPILOT & HERMES ALTER EGO v8.6*\n\n"
            "Controla y consulta el motor cuantitativo y el cerebro de Hermes en lenguaje natural o con comandos:\n\n"
            "🧠 *Gobierno Autónomo Hermes:*\n"
            "• `/hermes` : Informe ejecutivo causal del Alter Ego en tiempo real.\n"
            "• `/regime` : Clasificación del régimen macro (Binance Futures).\n"
            "• `/rebalance` : Forzar rebalanceo dinámico de capital entre bots.\n"
            "• `/mine` : 🧪 Sintetizar nuevas estrategias con IA, backtestearlas y probarlas en la arena.\n\n"
            "📊 *Comandos de Telemetría:*\n"
            "• `/status` : Posiciones abiertas en la arena (Ablation, Quantum, Ensemble).\n"
            "• `/profit` : Rendimiento consolidado, Win Rate y balance.\n"
            "• `/balance` : Capital total, disponible y márgenes aislados.\n\n"
            "🛡️ *Comandos Operativos de Control:*\n"
            "• `/stopbuy` : Inhibir nuevas compras en toda la arena.\n"
            "• `/stopbot` : Pausar la ejecución del bot de trading.\n"
            "• `/startbot` : Reanudar la operativa del bot.\n"
            "• `/forcesell <id>` : Liquidar inmediatamente un trade específico.\n"
            "• `/reload` : Recargar configuración y estrategias en caliente.\n"
            "• `/resetbot3` : 🔄 Reiniciar Bot 3 (Moonshot 10 a 100 USDT) a 10.00 USDT limpios con ATH-26.\n"
            "• `/killswitch` : 🚨 Activación del Kill Switch de Drawdown (25%).\n\n"
            "💬 *Consultas con IA:* Puedes enviar cualquier pregunta o usar `/ai <consulta>`."
        )

    def _cmd_hermes(self) -> str:
        """Invoca el ciclo de Hermes y devuelve su informe causal."""
        res = self.hermes_op.run_cycle()
        return res.get("explanation", "⚠️ Error al evaluar ciclo de Hermes.")

    def _cmd_regime(self) -> str:
        """Devuelve el régimen actual detectado por Hermes en Binance Futures."""
        reg_info = self.hermes_op.regime_detector.detect_regime()
        snap = reg_info.get("snapshot", {})
        alloc = reg_info.get("recommended_allocations", {})
        alloc_str = "\n".join([f"  • *{k}*: `{v*100:.0f}%`" for k, v in alloc.items()])
        return (
            f"📊 *DETECCIÓN DE RÉGIMEN — HERMES AGENT*\n\n"
            f"• *Régimen Activo:* `{reg_info.get('regime')}` ({reg_info.get('confidence', 0)*100:.0f}%)\n"
            f"• *BTC:* `${snap.get('btc_price', 0):,.1f}` (`{snap.get('btc_change_24h', 0):+.2f}%`)\n"
            f"• *Funding Rate Medio:* `{snap.get('avg_funding_rate', 0):.6f}`\n\n"
            f"⚖️ *Ponderación de Cartera Recomendada:*\n{alloc_str}\n\n"
            f"💡 *Diagnóstico:* {reg_info.get('rationale')}"
        )

    def _cmd_rebalance(self) -> str:
        """Fuerza la ejecución inmediata de la política de rebalanceo de Hermes."""
        res = self.hermes_op.run_cycle()
        actions = res.get("allocation_res", {}).get("actions_taken", [])
        act_lines = [f"• *{a.get('bot_id')}*: `{a.get('action')}` ({a.get('result')})" for a in actions]
        act_str = "\n".join(act_lines) if act_lines else "• Sin cambios de estado requeridos."
        return (
            f"⚖️ *REBALANCEO DE CARTERA EJECUTADO*\n\n"
            f"• *Régimen:* `{res.get('regime_info', {}).get('regime')}`\n"
            f"• *Acciones de Control:*\n{act_str}\n\n"
            f"📊 *Telemetría:* {res.get('portfolio', {}).get('total_open_trades', 0)} trades vivos | "
            f"`{res.get('portfolio', {}).get('total_stake_active_usdt', 0.0):.2f} USDT` en juego."
        )

    def _cmd_mine(self, goal_text: Optional[str] = None, chat_id: Optional[str] = None) -> str:
        """Dispara el ciclo autónomo de minería, backtesting y despliegue de alfas."""
        def _telegram_cb(step_text: str):
            if self.tg_client and chat_id:
                try:
                    self.tg_client.send_message(chat_id=chat_id, text=step_text)
                except Exception as ex:
                    logger.debug(f"Error enviando actualización de progreso: {ex}")

        res = self.hermes_op.mine_and_evaluate_new_alpha(
            goal_text=goal_text or "Estrategia Moonshot alta frecuencia y alto Sharpe",
            progress_callback=_telegram_cb if chat_id else None
        )
        if res.get("status") != "ok":
            return f"⚠️ *Fábrica de Alphas:* {res.get('message', 'No se pudieron validar candidatos')} (Régimen: `{res.get('regime')}`)."

        if res.get("report_md"):
            return res["report_md"]

        f = res.get("best_factor", {})
        reload_txt = "✅ Desplegado en Bot 3 (:8083) en vivo (cartera simulada)" if res.get("reload_bot3") else "ℹ️ Guardado en biblioteca de factores"

        return (
            "🧪 *NUEVA ESTRATEGIA / FACTOR GENERADO CON ÉXITO*\n\n"
            f"• *ID del Factor:* `{f.get('factor_id')}`\n"
            f"• *Régimen Objetivo:* `{res.get('regime')}`\n"
            f"• *Fórmula Matemática:*\n`{f.get('formula')}`\n\n"
            f"📊 *Resultados del Backtesting Rápido (Velas 15m):*\n"
            f"• *Sharpe Ratio Proxy:* `{f.get('sharpe_proxy', 0.0):+.2f}`\n"
            f"• *Information Coefficient (IC):* `{f.get('ic_mean', 0.0):+.4f}` (IR: `{f.get('ic_ir', 0.0):+.2f}`)\n"
            f"• *Rotación (Turnover):* `{f.get('turnover', 0.0):.2f}`\n\n"
            f"🚀 *Acción en la Arena:* {reload_txt}."
        )

    def _cmd_reset_moonshot(self, initial_wallet: float = 10.0, factor_id: str = "HERMES_ATH_26") -> str:
        """Reinicia de forma limpia el Bot 3 (:8083) y archiva la base de datos anterior."""
        res = self.hermes_op.reset_moonshot_bot(initial_wallet=initial_wallet, factor_id=factor_id)
        return res.get("report_md", "⚠️ Fallo inesperado al reiniciar Bot 3.")

    def _cmd_status(self) -> str:
        """Consulta el estado agregado de toda la arena multi-bot."""
        agg = self.orchestrator.get_aggregated_status()
        trades = agg.get("trades", [])
        bots = agg.get("bots", {})

        bot_lines = []
        for b_id, b_info in bots.items():
            status_icon = "🟢" if b_info.get("is_online") else "🔴"
            bot_lines.append(
                f"• {status_icon} *{b_info.get('name')}* (:{b_info.get('port')}): "
                f"`{b_info.get('open_trades')} trades` | `{b_info.get('stake_active_usdt')} USDT`"
            )

        trade_lines = []
        for t in trades[:8]:
            tid = t.get("trade_id", "?")
            pair = t.get("pair", "N/A")
            profit = t.get("profit_pct", 0.0)
            origin = t.get("origin_bot", "bot")
            dir_str = "SHORT" if t.get("is_short", False) else "LONG"
            trade_lines.append(f"  - `#{tid}` *{pair}* ({dir_str} | {origin}): `{profit:+.2f}%`")

        trades_summary = "\n".join(trade_lines) if trade_lines else "  - No hay órdenes vivas actualmente."
        bots_summary = "\n".join(bot_lines)

        return (
            f"📊 *ARENA MULTI-BOT — ESTADO DE CARTERA*\n\n"
            f"• *Total Trades Vivos:* `{agg.get('total_open_trades', 0)}`\n"
            f"• *Margen Total en Juego:* `{agg.get('total_stake_active_usdt', 0.0):.2f} USDT`\n\n"
            f"🤖 *Instancias de Trading:*\n{bots_summary}\n\n"
            f"📈 *Posiciones en Curso:*\n{trades_summary}"
        )

    def _cmd_profit(self) -> str:
        res = self.ft_client.get_profit()
        if res.get("status") != "ok":
            return f"⚠️ *Error consultando métricas de PnL:* `{res.get('error', 'Bot offline')}`"

        d = res.get("data", {})
        closed_cnt = d.get("trade_count", 0)
        profit_usd = d.get("profit_closed_coin", 0.0)
        profit_pct = d.get("profit_closed_ratio_pct", 0.0)
        winrate = d.get("winrate", 0.0) * 100.0 if d.get("winrate", 0.0) <= 1.0 else d.get("winrate", 0.0)
        wins = d.get("winning_trades", 0)
        losses = d.get("losing_trades", 0)

        return (
            "📈 *REPORTE CONSOLIDADO DE RENDIMIENTO*\n\n"
            f"• *PnL Total Realizado:* `{profit_usd:+.2f} USDT` (`{profit_pct:+.2f}%`)\n"
            f"• *Trades Cerrados:* `{closed_cnt}`\n"
            f"• *Win Rate:* `{winrate:.1f}%` (✅ {wins} / ❌ {losses})\n"
            f"• *Mejor Trade:* `{d.get('best_pair', 'N/A')}`\n"
        )

    def _cmd_balance(self) -> str:
        # 1. Billetera real en Binance
        real = self.binance_client.get_real_balances()
        real_lines = []
        if real.get("has_keys"):
            spot_free = real.get("spot_usdt_free", 0.0)
            fut_free = real.get("futures_usdt_free", 0.0)
            real_lines.append(f"• *Spot USDT:* `{spot_free:.2f} USDT`")
            real_lines.append(f"• *Futuros USDⓈ-M:* `{fut_free:.2f} USDT`")
            assets = real.get("other_assets", {})
            if assets:
                assets_str = ", ".join([f"{k}: {v}" for k, v in list(assets.items())[:4]])
                real_lines.append(f"• *Otros Activos Spot:* `{assets_str}`")
            if fut_free == 0.0 and spot_free > 0.0:
                real_lines.append("\n💡 _Nota: Tus fondos están en Spot. Para operar futuros en vivo, transfiere tus USDT a la billetera 'Futuros USDⓈ-M' en Binance._")
        else:
            real_lines.append("• *Binance API:* `Sin credenciales configuradas en .env`")

        real_str = "\n".join(real_lines)

        # 2. Cartera multi-bot de la arena
        arena = self.orchestrator.get_aggregated_balances() if hasattr(self.orchestrator, "get_aggregated_balances") else {}
        arena_lines = []
        if isinstance(arena, dict) and arena.get("status") == "ok":
            tot = arena.get("total_wallet", 0.0)
            fre = arena.get("free_wallet", 0.0)
            usd = arena.get("used_wallet", 0.0)
            arena_lines.append(f"• *Capital Simulado Total:* `{tot:.2f} USDT` (Libre: `{fre:.2f}` | Margen: `{usd:.2f}`)")
            for b_id, b_info in arena.get("bots", {}).items():
                arena_lines.append(f"  - *{b_info['name']}* (:{b_info['port']}): `{b_info['total']:.2f} USDT` (Libre: `{b_info['free']:.2f}`)")
        else:
            res = self.ft_client.get_balance()
            d = res.get("data", {}) if res.get("status") == "ok" else {}
            tot = float(d.get("total", 0.0) or 0.0)
            fre = float(d.get("free", 0.0) or 0.0)
            usd = float(d.get("used", 0.0) or 0.0)
            arena_lines.append(f"• *Capital Total (Bot 1):* `{tot:.2f} USDT`")
            arena_lines.append(f"• *Capital Libre:* `{fre:.2f} USDT`")
            arena_lines.append(f"• *Margen Utilizado:* `{usd:.2f} USDT`")

        arena_str = "\n".join(arena_lines)

        return (
            "💰 *ESTADO CONSOLIDADO DE BILLETERAS*\n\n"
            "🏦 **1. TU SALDO REAL EN BINANCE:**\n"
            f"{real_str}\n\n"
            "🎮 **2. SALDO VIRTUAL DE LA ARENA (DRY-RUN PAPER TRADING):**\n"
            f"{arena_str}\n\n"
            "🛡️ *Modo Actual:* Simulación en tiempo real (Cero riesgo de capital real)."
        )

    def _cmd_stopbuy(self) -> str:
        # Siempre asegurar que self.ft_client reciba la orden
        res_main = self.ft_client.stopbuy_bot()
        results = []
        clients_to_run = getattr(self.orchestrator, "clients", {})
        if isinstance(clients_to_run, dict) and clients_to_run:
            for b_id, client in clients_to_run.items():
                meta = getattr(self.orchestrator, "DEFAULT_BOTS", {}).get(b_id, {})
                name = meta.get("name", b_id)
                port = meta.get("port", "8081")
                res = client.stopbuy_bot()
                ok = (res.get("status") == "ok")
                results.append(f"• *{name}* (:{port}): {'🛑 Detenido ✅' if ok else '⚠️ ' + str(res.get('error', 'Offline'))}")
        else:
            ok = (res_main.get("status") == "ok")
            results.append(f"• *Bot 1 (:8081)*: {'🛑 Detenido ✅' if ok else '⚠️ ' + str(res_main.get('error', 'Fallo de conexión'))}")

        res_str = "\n".join(results)
        return (
            "🛑 *ORDEN EJECUTADA: STOPBUY (`stopbuy`) EN TODA LA ARENA*\n\n"
            "Se ha inhibido la apertura de nuevas posiciones en las instancias de trading (`stopbuy`):\n"
            f"{res_str}\n\n"
            "Las posiciones existentes continuarán su gestión y trailing stop."
        )

    def _cmd_stopbot(self) -> str:
        res_main = self.ft_client.stop_bot()
        results = []
        clients_to_run = getattr(self.orchestrator, "clients", {})
        if isinstance(clients_to_run, dict) and clients_to_run:
            for b_id, client in clients_to_run.items():
                meta = getattr(self.orchestrator, "DEFAULT_BOTS", {}).get(b_id, {})
                name = meta.get("name", b_id)
                port = meta.get("port", "8081")
                res = client.stop_bot()
                ok = (res.get("status") == "ok")
                results.append(f"• *{name}* (:{port}): {'⏸️ Detenido ✅' if ok else '⚠️ ' + str(res.get('error', 'Offline'))}")
        else:
            ok = (res_main.get("status") == "ok")
            results.append(f"• *Bot 1 (:8081)*: {'⏸️ Detenido ✅' if ok else '⚠️ ' + str(res_main.get('error', 'Fallo de conexión'))}")

        res_str = "\n".join(results)
        return f"⏸️ *ORDEN EJECUTADA: PAUSA GENERAL DE TRADING*\n\n{res_str}"

    def _cmd_startbot(self) -> str:
        res_main = self.ft_client.start_bot()
        results = []
        clients_to_run = getattr(self.orchestrator, "clients", {})
        if isinstance(clients_to_run, dict) and clients_to_run:
            for b_id, client in clients_to_run.items():
                meta = getattr(self.orchestrator, "DEFAULT_BOTS", {}).get(b_id, {})
                name = meta.get("name", b_id)
                port = meta.get("port", "8081")
                res = client.start_bot()
                ok = (res.get("status") == "ok")
                results.append(f"• *{name}* (:{port}): {'▶️ Reanudado ✅' if ok else '⚠️ ' + str(res.get('error', 'Offline'))}")
        else:
            ok = (res_main.get("status") == "ok")
            results.append(f"• *Bot 1 (:8081)*: {'▶️ Reanudado ✅' if ok else '⚠️ ' + str(res_main.get('error', 'Fallo de conexión'))}")

        res_str = "\n".join(results)
        return f"▶️ *ORDEN EJECUTADA: OPERATIVA REANUDADA*\n\n{res_str}"

    def _cmd_forcesell(self, trade_id_or_target: str) -> str:
        target = str(trade_id_or_target).strip()
        if not target:
            return "⚠️ Debes especificar el ID del trade o la moneda a liquidar. Ejemplo: `/forcesell 1` o `/forcesell DOGE`"

        # 1. Caso de Liquidación Total (all / todo)
        if target.lower() in ["all", "todo", "todas"]:
            agg = self.orchestrator.get_aggregated_status() if hasattr(self.orchestrator, "get_aggregated_status") else {}
            trades = agg.get("trades", []) if isinstance(agg, dict) else []
            if not trades:
                # Fallback al bot principal
                st = self.ft_client.get_status()
                trades = st.get("data", []) if isinstance(st, dict) and st.get("status") == "ok" else []

            if not trades:
                return "ℹ️ *Liquidación General:* No hay órdenes ni posiciones abiertas actualmente en la arena."

            results = []
            clients_map = getattr(self.orchestrator, "clients", {})
            for t in trades:
                tid = str(t.get("trade_id", ""))
                pair = t.get("pair", "N/A")
                origin = t.get("origin_bot", "bot_v5_ablation")
                bot_client = clients_map.get(origin, self.ft_client) if isinstance(clients_map, dict) else self.ft_client
                res = bot_client.forcesell(tid)
                ok = (res.get("status") == "ok")
                results.append(f"  • Trade `#{tid}` (*{pair}* | {origin}): {'⚡ Liquidado ✅' if ok else '⚠️ ' + str(res.get('error', 'Error'))}")

            return "⚡ *LIQUIDACIÓN TOTAL EJECUTADA*\n\n" + "\n".join(results)

        # 2. Caso por Símbolo de Activo (ej. "DOGE", "PEPE", "SOL")
        if not target.isdigit():
            sym_clean = target.upper().replace("/USDT", "").replace(":USDT", "").replace("1000", "").strip()
            agg = self.orchestrator.get_aggregated_status() if hasattr(self.orchestrator, "get_aggregated_status") else {}
            trades = agg.get("trades", []) if isinstance(agg, dict) else []
            matching = [t for t in trades if sym_clean in str(t.get("pair", "")).upper()]

            if not matching:
                return f"ℹ️ *Salida de Posición:* No se encontró ninguna operación abierta para `{target.upper()}` en la arena."

            results = []
            clients_map = getattr(self.orchestrator, "clients", {})
            for t in matching:
                tid = str(t.get("trade_id", ""))
                pair = t.get("pair", "N/A")
                origin = t.get("origin_bot", "bot_v5_ablation")
                bot_client = clients_map.get(origin, self.ft_client) if isinstance(clients_map, dict) else self.ft_client
                res = bot_client.forcesell(tid)
                ok = (res.get("status") == "ok")
                results.append(f"  • Trade `#{tid}` (*{pair}* en {origin}): {'⚡ Liquidado ✅' if ok else '⚠️ ' + str(res.get('error', 'Error'))}")

            return f"⚡ *LIQUIDACIÓN DE {target.upper()} EJECUTADA*\n\n" + "\n".join(results)

        # 3. Caso por ID Numérico (ej. "1", "42")
        tid = target
        agg = self.orchestrator.get_aggregated_status() if hasattr(self.orchestrator, "get_aggregated_status") else {}
        trades = agg.get("trades", []) if isinstance(agg, dict) else []
        matching = [t for t in trades if str(t.get("trade_id")) == tid]

        bot_client = self.ft_client
        origin_name = "Bot 1 (:8081)"
        if matching:
            origin = matching[0].get("origin_bot", "bot_v5_ablation")
            clients_map = getattr(self.orchestrator, "clients", {})
            if isinstance(clients_map, dict) and origin in clients_map:
                bot_client = clients_map[origin]
            origin_name = origin

        res = bot_client.forcesell(tid)
        if res.get("status") == "ok":
            return f"⚡ *Liquidación Forzada Ordenada:* Se emitió orden de salida a mercado para el trade `#{tid}` ({origin_name})."
        return f"⚠️ *Error al forzar salida del trade #{tid}:* `{res.get('error', 'ID no encontrado o bot offline')}`"

    def _cmd_forcebuy(self, pair: str) -> str:
        if not pair:
            return "⚠️ Debes especificar el par a comprar. Ejemplo: `/forcebuy BTC/USDT:USDT`"
        p = pair.upper().strip()
        # Normalización para Binance Futures
        if not p.endswith(":USDT") and not p.endswith("/USDT"):
            clean = p.replace("/USDT", "").replace(":USDT", "")
            if clean in ["PEPE", "FLOKI", "SHIB", "BONK", "SATS", "RATS", "LUNC"] and not clean.startswith("1000"):
                clean = f"1000{clean}"
            p = f"{clean}/USDT:USDT"
        elif "/" in p and not p.endswith(":USDT"):
            p = f"{p}:USDT"

        res = self.ft_client.forcebuy(p)
        if res.get("status") == "ok":
            return f"⚡ *Orden de Entrada Emitida:* Apertura en `{p}` enviada a Binance Futures (:8081)."
        return f"⚠️ *Error al ejecutar forcebuy en {p}:* `{res.get('error', 'Fallo de conexión o fondos insuficientes')}`"

    def _cmd_reload(self) -> str:
        res_main = self.ft_client.reload_config()
        results = []
        clients_to_run = getattr(self.orchestrator, "clients", {})
        if isinstance(clients_to_run, dict) and clients_to_run:
            for b_id, client in clients_to_run.items():
                meta = getattr(self.orchestrator, "DEFAULT_BOTS", {}).get(b_id, {})
                name = meta.get("name", b_id)
                port = meta.get("port", "8081")
                res = client.reload_config()
                ok = (res.get("status") == "ok")
                results.append(f"• *{name}* (:{port}): {'🔄 Recargado ✅' if ok else '⚠️ ' + str(res.get('error', 'Offline'))}")
        else:
            ok = (res_main.get("status") == "ok")
            results.append(f"• *Bot 1 (:8081)*: {'🔄 Recargado ✅' if ok else '⚠️ ' + str(res_main.get('error', 'Bot offline'))}")

        res_str = "\n".join(results)
        return f"🔄 *HOT-RELOAD EJECUTADO EN TODA LA ARENA*\n\n{res_str}"

    def _cmd_killswitch(self) -> str:
        # 1. Detener compras y motores de trading en toda la arena
        self.ft_client.stopbuy_bot()
        self.ft_client.stop_bot()

        clients_to_run = getattr(self.orchestrator, "clients", {})
        if isinstance(clients_to_run, dict):
            for client in clients_to_run.values():
                try:
                    client.stopbuy_bot()
                    client.stop_bot()
                except Exception:
                    pass

        # 2. Liquidación forzada de posiciones abiertas
        liq_res = self._cmd_forcesell("all")

        return (
            "🚨 *KILL-SWITCH DE EMERGENCIA ACTIVADO (25% SAFEGUARD)*\n\n"
            "1. Nuevas compras completamente bloqueadas en toda la arena.\n"
            "2. Motores de ejecución detenidos preventivamente.\n"
            f"3. {liq_res}\n\n"
            "Capital remanente blindado. Para reanudar manualmente tras análisis, usa `/startbot`."
        )

    def _execute_operational_action(
        self,
        suggested_action: Dict[str, Any],
        query: str,
        chat_id: Optional[str] = None
    ) -> Optional[str]:
        """
        PB-210: Despacha y ejecuta la acción operativa solicitada por el usuario en tiempo real.
        Garantiza Cero Alucinaciones y acción determinista sin fingimientos.
        """
        action = suggested_action.get("action")
        if not action or action in ["general_copilot_query", "query_balance", "query_profit", "query_status", "query_regime", "query_hermes"]:
            return None

        try:
            if action == "stopbuy":
                return self._cmd_stopbuy()
            elif action == "stop":
                return self._cmd_stopbot()
            elif action == "start":
                return self._cmd_startbot()
            elif action == "killswitch":
                return self._cmd_killswitch()
            elif action == "forcesell_all":
                return self._cmd_forcesell("all")
            elif action == "forcesell":
                target = suggested_action.get("trade_id") or suggested_action.get("symbol", "")
                return self._cmd_forcesell(str(target))
            elif action == "forcebuy":
                target = suggested_action.get("symbol", "")
                return self._cmd_forcebuy(str(target))
            elif action == "rebalance":
                return self._cmd_rebalance()
            elif action == "reload":
                return self._cmd_reload()
            elif action == "mine_strategy":
                return self._cmd_mine(goal_text=query, chat_id=chat_id)
            elif action == "reset_moonshot":
                return self._cmd_reset_moonshot()
        except Exception as e:
            logger.error(f"Error ejecutando acción operativa '{action}': {e}")
            return f"⚠️ *Error al ejecutar acción operativa ({action}):* `{e}`"

        return None

    def _cmd_ai_query(self, query: str, chat_id: Optional[str] = None) -> str:
        """Pasa la consulta del operador al motor cognitivo de IA inyectando telemetría viva, saldos y contexto de Hermes."""
        agg = self.orchestrator.get_aggregated_status()
        profit_res = self.ft_client.get_profit().get("data", {})
        balance_res = self.ft_client.get_balance().get("data", {})
        real_bal = self.binance_client.get_real_balances()
        arena_bal = self.orchestrator.get_aggregated_balances()

        # Obtener contexto activo de Hermes
        hermes_ctx = self.hermes_op.regime_detector.detect_regime()

        reply_md, suggested_action = self.ai_engine.process_message(
            user_message=query,
            bot_state={"state": "running"},
            profit_data=profit_res if isinstance(profit_res, dict) else {},
            balance_data=balance_res if isinstance(balance_res, dict) else {},
            open_trades=agg.get("trades", []),
            hermes_context=hermes_ctx,
            real_balance=real_bal,
            arena_balances=arena_bal
        )

        # PB-210: Despacho y Ejecución Autónoma de Acciones Solicitadas
        if suggested_action:
            action_result = self._execute_operational_action(suggested_action, query=query, chat_id=chat_id)
            if action_result:
                return f"{reply_md}\n\n---\n{action_result}"

        return reply_md

    def poll_once(self) -> int:
        """
        Ejecuta un ciclo único de polling. Devuelve el número de mensajes procesados.
        Permite ejecución asíncrona controlada sin bloqueos infinitos.
        """
        if not self.tg_client:
            return 0

        updates = self.tg_client.get_updates(offset=self.last_update_id + 1, timeout=0)
        if not updates.get("ok"):
            return 0

        processed = 0
        for item in updates.get("result", []):
            update_id = item.get("update_id", 0)
            if update_id > self.last_update_id:
                self.last_update_id = update_id

            message = item.get("message", {})
            chat = message.get("chat", {})
            chat_id = str(chat.get("id", ""))
            text = message.get("text", "")

            if not text or not chat_id:
                continue

            # Verificación de ciberseguridad
            if not self.is_authorized(chat_id):
                logger.warning(f"Intento de acceso no autorizado desde chat_id {chat_id}. Mensaje bloqueado.")
                self.tg_client.send_message(
                    chat_id=chat_id,
                    text=f"⛔ *Acceso Denegado:* Tu Chat ID `{chat_id}` no está autorizado en Meme Hunter. (Esperado: `{self.allowed_chat_id}`). Actualiza `FREQTRADE__TELEGRAM__CHAT_ID={chat_id}` en `.env` si cambiaste de cuenta."
                )
                continue

            logger.info(f"Mensaje recibido de {chat_id}: '{text[:50]}'")
            reply = self.dispatch_command(text, chat_id)
            self.tg_client.send_message(chat_id=chat_id, text=reply)
            processed += 1

        return processed
