"""
hermes_operator.py - Agente Autónomo Hermes como Alter Ego Operativo (Sprint 52: PB-180 & PB-181).

Gobierna de manera unificada el ecosistema Meme Hunter:
1. Lee telemetría viva de todos los bots (8081, 8082, 8083).
2. Clasifica el régimen macro y de volatilidad (RegimeDetector).
3. Aplica rebalanceos y salvaguardas de riesgo (CapitalAllocator).
4. Mantiene memoria episódica persistente en disco (/storage/hermes_memory.json).
5. Genera explicaciones causales en primera persona como Alter Ego del operador.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from client.multi_bot_orchestrator import MultiBotOrchestratorClient
try:
    from meme_hunter.hermes.regime_detector import HermesRegimeDetector
    from meme_hunter.hermes.capital_allocator import HermesCapitalAllocator
except (ImportError, ModuleNotFoundError):
    from src.meme_hunter.hermes.regime_detector import HermesRegimeDetector
    from src.meme_hunter.hermes.capital_allocator import HermesCapitalAllocator

logger = logging.getLogger("HermesOperator")


class HermesOperator:
    """
    Núcleo del Agente Autónomo Hermes para Meme Hunter.
    """

    def __init__(
        self,
        memory_path: str = "storage/hermes_memory.json",
        orchestrator: Optional[MultiBotOrchestratorClient] = None,
        regime_detector: Optional[HermesRegimeDetector] = None,
        capital_allocator: Optional[HermesCapitalAllocator] = None
    ):
        self.memory_path = memory_path
        self.orchestrator = orchestrator or MultiBotOrchestratorClient()
        self.regime_detector = regime_detector or HermesRegimeDetector()
        self.capital_allocator = capital_allocator or HermesCapitalAllocator(self.orchestrator)
        
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        """Carga la memoria episódica desde disco o inicializa una nueva."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error al leer memoria en {self.memory_path}: {e}")

        # Estructura canónica de memoria persistente
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_cycles_run": 0,
            "regime_history": [],
            "actions_history": [],
            "last_decision": None,
            "active_skills": [
                "regime_detection_v1",
                "dynamic_capital_allocation_v1",
                "profit_ratchet_guardian_v1"
            ]
        }

    def _save_memory(self) -> None:
        """Persiste la memoria episódica en disco de forma atómica."""
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        try:
            temp_path = f"{self.memory_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.memory_path)
        except Exception as e:
            logger.error(f"Error al persistir memoria en {self.memory_path}: {e}")

    def run_cycle(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo de evaluación y gobierno autónomo.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 1. Detección de Régimen
        regime_info = self.regime_detector.detect_regime()
        
        # 2. Aplicación de Gobernanza y Asignación de Capital
        allocation_res = self.capital_allocator.evaluate_and_enforce(regime_info)
        
        # 3. Telemetría de la Cartera
        portfolio = self.orchestrator.get_aggregated_status()
        
        # 4. Generación de Explicación Causal (Alter Ego)
        explanation = self.generate_causal_explanation(regime_info, portfolio, allocation_res)
        
        # 5. Actualización de Memoria Episódica
        cycle_record = {
            "timestamp": timestamp,
            "regime": regime_info.get("regime"),
            "confidence": regime_info.get("confidence"),
            "total_open_trades": portfolio.get("total_open_trades", 0),
            "stake_active_usdt": portfolio.get("total_stake_active_usdt", 0.0),
            "actions_count": len(allocation_res.get("actions_taken", []))
        }
        
        self.memory["total_cycles_run"] += 1
        self.memory["regime_history"].append(cycle_record)
        if len(self.memory["regime_history"]) > 100:
            self.memory["regime_history"] = self.memory["regime_history"][-100:]
            
        self.memory["last_decision"] = {
            "timestamp": timestamp,
            "explanation": explanation,
            "regime_info": regime_info,
            "allocation_res": allocation_res
        }
        
        self._save_memory()
        
        return {
            "timestamp": timestamp,
            "regime_info": regime_info,
            "portfolio": portfolio,
            "allocation_res": allocation_res,
            "explanation": explanation,
            "total_cycles_run": self.memory["total_cycles_run"]
        }

    def generate_causal_explanation(
        self,
        regime_info: Dict[str, Any],
        portfolio: Dict[str, Any],
        allocation_res: Dict[str, Any]
    ) -> str:
        """
        Produce un informe ejecutivo en primera persona.
        """
        regime = regime_info.get("regime", "UNKNOWN")
        snap = regime_info.get("snapshot", {})
        btc_price = snap.get("btc_price", 0.0)
        btc_chg = snap.get("btc_change_24h", 0.0)
        trades_count = portfolio.get("total_open_trades", 0)
        stake_active = portfolio.get("total_stake_active_usdt", 0.0)
        
        intro = f"🧠 **Hermes (Tu Alter Ego) | Meta: Extraer Ganancias en Binance Futures**"
        context = (
            f"He evaluado el mercado en vivo. BTC cotiza en `${btc_price:,.1f}` con una variación 24h de `{btc_chg:+.2f}%`. "
            f"El régimen actual catalogado es **{regime}** (Confianza: {regime_info.get('confidence', 0)*100:.0f}%)."
        )
        
        if regime == "BEAR_CASCADE":
            tactic = (
                "📉 **Táctica de Extracción de PnL:** Detecto debilidad estructural y liquidaciones de largos en memecoins. "
                "Canalizo el capital a **Ablation V5** y **Quantum V7** para capturar las extensiones bajistas y ganar en USDT."
            )
        elif regime == "BULL_PARABOLIC":
            tactic = (
                "🚀 **Táctica de Protección de Ganancias:** Fuerte aceleración alcista. Para evitar pérdidas por *short squeezes*, "
                "he congelado preventivamente las aperturas en corto y preservado el capital líquido para la siguiente oportunidad."
            )
        else:
            tactic = (
                "⚖️ **Táctica de Rango:** El mercado oscila sin tendencia dominante. "
                "Mantengo la cartera balanceada maximizando el ratio de Sharpe con Quantum V7 (Kelly sizing) para acumular beneficios constantes."
            )
            
        status_line = f"📊 **Estado de Posiciones:** {trades_count} operaciones vivas | Margen asignado: `{stake_active:.2f} USDT`."
        
        return f"{intro}\n\n{context}\n\n{tactic}\n\n{status_line}"

    def mine_and_evaluate_new_alpha(
        self,
        pair: str = "DOGE_USDT_USDT",
        n_candidates: int = 3
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de investigación cuantitativa autónoma:
        1. Consulta a OpenRouter para sintetizar fórmulas de alpha adaptadas al régimen actual.
        2. Carga datos reales del mercado de Binance Futures (4h).
        3. Evalúa vectorialmente y backtestea las fórmulas candidatas.
        4. Almacena las mejores fórmulas en factor_library.json y actualiza la memoria.
        5. Recarga en caliente el Bot 3 (MemeHunter_MinedEnsemble :8083) para prueba en vivo con cartera simulada.
        """
        try:
            from mining.llm_alpha_generator import LLMAlphaSynthesizer
            from data_engine.real_market_feed import load_real_market_dataframe
        except (ImportError, ModuleNotFoundError):
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
            from mining.llm_alpha_generator import LLMAlphaSynthesizer
            from data_engine.real_market_feed import load_real_market_dataframe

        regime_info = self.regime_detector.detect_regime()
        current_regime = regime_info.get("regime", "RANGE_CHOP")

        logger.info(f"🧠 [Hermes Mining] Sintetizando {n_candidates} alfas para régimen {current_regime}...")
        synthesizer = LLMAlphaSynthesizer()
        candidates = synthesizer.synthesize_alphas(market_regime=current_regime, n_candidates=n_candidates)

        if not candidates:
            return {
                "status": "error",
                "message": "No se pudieron generar fórmulas sintácticas válidas con el LLM.",
                "regime": current_regime
            }

        logger.info(f"🧠 [Hermes Mining] Backtesteando {len(candidates)} candidatos contra datos reales de {pair}...")
        df = load_real_market_dataframe(pair, timeframe="4h", n_bars=150)
        fwd_ret = df["close"].pct_change().shift(-1).fillna(0.0)

        evaluated = synthesizer.evaluate_and_build_factors(candidates, df, fwd_ret)
        if not evaluated:
            return {
                "status": "warning",
                "message": "Las fórmulas generadas no superaron los filtros de varianza mínima o correlación.",
                "regime": current_regime,
                "candidates_count": len(candidates)
            }

        # Ordenar por Sharpe Proxy descendente
        evaluated.sort(key=lambda x: x.sharpe_proxy, reverse=True)
        best_factor = evaluated[0]

        # Guardar en factor_library.json si tiene métricas aceptables
        library_path = "mining/factor_library.json"
        existing_factors = []
        if os.path.exists(library_path):
            try:
                with open(library_path, "r", encoding="utf-8") as f:
                    existing_factors = json.load(f)
            except Exception:
                existing_factors = []

        new_entry = {
            "factor_id": f"HERMES_ALPHA_{len(existing_factors)+1:02d}",
            "formula": best_factor.formula,
            "ic_mean": round(float(best_factor.ic_mean), 6),
            "ic_std": round(float(best_factor.ic_std), 6),
            "ic_ir": round(float(best_factor.ic_ir), 6),
            "sharpe_proxy": round(float(best_factor.sharpe_proxy), 4),
            "turnover": round(float(best_factor.turnover), 4),
            "depth": best_factor.depth,
            "correlation_with_existing": 0.0,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "regime": current_regime
        }
        existing_factors.append(new_entry)

        try:
            with open(library_path, "w", encoding="utf-8") as f:
                json.dump(existing_factors, f, indent=2)
        except Exception as e:
            logger.warning(f"No se pudo guardar factor_library.json: {e}")

        # Recargar configuración en caliente de Bot 3 (:8083) para que empiece a evaluarla
        reload_ok = False
        if hasattr(self.orchestrator, "clients") and "bot_mined_ensemble" in self.orchestrator.clients:
            reload_res = self.orchestrator.clients["bot_mined_ensemble"].reload_config()
            reload_ok = (reload_res.get("status") == "ok")

        # Registrar en la memoria episódica de Hermes
        self.memory.setdefault("mined_alphas_history", []).append(new_entry)
        self._save_memory()

        return {
            "status": "ok",
            "regime": current_regime,
            "best_factor": new_entry,
            "total_evaluated": len(evaluated),
            "reload_bot3": reload_ok
        }

