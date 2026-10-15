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
    """Informa sobre la unificación de la interfaz en FreqUI Oficial (:8081)."""
    print("=" * 60)
    print("🌐 MEME HUNTER - SINGLE PANE OF GLASS FREQUI (:8081)")
    print("=" * 60)
    print("ℹ️  AVISO DE ARQUITECTURA v8.2:")
    print("   El antiguo Cockpit de I+D (:8088) ha sido MIGRADO Y UNIFICADO por completo")
    print("   dentro de la interfaz oficial FreqUI en http://localhost:8081.")
    print("\n   Ahora tienes acceso nativo a:")
    print("   • 📈 Trading en Vivo, Velas TradingView & Órdenes")
    print("   • 🌐 Orquestación Multi-Agente (DAG) & Controles HITL (/dag)")
    print("   • 🔄 Motor de Auto-Mejora & Autopsias IA (/incubator)")
    print("   • 🧪 Laboratorio Cuantitativo Studio & AST (/studio)")
    print("\n💡 Ejecuta 'python scripts/ops/meme_cli.py frequi' para acceder.")
    return 0


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


def cmd_hermes(args):
    """Gestión y ejecución del Agente Autónomo Hermes (Sprint 52)."""
    from src.meme_hunter.hermes.hermes_operator import HermesOperator
    from src.meme_hunter.hermes.telegram_messenger import HermesTelegramMessenger

    op = HermesOperator()
    if getattr(args, "audit", False):
        print("📜 HISTORIAL DE DECISIONES DE HERMES:")
        print(f"Total ciclos ejecutados: {op.memory.get('total_cycles_run', 0)}")
        for rec in op.memory.get('regime_history', [])[-5:]:
            print(f"• [{rec.get('timestamp')[:19]}] Régimen: {rec.get('regime')} | Trades: {rec.get('total_open_trades')} | Stake: {rec.get('stake_active_usdt')} USDT")
        return 0

    print("🧠 Evaluando mercado con Hermes (Alter Ego Operativo)...")
    res = op.run_cycle()
    print("\n" + res["explanation"] + "\n")

    if getattr(args, "notify", False):
        tg = HermesTelegramMessenger()
        sent = tg.send_executive_report(res["explanation"])
        print(f"📡 Notificación Telegram: {'Enviada ✅' if sent.get('ok') else 'Omitida / Fallo ⚠️'}")
    return 0


def cmd_telegram_ai(args):
    """Gestión y control del Copilot de IA en Telegram."""
    runner = str(BASE_DIR / "scripts" / "ops" / "run_telegram_copilot.py")
    cmd = [sys.executable, runner]
    if args.poll:
        cmd.append("--poll")
    elif args.query:
        cmd.extend(["--query", args.query])
    else:
        cmd.append("--test")
    return subprocess.run(cmd).returncode


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
  python scripts/ops/meme_cli.py hermes --status # Ejecutar ciclo autónomo de Hermes
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

    # telegram-ai
    p_tg = subparsers.add_parser("telegram-ai", help="Gestión del Copilot de IA en Telegram (Sprint 50 & 51)")
    p_tg.add_argument("--poll", action="store_true", help="Inicia el servicio en polling continuo")
    p_tg.add_argument("--test", action="store_true", help="Audita conectividad con Telegram y Freqtrade")
    p_tg.add_argument("--query", type=str, default="", help="Ejecuta una consulta al AI Copilot con telemetría viva")

    # hermes
    p_hermes = subparsers.add_parser("hermes", help="Agente Autónomo Hermes: Orquestación, Régimen y Cartera (Sprint 52)")
    p_hermes.add_argument("--status", action="store_true", help="Evalúa mercado y muestra diagnóstico del Alter Ego")
    p_hermes.add_argument("--notify", action="store_true", help="Envía el informe ejecutivo a Telegram (@Atutaskbot)")
    p_hermes.add_argument("--audit", action="store_true", help="Muestra historial de decisiones de la memoria episódica")

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
        "research": cmd_research,
        "telegram-ai": cmd_telegram_ai,
        "hermes": cmd_hermes
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
