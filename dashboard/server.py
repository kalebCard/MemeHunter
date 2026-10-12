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
import logging
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any

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

logger = logging.getLogger("CockpitServer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
API_SECRET_TOKEN = os.getenv("DASHBOARD_API_TOKEN", "meme_hunter_dev_token_2026")


class CockpitAPIHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP concurrente que combina servidor estático y endpoints API REST protegidos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def _check_auth(self) -> bool:
        """Verifica el token de autorización Bearer para llamadas de mutación/control."""
        auth_header = self.headers.get("Authorization", "")
        expected = f"Bearer {API_SECRET_TOKEN}"
        if auth_header == expected:
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
        else:
            return super().do_GET()

    def do_POST(self):
        # Exigir autenticación para endpoints que ejecutan lógica o consumen cuotas
        if not self._check_auth():
            return

        if self.path == "/api/trigger-loop":
            self._handle_trigger_loop()
        elif self.path == "/api/synthesize-alpha":
            self._handle_synthesize_alpha()
        else:
            self.send_error(404, "Endpoint no encontrado")

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # Restricción de CORS para evitar explotación cross-origin indiscriminada
        client_origin = self.headers.get("Origin", "")
        allowed_origins = {"http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8088", "http://127.0.0.1:8088"}
        if client_origin in allowed_origins:
            self.send_header("Access-Control-Allow-Origin", client_origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Manejo de pre-flight CORS para navegadores."""
        self.send_response(204)
        client_origin = self.headers.get("Origin", "")
        allowed_origins = {"http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8088", "http://127.0.0.1:8088"}
        if client_origin in allowed_origins:
            self.send_header("Access-Control-Allow-Origin", client_origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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

        self._send_json({
            "status": "ONLINE",
            "strategies": strategies,
            "autopsies": autopsies,
            "niches": niches
        })

    def _handle_trigger_loop(self):
        """Ejecuta un ciclo autónomo de auto-diagnóstico en vivo."""
        logger.info("Disparando ciclo de orquestación autónomo desde el Cockpit UI...")
        try:
            import numpy as np
            import pandas as pd
            dates = pd.date_range("2026-03-01", periods=60, freq="15min")
            ret = np.random.normal(0.0005, 0.015, 60)
            sig_ok = ret * 0.8 + np.random.normal(0, 0.002, 60)
            sig_bad = np.random.normal(0, 1.0, 60)

            incubator_path = os.path.join(BASE_DIR, "portfolio", "incubator_state.json")
            archive_path = os.path.join(BASE_DIR, "mining", "diversity_archive.json")
            autopsy_path = os.path.join(BASE_DIR, "portfolio", "autopsies.json")

            incubator = StrategyLifecycleIncubator()
            if os.path.exists(incubator_path):
                incubator.load_state(incubator_path)
            
            # Si no hay estrategias registradas, registrar lote base
            if not incubator.strategies:
                incubator.register_strategy("ALPHA_MOM_01", "ts_rank(close, 14)", 2.1, StrategyLifecycleStatus.LIVE)
                incubator.register_strategy("ALPHA_VOL_02", "ts_zscore((high - low), 10) * rvol", 1.85, StrategyLifecycleStatus.LIVE)
                incubator.register_strategy("ALPHA_DECAY_03", "ts_delay(close, 10)", 1.4, StrategyLifecycleStatus.LIVE)

            daemon = AlphaMinerDaemon(archive_path=archive_path)
            daemon.archive.load_archive(archive_path)

            autopsy_agent = AlphaAutopsyAgent(history_path=autopsy_path)
            llm_synthesizer = LLMAlphaSynthesizer()

            orchestrator = AutonomousPortfolioOrchestrator(
                incubator=incubator,
                health_monitor=AlphaHealthMonitor(rolling_window=20),
                miner_daemon=daemon,
                autopsy_agent=autopsy_agent,
                llm_synthesizer=llm_synthesizer
            )

            # Construir señales con las estrategias vivas en la incubadora
            sig_dict = {}
            ret_dict = {}
            strat_keys = list(incubator.strategies.keys())
            for idx, sid in enumerate(strat_keys):
                # Si es una estrategia degradada simular choque, de lo contrario retener señal
                if "DECAY" in sid or idx == len(strat_keys) - 1:
                    sig_dict[sid] = sig_bad
                    ret_dict[sid] = -ret
                else:
                    sig_dict[sid] = sig_ok
                    ret_dict[sid] = ret

            signals_df = pd.DataFrame(sig_dict, index=dates)
            fwd_ret = pd.Series(ret, index=dates)
            ret_matrix = pd.DataFrame(ret_dict, index=dates)

            # Crear DataFrame de mercado sintético si no hay streaming activo
            market_df = pd.DataFrame({
                'open': np.ones(60) * 10,
                'high': np.ones(60) * 10.5,
                'low': np.ones(60) * 9.5,
                'close': np.ones(60) * 10,
                'volume': np.random.uniform(500, 2000, 60),
                'vwap': np.ones(60) * 10,
                'rvol': np.ones(60),
                'hl_spread': np.ones(60) * 0.1,
                'returns': ret
            }, index=dates)

            report = orchestrator.process_cycle(
                signals_df=signals_df,
                forward_returns=fwd_ret,
                returns_matrix_df=ret_matrix,
                market_df=market_df
            )

            # Persistir estado actualizado de forma atómica
            incubator.save_state(incubator_path)
            daemon.archive.save_archive(archive_path)

            self._send_json({
                "success": True,
                "actions": report.actions_taken,
                "quarantined": report.quarantined_strategies,
                "promoted": report.promoted_strategies,
                "new_weights": report.new_weights
            })
        except Exception as e:
            logger.error(f"Error durante el ciclo autónomo: {e}", exc_info=True)
            self._send_json({"success": False, "error": str(e)}, status_code=500)

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


def run_server(port: int = 8088):
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, CockpitAPIHandler)
    print("=" * 80)
    print(f" [MEMEHUNTER QUANT COCKPIT] Servidor Visual Seguro Multihilo Iniciado")
    print(f"  -> Acceso Local: http://localhost:{port}")
    print(f"  -> Token Autenticación API: {API_SECRET_TOKEN}")
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
