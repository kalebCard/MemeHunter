"""
backtest_scanner.py - Módulo de Escaneo e Inspección del Ecosistema Freqtrade.

Unifica:
1. Catálogo de estrategias físicas de Freqtrade en user_data/strategies/*.py
2. Historial de reportes de backtest en user_data/backtest_results/*.zip
3. Reportes de estrés y simulaciones de Monte Carlo
4. Trades reales y posiciones abiertas en user_data/tradesv3.futures.sqlite
"""

import os
import re
import glob
import json
import zipfile
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def scan_strategies(strategies_dir: str = "user_data/strategies", active_strategy: str = "MemeHunterFuturesV7_Quantum") -> List[Dict[str, Any]]:
    """Escanea todos los archivos de estrategia Python en user_data/strategies/."""
    strategies = []
    if not os.path.exists(strategies_dir):
        return strategies

    pattern = os.path.join(strategies_dir, "*.py")
    for filepath in sorted(glob.glob(pattern)):
        fname = os.path.basename(filepath)
        if fname.startswith("__"):
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Extraer nombre de la clase
            class_match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\(\s*IStrategy\s*\)", content)
            class_name = class_match.group(1) if class_match else fname.replace(".py", "")

            # Extraer docstring inicial
            doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            docstring = doc_match.group(1).strip() if doc_match else "Sin documentación docstring."
            summary_desc = docstring.split("\n\n")[0].replace("\n", " ").strip()

            # Extraer parámetros clave
            tf_match = re.search(r"timeframe\s*=\s*['\"]([^'\"]+)['\"]", content)
            timeframe = tf_match.group(1) if tf_match else "4h"

            sl_match = re.search(r"stoploss\s*=\s*([-0-9.]+)", content)
            stoploss = float(sl_match.group(1)) if sl_match else -0.10

            short_match = re.search(r"can_short\s*=\s*(True|False)", content)
            can_short = short_match.group(1) == "True" if short_match else True

            # Detectar features cuantitativas
            has_ffd = "calculate_ffd" in content or "ffd" in content.lower()
            has_bet_sizing = "continuous_leverage" in content or "kelly" in content.lower()
            has_killswitch = "killswitch" in content.lower() or "drawdown" in content.lower()

            stat = os.stat(filepath)
            updated_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

            is_active = (class_name == active_strategy or fname.replace(".py", "") == active_strategy)

            strategies.append({
                "filename": fname,
                "strategy_id": class_name,
                "name": class_name,
                "timeframe": timeframe,
                "stoploss": stoploss,
                "can_short": can_short,
                "description": summary_desc,
                "has_ffd": has_ffd,
                "has_bet_sizing": has_bet_sizing,
                "has_killswitch": has_killswitch,
                "size_kb": round(stat.st_size / 1024, 1),
                "updated_at": updated_at,
                "is_active": is_active
            })
        except Exception as e:
            pass

    return strategies


def scan_backtest_results(results_dir: str = "user_data/backtest_results") -> List[Dict[str, Any]]:
    """Abre y parsea todos los archivos de resultados (.zip) en user_data/backtest_results/."""
    results = []
    if not os.path.exists(results_dir):
        return results

    pattern = os.path.join(results_dir, "backtest-result-*.zip")
    for zpath in glob.glob(pattern):
        archive_name = os.path.basename(zpath)
        try:
            with zipfile.ZipFile(zpath, "r") as z:
                # Buscar el archivo json principal que no sea config
                json_files = [n for n in z.namelist() if n.endswith(".json") and not n.endswith("_config.json")]
                if not json_files:
                    continue

                with z.open(json_files[0]) as jf:
                    data = json.load(jf)

                strat_dict = data.get("strategy", {})
                if not strat_dict:
                    continue

                for strat_name, sdata in strat_dict.items():
                    # Parsear fecha de la ejecución
                    date_str = archive_name.replace("backtest-result-", "").replace(".zip", "")
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
                        formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        formatted_date = date_str

                    trades_cnt = sdata.get("total_trades", 0)
                    wins = sdata.get("wins", 0)
                    losses = sdata.get("losses", 0)
                    winrate = round(float(sdata.get("winrate", 0.0)) * 100, 1)

                    profit_total = float(sdata.get("profit_total", 0.0) or 0.0)
                    profit_pct = float(sdata.get("profit_total_pct", 0.0) or 0.0)
                    max_dd = round(float(sdata.get("max_drawdown_account", 0.0) or 0.0) * 100, 2)
                    sharpe = round(float(sdata.get("sharpe", 0.0) or 0.0), 2)
                    sortino = round(float(sdata.get("sortino", 0.0) or 0.0), 2)
                    calmar = round(float(sdata.get("calmar", 0.0) or 0.0), 2)
                    pf = round(float(sdata.get("profit_factor", 0.0) or 0.0), 2)

                    results.append({
                        "archive": archive_name,
                        "date": formatted_date,
                        "strategy": strat_name,
                        "trades": trades_cnt,
                        "wins": wins,
                        "losses": losses,
                        "winrate_pct": winrate,
                        "profit_total_usdt": round(profit_total, 2),
                        "profit_total_pct": round(profit_pct, 2),
                        "max_drawdown_pct": max_dd,
                        "sharpe_ratio": sharpe,
                        "sortino_ratio": sortino,
                        "calmar_ratio": calmar,
                        "profit_factor": pf,
                        "holding_avg": sdata.get("holding_avg_s", 0)
                    })
        except Exception:
            continue

    # Ordenar por fecha descendente
    results.sort(key=lambda x: x["archive"], reverse=True)
    return results


def load_stress_and_monte_carlo(results_dir: str = "user_data/backtest_results") -> Dict[str, Any]:
    """Carga los reportes institucionales de Stress Test y Monte Carlo."""
    out = {"stress_test": None, "monte_carlo": None}
    stress_file = os.path.join(results_dir, "stress_test_report.json")
    if os.path.exists(stress_file):
        try:
            with open(stress_file, "r", encoding="utf-8") as f:
                out["stress_test"] = json.load(f)
        except Exception:
            pass

    mc_file = os.path.join(results_dir, "monte_carlo_latest.json")
    if os.path.exists(mc_file):
        try:
            with open(mc_file, "r", encoding="utf-8") as f:
                out["monte_carlo"] = json.load(f)
        except Exception:
            pass

    return out


def get_live_trades_from_db(db_path: str = "user_data/tradesv3.futures.sqlite") -> Dict[str, Any]:
    """Consulta las posiciones abiertas y el historial de trades en la BD SQLite de Freqtrade."""
    out = {
        "open_positions": [],
        "closed_trades": [],
        "total_closed_count": 0,
        "total_realized_profit": 0.0
    }
    if not os.path.exists(db_path):
        return out

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 1. Posiciones abiertas
        cur.execute("""
            SELECT id, pair, open_date, open_rate, stake_amount, leverage, is_short, strategy, stop_loss
            FROM trades
            WHERE is_open = 1
            ORDER BY id DESC
        """)
        for row in cur.fetchall():
            out["open_positions"].append({
                "id": row[0],
                "pair": row[1],
                "open_date": str(row[2]),
                "open_rate": row[3],
                "stake_amount": round(row[4] or 0.0, 2),
                "leverage": row[5] or 1.0,
                "direction": "SHORT" if row[6] else "LONG",
                "strategy": row[7],
                "stop_loss": row[8]
            })

        # 2. Trades cerrados
        cur.execute("""
            SELECT id, pair, open_date, close_date, open_rate, close_rate, close_profit, close_profit_abs, leverage, is_short, exit_reason, strategy
            FROM trades
            WHERE is_open = 0
            ORDER BY id DESC
            LIMIT 30
        """)
        total_pnl = 0.0
        for row in cur.fetchall():
            profit_pct = round((row[6] or 0.0) * 100, 2)
            profit_abs = round(row[7] or 0.0, 2)
            total_pnl += profit_abs
            out["closed_trades"].append({
                "id": row[0],
                "pair": row[1],
                "open_date": str(row[2]),
                "close_date": str(row[3]),
                "open_rate": row[4],
                "close_rate": row[5],
                "profit_pct": profit_pct,
                "profit_abs": profit_abs,
                "leverage": row[8] or 1.0,
                "direction": "SHORT" if row[9] else "LONG",
                "exit_reason": row[10] or "roi",
                "strategy": row[11]
            })

        # Contar total
        cur.execute("SELECT count(*), coalesce(sum(close_profit_abs), 0.0) FROM trades WHERE is_open = 0")
        cnt_row = cur.fetchone()
        out["total_closed_count"] = cnt_row[0]
        out["total_realized_profit"] = round(cnt_row[1], 2)

        conn.close()
    except Exception as e:
        pass

    return out
