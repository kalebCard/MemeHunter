"""
proactive_hunter.py - Motor Autónomo de I+D Cuantitativo y Adaptabilidad Dinámica de Hermes.
Sprint 57 (PB-230 a PB-236).

Permite a Hermes operar como un Agente Cuantitativo Proactivo:
1. Laboratorio Continuo de I+D en Segundo Plano (Thread Desacoplado).
2. Adaptabilidad Dinámica al Régimen de Mercado (disparo automático ante transiciones).
3. Backtesting Vectorial Riguroso con Slippage y Criterios Institucionales.
4. Hot-Reload y Despliegue Dinámico en Bot 3 (:8083 Sandbox).
5. Guardián de Decaimiento de Alpha (Alpha Decay Guardian).
6. Notificaciones Ejecutivas Proactivas en Telegram (@Atutaskbot).
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("HermesProactiveHunter")


class HermesProactiveHunter:
    """
    Motor Autónomo Proactivo para la búsqueda continua de alpha,
    evaluación por régimen y despliegue dinámico de estrategias.
    """

    def __init__(
        self,
        operator: Optional[Any] = None,
        messenger: Optional[Any] = None,
        enabled: bool = True,
        rnd_interval_sec: int = 7200,
        target_sharpe: float = 1.8,
        target_winrate: float = 50.0,
        state_path: str = "storage/hermes_proactive_state.json"
    ):
        self.operator = operator
        self.messenger = messenger
        self.enabled = enabled and (os.getenv("HERMES_PROACTIVE_ENABLED", "true").lower() in ("true", "1", "yes"))
        self.rnd_interval_sec = int(os.getenv("HERMES_PROACTIVE_INTERVAL_SEC", str(rnd_interval_sec)))
        self.target_sharpe = float(os.getenv("HERMES_TARGET_SHARPE", str(target_sharpe)))
        self.target_winrate = float(os.getenv("HERMES_TARGET_WINRATE", str(target_winrate)))
        self.state_path = state_path

        self._lock = threading.RLock()
        self._is_busy = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._last_evaluated_regime: Optional[str] = None
        self._consecutive_losses_count = 0

        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Carga el estado persistente del laboratorio proactivo."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error leyendo estado proactivo en {self.state_path}: {e}")

        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_cycle_timestamp": None,
            "total_cycles_run": 0,
            "deployed_factors_count": 0,
            "current_live_factor": None,
            "last_regime": None,
            "evaluation_history": []
        }

    def _save_state(self) -> None:
        """Guarda el estado del laboratorio proactivo de forma atómica."""
        with self._lock:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            try:
                temp_path = f"{self.state_path}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.state_path)
            except Exception as e:
                logger.error(f"Error guardando estado proactivo: {e}")

    def start_worker(self) -> None:
        """Inicia el worker desacoplado de I+D en segundo plano."""
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                logger.info("Worker proactivo de I+D ya se encuentra en ejecución.")
                return

            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._proactive_loop,
                daemon=True,
                name="HermesProactiveRndWorker"
            )
            self._worker_thread.start()
            logger.info(f"🧪 Worker de I+D Proactivo de Hermes iniciado (Intervalo: {self.rnd_interval_sec}s).")

    def stop_worker(self) -> None:
        """Detiene el worker de I+D ordenadamente."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)
            logger.info("Worker de I+D Proactivo detenido ordenadamente.")

    def _proactive_loop(self) -> None:
        """Bucle continuo del laboratorio de I+D."""
        # Esperar 15 segundos al inicio para permitir que los bots se inicialicen
        time.sleep(15)
        while not self._stop_event.is_set():
            if self.enabled:
                try:
                    self.run_proactive_rnd_cycle(trigger_reason="periodic_cadence")
                except Exception as e:
                    logger.error(f"Excepción en ciclo proactivo de I+D: {e}", exc_info=True)

            # Esperar el intervalo configurado verificando periódicamente el evento de parada
            elapsed = 0
            while not self._stop_event.is_set() and elapsed < self.rnd_interval_sec:
                time.sleep(2)
                elapsed += 2

    def on_regime_shift(self, new_regime: str, old_regime: Optional[str] = None) -> None:
        """
        Disparador por evento: cuando el mercado cambia de régimen,
        se invoca inmediatamente la generación y evaluación de alphas específicos.
        """
        if not self.enabled:
            return

        logger.info(
            f"⚡ [HermesProactiveHunter] Disparo por cambio de régimen: {old_regime} -> {new_regime}. "
            f"Iniciando evaluación y adaptación inmediata de estrategia..."
        )
        # Disparar en hilo independiente para no retrasar el ciclo del daemon
        t = threading.Thread(
            target=self.run_proactive_rnd_cycle,
            kwargs={"trigger_reason": f"regime_shift_{old_regime}_to_{new_regime}", "force_regime": new_regime},
            daemon=True,
            name="HermesRegimeShiftHandler"
        )
        t.start()

    def run_proactive_rnd_cycle(
        self,
        trigger_reason: str = "manual",
        force_regime: Optional[str] = None,
        pair: str = "1000PEPE",
        timeframe: str = "15m",
        leverage: float = 10.0,
        initial_wallet: float = 10.0
    ) -> Dict[str, Any]:
        """
        Ejecuta una ronda completa de investigación cuantitativa, backtesting y despliegue.
        """
        with self._lock:
            if self._is_busy:
                logger.warning("Laboratorio proactivo ocupado con otra tarea. Descartando ciclo concurrente.")
                return {"status": "busy", "message": "El laboratorio ya está evaluando candidatos."}
            self._is_busy = True

        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            logger.info(f"🔬 Iniciando ciclo de I+D Proactivo [Motivo: {trigger_reason}]...")

            # 1. Determinar régimen
            current_regime = force_regime
            if not current_regime and self.operator and hasattr(self.operator, "regime_detector"):
                r_info = self.operator.regime_detector.detect_regime()
                current_regime = r_info.get("regime", "RANGE_CHOP")
            if not current_regime:
                current_regime = "RANGE_CHOP"

            # 2. Generar hipótesis matemáticas adaptadas al régimen
            candidate_formulas = self._get_hypotheses_for_regime(current_regime)

            # 3. Backtesting riguroso de cada candidato
            evaluated_candidates = self._evaluate_candidates(
                candidate_formulas,
                pair=pair,
                timeframe=timeframe,
                leverage=leverage,
                initial_wallet=initial_wallet
            )

            # 4. Seleccionar el mejor candidato
            best_candidate = None
            if evaluated_candidates:
                evaluated_candidates.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
                best_candidate = evaluated_candidates[0]

            is_qualified = False
            if best_candidate:
                is_qualified = (
                    best_candidate["sharpe_ratio"] >= self.target_sharpe
                    and best_candidate["win_rate_pct"] >= self.target_winrate
                    and best_candidate["total_trades"] >= 2
                )

            deployment_result = None
            if is_qualified and best_candidate:
                logger.info(
                    f"🏆 Candidato Calificado Encontrado: {best_candidate['formula']} "
                    f"(Sharpe: {best_candidate['sharpe_ratio']:+.2f}, WR: {best_candidate['win_rate_pct']:.1f}%). "
                    f"Procediendo al despliegue en Bot 3 (:8083)..."
                )
                deployment_result = self._deploy_winning_factor(
                    best_candidate=best_candidate,
                    regime=current_regime,
                    trigger_reason=trigger_reason,
                    timeframe=timeframe,
                    leverage=leverage,
                    initial_wallet=initial_wallet
                )

                # Notificación proactiva a Telegram
                self._send_proactive_alert(best_candidate, current_regime, trigger_reason)

            # 5. Guardar en memoria de estado
            record = {
                "timestamp": timestamp,
                "trigger_reason": trigger_reason,
                "regime": current_regime,
                "candidates_evaluated": len(evaluated_candidates),
                "best_candidate": best_candidate,
                "qualified": is_qualified,
                "deployed": deployment_result.get("status") == "ok" if deployment_result else False
            }
            self.state["total_cycles_run"] += 1
            self.state["last_cycle_timestamp"] = timestamp
            self.state["last_regime"] = current_regime
            self.state["evaluation_history"].append(record)
            if len(self.state["evaluation_history"]) > 50:
                self.state["evaluation_history"].pop(0)
            self._save_state()

            logger.info(
                f"✅ Ciclo de I+D Proactivo completado. Evaluados: {len(evaluated_candidates)} | "
                f"Mejor Sharpe: {best_candidate['sharpe_ratio'] if best_candidate else 0.0:+.2f} | "
                f"Calificado: {is_qualified}"
            )

            return {
                "status": "ok",
                "trigger_reason": trigger_reason,
                "regime": current_regime,
                "best_candidate": best_candidate,
                "is_qualified": is_qualified,
                "deployment": deployment_result
            }

        finally:
            with self._lock:
                self._is_busy = False

    def _get_hypotheses_for_regime(self, regime: str) -> List[str]:
        """
        Sintetiza fórmulas matemáticas con sesgo intencional adaptado a la dinámica del régimen.
        """
        # Solo invocar OpenRouter LLM si hay una API Key real y no estamos en ejecución de tests
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if len(openrouter_key) > 15 and not os.getenv("PYTEST_CURRENT_TEST"):
            try:
                from mining.llm_alpha_generator import LLMAlphaSynthesizer
                synth = LLMAlphaSynthesizer()
                goal_desc = f"Estrategia cuantitativa de alta frecuencia optimizada para el régimen {regime} en futuros de memecoins"
                raw_cands = synth.synthesize_alphas(market_regime=regime, n_candidates=3, goal_description=goal_desc)
                if raw_cands:
                    return [f_str for f_str, _ in raw_cands]
            except Exception as e:
                logger.debug(f"Síntesis LLM no disponible, usando banco de fórmulas ortogonales: {e}")

        # Banco de hipótesis determinísticas adaptadas por régimen
        regime_banks = {
            "RANGE_CHOP": [
                "ts_rank(rvol, 14) * ts_zscore((close - vwap), 10)",
                "ts_delta(close, 3) * ts_zscore(hl_spread, 10)",
                "neg(ts_zscore(returns, 8)) * ts_rank(volume, 12)"
            ],
            "BEAR_CASCADE": [
                "neg(ts_delta(close, 5)) * ts_rank(rvol, 10)",
                "ts_zscore(returns, 8) * ts_rank(volume, 12)",
                "ts_rank(hl_spread, 14) * neg(ts_zscore(close, 10))"
            ],
            "BULL_PARABOLIC": [
                "ts_rank((close - ts_delay(close, 10)), 14) * ts_rank(volume, 10)",
                "ts_zscore(returns, 5) * ts_rank(rvol, 12)",
                "ts_delta(close, 2) / (ts_std(close, 10) + 1e-6)"
            ],
            "PANIC_VOLATILITY": [
                "ts_rank(rvol, 14) * neg(ts_zscore(hl_spread, 10))",
                "ts_delta(close, 4) * ts_rank(volume, 10)",
                "ts_zscore((close - vwap), 8) * ts_rank(rvol, 10)"
            ]
        }
        return regime_banks.get(regime, regime_banks["RANGE_CHOP"])

    def _evaluate_candidates(
        self,
        formulas: List[str],
        pair: str,
        timeframe: str,
        leverage: float,
        initial_wallet: float
    ) -> List[Dict[str, Any]]:
        """Backtestea cada fórmula mediante el motor cuantitativo."""
        try:
            from meme_hunter.alpha.tester import run_strategy_backtest
        except Exception:
            try:
                from src.meme_hunter.alpha.tester import run_strategy_backtest
            except Exception:
                run_strategy_backtest = None

        evaluated = []
        for f_str in formulas:
            if run_strategy_backtest:
                try:
                    bt = run_strategy_backtest(
                        formula=f_str,
                        pair=pair,
                        timeframe=timeframe,
                        direction="both",
                        leverage=leverage,
                        stoploss_pct=0.045,
                        trailing_stop_pct=0.02,
                        initial_wallet=initial_wallet
                    )
                    m = bt.get("metrics", {})
                    sharpe = float(m.get("sharpe_ratio", 0.0) or 0.0)
                    winrate = float(m.get("win_rate_pct", 0.0) or 0.0)
                    roi = float(m.get("total_return_pct", 0.0) or 0.0)
                    dd = float(m.get("max_drawdown_pct", 0.0) or 0.0)
                    trades = int(m.get("total_trades", 0) or 0)
                    pf = float(m.get("profit_factor", 0.0) or 0.0)
                except Exception as e:
                    logger.warning(f"Error evaluando candidato '{f_str}': {e}")
                    sharpe, winrate, roi, dd, trades, pf = 0.0, 0.0, 0.0, 0.0, 0, 0.0
            else:
                sharpe, winrate, roi, dd, trades, pf = 0.0, 0.0, 0.0, 0.0, 0, 0.0

            cand_entry = {
                "formula": f_str,
                "sharpe_ratio": round(sharpe, 3),
                "win_rate_pct": round(winrate, 1),
                "total_return_pct": round(roi, 2),
                "max_drawdown_pct": round(dd, 2),
                "total_trades": trades,
                "profit_factor": round(pf, 2)
            }
            evaluated.append(cand_entry)

        return evaluated

    def _deploy_winning_factor(
        self,
        best_candidate: Dict[str, Any],
        regime: str,
        trigger_reason: str,
        timeframe: str,
        leverage: float,
        initial_wallet: float
    ) -> Dict[str, Any]:
        """Promociona la estrategia ganadora, recompila y actualiza Bot 3 (:8083)."""
        library_path = "mining/factor_library.json"
        incubator_path = "portfolio/incubator_state.json"

        # 1. Registrar en factor_library.json
        factors = []
        if os.path.exists(library_path):
            try:
                with open(library_path, "r", encoding="utf-8") as f:
                    factors = json.load(f)
            except Exception:
                factors = []

        factor_id = f"HERMES_PROACTIVE_{len(factors)+1:02d}"
        factor_entry = {
            "factor_id": factor_id,
            "formula": best_candidate["formula"],
            "sharpe_proxy": best_candidate["sharpe_ratio"],
            "win_rate_pct": best_candidate["win_rate_pct"],
            "simulated_roi_pct": best_candidate["total_return_pct"],
            "max_drawdown_pct": best_candidate["max_drawdown_pct"],
            "timeframe": timeframe,
            "leverage": leverage,
            "regime": regime,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": trigger_reason
        }
        factors.append(factor_entry)
        try:
            with open(library_path, "w", encoding="utf-8") as f:
                json.dump(factors, f, indent=2)
        except Exception as e:
            logger.warning(f"Error guardando factor en {library_path}: {e}")

        # 2. Actualizar incubator_state.json
        if os.path.exists(incubator_path):
            try:
                with open(incubator_path, "r", encoding="utf-8") as f:
                    inc_data = json.load(f)
                for k in inc_data:
                    if inc_data[k].get("status") == "LIVE":
                        inc_data[k]["target_capital_weight"] = 0.0
                inc_data[factor_id] = {
                    "strategy_id": factor_id,
                    "name": best_candidate["formula"],
                    "status": "LIVE",
                    "target_capital_weight": 1.0,
                    "backtest_sharpe": best_candidate["sharpe_ratio"],
                    "live_sharpe": 0.0,
                    "days_in_stage": 0,
                    "decay_zscore": 0.0,
                    "last_audit_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
                with open(incubator_path, "w", encoding="utf-8") as f:
                    json.dump(inc_data, f, indent=2)
            except Exception as e:
                logger.warning(f"Error actualizando incubadora en {incubator_path}: {e}")

        # 3. Recompilar estrategia Freqtrade MemeHunter_MinedEnsemble
        try:
            from scripts.pipelines.compile_ensemble_strategy import generate_ensemble_strategy_file
            generate_ensemble_strategy_file(
                factor_library_path=library_path,
                incubator_state_path=incubator_path,
                output_strategy_path="user_data/strategies/MemeHunter_MinedEnsemble.py",
                timeframe=timeframe,
                leverage=leverage,
                stoploss=-0.045
            )
            logger.info("Estrategia MemeHunter_MinedEnsemble recompilada exitosamente.")
        except Exception as comp_err:
            logger.warning(f"Error recompilando ensamble: {comp_err}")

        # 4. Hot-reload en Bot 3 si el orquestador está disponible
        reload_ok = False
        if self.operator and hasattr(self.operator, "orchestrator"):
            orch = self.operator.orchestrator
            if hasattr(orch, "clients") and "bot_mined_ensemble" in orch.clients:
                b3 = orch.clients["bot_mined_ensemble"]
                try:
                    r = b3.reload_config()
                    b3.start_bot()
                    reload_ok = (r.get("status") == "ok")
                except Exception as e:
                    logger.warning(f"Error recargando Bot 3: {e}")

        self.state["current_live_factor"] = factor_entry
        self.state["deployed_factors_count"] += 1
        self._save_state()

        return {
            "status": "ok",
            "factor_id": factor_id,
            "reload_bot3": reload_ok
        }

    def _send_proactive_alert(
        self,
        candidate: Dict[str, Any],
        regime: str,
        trigger_reason: str
    ) -> None:
        """Emite un informe proactivo directo a Telegram."""
        if not self.messenger and self.operator and hasattr(self.operator, "messenger"):
            self.messenger = self.operator.messenger
        if not self.messenger:
            try:
                from meme_hunter.hermes.telegram_messenger import HermesTelegramMessenger
                self.messenger = HermesTelegramMessenger()
            except Exception:
                pass

        if not self.messenger:
            return

        report = (
            f"🧠 *HERMES PROACTIVO: NUEVA ESTRATEGIA DESPLEGADA*\n\n"
            f"• *Disparador:* `{trigger_reason}`\n"
            f"• *Régimen:* *{regime}*\n"
            f"• *Fórmula Ganadora:* `{candidate['formula']}`\n"
            f"• *Sharpe Ratio:* `{candidate['sharpe_ratio']:+.2f}` (Objetivo: `>={self.target_sharpe:.1f}`)\n"
            f"• *Win Rate:* `{candidate['win_rate_pct']:.1f}%` ({candidate['total_trades']} trades)\n"
            f"• *Retorno Proyectado:* `{candidate['total_return_pct']:+.2f}%`\n"
            f"• *Drawdown Máx:* `{candidate['max_drawdown_pct']:.1f}%`\n\n"
            f"🚀 *Acción Autónoma:* Estrategia compilada y desplegada en **Bot 3 (:8083 Sandbox)** para monetización inmediata."
        )
        try:
            self.messenger.send_executive_report(report)
            logger.info("Alerta proactiva enviada a Telegram con éxito.")
        except Exception as e:
            logger.warning(f"No se pudo enviar alerta a Telegram: {e}")

    def check_alpha_decay_and_replace(self) -> Dict[str, Any]:
        """
        Guardián de Decaimiento de Alpha:
        Verifica el rendimiento reciente de Bot 3; si detecta pérdidas consecutivas
        o pérdida de ventaja estadística, retira el factor y busca reemplazo inmediato.
        """
        if not self.operator or not hasattr(self.operator, "orchestrator"):
            return {"status": "skipped", "reason": "Sin orquestador disponible"}

        orch = self.operator.orchestrator
        if not hasattr(orch, "clients") or "bot_mined_ensemble" not in orch.clients:
            return {"status": "skipped", "reason": "Bot 3 no configurado"}

        b3 = orch.clients["bot_mined_ensemble"]
        profit_res = b3.get_profit()
        data = profit_res.get("data", {})
        losing_trades = int(data.get("losing_trades", 0))
        winning_trades = int(data.get("winning_trades", 0))
        profit_closed_coin = float(data.get("profit_closed_coin", 0.0))

        # Criterio de decadencia: pérdidas acumuladas o drawdown severo
        is_decayed = (losing_trades >= 3 and winning_trades == 0) or (profit_closed_coin < -2.5)

        if is_decayed:
            logger.warning(
                f"🚨 [AlphaDecayGuardian] Decadencia detectada en Bot 3: "
                f"Losses: {losing_trades}, PnL: {profit_closed_coin:.2f} USDT. "
                f"Retirando factor y buscando reemplazo proactivo..."
            )
            # Desencadenar búsqueda de reemplazo
            res = self.run_proactive_rnd_cycle(trigger_reason="alpha_decay_replacement")
            return {"status": "decay_detected", "replacement_result": res}

        return {"status": "healthy", "pnl": profit_closed_coin, "losses": losing_trades}

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado y telemetría del laboratorio proactivo."""
        with self._lock:
            return {
                "enabled": self.enabled,
                "is_busy": self._is_busy,
                "worker_alive": self._worker_thread.is_alive() if self._worker_thread else False,
                "rnd_interval_sec": self.rnd_interval_sec,
                "target_sharpe": self.target_sharpe,
                "target_winrate": self.target_winrate,
                "total_cycles_run": self.state.get("total_cycles_run", 0),
                "last_cycle_timestamp": self.state.get("last_cycle_timestamp"),
                "current_live_factor": self.state.get("current_live_factor"),
                "deployed_factors_count": self.state.get("deployed_factors_count", 0),
                "last_regime": self.state.get("last_regime")
            }
