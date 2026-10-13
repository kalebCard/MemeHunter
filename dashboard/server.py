"""
Servidor HTTP y API REST Liviano para el MemeHunter Alpha Cockpit Dashboard.
Sprint 3: Monitoreo Visual e Interfaz de Control Cuantitativo.

No requiere dependencias externas; utiliza el módulo estándar `http.server`.
Provee:
- Servidor de archivos estáticos para la interfaz (HTML, CSS, JS).
- Endpoints REST `/api/status`, `/api/trigger-loop`, `/api/synthesize-alpha`.
"""

import os
import sys
import json
import time
import logging
import hashlib
import hmac
import secrets
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, Optional, Set

# Asegurar path raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from portfolio.alpha_health_monitor import AlphaHealthMonitor
from portfolio.autonomous_orchestrator import AutonomousPortfolioOrchestrator
from portfolio.alpha_autopsy import AlphaAutopsyAgent
from mining.alpha_daemon import AlphaMinerDaemon
from mining.llm_alpha_generator import LLMAlphaSynthesizer
from mining.llm_client import OpenRouterClient
from portfolio.atomic_io import atomic_write_json
from portfolio.secrets_vault import get_secret
from dashboard.backtest_scanner import (
    scan_strategies,
    scan_backtest_results,
    load_stress_and_monte_carlo,
    get_live_trades_from_db
)

logger = logging.getLogger("CockpitServer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
INSECURE_DEFAULT_TOKEN = "meme_hunter_dev_token_2026"
MIN_TOKEN_LENGTH = 32


class TokenBucketRateLimiter:
    """Limitador de tasa por IP en memoria para proteger endpoints de mutación REST (Sprint 1: US-1.3)."""

    def __init__(self, capacity: int = 30, refill_rate_per_sec: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self._tokens: Dict[str, float] = {}
        self._last_check: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        with self._lock:
            last = self._last_check.get(client_ip, now)
            tokens = self._tokens.get(client_ip, float(self.capacity))
            elapsed = now - last
            tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)
            self._last_check[client_ip] = now
            if tokens >= 1.0:
                self._tokens[client_ip] = tokens - 1.0
                return True
            else:
                self._tokens[client_ip] = tokens
                return False


rate_limiter = TokenBucketRateLimiter(capacity=30, refill_rate_per_sec=2.0)
loop_execution_lock = threading.Lock()


def resolve_and_validate_token(enforce_production: bool = False) -> str:
    """
    Resuelve el token API y valida los estándares de seguridad 2026 (Sprint 1: US-1.1).
    Falla tempranamente (fail-fast) si el token falta, es inseguro o menor a 32 caracteres.
    """
    token = os.getenv("DASHBOARD_API_TOKEN", "")
    if not token:
        try:
            token = get_secret("DASHBOARD_API_TOKEN", "") or ""
        except Exception:
            pass

    if not token:
        env_path = os.path.join(BASE_DIR, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("DASHBOARD_API_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass

    if enforce_production:
        if not token:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: 'DASHBOARD_API_TOKEN' no está configurado. "
                "Para operar de forma segura, defina la variable DASHBOARD_API_TOKEN en su entorno o archivo .env "
                "con al menos 32 caracteres criptográficos (ej. generado con `secrets.token_hex(32)`)."
            )
        if token == INSECURE_DEFAULT_TOKEN:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Se detectó el token por defecto inseguro ('meme_hunter_dev_token_2026'). "
                "Por favor configure un token criptográficamente seguro en DASHBOARD_API_TOKEN."
            )
        if len(token) < MIN_TOKEN_LENGTH:
            raise RuntimeError(
                f"SECURITY ERROR: 'DASHBOARD_API_TOKEN' es demasiado corto ({len(token)} caracteres). "
                f"Debe tener al menos {MIN_TOKEN_LENGTH} caracteres para prevenir ataques de fuerza bruta."
            )
    else:
        if not token or token == INSECURE_DEFAULT_TOKEN:
            token = secrets.token_hex(32)

    return token


# Cargar token inicial seguro
try:
    API_SECRET_TOKEN = resolve_and_validate_token(enforce_production=False)
except Exception:
    API_SECRET_TOKEN = secrets.token_hex(32)

# Orígenes CORS estrictos configurables (nunca wildcard '*')
RAW_ALLOWED_ORIGINS = os.getenv(
    "DASHBOARD_ALLOWED_ORIGINS",
    "http://127.0.0.1:8088,http://localhost:8088,http://127.0.0.1:8080,http://localhost:8080"
)
ALLOWED_ORIGINS: Set[str] = {o.strip() for o in RAW_ALLOWED_ORIGINS.split(",") if o.strip()}


class CockpitAPIHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP concurrente que combina servidor estático y endpoints API REST protegidos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def _check_auth(self) -> bool:
        """Verifica el token de autorización Bearer de forma segura en tiempo constante."""
        auth_header = self.headers.get("Authorization", "").strip()
        expected = f"Bearer {API_SECRET_TOKEN}"
        if auth_header and hmac.compare_digest(auth_header, expected):
            return True
        # Rechazo explícito con 401
        self._send_json({"error": "No autorizado. Token Bearer requerido o inválido."}, status_code=401)
        return False

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
        elif self.path == "/api/status":
            self._handle_api_status()
        elif self.path == "/api/strategies-catalog":
            self._handle_strategies_catalog()
        elif self.path == "/api/backtests-catalog":
            self._handle_backtests_catalog()
        elif self.path == "/api/stress-report":
            self._handle_stress_report()
        elif self.path == "/api/live-trades":
            self._handle_live_trades()
        elif self.path == "/api/emergency/kill-switch":
            self._handle_get_kill_switch()
        elif self.path == "/api/sentinel/status":
            self._handle_get_sentinel_status()
        elif self.path == "/api/llm/telemetry":
            self._handle_get_llm_telemetry()
        elif self.path in ("/api/loop-status", "/api/loop_status"):
            self._handle_loop_status()
        else:
            return super().do_GET()

    def do_POST(self):
        # 1. Rate limiting defensivo por IP (Sprint 1: US-1.3)
        client_ip = self.client_address[0]
        if not rate_limiter.is_allowed(client_ip):
            self._send_json(
                {"error": "Límite de peticiones excedido (429 Too Many Requests). Espere antes de reintentar."},
                status_code=429
            )
            return

        # 2. Exigir autenticación Bearer para endpoints que ejecutan lógica o consumen cuotas
        if not self._check_auth():
            return

        if self.path == "/api/trigger-loop":
            self._handle_trigger_loop()
        elif self.path == "/api/synthesize-alpha":
            self._handle_synthesize_alpha()
        elif self.path == "/api/validate-formula":
            self._handle_validate_formula()
        elif self.path == "/api/test-strategy":
            self._handle_test_strategy()
        elif self.path == "/api/deploy-to-sandbox":
            self._handle_deploy_to_sandbox()
        elif self.path == "/api/emergency/kill-switch":
            self._handle_post_kill_switch()
        elif self.path == "/api/emergency/kill-switch/reset":
            self._handle_post_kill_switch_reset()
        else:
            self.send_error(404, "Endpoint no encontrado")

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))

        # Cabeceras CORS estrictas (nunca wildcard '*')
        client_origin = self.headers.get("Origin", "").strip()
        if client_origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", client_origin)
            self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8088")

        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        # Cabeceras de seguridad reforzadas
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com;"
        )
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Manejo de pre-flight CORS seguro para navegadores."""
        self.send_response(204)
        client_origin = self.headers.get("Origin", "").strip()
        if client_origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", client_origin)
            self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8088")

        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def _handle_api_status(self):
        """Retorna el estado actual de la incubadora y autopsias."""
        incubator_path = os.path.join(BASE_DIR, "portfolio", "incubator_state.json")
        autopsy_path = os.path.join(BASE_DIR, "portfolio", "autopsies.json")
        archive_path = os.path.join(BASE_DIR, "mining", "diversity_archive.json")

        strategies = []
        if os.path.exists(incubator_path):
            try:
                with open(incubator_path, "r", encoding="utf-8") as f:
                    inc_data = json.load(f)
                    for sid, sinfo in inc_data.items():
                        strategies.append({
                            "id": sid,
                            "formula": sinfo.get("name", "N/A"),
                            "status": sinfo.get("status", "SANDBOX"),
                            "weight": sinfo.get("target_capital_weight", 0.0),
                            "backtest_sharpe": sinfo.get("backtest_sharpe", 0.0),
                            "ic": sinfo.get("live_sharpe", 0.0) / 20.0,
                            "pval": 0.005
                        })
            except Exception as e:
                logger.error(f"Error leyendo incubadora: {e}")

        # Si aún no hay incubador guardado en disco, proveer estado inicial
        if not strategies:
            strategies = [
                {"id": "ALPHA_MOM_01", "formula": "ts_rank(close, 14)", "status": "LIVE", "weight": 0.65, "backtest_sharpe": 2.10, "ic": 0.082, "pval": 0.001},
                {"id": "ALPHA_VOL_02", "formula": "ts_zscore((high - low), 10) * rvol", "status": "LIVE", "weight": 0.35, "backtest_sharpe": 1.85, "ic": 0.065, "pval": 0.004},
                {"id": "ALPHA_DECAYED_03", "formula": "ts_delay(close, 10)", "status": "ALPHA_DECAY", "weight": 0.00, "backtest_sharpe": 1.40, "ic": -0.012, "pval": 0.320}
            ]

        autopsies = []
        if os.path.exists(autopsy_path):
            try:
                with open(autopsy_path, "r", encoding="utf-8") as f:
                    autopsies = json.load(f)
            except Exception as e:
                logger.error(f"Error leyendo autopsias: {e}")

        niches = []
        if os.path.exists(archive_path):
            try:
                with open(archive_path, "r", encoding="utf-8") as f:
                    arch_data = json.load(f)
                    for nid, c in arch_data.items():
                        if c.get("factor"):
                            niches.append({
                                "niche": nid,
                                "formula": c["factor"]["formula"],
                                "ic_ir": c["factor"]["ic_ir"],
                                "status": "LIDER"
                            })
            except Exception as e:
                logger.error(f"Error leyendo archivo de nichos: {e}")

        history = []
        history_path = os.path.join(BASE_DIR, "portfolio", "cycle_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as hf:
                    history = json.load(hf)
            except Exception as e:
                logger.error(f"Error leyendo historial: {e}")

        # Cargar estado de Trinquete de Ganancias (Profit Ratchet)
        ratchet_path = os.path.join(BASE_DIR, "user_data", "ratchet_state.json")
        ratchet_data = None
        if os.path.exists(ratchet_path):
            try:
                with open(ratchet_path, "r", encoding="utf-8") as rf:
                    ratchet_data = json.load(rf)
            except Exception as e:
                logger.error(f"Error leyendo ratchet_state: {e}")

        # Cargar estado de Bóveda Delta-Neutral (Cash & Carry Vault)
        vault_path = os.path.join(BASE_DIR, "user_data", "vault_state.json")
        vault_data = None
        if os.path.exists(vault_path):
            try:
                with open(vault_path, "r", encoding="utf-8") as vf:
                    vault_data = json.load(vf)
            except Exception as e:
                logger.error(f"Error leyendo vault_state: {e}")

        # Resumen del ecosistema Freqtrade
        prod_strats = scan_strategies()
        backtests_data = scan_backtest_results()
        live_trades_data = get_live_trades_from_db()

        self._send_json({
            "status": "ONLINE",
            "active_strategy": "MemeHunterFuturesV7_Quantum",
            "production_strategies_count": len(prod_strats),
            "historical_backtests_count": len(backtests_data),
            "open_positions": live_trades_data.get("open_positions", []),
            "total_realized_profit": live_trades_data.get("total_realized_profit", 0.0),
            "strategies": strategies,
            "autopsies": autopsies,
            "niches": niches,
            "history": history,
            "ratchet": ratchet_data,
            "vault": vault_data
        })

    def _handle_strategies_catalog(self):
        """Devuelve el catálogo de las 11 estrategias Python físicas de Freqtrade."""
        strats = scan_strategies()
        self._send_json({"success": True, "strategies": strats, "total": len(strats)})

    def _handle_backtests_catalog(self):
        """Devuelve los 34 reportes históricos de backtesting extraídos de los zips."""
        bts = scan_backtest_results()
        self._send_json({"success": True, "backtests": bts, "total": len(bts)})

    def _handle_stress_report(self):
        """Devuelve el reporte de Stress Testing y Monte Carlo."""
        rep = load_stress_and_monte_carlo()
        self._send_json({"success": True, "data": rep})

    def _handle_live_trades(self):
        """Devuelve posiciones abiertas y trades recientes de la BD SQLite."""
        trades = get_live_trades_from_db()
        self._send_json({"success": True, "data": trades})

    def _handle_loop_status(self):
        """Retorna el estado de ejecución y telemetría del bucle de auto-mejora (PB-91)."""
        db_path = os.path.join(BASE_DIR, "portfolio", "alpha_factory.db")
        from portfolio.db_schema import get_cycle_history_db
        recent_cycles = get_cycle_history_db(limit=5, db_path=db_path)
        self._send_json({
            "status": "success",
            "is_busy": loop_execution_lock.locked(),
            "recent_cycles": recent_cycles
        })

    def _handle_trigger_loop(self):
        """Ejecuta un ciclo autónomo de auto-diagnóstico en vivo con datos reales (PB-90 y PB-91)."""
        logger.info("Disparando ciclo de orquestación autónomo desde el Cockpit UI...")

        if not loop_execution_lock.acquire(blocking=False):
            self._send_json({
                "success": False,
                "status": "busy",
                "error": "Un ciclo autónomo ya está ejecutándose en segundo plano. Espere a que culmine."
            }, status_code=429)
            return

        try:
            incubator_path = os.path.join(BASE_DIR, "portfolio", "incubator_state.json")
            archive_path = os.path.join(BASE_DIR, "mining", "diversity_archive.json")
            autopsy_path = os.path.join(BASE_DIR, "portfolio", "autopsies.json")
            db_path = os.path.join(BASE_DIR, "portfolio", "alpha_factory.db")

            incubator = StrategyLifecycleIncubator()
            if os.path.exists(db_path):
                incubator.load_from_db(db_path)
            elif os.path.exists(incubator_path):
                incubator.load_state(incubator_path)
            
            # Si no hay estrategias registradas, registrar lote base
            if not incubator.strategies:
                incubator.register_strategy("ALPHA_MOM_01", "ts_rank(close, 14)", 2.1, StrategyLifecycleStatus.LIVE)
                incubator.register_strategy("ALPHA_VOL_02", "ts_zscore((high - low), 10) * rvol", 1.85, StrategyLifecycleStatus.LIVE)
                incubator.register_strategy("ALPHA_DECAY_03", "ts_delay(close, 10)", 1.4, StrategyLifecycleStatus.LIVE)

            daemon = AlphaMinerDaemon(archive_path=archive_path)
            daemon.archive.load_archive(archive_path, db_path=db_path)

            autopsy_agent = AlphaAutopsyAgent(history_path=autopsy_path)
            llm_synthesizer = LLMAlphaSynthesizer()

            orchestrator = AutonomousPortfolioOrchestrator(
                incubator=incubator,
                health_monitor=AlphaHealthMonitor(rolling_window=20),
                miner_daemon=daemon,
                autopsy_agent=autopsy_agent,
                llm_synthesizer=llm_synthesizer
            )

            # PB-90: Ingesta de velas y microestructura real de Binance Futures
            from data_engine.real_market_feed import load_real_market_dataframe, build_signals_and_returns_for_strategies
            market_df = load_real_market_dataframe(pair="DOGE_USDT_USDT", timeframe="4h", n_bars=150)
            signals_df, fwd_ret, ret_matrix = build_signals_and_returns_for_strategies(
                market_df=market_df,
                strategies=incubator.strategies
            )

            report = orchestrator.process_cycle(
                signals_df=signals_df,
                forward_returns=fwd_ret,
                returns_matrix_df=ret_matrix,
                market_df=market_df
            )

            # Persistir estado actualizado en SQLite y JSON
            incubator.save_state(incubator_path, db_path=db_path)
            daemon.archive.save_archive(archive_path, db_path=db_path)

            # Persistir en historial de ciclos
            history_path = os.path.join(BASE_DIR, "portfolio", "cycle_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, "r", encoding="utf-8") as hf:
                        history = json.load(hf)
                except Exception:
                    pass

            cycle_entry = {
                "timestamp": report.cycle_timestamp,
                "actions": report.actions_taken,
                "quarantined": report.quarantined_strategies,
                "promoted": report.promoted_strategies,
                "new_weights": report.new_weights,
                "goal_reached": report.goal_reached,
                "estimated_cycle_cost_usd": report.estimated_cycle_cost_usd,
                "accumulated_cost_usd": report.accumulated_cost_usd,
                "active_strategies": len([s for s in incubator.strategies.values() if s.status.value == "LIVE"])
            }
            history.insert(0, cycle_entry)
            history = history[:25] # Retener últimos 25 ciclos
            try:
                atomic_write_json(history_path, history)
                from portfolio.db_schema import record_cycle_history_db
                record_cycle_history_db(cycle_entry, db_path=db_path)
            except Exception as e:
                logger.error(f"Error guardando cycle_history: {e}")

            self._send_json({
                "success": True,
                "cycle": cycle_entry,
                "history": history,
                "actions": report.actions_taken,
                "quarantined": report.quarantined_strategies,
                "promoted": report.promoted_strategies,
                "new_weights": report.new_weights,
                "goal_reached": report.goal_reached,
                "estimated_cycle_cost_usd": report.estimated_cycle_cost_usd,
                "accumulated_cost_usd": report.accumulated_cost_usd
            })
        except Exception as e:
            logger.error(f"Error durante el ciclo autónomo: {e}", exc_info=True)
            self._send_json({"success": False, "error": str(e)}, status_code=500)
        finally:
            loop_execution_lock.release()

    def _handle_synthesize_alpha(self):
        """Genera nuevos alphas semánticos utilizando OpenRouter."""
        logger.info("Sintetizando alphas semánticos vía OpenRouter...")
        try:
            synth = LLMAlphaSynthesizer()
            alphas = synth.synthesize_alphas(market_regime="HIGH_VOLATILITY", n_candidates=3)
            self._send_json({
                "success": True,
                "count": len(alphas),
                "formulas": [a[0] for a in alphas]
            })
        except Exception as e:
            logger.error(f"Error sintetizando alphas: {e}", exc_info=True)
            self._send_json({"success": False, "error": str(e)}, status_code=500)

    def _read_json_body(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _handle_validate_formula(self):
        """Valida una fórmula mediante AST Zero-Eval."""
        data = self._read_json_body()
        formula = data.get("formula", "").strip()
        from dashboard.strategy_tester import validate_formula_ast
        res = validate_formula_ast(formula)
        self._send_json(res)

    def _handle_test_strategy(self):
        """Ejecuta el backtest rápido vectorial de una estrategia diseñada."""
        try:
            data = self._read_json_body()
            formula = data.get("formula", "").strip()
            pair = data.get("pair", "1000PEPE")
            timeframe = data.get("timeframe", "4h")
            direction = data.get("direction", "short_only")
            leverage = float(data.get("leverage", 1.5))
            stoploss = float(data.get("stoploss", 0.10))
            trailing_stop = float(data.get("trailing_stop", 0.04))

            logger.info(f"Ejecutando backtest para fórmula '{formula}' en {pair} ({timeframe}, {direction}, {leverage}x)...")
            from dashboard.strategy_tester import run_strategy_backtest
            res = run_strategy_backtest(
                formula=formula,
                pair=pair,
                timeframe=timeframe,
                direction=direction,
                leverage=leverage,
                stoploss_pct=stoploss,
                trailing_stop_pct=trailing_stop
            )
            self._send_json(res)
        except Exception as e:
            logger.error(f"Error en backtest: {e}", exc_info=True)
            self._send_json({"success": False, "status": "error", "error": str(e)}, status_code=500)

    def _handle_deploy_to_sandbox(self):
        """Inyecta una estrategia testeada a la incubadora en estado SANDBOX."""
        try:
            data = self._read_json_body()
            strategy_id = data.get("strategy_id", f"CUSTOM_{int(time.time())}")
            formula = data.get("formula", "").strip()
            sharpe = float(data.get("backtest_sharpe", data.get("sharpe", 0.0)))

            incubator_path = os.path.join(BASE_DIR, "portfolio", "incubator_state.json")
            incubator = StrategyLifecycleIncubator()
            if os.path.exists(incubator_path):
                incubator.load_state(incubator_path)

            rec = incubator.register_strategy(strategy_id=strategy_id, name=formula, backtest_sharpe=sharpe)
            incubator.save_state(incubator_path)
            logger.info(f"Estrategia {strategy_id} desplegada exitosamente a SANDBOX (Sharpe: {sharpe}).")

            self._send_json({
                "success": True,
                "status": "success",
                "message": f"Estrategia '{strategy_id}' registrada con éxito en SANDBOX.",
                "strategy": {
                    "id": rec.strategy_id,
                    "name": rec.name,
                    "status": rec.status.value,
                    "backtest_sharpe": rec.backtest_sharpe
                }
            })
        except Exception as e:
            logger.error(f"Error desplegando a sandbox: {e}", exc_info=True)
            self._send_json({"success": False, "status": "error", "error": str(e)}, status_code=500)

    def _handle_get_kill_switch(self):
        """Retorna el estado de seguridad en tiempo real del EmergencyKillSwitch."""
        try:
            from portfolio.kill_switch import EmergencyKillSwitch
            ks = EmergencyKillSwitch()
            self._send_json({
                "status": "success",
                "is_active": ks.is_active,
                "current_level": int(ks.current_level),
                "level_name": ks.current_level.name,
                "last_trigger_reason": ks.last_trigger_reason,
                "last_triggered_at": ks.last_triggered_at
            })
        except Exception as e:
            logger.error(f"Error obteniendo estado del kill-switch: {e}")
            self._send_json({"status": "error", "error": str(e)}, status_code=500)

    def _handle_get_sentinel_status(self):
        """Retorna el estado de supervisión del AdversarialMarketSentinel."""
        try:
            from portfolio.adversarial_sentinel import AdversarialMarketSentinel
            sentinel = AdversarialMarketSentinel()
            self._send_json({
                "status": "success",
                "max_vol_to_depth_ratio": sentinel.max_vol_to_depth,
                "max_price_divergence_pct": sentinel.max_divergence,
                "max_funding_imbalance_pct": sentinel.max_funding,
                "audit_history_count": len(sentinel.audit_history)
            })
        except Exception as e:
            logger.error(f"Error obteniendo estado del centinela: {e}")
            self._send_json({"status": "error", "error": str(e)}, status_code=500)

    def _handle_get_llm_telemetry(self):
        """Retorna telemetría cuantitativa de consumo y SLAs del cliente LLM."""
        try:
            from mining.llm_client import OpenRouterClient
            client = OpenRouterClient()
            self._send_json({
                "status": "success",
                "telemetry": client.get_sla_telemetry()
            })
        except Exception as e:
            logger.error(f"Error obteniendo telemetría LLM: {e}")
            self._send_json({"status": "error", "error": str(e)}, status_code=500)

    def _handle_post_kill_switch(self):
        """Dispara de forma forzada un nivel de bloqueo en el EmergencyKillSwitch."""
        try:
            data = self._read_json_body()
            level = int(data.get("level", 1))
            reason = str(data.get("reason", "Disparo manual desde Cockpit API"))
            from portfolio.kill_switch import EmergencyKillSwitch
            ks = EmergencyKillSwitch()
            res = ks.trigger(level, reason)
            self._send_json({"status": "success", "result": res})
        except Exception as e:
            logger.error(f"Error activando kill-switch: {e}")
            self._send_json({"status": "error", "error": str(e)}, status_code=500)

    def _handle_post_kill_switch_reset(self):
        """Restaura el estado de trading a NORMAL con verificación de token."""
        try:
            data = self._read_json_body()
            token = str(data.get("auth_token", ""))
            from portfolio.kill_switch import EmergencyKillSwitch
            ks = EmergencyKillSwitch()
            success = ks.reset(auth_token=token, expected_token=API_SECRET_TOKEN)
            if success:
                self._send_json({"status": "success", "message": "Kill-switch restablecido a NORMAL"})
            else:
                self._send_json({"status": "error", "message": "Token de autorización inválido"}, status_code=403)
        except Exception as e:
            logger.error(f"Error reseteando kill-switch: {e}")
            self._send_json({"status": "error", "error": str(e)}, status_code=500)




def run_server(port: int = 8088):
    global API_SECRET_TOKEN
    # Validación fail-fast estricta en producción
    API_SECRET_TOKEN = resolve_and_validate_token(enforce_production=True)
    masked_fingerprint = hashlib.sha256(API_SECRET_TOKEN.encode("utf-8")).hexdigest()[:12]

    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, CockpitAPIHandler)
    print("=" * 80)
    print(" [MEMEHUNTER QUANT COCKPIT] Servidor Visual Seguro Multihilo Iniciado")
    print(f"  -> Acceso Local: http://localhost:{port}")
    print(f"  -> Seguridad API: Bearer Token ACTIVO [SHA256 Fingerprint: {masked_fingerprint}...****]")
    print(f"  -> Orígenes CORS Autorizados: {', '.join(sorted(ALLOWED_ORIGINS))}")
    print("  -> Presiona Ctrl+C para detener el servidor.")
    print("=" * 80)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor visual...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    run_server(port)
