"""
meme_hunter.execution.multi_bot_orchestrator - Conector y Orquestador de Telemetría Multi-Bot.

Permite al Agente Autónomo Hermes monitorear y controlar en tiempo real
las instancias de trading aisladas en la arena A/B de Meme Hunter:
- Bot 1 (:8081): MemeHunterFuturesV5_Ablation (Shorts Asimétricos)
- Bot 2 (:8082): MemeHunterFuturesV7_Quantum (Gestión Kelly & Bajo Drawdown)
- Bot 3 (:8083): MemeHunter_MinedEnsemble (Ensamble Multi-Factor HRP)
"""

import os
import logging
from typing import Dict, Any, List, Optional
from meme_hunter.execution.freqtrade_client import FreqtradeRestClient

try:
    from portfolio.secrets_vault import get_secret
except ImportError:
    get_secret = lambda k, default="": os.getenv(k, default)

logger = logging.getLogger("MultiBotOrchestrator")


class MultiBotOrchestratorClient:
    """
    Cliente orquestador unificado que agrega la telemetría y ejecuta
    órdenes de control simultáneas sobre todos los bots de la arena.
    """

    DEFAULT_BOTS = {
        "bot_v5_ablation": {
            "name": "MemeHunterFuturesV5_Ablation",
            "port": 8081,
            "role": "short_sniper",
            "db": "tradesv3.ablation_100u.sqlite"
        },
        "bot_v7_quantum": {
            "name": "MemeHunterFuturesV7_Quantum",
            "port": 8082,
            "role": "kelly_guardian",
            "db": "tradesv3.quantum_100u.sqlite"
        },
        "bot_mined_ensemble": {
            "name": "MemeHunter_MinedEnsemble",
            "port": 8083,
            "role": "multi_factor_hrp",
            "db": "tradesv3.ensemble_100u.sqlite"
        }
    }

    def __init__(
        self,
        base_host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout_sec: float = 4.0
    ):
        try:
            from meme_hunter.core.config import get_settings
            settings = get_settings()
            cfg_user = settings.FREQTRADE_API_USERNAME
            cfg_pass = settings.get_raw_secret(settings.FREQTRADE_API_PASSWORD) or ""
            cfg_url = settings.FREQTRADE_API_URL
        except Exception:
            cfg_user = "admin"
            cfg_pass = ""
            cfg_url = "http://127.0.0.1"

        default_host = os.getenv("FREQTRADE_BASE_HOST", cfg_url.rsplit(":", 1)[0] if ":" in cfg_url else "http://127.0.0.1")
        self.base_host = (base_host or default_host).rstrip("/")
        self.username = username or cfg_user or get_secret("FREQTRADE_API_USER") or "admin"
        self.password = (
            password
            or cfg_pass
            or os.environ.get("FREQTRADE__API_SERVER__PASSWORD")
            or get_secret("FREQTRADE_API_PASSWORD")
            or os.environ.get("FREQTRADE_API_PASSWORD")
            or ""
        )
        self.timeout_sec = float(timeout_sec)

        self.clients: Dict[str, FreqtradeRestClient] = {}
        for bot_id, cfg in self.DEFAULT_BOTS.items():
            url = f"{self.base_host}:{cfg['port']}"
            self.clients[bot_id] = FreqtradeRestClient(
                base_url=url,
                username=self.username,
                password=self.password,
                timeout_sec=self.timeout_sec
            )

    def ping_all(self) -> Dict[str, bool]:
        """Verifica la salud y respuesta HTTP de todos los bots."""
        results = {}
        for bot_id, client in self.clients.items():
            res = client.ping()
            results[bot_id] = (res.get("status") == "ok")
        return results

    def get_aggregated_status(self) -> Dict[str, Any]:
        """
        Recopila telemetría agregada de los 3 bots:
        - Total de operaciones vivas
        - Desglose por bot
        - Capital flotante y exposición
        """
        all_trades: List[Dict[str, Any]] = []
        bot_summaries: Dict[str, Any] = {}
        total_open_trades = 0
        total_stake_active = 0.0

        for bot_id, client in self.clients.items():
            meta = self.DEFAULT_BOTS[bot_id]
            st = client.get_status()
            cnt = client.get_count()
            
            is_online = (st.get("status") == "ok")
            trades = st.get("data", []) if is_online else []
            count_data = cnt.get("data", {}) if cnt.get("status") == "ok" else {}

            bot_trades_count = count_data.get("current", len(trades))
            bot_stake_active = float(count_data.get("total_stake", 0.0))
            
            for t in trades:
                t_copy = dict(t)
                t_copy["origin_bot"] = bot_id
                t_copy["strategy_name"] = meta["name"]
                all_trades.append(t_copy)

            total_open_trades += bot_trades_count
            total_stake_active += bot_stake_active

            bot_summaries[bot_id] = {
                "name": meta["name"],
                "role": meta["role"],
                "port": meta["port"],
                "is_online": is_online,
                "open_trades": bot_trades_count,
                "stake_active_usdt": round(bot_stake_active, 4)
            }

        return {
            "status": "ok",
            "total_open_trades": total_open_trades,
            "total_stake_active_usdt": round(total_stake_active, 4),
            "bots": bot_summaries,
            "trades": all_trades
        }

    def stopbuy_bot(self, bot_id: str) -> Dict[str, Any]:
        """Pausa la apertura de nuevas posiciones en un bot específico."""
        if bot_id not in self.clients:
            return {"status": "error", "error": f"Bot {bot_id} desconocido"}
        return self.clients[bot_id].stopbuy_bot()

    def start_bot(self, bot_id: str) -> Dict[str, Any]:
        """Reanuda la operativa y compras en un bot específico."""
        if bot_id not in self.clients:
            return {"status": "error", "error": f"Bot {bot_id} desconocido"}
        return self.clients[bot_id].start_bot()

    def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """Detiene un bot de forma segura."""
        if bot_id not in self.clients:
            return {"status": "error", "error": f"Bot {bot_id} desconocido"}
        return self.clients[bot_id].stop_bot()

    def pause_all_shorts(self) -> Dict[str, Any]:
        """Pausa preventiva de entradas Short en toda la arena (ej. Bull Run detectado)."""
        res = {}
        for bot_id in ["bot_v5_ablation", "bot_v7_quantum"]:
            res[bot_id] = self.clients[bot_id].stopbuy_bot()
        return {"action": "pause_all_shorts", "results": res}

    def resume_all_shorts(self) -> Dict[str, Any]:
        """Reanuda la búsqueda de shorts en la arena (ej. Cascada detectada)."""
        res = {}
        for bot_id in ["bot_v5_ablation", "bot_v7_quantum"]:
            res[bot_id] = self.clients[bot_id].start_bot()
        return {"action": "resume_all_shorts", "results": res}

    def get_aggregated_balances(self) -> Dict[str, Any]:
        """
        Recopila los saldos de los 3 bots de la arena (Dry-Run / Simulado)
        y calcula el balance total de la cartera multi-bot.
        """
        bots_balance: Dict[str, Any] = {}
        total_wallet = 0.0
        free_wallet = 0.0
        used_wallet = 0.0

        for bot_id, client in self.clients.items():
            meta = self.DEFAULT_BOTS[bot_id]
            res = client.get_balance()
            if res.get("status") == "ok":
                d = res.get("data", {})
                b_tot = float(d.get("total", 0.0) or 0.0)
                b_free = float(d.get("free", 0.0) or 0.0)
                b_used = float(d.get("used", 0.0) or 0.0)
                total_wallet += b_tot
                free_wallet += b_free
                used_wallet += b_used
                bots_balance[bot_id] = {
                    "name": meta["name"],
                    "port": meta["port"],
                    "total": round(b_tot, 2),
                    "free": round(b_free, 2),
                    "used": round(b_used, 2),
                    "is_online": True
                }
            else:
                bots_balance[bot_id] = {
                    "name": meta["name"],
                    "port": meta["port"],
                    "total": 0.0,
                    "free": 0.0,
                    "used": 0.0,
                    "is_online": False
                }

        return {
            "status": "ok",
            "total_wallet": round(total_wallet, 2),
            "free_wallet": round(free_wallet, 2),
            "used_wallet": round(used_wallet, 2),
            "bots": bots_balance
        }


__all__ = ["MultiBotOrchestratorClient"]
