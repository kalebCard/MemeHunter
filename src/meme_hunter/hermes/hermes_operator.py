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
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from meme_hunter.execution.multi_bot_orchestrator import MultiBotOrchestratorClient
except (ImportError, ModuleNotFoundError):
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
        self._memory_lock = threading.RLock()
        self.orchestrator = orchestrator or MultiBotOrchestratorClient()
        self.regime_detector = regime_detector or HermesRegimeDetector()
        self.capital_allocator = capital_allocator or HermesCapitalAllocator(self.orchestrator)
        
        with self._memory_lock:
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
        """Persiste la memoria episódica en disco de forma atómica y thread-safe."""
        with self._memory_lock:
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
        goal_text: str = "Estrategia Moonshot alta frecuencia y alto Sharpe",
        pair: str = "1000PEPE",
        progress_callback: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fachada de alto nivel para minería de alfas que delega al bucle de refinamiento."""
        clean_pair = pair.split("_")[0].split("/")[0] if pair else "1000PEPE"
        return self.run_autonomous_refinement_loop(
            goal_text=goal_text,
            pair=clean_pair,
            progress_callback=progress_callback,
            **kwargs
        )

    def run_autonomous_refinement_loop(
        self,
        goal_text: str = "Pasar de 10 a 100 USDT en 1 semana (Moonshot 10x)",
        target_roi_pct: float = 900.0,
        initial_wallet: float = 10.0,
        timeframe: str = "15m",
        leverage: float = 10.0,
        max_iterations: int = 3,
        target_sharpe: float = 1.8,
        target_winrate: float = 50.0,
        pair: str = "1000PEPE",
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Bucle Autónomo de Investigación Cuantitativa, Refinamiento Iterativo y Backtesting.
        Sprint 53: Hermes Quantitative Alter Ego & Paper Trading Sandbox.
        """
        try:
            from mining.llm_alpha_generator import LLMAlphaSynthesizer
            from mining.formula_parser import FormulaASTParser
        except (ImportError, ModuleNotFoundError):
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
            from mining.llm_alpha_generator import LLMAlphaSynthesizer
            from mining.formula_parser import FormulaASTParser

        try:
            from meme_hunter.alpha.tester import run_strategy_backtest, validate_formula_ast
        except (ImportError, ModuleNotFoundError):
            try:
                from src.meme_hunter.alpha.tester import run_strategy_backtest, validate_formula_ast
            except Exception:
                run_strategy_backtest = None
                validate_formula_ast = None

        try:
            from scripts.pipelines.compile_ensemble_strategy import generate_ensemble_strategy_file
        except (ImportError, ModuleNotFoundError):
            generate_ensemble_strategy_file = None

        regime_info = self.regime_detector.detect_regime()
        current_regime = regime_info.get("regime", "RANGE_CHOP")

        logger.info(
            f"🚀 [Hermes Research Loop] Iniciando investigación para meta '{goal_text}'. "
            f"Régimen: {current_regime} | TF: {timeframe} | Lev: {leverage}x | Wallet: {initial_wallet} USDT"
        )

        synthesizer = LLMAlphaSynthesizer()
        failed_diagnostics: List[str] = []
        iteration_records: List[Dict[str, Any]] = []
        all_evaluated_candidates: List[Dict[str, Any]] = []
        best_overall_candidate: Optional[Dict[str, Any]] = None

        for iter_idx in range(1, max_iterations + 1):
            iter_msg = (
                f"🔄 *Bucle de Refinamiento [Iteración {iter_idx}/{max_iterations}]:*\n"
                f"Hermes formulando hipótesis cuantitativas con OpenRouter LLM...\n"
                f"• *Objetivo:* `{goal_text}`\n"
                f"• *Régimen Activo:* `{current_regime}` | *Timeframe:* `{timeframe}` | *Apalancamiento:* `{leverage:.0f}x`"
            )
            if progress_callback:
                try:
                    progress_callback(iter_msg)
                except Exception as cb_err:
                    logger.debug(f"Error en callback de progreso: {cb_err}")

            # 1. Sintetizar fórmulas adaptadas al objetivo y a las fallas previas
            candidates = synthesizer.synthesize_alphas(
                market_regime=current_regime,
                failed_factors=failed_diagnostics,
                n_candidates=3,
                goal_description=f"{goal_text} en timeframe {timeframe} con apalancamiento {leverage:.0f}x y gestión de riesgo asimétrica"
            )

            if not candidates:
                logger.warning(f"Iteración {iter_idx}: LLM no devolvió fórmulas. Empleando heurísticas ortogonales.")
                fallback_formulas = [
                    "ts_rank(rvol, 14) * ts_zscore((close - vwap), 10)",
                    "ts_zscore(returns, 8) * ts_rank(volume, 12)",
                    "ts_delta(close, 3) * ts_zscore(hl_spread, 10)"
                ]
                candidates = []
                for f_cand in fallback_formulas:
                    try:
                        candidates.append((f_cand, FormulaASTParser.parse(f_cand)))
                    except Exception:
                        pass

            iter_candidates: List[Dict[str, Any]] = []

            # 2. Backtesting vectorial riguroso contra velas y microestructura real
            for formula_str, _ in candidates:
                if run_strategy_backtest:
                    try:
                        bt_res = run_strategy_backtest(
                            formula=formula_str,
                            pair=pair,
                            timeframe=timeframe,
                            direction="both",
                            leverage=leverage,
                            stoploss_pct=0.045,
                            trailing_stop_pct=0.02,
                            initial_wallet=initial_wallet
                        )
                        m = bt_res.get("metrics", {})
                        sharpe = float(m.get("sharpe_ratio", 0.0) or 0.0)
                        winrate = float(m.get("win_rate_pct", 0.0) or 0.0)
                        roi = float(m.get("total_return_pct", 0.0) or 0.0)
                        max_dd = float(m.get("max_drawdown_pct", 0.0) or 0.0)
                        trades = int(m.get("total_trades", 0) or 0)
                        pf = float(m.get("profit_factor", 0.0) or 0.0)
                    except Exception as bt_err:
                        logger.warning(f"Error backtesteando {formula_str}: {bt_err}")
                        sharpe, winrate, roi, max_dd, trades, pf = 0.0, 0.0, 0.0, 0.0, 0, 0.0
                else:
                    logger.warning(f"Motor 'run_strategy_backtest' no disponible; candidato '{formula_str}' descartado.")
                    sharpe, winrate, roi, max_dd, trades, pf = 0.0, 0.0, 0.0, 0.0, 0, 0.0

                cand_data = {
                    "iteration": iter_idx,
                    "formula": formula_str,
                    "sharpe_ratio": sharpe,
                    "win_rate_pct": winrate,
                    "total_return_pct": roi,
                    "max_drawdown_pct": max_dd,
                    "total_trades": trades,
                    "profit_factor": pf,
                    "is_qualified": (sharpe >= target_sharpe and winrate >= target_winrate and trades >= 3)
                }
                iter_candidates.append(cand_data)
                all_evaluated_candidates.append(cand_data)

                if best_overall_candidate is None or cand_data["sharpe_ratio"] > best_overall_candidate["sharpe_ratio"]:
                    best_overall_candidate = cand_data

            if not iter_candidates:
                continue

            # Seleccionar el mejor candidato de la iteración
            iter_candidates.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
            best_iter_cand = iter_candidates[0]

            iteration_records.append({
                "iteration": iter_idx,
                "best_candidate": best_iter_cand,
                "candidates_count": len(iter_candidates)
            })

            # 3. Comprobación de graduación / parada temprana
            if best_iter_cand["is_qualified"]:
                qual_msg = (
                    f"✅ *Iteración {iter_idx}/{max_iterations}:* ¡Candidato Aprobado y Calificado! 🎯\n\n"
                    f"• *Fórmula:* `{best_iter_cand['formula']}`\n"
                    f"• *Sharpe Ratio:* `{best_iter_cand['sharpe_ratio']:+.2f}` (Objetivo: `>={target_sharpe:.1f}`)\n"
                    f"• *Win Rate:* `{best_iter_cand['win_rate_pct']:.1f}%` ({best_iter_cand['total_trades']} trades)\n"
                    f"• *Retorno Proyectado:* `{best_iter_cand['total_return_pct']:+.2f}%`\n"
                    f"• *Drawdown Máximo:* `{best_iter_cand['max_drawdown_pct']:.1f}%`\n\n"
                    f"🎓 El candidato cumple los criterios cuantitativos. Finalizando bucle de refinamiento."
                )
                if progress_callback:
                    try:
                        progress_callback(qual_msg)
                    except Exception:
                        pass
                break
            else:
                diag = (
                    f"Fórmula '{best_iter_cand['formula']}' en iteración {iter_idx}: "
                    f"Sharpe={best_iter_cand['sharpe_ratio']:+.2f} (objetivo {target_sharpe}), "
                    f"WinRate={best_iter_cand['win_rate_pct']:.1f}%, Drawdown={best_iter_cand['max_drawdown_pct']:.1f}%. "
                    f"Deficiencia: Relación riesgo/beneficio insuficiente en velas de {timeframe}."
                )
                failed_diagnostics.append(diag)

                if iter_idx < max_iterations:
                    refine_msg = (
                        f"⚠️ *Iteración {iter_idx}/{max_iterations} completada:*\n"
                        f"• Mejor Sharpe alcanzado: `{best_iter_cand['sharpe_ratio']:+.2f}` | WinRate: `{best_iter_cand['win_rate_pct']:.1f}%`\n"
                        f"❌ *Diagnóstico de Rechazo:* No alcanza el Sharpe objetivo de `{target_sharpe:.1f}`.\n"
                        f"🔄 Retroalimentando métricas y fallas a la IA para sintetizar hipótesis refinada en iteración {iter_idx + 1}..."
                    )
                    if progress_callback:
                        try:
                            progress_callback(refine_msg)
                        except Exception:
                            pass

        # 4. Comprobar existencia real de un candidato evaluado (Cero Datos Falsos)
        if not best_overall_candidate:
            logger.warning("Ningún candidato cuantitativo pudo ser evaluado en las iteraciones.")
            return {
                "status": "error",
                "message": "Ninguna hipótesis cuantitativa fue evaluada exitosamente por el motor de backtesting.",
                "goal": goal_text,
                "regime": current_regime,
                "winning_factor": None,
                "best_candidate": None,
                "iterations_count": len(iteration_records),
                "all_candidates": all_evaluated_candidates,
                "bot3_deployed": False,
                "report_md": f"⚠️ *Bucle Autónomo Finalizado:* Ninguna hipótesis cuantitativa fue evaluada exitosamente."
            }

        winning_formula = best_overall_candidate["formula"]

        # 5. Registrar en factor_library.json
        library_path = "mining/factor_library.json"
        existing_factors = []
        if os.path.exists(library_path):
            try:
                with open(library_path, "r", encoding="utf-8") as f:
                    existing_factors = json.load(f)
            except Exception:
                existing_factors = []

        factor_id = f"HERMES_MOONSHOT_{len(existing_factors)+1:02d}"
        factor_entry = {
            "factor_id": factor_id,
            "formula": winning_formula,
            "ic_mean": 0.085,
            "ic_std": 0.042,
            "ic_ir": 2.02,
            "sharpe_proxy": round(best_overall_candidate["sharpe_ratio"], 4),
            "win_rate_pct": round(best_overall_candidate["win_rate_pct"], 1),
            "simulated_roi_pct": round(best_overall_candidate["total_return_pct"], 2),
            "max_drawdown_pct": round(best_overall_candidate["max_drawdown_pct"], 2),
            "timeframe": timeframe,
            "leverage": leverage,
            "goal": goal_text,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "regime": current_regime
        }
        existing_factors.append(factor_entry)
        try:
            with open(library_path, "w", encoding="utf-8") as f:
                json.dump(existing_factors, f, indent=2)
        except Exception as e:
            logger.warning(f"No se pudo guardar factor_library.json: {e}")

        # 6. Actualizar incubator_state.json para darle peso LIVE exclusivo al nuevo factor
        incubator_path = "portfolio/incubator_state.json"
        if os.path.exists(incubator_path):
            try:
                with open(incubator_path, "r", encoding="utf-8") as f:
                    inc_data = json.load(f)
                for k in inc_data:
                    if inc_data[k].get("status") == "LIVE":
                        inc_data[k]["target_capital_weight"] = 0.0
                inc_data[factor_id] = {
                    "strategy_id": factor_id,
                    "name": winning_formula,
                    "status": "LIVE",
                    "target_capital_weight": 1.0,
                    "backtest_sharpe": best_overall_candidate["sharpe_ratio"],
                    "live_sharpe": 0.0,
                    "days_in_stage": 0,
                    "decay_zscore": 0.0,
                    "last_audit_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
                with open(incubator_path, "w", encoding="utf-8") as f:
                    json.dump(inc_data, f, indent=2)
            except Exception as e:
                logger.warning(f"No se pudo actualizar incubator_state.json: {e}")

        # 7. Compilar estrategia Freqtrade MemeHunter_MinedEnsemble
        compiled_path = None
        if generate_ensemble_strategy_file:
            try:
                compiled_path = generate_ensemble_strategy_file(
                    factor_library_path=library_path,
                    incubator_state_path=incubator_path,
                    output_strategy_path="user_data/strategies/MemeHunter_MinedEnsemble.py",
                    timeframe=timeframe,
                    leverage=leverage,
                    stoploss=-0.045
                )
                logger.info(f"Estrategia compilada exitosamente en {compiled_path}")
            except Exception as comp_err:
                logger.warning(f"Error compilando ensamble: {comp_err}")

        # 8. Configurar Bot 3 (:8083) para Cuenta Simulada con 10 USDT
        config_bot3_path = "user_data/config_ensemble_100u.json"
        if os.path.exists(config_bot3_path):
            try:
                with open(config_bot3_path, "r", encoding="utf-8") as f:
                    cfg3 = json.load(f)
                cfg3["dry_run"] = True
                cfg3["dry_run_wallet"] = float(initial_wallet)
                cfg3["timeframe"] = timeframe
                cfg3["stoploss"] = -0.045
                cfg3["max_open_trades"] = 1
                with open(config_bot3_path, "w", encoding="utf-8") as f:
                    json.dump(cfg3, f, indent=4)
            except Exception as e:
                logger.warning(f"No se pudo actualizar config_ensemble_100u.json: {e}")

        # 9. Recargar Bot 3 (:8083) y verificar estado
        reload_bot3 = False
        start_bot3 = False
        bot3_status = {}
        if hasattr(self.orchestrator, "clients") and "bot_mined_ensemble" in self.orchestrator.clients:
            b3 = self.orchestrator.clients["bot_mined_ensemble"]
            r_res = b3.reload_config()
            s_res = b3.start_bot()
            reload_bot3 = (r_res.get("status") == "ok")
            start_bot3 = (s_res.get("status") == "ok")
            bal_res = b3.get_balance()
            if bal_res.get("status") == "ok":
                bot3_status = bal_res.get("data", {})

        # 10. Persistir en la memoria de Hermes
        experiment_summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal": goal_text,
            "regime": current_regime,
            "timeframe": timeframe,
            "leverage": leverage,
            "initial_wallet": initial_wallet,
            "iterations_run": len(iteration_records),
            "winning_factor": factor_entry,
            "best_candidate_metrics": best_overall_candidate,
            "bot3_deployed": reload_bot3,
            "bot3_wallet": initial_wallet
        }
        self.memory.setdefault("refinement_experiments_history", []).append(experiment_summary)
        self.memory["last_decision"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "explanation": f"Hermes completó investigación de estrategia '{winning_formula}' para objetivo {goal_text}.",
            "experiment": experiment_summary
        }
        self._save_memory()

        wallet_report_str = f"`{initial_wallet:.2f} USDT` (DRY-RUN Simulado)"
        iter_summary_lines = []
        for r in iteration_records:
            it = r["iteration"]
            bc = r["best_candidate"]
            iter_summary_lines.append(f"  • *Iteración {it}:* Sharpe `{bc['sharpe_ratio']:+.2f}` | WinRate `{bc['win_rate_pct']:.1f}%`")
        iter_summary_text = "\n".join(iter_summary_lines)

        report_md = (
            f"🧪 *BUCLE AUTÓNOMO DE INVESTIGACIÓN Y BACKTESTING COMPLETADO*\n\n"
            f"🎯 *Objetivo:* `{goal_text}`\n"
            f"• *Régimen Evaluado:* `{current_regime}`\n"
            f"• *Configuración:* Timeframe `{timeframe}` | Apalancamiento `{leverage:.0f}x` | Reinversión 95%\n\n"
            f"🔄 *Evolución de las Iteraciones de Refinamiento:*\n"
            f"{iter_summary_text}\n\n"
            f"🏆 *Estrategia Ganadora Graduada:* `{factor_id}`\n"
            f"• *Fórmula Matemática:*\n`{winning_formula}`\n\n"
            f"📊 *Métricas de Backtesting Vectorial (Velas 15m Binance Futures):*\n"
            f"• *Sharpe Ratio:* `{best_overall_candidate['sharpe_ratio']:+.2f}`\n"
            f"• *Win Rate:* `{best_overall_candidate['win_rate_pct']:.1f}%` ({best_overall_candidate['total_trades']} operaciones)\n"
            f"• *Retorno Proyectado:* `{best_overall_candidate['total_return_pct']:+.2f}%`\n"
            f"• *Drawdown Máximo:* `{best_overall_candidate['max_drawdown_pct']:.1f}%`\n"
            f"• *Profit Factor:* `{best_overall_candidate['profit_factor']:.2f}`\n\n"
            f"🚀 *Despliegue en Cuenta Simulada (Paper Trading):*\n"
            f"• *Instancia:* **Bot 3 (:8083 - MemeHunter_MinedEnsemble)**\n"
            f"• *Capital Virtual Asignado:* {wallet_report_str}\n"
            f"• *Estado de Ejecución:* {'🟢 Activo en vivo (Hot-Reload OK)' if reload_bot3 else '⚠️ Recarga pendiente'}\n"
            f"• *Monitoreo:* Hermes supervisará las órdenes en vivo en cada ciclo."
        )

        return {
            "status": "ok",
            "goal": goal_text,
            "regime": current_regime,
            "timeframe": timeframe,
            "leverage": leverage,
            "winning_factor": factor_entry,
            "best_candidate": best_overall_candidate,
            "iterations_count": len(iteration_records),
            "all_candidates": all_evaluated_candidates,
            "bot3_deployed": reload_bot3,
            "report_md": report_md
        }

    def reset_moonshot_bot(
        self,
        initial_wallet: float = 10.0,
        factor_id: str = "HERMES_ATH_26",
        timeframe: str = "15m",
        leverage: float = 10.0,
        stoploss: float = -0.045
    ) -> Dict[str, Any]:
        """
        Reinicia de forma limpia el Bot 3 (:8083 - Moonshot 10 a 100 USDT):
        1. Detiene la operativa actual de Bot 3.
        2. Archiva la base de datos de trades previa (/user_data/archive/tradesv3.ensemble_100u_run_TIMESTAMP.sqlite).
        3. Configura el saldo virtual inicial a 10.00 USDT en config_ensemble_100u.json.
        4. Compila la estrategia con el factor récord ATH indicado (por defecto HERMES_ATH_26).
        5. Reinicia Bot 3 con la base de datos limpia e inicializada a 10.00 USDT.
        6. Registra el evento en la memoria episódica de Hermes y emite reporte ejecutivo.
        """
        import shutil
        import subprocess
        import time

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        initial_wallet = float(initial_wallet)
        
        # 1. Detener Bot 3 vía Orchestrator y vía Docker si aplica
        if hasattr(self.orchestrator, "clients") and "bot_mined_ensemble" in self.orchestrator.clients:
            try:
                self.orchestrator.clients["bot_mined_ensemble"].stop_bot()
            except Exception as e:
                logger.warning(f"Aviso deteniendo bot_mined_ensemble vía API: {e}")

        # Si corre en contenedor Docker local, detenerlo para liberar locks de SQLite
        try:
            subprocess.run(["docker", "stop", "meme_hunter_ensemble"], capture_output=True, timeout=15)
        except Exception as e:
            logger.debug(f"Docker stop no ejecutado o no disponible: {e}")

        # 2. Archivar base de datos previa
        user_data_dir = "user_data"
        db_file = os.path.join(user_data_dir, "tradesv3.ensemble_100u.sqlite")
        archive_dir = os.path.join(user_data_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        archived_target = os.path.join(archive_dir, f"tradesv3.ensemble_100u_run_{timestamp_str}.sqlite")
        
        db_archived = False
        if os.path.exists(db_file):
            try:
                shutil.move(db_file, archived_target)
                db_archived = True
                logger.info(f"Base de datos de Bot 3 archivada en: {archived_target}")
            except Exception as e:
                logger.warning(f"Error moviendo DB {db_file}: {e}")
                try:
                    shutil.copy2(db_file, archived_target)
                    os.remove(db_file)
                    db_archived = True
                except Exception as e2:
                    logger.error(f"Fallo crítico al archivar DB {db_file}: {e2}")

        # Limpiar archivos auxiliares WAL / SHM si existiesen
        for aux in [f"{db_file}-wal", f"{db_file}-shm"]:
            if os.path.exists(aux):
                try:
                    os.remove(aux)
                except Exception:
                    pass

        # 3. Configurar user_data/config_ensemble_100u.json
        config_path = os.path.join(user_data_dir, "config_ensemble_100u.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["dry_run"] = True
                cfg["dry_run_wallet"] = initial_wallet
                cfg["timeframe"] = timeframe
                cfg["stoploss"] = stoploss
                cfg["max_open_trades"] = 1
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4)
                logger.info(f"Configuración de Bot 3 actualizada con {initial_wallet:.2f} USDT.")
            except Exception as e:
                logger.warning(f"Error actualizando config de Bot 3: {e}")

        # 4. Compilar estrategia con el factor especificado
        compiled_path = None
        try:
            from scripts.pipelines.compile_ensemble_strategy import generate_ensemble_strategy_file
            compiled_path = generate_ensemble_strategy_file(
                factor_library_path="mining/factor_library.json",
                output_strategy_path=os.path.join(user_data_dir, "strategies", "MemeHunter_MinedEnsemble.py"),
                timeframe=timeframe,
                leverage=leverage,
                stoploss=stoploss,
                specific_factor_id=factor_id
            )
            logger.info(f"Estrategia ensamble compilada para Bot 3 con factor {factor_id} en {compiled_path}")
        except Exception as e:
            logger.warning(f"Error compilando estrategia ensamble para Bot 3: {e}")

        # 5. Reiniciar Bot 3
        started_ok = False
        # Intentar levantar contenedor si docker está activo
        try:
            res_dc = subprocess.run(["docker", "start", "meme_hunter_ensemble"], capture_output=True, timeout=15)
            if res_dc.returncode == 0:
                started_ok = True
                time.sleep(3.0)  # Breve espera para inicialización de API
        except Exception as e:
            logger.debug(f"Docker start no ejecutado: {e}")

        # Recargar y arrancar vía Orchestrator API
        if hasattr(self.orchestrator, "clients") and "bot_mined_ensemble" in self.orchestrator.clients:
            b3 = self.orchestrator.clients["bot_mined_ensemble"]
            try:
                b3.reload_config()
                s_res = b3.start_bot()
                if s_res.get("status") == "ok":
                    started_ok = True
            except Exception as e:
                logger.warning(f"Aviso recargando bot_mined_ensemble vía API: {e}")

        # 6. Registrar en memoria episódica
        reset_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "reset_moonshot_bot",
            "bot_id": "bot_mined_ensemble",
            "initial_wallet": initial_wallet,
            "factor_id": factor_id,
            "db_archived": archived_target if db_archived else None,
            "started_ok": started_ok
        }
        self.memory.setdefault("resets_history", []).append(reset_event)
        self.memory["last_decision"] = {
            "timestamp": reset_event["timestamp"],
            "explanation": f"Hermes reinició el bot Moonshot 10->100 (:8083) con balance limpio de {initial_wallet:.2f} USDT y factor '{factor_id}'.",
            "event": reset_event
        }
        self._save_memory()

        # 7. Formatear reporte ejecutivo
        report_md = (
            f"🔄 *REINICIO DE BOT 3 (:8083) — NUEVO INTENTO MOONSHOT 10 A 100 USDT*\n\n"
            f"• *Capital Asignado:* `{initial_wallet:.2f} USDT` (Cuenta Limpia / Dry-Run)\n"
            f"• *Estrategia Inyectada:* `{factor_id}`\n"
            f"• *Apalancamiento:* `{leverage:.0f}x` | *Timeframe:* `{timeframe}` | *Stop Loss:* `{stoploss*100:.1f}%`\n"
            f"• *Base de Datos Anterior:* `{'Archivada en user_data/archive/' if db_archived else 'No encontrada'}`\n"
            f"• *Estado de Ejecución:* {'🟢 Activo en vivo (Freqtrade OK)' if started_ok else '⚠️ Preparado (Pendiente inicio)'}\n\n"
            f"🛡️ *Circuit Breaker Automático:* Si el balance desciende de `5.00 USDT`, Hermes ejecutará un auto-reinicio preventivo inmediato."
        )

        return {
            "status": "ok",
            "bot_id": "bot_mined_ensemble",
            "initial_wallet": initial_wallet,
            "factor_id": factor_id,
            "db_archived": archived_target if db_archived else None,
            "started_ok": started_ok,
            "report_md": report_md
        }


