#!/usr/bin/env python3
"""
meme_cli.py - Interfaz de Línea de Comandos Unificada (Meme Hunter v7.2).

Punto de entrada único para operar, monitorear y realizar investigación en el sistema,
eliminando la sobrecarga cognitiva de recordar comandos de Docker y 19 scripts dispersos.

Uso:
    python scripts/meme_cli.py health          # Auditoría de salud en 2s (Docker, DB, API, .env)
    python scripts/meme_cli.py cockpit         # Estado y acceso al Cockpit Visual (:8088)
    python scripts/meme_cli.py futures [start|stop|logs|status]  # Gestión del motor de trading en vivo
    python scripts/meme_cli.py test            # Ejecución de la suite hermética de 117 tests
    python scripts/meme_cli.py research [tool] # Ejecución guiada de módulos de I+D y satélites
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Configurar encoding UTF-8 seguro para consolas Windows
if sys.platform.startswith("win"):
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "docker-compose.futures.yml").exists() or (parent / "pyproject.toml").exists():
            return parent
    return Path(__file__).resolve().parent.parent.parent

BASE_DIR = get_project_root()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def cmd_health(args):
    """Ejecuta el centinela de salud integral."""
    from scripts.ops.check_health import run_all_checks
    return run_all_checks()


def cmd_frequi(args):
    """Muestra el estado, URL y credenciales de acceso a FreqUI (Interfaz Oficial)."""
    print("=" * 60)
    print("🌐 FREQUI - INTERFAZ WEB OFICIAL DE CONTROL (:8081)")
    print("=" * 60)
    print("• URL Local        : http://localhost:8081 (o http://127.0.0.1:8081)")
    print("• Contenedor Docker: meme_hunter_futures")
    print("• API URL en Login : http://localhost:8081")
    print("• Usuario          : admin")
    print("• Contraseña       : MemeHunter2026!")
    print("\nVerificando conexión con el contenedor...")
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8081", timeout=3.0) as resp:
            if resp.getcode() == 200:
                print("🟢 ESTADO: FreqUI está ACTIVO y sirviendo la interfaz web.")
                print("💡 Abre http://localhost:8081 en tu navegador para ver tus trades en vivo.")
                return 0
    except Exception as e:
        print(f"⚠️  ESTADO: No se pudo conectar a FreqUI ({e}).")
        print("💡 Ejecuta 'python scripts/ops/meme_cli.py futures start' para iniciar el contenedor.")
        return 1


def cmd_cockpit(args):
    """Gestiona e informa sobre el estado del Cockpit de I+D (Laboratorio bajo demanda)."""
    print("=" * 60)
    print("🔬 MEME HUNTER - COCKPIT DE I+D Y LABORATORIO (:8088)")
    print("=" * 60)
    print("ℹ️  Nota: Para trading diario, usa FreqUI (:8081). Este Cockpit es para I+D.")
    
    # Verificar si está corriendo
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8088/api/status", timeout=2.0) as resp:
            if resp.getcode() == 200:
                print("🟢 ESTADO: El Cockpit de I+D está ACTIVO.")
                print("🌐 URL: http://localhost:8088")
                print("🔑 Token de Acceso: Bearer Token configurado en DASHBOARD_API_TOKEN (.env)")
                print("\nPestañas disponibles:")
                print("  • 🧪 Laboratorio Cuantitativo (Strategy Studio)")
                print("  • 🧠 Incubadora Autónoma (HRP & Autopsias IA)")
                print("  • 📚 Estrategias & Backtests (Catálogo)")
                return 0
    except Exception:
        pass

    print("ℹ️  ESTADO: El Cockpit de I+D no está activo en :8088.")
    if args.start:
        print("🚀 Iniciando Cockpit localmente...")
        script = BASE_DIR / "scripts" / "ops" / "start_dashboard.py"
        subprocess.run([sys.executable, str(script)])
        return 0
    else:
        print("\nPara iniciarlo bajo demanda:")
        print("  python scripts/ops/meme_cli.py cockpit --start")
        return 0
        return 1


def cmd_futures(args):
    """Controla el motor de ejecución en vivo de futuros en Docker."""
    action = args.action or "status"
    compose_file = "docker-compose.futures.yml"

    print("=" * 60)
    print(f"⚡ MOTOR DE FUTUROS (Freqtrade 4H - {action.upper()})")
    print("=" * 60)

    if action == "start":
        print("Iniciando contenedor 'meme_hunter_futures' en background...")
        res = subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d"])
        if res.returncode == 0:
            print("✅ Motor de futuros iniciado con éxito.")
            print("📊 FreqUI disponible en: http://127.0.0.1:8081")
        return res.returncode

    elif action == "stop":
        print("Deteniendo contenedor 'meme_hunter_futures' de forma segura...")
        res = subprocess.run(["docker", "compose", "-f", compose_file, "down"])
        return res.returncode

    elif action == "logs":
        print("Mostrando logs en vivo (Ctrl+C para salir)...")
        return subprocess.run(["docker", "logs", "-f", "meme_hunter_futures", "--tail", "50"]).returncode

    elif action == "status":
        res = subprocess.run(
            ["docker", "ps", "--filter", "name=meme_hunter_futures", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"]
        )
        print("\n🌐 FreqUI (Interfaz Web Oficial):")
        print("  • URL         : http://localhost:8081")
        print("  • Credenciales: admin / MemeHunter2026!")
        return res.returncode


def cmd_test(args):
    """Ejecuta los tests unitarios e integrales certificados en Docker."""
    print("=" * 60)
    print("🧪 SUITE HERMÉTICA DE PRUEBAS (117 TESTS CERTIFICADOS)")
    print("=" * 60)
    cmd = [
        "docker", "compose", "run", "--rm",
        "-e", "PYTHONPATH=/freqtrade",
        "--entrypoint", "pytest",
        "freqtrade", "tests/", "-v"
    ]
    if args.fast:
        cmd.extend(["-q"])
    return subprocess.run(cmd).returncode


def cmd_research(args):
    """Muestra y ejecuta herramientas satélite de investigación y estrés."""
    tools = {
        "stress": ("scripts/simulation/stress_test.py", "Somete trades a comisiones hostiles y deslizamiento"),
        "monte-carlo": ("scripts/simulation/monte_carlo.py", "Simulación Bootstrap de 7,500 caminos y VaR"),
        "vault": ("scripts/ops/delta_neutral_vault.py", "Escaneo de oportunidades Cash & Carry delta-neutral"),
        "sentinel": ("scripts/ops/meme_sentinel.py", "Detector de volumen anómalo y pumps de memecoins"),
        "radar": ("scripts/ops/dex_viral_radar.py", "Radar on-chain DEX (DexScreener API)"),
        "ratchet": ("scripts/ops/profit_ratchet_daemon.py", "Daemon de cosecha y trinquete de utilidades"),
        "metrics": ("scripts/research/advanced_metrics.py", "Cálculo de PSR, DSR y PBO institucional"),
        "telegram": ("scripts/ops/telegram_healthcheck.py", "Verificación y test de alertas Telegram"),
        "binance": ("scripts/ops/test_binance_connection.py", "Auditoría de conexión API a Binance Futures")
    }

    if not args.tool:
        print("=" * 60)
        print("🔬 CATÁLOGO DE HERRAMIENTAS DE INVESTIGACIÓN (I+D)")
        print("=" * 60)
        for name, (path, desc) in tools.items():
            print(f"  • {name:<12} : {desc}")
        print("\nEjecución:")
        print("  python scripts/ops/meme_cli.py research <nombre_herramienta>")
        return 0

    tool = args.tool.lower()
    if tool not in tools:
        print(f"❌ Herramienta '{tool}' desconocida.")
        print(f"Opciones válidas: {', '.join(tools.keys())}")
        return 1

    script_path, desc = tools[tool]
    print(f"🚀 Ejecutando {tool}: {desc}...")
    full_path = str(BASE_DIR / script_path)
    
    # Ejecutar localmente con Python
    return subprocess.run([sys.executable, full_path]).returncode


def main():
    parser = argparse.ArgumentParser(
        description="Meme Hunter v7.2 - CLI Centralizado de Control y Operaciones",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos comunes:
  python scripts/ops/meme_cli.py health          # Chequeo rápido de salud en 2s
  python scripts/ops/meme_cli.py frequi          # Ver datos de acceso a FreqUI (:8081)
  python scripts/ops/meme_cli.py futures status  # Ver estado de Freqtrade en Docker
  python scripts/ops/meme_cli.py test            # Correr suite de 117 tests
  python scripts/ops/meme_cli.py research stress # Correr stress-test
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # health
    p_health = subparsers.add_parser("health", help="Auditoría de salud y estado en 2 segundos")

    # frequi
    p_frequi = subparsers.add_parser("frequi", help="Estado, enlace y credenciales de FreqUI Oficial (:8081)")

    # cockpit
    p_cockpit = subparsers.add_parser("cockpit", help="Gestión del Cockpit de I+D (:8088)")
    p_cockpit.add_argument("--start", action="store_true", help="Inicia el cockpit si no está activo")

    # futures
    p_futures = subparsers.add_parser("futures", help="Gestión del motor de futuros Freqtrade")
    p_futures.add_argument("action", nargs="?", choices=["start", "stop", "logs", "status"], default="status",
                           help="Acción a realizar (start, stop, logs, status)")

    # test
    p_test = subparsers.add_parser("test", help="Ejecutar suite hermética de 117 tests")
    p_test.add_argument("--fast", action="store_true", help="Modo silencioso rápido (-q)")

    # research
    p_research = subparsers.add_parser("research", help="Ejecutar herramientas de investigación de I+D")
    p_research.add_argument("tool", nargs="?", help="Nombre de la herramienta (stress, monte-carlo, vault, sentinel, etc.)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "health": cmd_health,
        "frequi": cmd_frequi,
        "cockpit": cmd_cockpit,
        "futures": cmd_futures,
        "test": cmd_test,
        "research": cmd_research
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
