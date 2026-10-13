"""
test_cli.py - Pruebas Unitarias de la Interfaz de Línea de Comandos (meme-hunter v8.0).
"""

from typer.testing import CliRunner
from meme_hunter.cli.main import app

runner = CliRunner()


def test_cli_version():
    """Valida la ejecución del comando 'meme-hunter version'."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Meme Hunter Platform" in result.output
    assert "v8.0.0" in result.output
    assert "SQLite Write-Ahead Logging (WAL)" in result.output


def test_cli_db_inspect():
    """Valida la inspección de base de datos 'meme-hunter db inspect'."""
    result = runner.invoke(app, ["db", "inspect"])
    assert result.exit_code == 0
    assert "Estado de Base de Datos" in result.output
    assert "Total Estrategias" in result.output


def test_cli_help():
    """Valida la visualización de la ayuda global y subcomandos."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "db" in result.output
    assert "run" in result.output
    assert "mine" in result.output
    assert "backtest" in result.output
    assert "sim" in result.output
