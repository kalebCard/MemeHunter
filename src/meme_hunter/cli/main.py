"""
meme_hunter.cli.main - Interfaz de Línea de Comandos Institucional (meme-hunter v8.0).
Consolida los 47 scripts dispersos bajo una herramienta unificada con Typer y Rich.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Resiliencia de codificación en consolas de Windows (CP1252 / PowerShell)
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from meme_hunter.core.config import get_settings
from meme_hunter.core.types import StrategyStatus
from meme_hunter.storage.db import get_sqlite_connection, sqlite_cursor_context
from meme_hunter.storage.repositories import (
    AutopsyRepository,
    MarketBiasRepository,
    StrategyRepository,
)
from meme_hunter.storage.schema import init_database

app = typer.Typer(
    name="meme-hunter",
    help="🛡️ Meme Hunter v8.0 - Plataforma Cuantitativa Multi-Agente & Motor Autónomo",
    add_completion=False,
)
console = Console()

# Sub-comandos
db_app = typer.Typer(help="📦 Gestión y auditoría de la base de datos canónica SQLite WAL")
run_app = typer.Typer(help="🚀 Ejecución de bucles de mercado y daemons de producción")
mine_app = typer.Typer(help="⛏️ Minería genética de factores y compilación de estrategias")
backtest_app = typer.Typer(help="📊 Backtesting institucional y auditoría forense DSR / PBO")
sim_app = typer.Typer(help="🎲 Simulaciones Monte Carlo y modelos de crecimiento")

app.add_typer(db_app, name="db")
app.add_typer(run_app, name="run")
app.add_typer(mine_app, name="mine")
app.add_typer(backtest_app, name="backtest")
app.add_typer(sim_app, name="sim")


# =====================================================================
# COMANDOS GENERALES
# =====================================================================

@app.command()
def version() -> None:
    """Muestra la versión del sistema, entorno y estado de configuración."""
    settings = get_settings()
    panel = Panel(
        f"[bold cyan]Meme Hunter Platform[/bold cyan] v8.0.0\n"
        f"[dim]Entorno:[/dim] [yellow]{settings.ENV}[/yellow]\n"
        f"[dim]Raíz del Sistema:[/dim] {settings.ROOT_DIR}\n"
        f"[dim]Base de Datos Canónica:[/dim] {settings.DB_PATH}\n"
        f"[dim]Modo Concurrencia:[/dim] SQLite Write-Ahead Logging (WAL)",
        title="🛡️ Sistema Canónico",
        border_style="green",
    )
    console.print(panel)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host de escucha del Cockpit Web"),
    port: int = typer.Option(8088, help="Puerto TCP del Cockpit Web"),
) -> None:
    """Inicia el servidor del Cockpit Web y telemetría."""
    console.print(f"[bold green]Iniciando Cockpit Server en http://{host}:{port}...[/bold green]")
    settings = get_settings()
    server_script = settings.ROOT_DIR / "dashboard" / "server.py"
    if server_script.exists():
        import subprocess
        env = os.environ.copy()
        env["DASHBOARD_HOST"] = host
        env["DASHBOARD_PORT"] = str(port)
        subprocess.run([sys.executable, str(server_script)], env=env)
    else:
        console.print(f"[red]Error: {server_script} no encontrado.[/red]")


# =====================================================================
# SUBCOMANDOS: DB (Base de Datos Canónica)
# =====================================================================

@db_app.command("init")
def db_init() -> None:
    """Inicializa el esquema de tablas canónico en storage/meme_hunter.db."""
    settings = get_settings()
    init_database(settings.DB_PATH)
    console.print(
        Panel(
            f"[bold green]Base de datos inicializada exitosamente[/bold green]\n"
            f"Archivo: [cyan]{settings.DB_PATH}[/cyan]\n"
            f"Modo: [yellow]WAL (Write-Ahead Logging)[/yellow] | Timeout: [yellow]15,000 ms[/yellow]",
            title="📦 SQLite WAL Storage",
            border_style="cyan",
        )
    )


@db_app.command("inspect")
def db_inspect() -> None:
    """Inspecciona el estado de la base de datos, tablas, estrategias y alfas."""
    settings = get_settings()
    if not settings.DB_PATH.exists():
        console.print(f"[yellow]Aviso: La base de datos no existe aún en {settings.DB_PATH}. Ejecute 'meme-hunter db init'.[/yellow]")
        return

    strat_repo = StrategyRepository(settings.DB_PATH)
    bias_repo = MarketBiasRepository(settings.DB_PATH)
    autopsy_repo = AutopsyRepository(settings.DB_PATH)

    all_strats = strat_repo.get_all()
    active_biases = bias_repo.get_all_active()
    latest_autopsies = autopsy_repo.get_latest(limit=5)

    size_kb = settings.DB_PATH.stat().st_size / 1024.0

    table = Table(title=f"Estado de Base de Datos ({settings.DB_PATH.name} - {size_kb:.1f} KB)")
    table.add_column("Métrica / Tabla", style="cyan")
    table.add_column("Valor Actual", style="green")

    table.add_row("Total Estrategias", str(len(all_strats)))
    table.add_row("Estrategias LIVE", str(len([s for s in all_strats if s['status'] == 'LIVE'])))
    table.add_row("Estrategias SANDBOX", str(len([s for s in all_strats if s['status'] == 'SANDBOX'])))
    table.add_row("Estrategias DECAY", str(len([s for s in all_strats if s['status'] == 'ALPHA_DECAY'])))
    table.add_row("Sesgos de Mercado Activos", str(len(active_biases)))
    table.add_row("Autopsias Forenses Registradas", str(len(latest_autopsies)))

    console.print(table)


@db_app.command("migrate")
def db_migrate() -> None:
    """Migra datos históricos desde archivos JSON sueltos hacia SQLite WAL canónico."""
    settings = get_settings()
    init_database(settings.DB_PATH)
    strat_repo = StrategyRepository(settings.DB_PATH)
    autopsy_repo = AutopsyRepository(settings.DB_PATH)

    migrated_strats = 0
    migrated_autopsies = 0

    # 1. Migrar incubator_state.json si existe
    incubator_json = settings.ROOT_DIR / "portfolio" / "incubator_state.json"
    if incubator_json.exists():
        try:
            with open(incubator_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            for stage_key in ["SANDBOX", "LIVE", "ALPHA_DECAY", "RETIRED"]:
                for s in data.get(stage_key, []):
                    strat_repo.upsert_strategy({
                        "strategy_id": s.get("strategy_id", s.get("id")),
                        "name": s.get("name", s.get("strategy_id")),
                        "status": stage_key,
                        "target_capital_weight": float(s.get("weight", s.get("target_capital_weight", 0.0))),
                        "backtest_sharpe": float(s.get("backtest_sharpe", 0.0)),
                        "live_sharpe": float(s.get("live_sharpe", 0.0)),
                    })
                    migrated_strats += 1
        except Exception as e:
            console.print(f"[red]Aviso migrando {incubator_json.name}: {e}[/red]")

    # 2. Migrar autopsies.json si existe
    autopsies_json = settings.ROOT_DIR / "portfolio" / "autopsies.json"
    if autopsies_json.exists():
        try:
            with open(autopsies_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            for a in data:
                autopsy_repo.insert_autopsy(a)
                migrated_autopsies += 1
        except Exception as e:
            console.print(f"[red]Aviso migrando {autopsies_json.name}: {e}[/red]")

    console.print(
        Panel(
            f"[bold green]Migración Finalizada Exitosamente[/bold green]\n"
            f"Estrategias migradas a SQLite: [cyan]{migrated_strats}[/cyan]\n"
            f"Autopsias cognitivas migradas: [cyan]{migrated_autopsies}[/cyan]\n"
            f"Destino: [yellow]{settings.DB_PATH}[/yellow]",
            title="🔄 Migración Canónica",
            border_style="green",
        )
    )


# =====================================================================
# SUBCOMANDOS: RUN (Ejecución y Daemons)
# =====================================================================

@run_app.command("live")
def run_live(
    config: str = typer.Option("./user_data/config_futures.json", help="Ruta al archivo config de Freqtrade"),
    loop_interval: int = typer.Option(10, help="Intervalo de consulta en segundos"),
) -> None:
    """Ejecuta el bucle de trading y orquestación multi-agente en vivo."""
    console.print(f"[bold cyan]Iniciando bucle de trading con {config}...[/bold cyan]")
    settings = get_settings()
    script = settings.ROOT_DIR / "scripts" / "run_live_alpha_loop.py"
    if script.exists():
        import subprocess
        subprocess.run([sys.executable, str(script)])
    else:
        console.print(f"[red]Error: {script} no encontrado.[/red]")


@run_app.command("ratchet")
def run_ratchet(
    threshold: float = typer.Option(1.0, help="Umbral de duplicación de cuenta (+100%)"),
    extract_ratio: float = typer.Option(0.60, help="Porcentaje de beneficios a transferir a la bóveda"),
) -> None:
    """Ejecuta el daemon de trinquete de ganancias (Profit Ratchet Daemon)."""
    console.print(f"[bold green]Iniciando Profit Ratchet Daemon (+{threshold*100:.0f}% -> {extract_ratio*100:.0f}% extracción)...[/bold green]")
    settings = get_settings()
    script = settings.ROOT_DIR / "scripts" / "profit_ratchet_daemon.py"
    if script.exists():
        import subprocess
        subprocess.run([sys.executable, str(script)])
    else:
        console.print(f"[red]Error: {script} no encontrado.[/red]")


@run_app.command("vault")
def run_vault() -> None:
    """Ejecuta el gestor de la Bóveda Delta-Neutral Cash & Carry (Archivado en Sprint 56)."""
    settings = get_settings()
    script = settings.ROOT_DIR / "scripts" / "archive" / "legacy_satellites" / "delta_neutral_vault.py"
    if script.exists():
        console.print("[bold yellow]Iniciando Delta-Neutral Vault Scanner...[/bold yellow]")
        console.print("[dim yellow]ℹ️ Nota: Módulo archivado (Tier 9). Ejecutando desde archive/legacy_satellites...[/dim yellow]")
        import subprocess
        subprocess.run([sys.executable, str(script)])
    else:
        console.print(f"[red]Error: {script} no encontrado.[/red]")


# =====================================================================
# SUBCOMANDOS: MINE (Minería de Alfas y Compilador)
# =====================================================================

@mine_app.command("compile")
def mine_compile(
    output: str = typer.Option("./user_data/strategies/MemeHunter_MinedEnsemble.py", help="Ruta del archivo generado"),
) -> None:
    """Compila dinámicamente el ensamble minado con verificación AST Zero-Eval."""
    console.print(f"[bold cyan]Compilando estrategia en {output}...[/bold cyan]")
    settings = get_settings()
    script = settings.ROOT_DIR / "scripts" / "compile_ensemble_strategy.py"
    if script.exists():
        import subprocess
        subprocess.run([sys.executable, str(script)])
    else:
        console.print(f"[red]Error: {script} no encontrado.[/red]")


# =====================================================================
# SUBCOMANDOS: BACKTEST & SIM
# =====================================================================

@backtest_app.command("audit")
def backtest_audit(
    zip_path: str = typer.Option(..., help="Ruta al archivo ZIP oficial de backtest exportado por Freqtrade"),
) -> None:
    """Audita un backtest certificando DSR y PBO contra data snooping."""
    console.print(f"[bold cyan]Auditando archivo de backtest: {zip_path}...[/bold cyan]")
    settings = get_settings()
    script = settings.ROOT_DIR / "scripts" / "audit_advanced_backtests.py"
    if script.exists():
        import subprocess
        subprocess.run([sys.executable, str(script), "--zip", zip_path])
    else:
        console.print(f"[red]Error: {script} no encontrado.[/red]")


@sim_app.command("montecarlo")
def sim_montecarlo(
    iterations: int = typer.Option(10000, help="Número de iteraciones de simulación"),
    drawdown_limit: float = typer.Option(0.25, help="Límite crítico de drawdown (Kill Switch)"),
) -> None:
    """Ejecuta simulación de colas pesadas de Monte Carlo."""
    console.print(f"[bold yellow]Ejecutando Monte Carlo ({iterations} iteraciones, DD límite: {drawdown_limit*100}%)...[/bold yellow]")
    settings = get_settings()
    script = settings.ROOT_DIR / "scripts" / "fat_tail_montecarlo.py"
    if script.exists():
        import subprocess
        subprocess.run([sys.executable, str(script)])
    else:
        console.print(f"[red]Error: {script} no encontrado.[/red]")


if __name__ == "__main__":
    app()
