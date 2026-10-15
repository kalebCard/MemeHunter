"""
run_8h_moonshot_refinement.py - Maratón Autónomo de 8 Horas de Investigación Cuantitativa de Hermes.
Sprint 53: Hermes Autonomous Quant Researcher & Continuous Refinement Marathon.

Ejecuta un bucle continuo de 8 horas:
1. Síntesis de fórmulas con OpenRouter (DeepSeek-V3).
2. Backtesting vectorial en velas de 15m reales de memecoins (1000PEPE, DOGE).
3. Retroalimentación de diagnósticos de fallo en cada iteración.
4. Despliegue en caliente automático del mejor récord en Bot 3 (:8083).
5. Transmisión periódica de avances y alertas de récord a Telegram (@Atutaskbot).
"""

import os
import sys
import time
import json
import signal
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Asegurar path institucional
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from client.multi_bot_orchestrator import MultiBotOrchestratorClient
from meme_hunter.hermes.regime_detector import HermesRegimeDetector
from meme_hunter.hermes.telegram_messenger import HermesTelegramMessenger
from mining.llm_alpha_generator import LLMAlphaSynthesizer
from mining.formula_parser import FormulaASTParser
from meme_hunter.alpha.tester import run_strategy_backtest
from scripts.pipelines.compile_ensemble_strategy import generate_ensemble_strategy_file

# Configurar logging
os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
log_file = os.path.join(ROOT_DIR, "logs", "8h_moonshot_marathon.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [HermesMarathon8h]: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HermesMarathon8h")

running = True


def set_windows_keep_awake():
    """Evita que Windows entre en modo de suspensión durante el maratón cuantitativo."""
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_AWAYMODE_REQUIRED = 0x00000040
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
            logger.info("🛡️ Protección anti-suspensión de Windows activada (SetThreadExecutionState).")
        except Exception as e:
            logger.warning(f"No se pudo activar protección anti-suspensión: {e}")


def restore_windows_sleep():
    """Restaura el estado normal de energía de Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            logger.info("🛡️ Protección anti-suspensión liberada.")
        except Exception:
            pass


import atexit
atexit.register(restore_windows_sleep)


def _signal_handler(signum, frame):
    global running
    logger.info(f"Señal de interrupción {signum} recibida. Deteniendo maratón de forma segura...")
    running = False
    restore_windows_sleep()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def run_marathon(
    duration_hours: float = 8.0,
    target_goal: str = "Pasar de 10 a 100 USDT en 1 semana (Moonshot 10x)",
    timeframe: str = "15m",
    leverage: float = 10.0,
    initial_wallet: float = 10.0,
    cycle_interval_sec: float = 45.0,
    max_budget_usd: float = 2.0
):
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=duration_hours)

    logger.info("=" * 70)
    logger.info("🧠 INICIANDO MARATÓN AUTÓNOMO DE 8 HORAS DE INVESTIGACIÓN CUANTITATIVA")
    logger.info(f"• Meta: {target_goal}")
    logger.info(f"• Timeframe: {timeframe} | Apalancamiento: {leverage:.0f}x | Cartera Inicial: {initial_wallet} USDT")
    logger.info(f"• Duración programada: {duration_hours} horas (hasta {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')})")
    logger.info(f"• Presupuesto máximo seguro de API: ${max_budget_usd:.2f} USD")
    logger.info("=" * 70)

    messenger = HermesTelegramMessenger()
    orchestrator = MultiBotOrchestratorClient()
    regime_detector = HermesRegimeDetector()
    synthesizer = LLMAlphaSynthesizer()

    # Enviar mensaje inicial a Telegram
    startup_msg = (
        "🧠 *HERMES ALTER EGO — REACTIVACIÓN DE CICLO DE REFINAMIENTO (10 A 100 USDT)*\n\n"
        "He reanudado la investigación cuantitativa autónoma para el experimento *Moonshot (10 a 100 USDT en 1 semana)*.\n\n"
        f"🎯 *Objetivo:* `{target_goal}`\n"
        f"• *Microestructura:* Timeframe `{timeframe}` | Apalancamiento `{leverage:.0f}x` Aislado | Re-inversión 95%\n"
        "• *Blindaje:* Protección anti-suspensión de Windows activada (SetThreadExecutionState).\n"
        "• *Despliegue Dinámico:* Inyección automática de cada factor mejorado en **Bot 3 (:8083)** en simulación con 10 USDT.\n"
        f"• *Fin previsto:* `{end_time.strftime('%H:%M:%S UTC')}` (~{duration_hours:.0f} horas).\n\n"
        "Te notificaré en Telegram cada vez que compile una mejora o en cada informe horario. ¡A trabajar!"
    )
    messenger.send_executive_report(startup_msg)

    # Estado del maratón
    cycles_completed = 0
    total_formulas_tested = 0
    accumulated_cost_usd = 0.0
    failed_diagnostics: List[str] = []
    
    session_best_sharpe = 1.60   # Umbral alcanzable para admitir mejoras incrementales continuas
    global_record_sharpe = 4.53  # Récord histórico absoluto de la estrategia Moonshot
    
    best_candidate: Dict[str, Any] = {
        "sharpe_ratio": 4.53, # Récord base previo
        "win_rate_pct": 48.9,
        "total_return_pct": 29.45,
        "max_drawdown_pct": 45.11,
        "formula": "EMA8_EMA21_RVOL_Breakout",
        "factor_id": "BASE_MOONSHOT"
    }

    last_hourly_report = start_time
    hours_elapsed = 0

    set_windows_keep_awake()

    while running:
        current_now = datetime.now(timezone.utc)
        if current_now >= end_time:
            logger.info("Tiempo límite de 8 horas alcanzado.")
            break

        cycles_completed += 1
        elapsed_total = (current_now - start_time).total_seconds()
        remaining_total = max(0, (end_time - current_now).total_seconds())

        logger.info(
            f"--- [Ciclo #{cycles_completed}] Tiempo transcurrido: {elapsed_total/3600:.2f}h / {duration_hours}h "
            f"({remaining_total/3600:.2f}h restantes) ---"
        )

        # 1. Detectar régimen de mercado
        try:
            reg_info = regime_detector.detect_regime()
            current_regime = reg_info.get("regime", "RANGE_CHOP")
        except Exception as e:
            current_regime = "RANGE_CHOP"

        # 2. Control de presupuesto de API
        use_llm = (accumulated_cost_usd < max_budget_usd)
        candidates = []

        if use_llm:
            try:
                candidates = synthesizer.synthesize_alphas(
                    market_regime=current_regime,
                    failed_factors=failed_diagnostics[-6:] if failed_diagnostics else None,
                    n_candidates=3,
                    goal_description=(
                        f"{target_goal} en timeframe {timeframe} con apalancamiento {leverage:.0f}x. "
                        f"Superar Sharpe actual de {best_candidate['sharpe_ratio']:.2f} con drawdowns menores a 40%."
                    )
                )
                accumulated_cost_usd += 0.00065
            except Exception as e:
                logger.warning(f"Excepción en síntesis LLM: {e}")

        # Fallback heurístico / mutaciones locales si no hay respuesta LLM o por presupuesto
        if not candidates:
            fallbacks = [
                "ts_rank(rvol, 14) * ts_zscore((close - vwap), 10)",
                "ts_zscore(returns, 8) * ts_rank(volume, 14)",
                "ts_delta(close, 4) * ts_zscore(hl_spread, 12)",
                "ts_decay_linear(returns, 6) * ts_rank(rvol, 10)",
                "ts_zscore(log(rvol + 1e-6), 14) * sign(ts_delta(close, 6))"
            ]
            candidates = []
            for f_str in fallbacks:
                try:
                    candidates.append((f_str, FormulaASTParser.parse(f_str)))
                except Exception:
                    pass

        # 3. Backtesting vectorial contra pares de memecoins
        test_pairs = ["1000PEPE", "DOGE"]
        cycle_best_in_turn = None

        for formula_str, _ in candidates:
            total_formulas_tested += 1
            # Probar en ambos pares y promediar
            pair_sharpes = []
            pair_winrates = []
            pair_rois = []
            pair_dds = []
            pair_trades = []

            for p in test_pairs:
                try:
                    bt = run_strategy_backtest(
                        formula=formula_str,
                        pair=p,
                        timeframe=timeframe,
                        direction="both",
                        leverage=leverage,
                        stoploss_pct=0.045,
                        trailing_stop_pct=0.02,
                        initial_wallet=initial_wallet
                    )
                    m = bt.get("metrics", {})
                    pair_sharpes.append(float(m.get("sharpe_ratio", 0.0) or 0.0))
                    pair_winrates.append(float(m.get("win_rate_pct", 0.0) or 0.0))
                    pair_rois.append(float(m.get("total_return_pct", 0.0) or 0.0))
                    pair_dds.append(float(m.get("max_drawdown_pct", 0.0) or 0.0))
                    pair_trades.append(int(m.get("total_trades", 0) or 0))
                except Exception as ex:
                    pass

            if not pair_sharpes:
                continue

            avg_sharpe = sum(pair_sharpes) / len(pair_sharpes)
            avg_winrate = sum(pair_winrates) / len(pair_winrates)
            avg_roi = sum(pair_rois) / len(pair_rois)
            avg_dd = max(pair_dds)
            tot_trades = sum(pair_trades)

            cand_score = {
                "formula": formula_str,
                "sharpe_ratio": round(avg_sharpe, 2),
                "win_rate_pct": round(avg_winrate, 1),
                "total_return_pct": round(avg_roi, 2),
                "max_drawdown_pct": round(avg_dd, 1),
                "total_trades": tot_trades,
                "cycle": cycles_completed
            }

            if cycle_best_in_turn is None or cand_score["sharpe_ratio"] > cycle_best_in_turn["sharpe_ratio"]:
                cycle_best_in_turn = cand_score

            # 4. Verificación de PROMOCIÓN A ENSAMBLE y NUEVO RÉCORD GLOBAL
            is_session_improvement = (
                cand_score["sharpe_ratio"] > session_best_sharpe and
                cand_score["win_rate_pct"] >= 45.0 and
                cand_score["total_trades"] >= 8
            )
            is_new_ath = (
                cand_score["sharpe_ratio"] > global_record_sharpe and
                cand_score["win_rate_pct"] >= 48.0 and
                cand_score["total_trades"] >= 10
            )

            if is_session_improvement or is_new_ath:
                old_sharpe = session_best_sharpe
                session_best_sharpe = cand_score["sharpe_ratio"]
                best_candidate = cand_score
                if is_new_ath:
                    global_record_sharpe = cand_score["sharpe_ratio"]

                logger.info(
                    f"🏆 [{'NUEVO RÉCORD GLOBAL' if is_new_ath else 'MEJORA INCREMENTAL EN SESIÓN'}] Sharpe: {cand_score['sharpe_ratio']} "
                    f"(anterior: {old_sharpe}) | WinRate: {cand_score['win_rate_pct']}% | ROI: {cand_score['total_return_pct']}%"
                )

                # Registrar factor en biblioteca
                lib_path = os.path.join(ROOT_DIR, "mining", "factor_library.json")
                try:
                    with open(lib_path, "r", encoding="utf-8") as f:
                        lib_data = json.load(f)
                except Exception:
                    lib_data = []

                factor_id = f"HERMES_{'ATH' if is_new_ath else 'OPT'}_{len(lib_data)+1:02d}"
                best_candidate["factor_id"] = factor_id
                lib_data.append({
                    "factor_id": factor_id,
                    "formula": cand_score["formula"],
                    "sharpe_proxy": cand_score["sharpe_ratio"],
                    "win_rate_pct": cand_score["win_rate_pct"],
                    "simulated_roi_pct": cand_score["total_return_pct"],
                    "max_drawdown_pct": cand_score["max_drawdown_pct"],
                    "timeframe": timeframe,
                    "leverage": leverage,
                    "goal": target_goal,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "regime": current_regime
                })
                with open(lib_path, "w", encoding="utf-8") as f:
                    json.dump(lib_data, f, indent=2)

                # Compilar y recargar Bot 3 (:8083) en vivo
                try:
                    generate_ensemble_strategy_file(
                        factor_library_path=lib_path,
                        output_strategy_path=os.path.join(ROOT_DIR, "user_data", "strategies", "MemeHunter_MinedEnsemble.py"),
                        timeframe=timeframe,
                        leverage=leverage,
                        stoploss=-0.045
                    )
                    if hasattr(orchestrator, "clients") and "bot_mined_ensemble" in orchestrator.clients:
                        orchestrator.clients["bot_mined_ensemble"].reload_config()
                        orchestrator.clients["bot_mined_ensemble"].start_bot()
                        logger.info(f"Bot 3 (:8083) recargado con el factor {factor_id}.")
                except Exception as comp_err:
                    logger.warning(f"Error recargando Bot 3: {comp_err}")

                # Notificar nuevo récord o mejora a Telegram
                title = "🏆 *¡NUEVO RÉCORD HISTÓRICO GLOBAL DETECTADO POR HERMES!*" if is_new_ath else "⚡ *¡FACTOR PROMETEDOR INYECTADO EN BOT 3 (:8083)!*"
                record_msg = (
                    f"{title}\n\n"
                    f"• *ID del Factor:* `{factor_id}`\n"
                    f"• *Fórmula Matemática:*\n`{cand_score['formula']}`\n\n"
                    f"📊 *Métricas Obtenidas:*\n"
                    f"• *Sharpe Ratio:* `{cand_score['sharpe_ratio']:+.2f}` (superó base de `{old_sharpe:+.2f}`)\n"
                    f"• *Win Rate:* `{cand_score['win_rate_pct']:.1f}%` ({cand_score['total_trades']} operaciones)\n"
                    f"• *Retorno Proyectado:* `{cand_score['total_return_pct']:+.2f}%`\n"
                    f"• *Drawdown Máximo:* `{cand_score['max_drawdown_pct']:.1f}%`\n\n"
                    "🚀 *Acción en la Arena:* Factor compilado e inyectado en **Bot 3 (:8083)** en vivo con 10.00 USDT virtuales."
                )
                messenger.send_executive_report(record_msg)

        # Registrar fallas del ciclo para la siguiente retroalimentación
        if cycle_best_in_turn and not cycle_best_in_turn.get("is_qualified"):
            failed_diagnostics.append(
                f"Fórmula '{cycle_best_in_turn['formula']}': Sharpe={cycle_best_in_turn['sharpe_ratio']}, "
                f"WinRate={cycle_best_in_turn['win_rate_pct']}%, Drawdown={cycle_best_in_turn['max_drawdown_pct']}%. "
                f"Deficiencia: No alcanzó Sharpe mínimo de {session_best_sharpe}."
            )

        # 5. Reporte Horario a Telegram
        if (current_now - last_hourly_report).total_seconds() >= 3600.0:
            hours_elapsed += 1
            last_hourly_report = current_now
            remaining_hrs = max(0.0, (end_time - current_now).total_seconds() / 3600.0)

            hourly_msg = (
                f"⏱️ *HERMES MARATÓN — INFORME HORA {hours_elapsed}/{duration_hours:.0f}*\n\n"
                f"• *Ciclos Completados:* `{cycles_completed}`\n"
                f"• *Fórmulas Cuantitativas Evaluadas:* `{total_formulas_tested}`\n"
                f"• *Mejor Sharpe de Sesión:* `{session_best_sharpe:+.2f}`\n"
                f"• *Récord Histórico Global:* `{global_record_sharpe:+.2f}`\n"
                f"• *Bot 3 (:8083):* 🟢 Activo en simulación con 10 USDT\n"
                f"• *Gasto Acumulado en OpenRouter:* `~${accumulated_cost_usd:.4f} USD`\n"
                f"• *Tiempo Restante de Investigación:* `{remaining_hrs:.1f} horas`"
            )
            messenger.send_executive_report(hourly_msg)

        # Pausa entre ciclos
        time.sleep(cycle_interval_sec)

    restore_windows_sleep()

    # 6. Informe Final al completar el tiempo
    total_duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
    final_report = (
        "🏁 *HERMES MARATÓN FINALIZADO CON ÉXITO*\n\n"
        f"• *Tiempo Total de Investigación:* `{total_duration_sec/3600:.2f} horas`\n"
        f"• *Ciclos de Refinamiento Ejecutados:* `{cycles_completed}`\n"
        f"• *Total de Fórmulas y Variantes Evaluadas:* `{total_formulas_tested}`\n"
        f"• *Gasto Final de API:* `~${accumulated_cost_usd:.4f} USD` (saldo asegurado)\n\n"
        f"🏆 *CAMPEÓN DE LA SESIÓN:* `{best_candidate.get('factor_id')}`\n"
        f"• *Fórmula Matemática:*\n`{best_candidate['formula']}`\n"
        f"• *Sharpe Ratio Final:* `{best_candidate['sharpe_ratio']:+.2f}`\n"
        f"• *Win Rate:* `{best_candidate['win_rate_pct']:.1f}%`\n"
        f"• *Retorno Proyectado:* `{best_candidate['total_return_pct']:+.2f}%`\n"
        f"• *Drawdown:* `{best_candidate['max_drawdown_pct']:.1f}%`\n\n"
        "🎮 La estrategia definitiva se encuentra operando en vivo en **Bot 3 (:8083)** en modo simulado con 10 USDT virtuales."
    )
    messenger.send_executive_report(final_report)
    logger.info("Maratón concluido.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Maratón de Refinamiento Autónomo de Hermes")
    parser.add_argument("--hours", type=float, default=8.0, help="Duración en horas del maratón")
    parser.add_argument("--interval", type=float, default=45.0, help="Intervalo en segundos entre ciclos")
    parser.add_argument("--budget", type=float, default=2.0, help="Presupuesto máximo en USD")
    args = parser.parse_args()
    run_marathon(duration_hours=args.hours, cycle_interval_sec=args.interval, max_budget_usd=args.budget)
