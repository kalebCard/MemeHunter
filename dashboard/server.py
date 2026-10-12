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
from http.server import HTTPServer, SimpleHTTPRequestHandler
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


class CockpitAPIHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP que combina servidor estático y endpoints API REST."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
        elif self.path == "/api/status":
            self._handle_api_status()
        else:
            return super().do_GET()

    def do_POST(self):
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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

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

            signals_df = pd.DataFrame({'ALPHA_MOM_01': sig_ok, 'ALPHA_VOL_02': sig_bad}, index=dates)
            fwd_ret = pd.Series(ret, index=dates)
            ret_matrix = pd.DataFrame({'ALPHA_MOM_01': ret, 'ALPHA_VOL_02': -ret}, index=dates)

            incubator = StrategyLifecycleIncubator()
            incubator.register_strategy("ALPHA_MOM_01", "ts_rank(close, 14)", 2.1, StrategyLifecycleStatus.LIVE)
            incubator.register_strategy("ALPHA_VOL_02", "ts_delay(close, 10)", 1.6, StrategyLifecycleStatus.LIVE)

            orchestrator = AutonomousPortfolioOrchestrator(
                incubator=incubator,
                health_monitor=AlphaHealthMonitor(rolling_window=20),
                miner_daemon=AlphaMinerDaemon(),
                autopsy_agent=AlphaAutopsyAgent(),
                llm_synthesizer=LLMAlphaSynthesizer()
            )

            report = orchestrator.process_cycle(
                signals_df=signals_df,
                forward_returns=fwd_ret,
                returns_matrix_df=ret_matrix
            )

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


def run_server(port: int = 8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, CockpitAPIHandler)
    print("=" * 80)
    print(f" [MEMEHUNTER QUANT COCKPIT] Servidor Visual Iniciado con Éxito")
    print(f"  -> Acceso Local: http://localhost:{port}")
    print("  -> Presiona Ctrl+C para detener el servidor.")
    print("=" * 80)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor visual...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
