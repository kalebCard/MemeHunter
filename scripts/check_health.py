#!/usr/bin/env python3
"""
check_health.py - Centinela de Salud y Diagnóstico Operativo Rápido (Meme Hunter v7.2).

Audita en ~2-5 segundos:
1. Docker daemon y estado de contenedores (Cockpit, Futures).
2. Base de datos SQLite (existencia, lectura, PRAGMA integrity_check).
3. Conectividad HTTP con el Cockpit (:8088).
4. Estado de configuración y secretos (.env).
5. Persistencia del estado de la incubadora (portfolio/incubator_state.json).

Retorna código 0 si todo está saludable, o código 1 si hay fallas críticas.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

# Configurar encoding UTF-8 seguro para consolas de Windows (evita charmap cp1252 error)
if sys.platform.startswith("win"):
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent


def check_docker_containers():
    """Verifica si Docker está corriendo y el estado de los contenedores clave."""
    report = {"name": "Docker & Contenedores", "status": "UNKNOWN", "details": []}
    try:
        res = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}} - {{.Status}} - {{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode != 0:
            report["status"] = "WARN"
            report["details"].append(f"Docker CLI retornó código {res.returncode}: {res.stderr.strip()}")
            return report

        lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        if not lines:
            report["status"] = "WARN"
            report["details"].append("Docker está corriendo pero no hay contenedores activos.")
            return report

        has_cockpit = any("cockpit" in l.lower() for l in lines)
        has_futures = any("futures" in l.lower() for l in lines)

        for l in lines:
            report["details"].append(f"Contenedor: {l}")

        if has_cockpit or has_futures:
            report["status"] = "OK"
        else:
            report["status"] = "WARN"
            report["details"].append("Ni el cockpit ni el motor de futuros fueron detectados en docker ps.")

    except subprocess.TimeoutExpired:
        report["status"] = "FAIL"
        report["details"].append("Timeout (5s) al consultar Docker daemon.")
    except FileNotFoundError:
        report["status"] = "WARN"
        report["details"].append("Comando 'docker' no encontrado en el sistema.")
    except Exception as e:
        report["status"] = "FAIL"
        report["details"].append(f"Error inesperado: {e}")
    return report


def check_sqlite_integrity(db_relative_path="user_data/tradesv3.futures.sqlite"):
    """Verifica la integridad de la base de datos de trading."""
    report = {"name": f"SQLite ({db_relative_path})", "status": "OK", "details": []}
    db_path = BASE_DIR / db_relative_path

    if not db_path.exists():
        report["status"] = "INFO"
        report["details"].append("El archivo aún no existe (se creará al iniciar la primera sesión).")
        return report

    try:
        # Abrir en modo lectura con URI
        uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=3.0)
        cur = conn.cursor()

        # PRAGMA integrity_check
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()
        if res and res[0] == "ok":
            report["details"].append("Integridad física: OK")
        else:
            report["status"] = "FAIL"
            report["details"].append(f"Falla de integridad: {res}")

        # Contar trades si existe la tabla
        try:
            cur.execute("SELECT count(*) FROM trades WHERE is_open = 1;")
            open_cnt = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM trades WHERE is_open = 0;")
            closed_cnt = cur.fetchone()[0]
            report["details"].append(f"Posiciones vivas: {open_cnt} | Trades históricos cerrados: {closed_cnt}")
        except sqlite3.OperationalError:
            report["details"].append("Tabla 'trades' vacía o aún no inicializada por Freqtrade.")

        conn.close()
    except Exception as e:
        report["status"] = "FAIL"
        report["details"].append(f"Error al verificar base de datos: {e}")

    return report


def check_cockpit_http(port=8088):
    """Verifica si el servidor HTTP del Cockpit responde en el puerto esperado."""
    report = {"name": f"Cockpit HTTP API (:{port})", "status": "UNKNOWN", "details": []}
    url = f"http://127.0.0.1:{port}/api/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MemeHunter-HealthCheck"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            code = resp.getcode()
            if code == 200:
                data = json.loads(resp.read().decode("utf-8"))
                version = data.get("version", "desconocida")
                strategies_count = data.get("total_strategies", 0)
                report["status"] = "OK"
                report["details"].append(f"HTTP {code} OK | Versión API: {version} | Estrategias monitoreadas: {strategies_count}")
            else:
                report["status"] = "WARN"
                report["details"].append(f"HTTP responde con código inesperado: {code}")
    except urllib.error.URLError as e:
        report["status"] = "WARN"
        report["details"].append(f"Cockpit no responde en :{port} ({e.reason})")
    except Exception as e:
        report["status"] = "FAIL"
        report["details"].append(f"Error consultando endpoint: {e}")
    return report


def check_incubator_state():
    """Verifica la persistencia del estado de la incubadora de estrategias."""
    report = {"name": "Incubadora Autónoma (incubator_state.json)", "status": "OK", "details": []}
    path = BASE_DIR / "portfolio" / "incubator_state.json"
    if not path.exists():
        report["status"] = "WARN"
        report["details"].append("No se encontró 'portfolio/incubator_state.json'.")
        return report

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        strategies = data.get("strategies", {})
        counts = {}
        for s in strategies.values():
            st = s.get("status", "UNKNOWN")
            counts[st] = counts.get(st, 0) + 1

        summary_str = ", ".join(f"{k}: {v}" for k, v in counts.items()) if counts else "0 estrategias registradas"
        report["details"].append(f"Estrategias totales: {len(strategies)} ({summary_str})")
    except Exception as e:
        report["status"] = "FAIL"
        report["details"].append(f"Archivo de estado corrupto o ilegible: {e}")
    return report


def check_environment():
    """Verifica la presencia de variables de entorno y archivos de configuración."""
    report = {"name": "Configuración y Entorno (.env)", "status": "OK", "details": []}
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        report["status"] = "WARN"
        report["details"].append("Archivo '.env' no existe. Usando configuración por defecto.")
    else:
        report["details"].append("Archivo '.env' presente.")

    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    has_binance_key = bool(os.getenv("BINANCE_API_KEY"))

    if has_openrouter:
        report["details"].append("OpenRouter API Key: Configurada")
    else:
        report["details"].append("OpenRouter API Key: No detectada (Modo Offline / Heurístico activo)")

    if has_binance_key:
        report["details"].append("Binance API Key: Configurada")
    else:
        report["details"].append("Binance API Key: No detectada (Modo Dry-Run / Simulado seguro)")

    return report


def run_all_checks():
    """Ejecuta toda la batería de comprobaciones y muestra el resultado consolidado."""
    print("=" * 70)
    print("🏹 MEME HUNTER v7.2 - CENTINELA DE SALUD OPERATIVA")
    print("=" * 70)

    checks = [
        check_docker_containers(),
        check_cockpit_http(),
        check_sqlite_integrity("user_data/tradesv3.futures.sqlite"),
        check_incubator_state(),
        check_environment(),
    ]

    has_fail = False
    for c in checks:
        status = c["status"]
        if status == "OK":
            icon = "🟢 [OK]"
        elif status == "INFO":
            icon = "ℹ️  [INFO]"
        elif status == "WARN":
            icon = "⚠️  [WARN]"
        else:
            icon = "🔴 [FAIL]"
            has_fail = True

        print(f"\n{icon} {c['name']}")
        for d in c["details"]:
            print(f"    • {d}")

    print("\n" + "=" * 70)
    if has_fail:
        print("❌ RESULTADO: Se detectaron fallas críticas que requieren atención.")
        print("=" * 70)
        return 1
    else:
        print("✅ RESULTADO: Sistema saludable y listo para operar.")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(run_all_checks())
