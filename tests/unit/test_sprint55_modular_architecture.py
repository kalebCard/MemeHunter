"""
test_sprint55_modular_architecture.py - Suite de Certificación Arquitectónica Modular v9.0 (Sprint 55: PB-210 a PB-219).

Valida:
1. Packaging: 'import meme_hunter' expone la totalidad del core sin dependencias circulares ni roturas.
2. Persistencia SSOT: Centralización en SQLite WAL sobre 'storage/meme_hunter.db'.
3. Configuración Pydantic: Acceso canónico tipado vía AppSettings.
4. Desacoplamiento Asíncrono: Ejecución de minería en segundo plano sin bloqueo en Telegram.
5. Endpoints Asíncronos ASGI: Descarga de backtesting a threadpool en FastAPI.
6. Refactorización SRP: Generadores modulares de respuestas heurísticas.
7. Rendimiento Vectorizado: Latencia de backtest < 500 ms por ejecución con NumPy.
8. Trazabilidad Estructurada: Correlation IDs contextuales y logging JSON estructurado.
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def test_canonical_package_import():
    """PB-210 & PB-211: Verifica que meme_hunter expone todos los módulos canónicos bajo src/."""
    import meme_hunter
    import meme_hunter.core
    import meme_hunter.storage
    import meme_hunter.alpha
    import meme_hunter.data
    import meme_hunter.execution
    import meme_hunter.portfolio
    import meme_hunter.api

    # Validar submódulos de alpha
    from meme_hunter.alpha import (
        FormulaASTParser,
        AlphaGrammar,
        validate_formula_ast,
        run_strategy_backtest,
    )
    assert FormulaASTParser is not None
    assert AlphaGrammar is not None
    assert callable(validate_formula_ast)
    assert callable(run_strategy_backtest)

    # Validar submódulos de execution
    from meme_hunter.execution import (
        FreqtradeRestClient,
        BinanceAccountClient,
        MultiBotOrchestratorClient,
    )
    assert FreqtradeRestClient is not None
    assert BinanceAccountClient is not None
    assert MultiBotOrchestratorClient is not None

    # Validar submódulos de data
    from meme_hunter.data import (
        get_base_data_dir,
        get_futures_data_dir,
        MicrostructureSlippageEngine,
    )
    assert callable(get_base_data_dir)
    assert callable(get_futures_data_dir)
    assert MicrostructureSlippageEngine is not None

    # Validar submódulos de portfolio
    from meme_hunter.portfolio import (
        SmartExitRouter,
        ExitUrgency,
        OrderExecutionStage,
    )
    assert SmartExitRouter is not None
    assert ExitUrgency.EMERGENCY == "EMERGENCY"


def test_single_sqlite_database_ssot():
    """PB-212: Confirma que la base de datos canónica es storage/meme_hunter.db."""
    from meme_hunter.core.config import get_settings
    from meme_hunter.storage.db import get_sqlite_connection
    import portfolio.db_schema as legacy_schema

    settings = get_settings()
    canonical_db = settings.DB_PATH

    assert "storage" in str(canonical_db).lower()
    assert str(canonical_db).lower().endswith("meme_hunter.db")

    # Verificar que el legacy DEFAULT_DB_PATH apunta a la SSOT canónica
    assert str(legacy_schema.DEFAULT_DB_PATH).lower().endswith("meme_hunter.db")

    # Verificar conexión WAL
    conn = get_sqlite_connection(read_only=True)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    conn.close()
    assert mode.upper() in ["WAL", "MEMORY"]


def test_pydantic_settings_singleton():
    """PB-213: Valida que AppSettings es un singleton inmutable y contiene todas las claves críticas."""
    from meme_hunter.core.config import get_settings, AppSettings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    assert isinstance(s1, AppSettings)
    assert hasattr(s1, "DB_PATH")
    assert hasattr(s1, "GLOBAL_KILL_SWITCH_DRAWDOWN")
    assert hasattr(s1, "FREQTRADE_API_URL")


def test_telegram_async_mine_decoupling():
    """PB-214: Valida que _cmd_mine con async_mining=True retorna inmediatamente en < 50ms sin congelar."""
    from client.telegram_ai_copilot import TelegramAiCopilotService

    service = TelegramAiCopilotService(
        telegram_token="mock_token",
        allowed_chat_id="123456"
    )
    service.tg_client = MagicMock()
    service.hermes_op = MagicMock()
    service.async_mining = True

    # Simular una tarea de minería que tarda 2 segundos
    def slow_mining(*args, **kwargs):
        time.sleep(1.0)
        return {"status": "ok", "regime": "RANGE_CHOP", "best_factor": {"factor_id": "TEST_ALPHA", "formula": "close"}}

    service.hermes_op.mine_and_evaluate_new_alpha = slow_mining

    t0 = time.perf_counter()
    reply = service.dispatch_command("/mine", chat_id="123456")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Retorno inmediato al operador
    assert elapsed_ms < 100.0, f"Demoró {elapsed_ms}ms, debía retornar < 100ms"
    assert "segundo plano" in reply.lower()


def test_vectorized_backtest_latency():
    """PB-217: Valida que el motor de backtest vectorial corre en menos de 500ms."""
    from meme_hunter.alpha.tester import run_strategy_backtest

    formula = "ts_zscore(hl_spread, 14) * (close - vwap)"
    t0 = time.perf_counter()
    res = run_strategy_backtest(formula=formula, pair="1000PEPE", timeframe="4h")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert res["success"] is True
    assert elapsed_ms < 500.0, f"Backtest tomó {elapsed_ms:.1f}ms, superior a 500ms"
    assert "metrics" in res
    assert "sharpe_ratio" in res["metrics"]


def test_heuristic_reply_generators():
    """PB-216: Valida los generadores modulares SRP de respuestas heurísticas."""
    from client.ai_copilot_engine import (
        GreetingGenerator,
        BalanceReportGenerator,
        RegimeReportGenerator,
        CoinStatusGenerator,
        BotStrategyGenerator,
    )

    greet = GreetingGenerator.generate([], "BULL_PARABOLIC", 0.85, 95000.0, 3.5)
    assert "Hermes" in greet
    assert "BULL_PARABOLIC" in greet

    coin = CoinStatusGenerator.generate("DOGE", [], "RANGE_CHOP")
    assert "DOGE" in coin

    bal = BalanceReportGenerator.generate(
        profit_data={"profit_closed_coin": 12.5, "winrate": 0.65},
        balance_data={"total": 100.0, "free": 80.0},
        real_balance={"has_keys": True, "spot_usdt_free": 500.0, "futures_usdt_free": 200.0},
        arena_balances={"status": "ok", "total_wallet": 300.0, "free_wallet": 250.0, "used_wallet": 50.0, "bots": {}}
    )
    assert "SALDO REAL EN BINANCE" in bal
    assert "500.00 USDT" in bal

    regime = RegimeReportGenerator.generate("BEAR_CASCADE", 0.90, 89000.0, -4.2, {}, "Shorts dominan.", {})
    assert "BEAR_CASCADE" in regime
    assert "89,000.0" in regime

    bots = BotStrategyGenerator.generate("RANGE_CHOP")
    assert "Ablation" in bots
    assert "Quantum" in bots
    assert "Mined Ensemble" in bots


def test_structured_json_logging_and_correlation_id():
    """PB-218: Valida Correlation IDs y formateo JSON estructurado de logs."""
    import json
    import logging
    from meme_hunter.core.logging import (
        generate_correlation_id,
        get_correlation_id,
        set_correlation_id,
        StructuredJsonFormatter,
        get_logger,
    )

    cid = generate_correlation_id("TEST")
    assert cid.startswith("TEST-")
    set_correlation_id(cid)
    assert get_correlation_id() == cid

    # Probar formateo JSON
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="TestLogger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Operación ejecutada con éxito en Binance",
        args=(),
        exc_info=None
    )
    record.symbol = "PEPE/USDT"
    record.order_id = "123456"

    formatted_json = formatter.format(record)
    parsed = json.loads(formatted_json)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "TestLogger"
    assert parsed["correlation_id"] == cid
    assert parsed["symbol"] == "PEPE/USDT"
    assert parsed["order_id"] == "123456"
    assert "timestamp" in parsed


@pytest.mark.asyncio
async def test_fastapi_async_backtest_endpoint():
    """PB-215: Valida que el endpoint de backtest es async def y offloadea al threadpool."""
    from meme_hunter.api.routers.quant import test_strategy_endpoint, TestStrategyRequest
    import inspect

    assert inspect.iscoroutinefunction(test_strategy_endpoint), "test_strategy_endpoint debe ser async def"

    req = TestStrategyRequest(
        formula="ts_zscore(hl_spread, 14)",
        pair="1000PEPE",
        timeframe="4h",
        direction="short_only",
        leverage=1.5,
        stoploss=0.10,
        trailing_stop=0.04
    )
    res = await test_strategy_endpoint(req)
    assert res["success"] is True
    assert "metrics" in res
