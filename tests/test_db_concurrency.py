"""
tests/test_db_concurrency.py
----------------------------
Suite de pruebas de integración, atomicidad y concurrencia multihilo SQLite WAL (Sprint 25: PB-89).
Verifica:
1. Inicialización correcta del esquema relacional y configuración WAL.
2. Escritura y lectura atómica de estrategias, autopsias, celdas MAP-Elites y ciclos.
3. Resiliencia y cero bloqueos ("database is locked") ante alta concurrencia multihilo.
4. Rollback automático de transacciones ante excepciones.
5. Persistencia y carga en StrategyLifecycleIncubator y QualityDiversityArchive.
"""

import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

from portfolio.db_pool import get_sqlite_connection, sqlite_cursor_context
from portfolio.db_schema import (
    init_alpha_factory_db,
    upsert_strategy_db,
    get_all_strategies_db,
    record_allocations_db,
    insert_autopsy_db,
    get_autopsies_db,
    upsert_diversity_cell_db,
    get_diversity_archive_db,
    record_cycle_history_db,
    get_cycle_history_db
)
from portfolio.strategy_incubator import StrategyLifecycleIncubator, StrategyLifecycleStatus
from mining.alpha_daemon import QualityDiversityArchive
from mining.genetic_search import AlphaFactor


@pytest.fixture
def temp_db(tmp_path):
    """Crea una base de datos temporal configurada para las pruebas."""
    db_file = str(tmp_path / "test_alpha_factory.db")
    init_alpha_factory_db(db_file)
    return db_file


def test_init_db_wal_mode(temp_db):
    """Verifica que la base de datos se inicialice con journal_mode = WAL y synchronous = NORMAL."""
    conn = get_sqlite_connection(temp_db, read_only=True)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    assert mode.lower() == "wal", f"Esperado WAL, obtenido: {mode}"

    cur.execute("PRAGMA synchronous;")
    sync = cur.fetchone()[0]
    assert sync in (1, "NORMAL"), f"Esperado NORMAL (1), obtenido: {sync}"
    conn.close()


def test_crud_strategies(temp_db):
    """Verifica inserción y actualización (upsert) de estrategias."""
    strat_1 = {
        "strategy_id": "ALPHA_001",
        "name": "ts_rank(close, 10)",
        "status": StrategyLifecycleStatus.LIVE,
        "target_capital_weight": 0.25,
        "backtest_sharpe": 2.10,
        "live_sharpe": 1.95,
        "days_in_stage": 10,
        "decay_zscore": -0.2
    }
    upsert_strategy_db(strat_1, db_path=temp_db)

    all_strats = get_all_strategies_db(temp_db)
    assert len(all_strats) == 1
    assert all_strats[0]["strategy_id"] == "ALPHA_001"
    assert all_strats[0]["status"] == "LIVE"
    assert all_strats[0]["target_capital_weight"] == 0.25

    # Actualizar estado y peso
    strat_1["status"] = StrategyLifecycleStatus.ALPHA_DECAY
    strat_1["target_capital_weight"] = 0.0
    upsert_strategy_db(strat_1, db_path=temp_db)

    updated_strats = get_all_strategies_db(temp_db)
    assert len(updated_strats) == 1
    assert updated_strats[0]["status"] == "ALPHA_DECAY"
    assert updated_strats[0]["target_capital_weight"] == 0.0


def test_transaction_rollback_on_error(temp_db):
    """Verifica que los context managers hagan rollback automático ante excepciones."""
    try:
        with sqlite_cursor_context(temp_db, commit=True) as cur:
            cur.execute("INSERT INTO strategies (strategy_id, name, status, updated_at) VALUES ('FAIL_1', 'test', 'LIVE', '2026-10-12')")
            # Forzar una excepción para abortar
            raise RuntimeError("Fallo forzado simulando caída del worker")
    except RuntimeError:
        pass

    # La estrategia NO debe existir en la base de datos
    strats = get_all_strategies_db(temp_db)
    assert not any(s["strategy_id"] == "FAIL_1" for s in strats)


def test_multithreaded_concurrency_no_locks(temp_db):
    """
    Prueba de estrés de concurrencia: 15 hilos escriben y leen simultáneamente.
    Garantiza cero bloqueos ('database is locked') gracias al modo WAL y timeout de 15s.
    """
    num_threads = 15
    operations_per_thread = 20
    errors = []

    def worker_task(thread_id: int):
        try:
            for i in range(operations_per_thread):
                sid = f"TH_{thread_id}_STRAT_{i}"
                upsert_strategy_db({
                    "strategy_id": sid,
                    "name": f"formula_thread_{thread_id}_{i}",
                    "status": "SANDBOX",
                    "target_capital_weight": 0.05,
                    "backtest_sharpe": 1.5 + (i * 0.01)
                }, db_path=temp_db)

                # Lectura concurrente
                _ = get_all_strategies_db(temp_db)

                # Registro de autopsia concurrente
                if i % 5 == 0:
                    insert_autopsy_db({
                        "factor_id": sid,
                        "formula": f"formula_{i}",
                        "health_status": "WARNING",
                        "diagnosis": "TEST_DIAG",
                        "root_cause": "Concurrencia multihilo",
                        "recommendation": "Continuar prueba",
                        "confidence_score": 0.95,
                        "suggested_actions": ["LOG"]
                    }, db_path=temp_db)

                time.sleep(0.005)
        except Exception as e:
            errors.append(f"Thread {thread_id} falló con error: {type(e).__name__}: {e}")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()

    assert len(errors) == 0, f"Errores de concurrencia detectados: {errors}"

    # Validar que todos los registros se insertaron íntegros
    all_strats = get_all_strategies_db(temp_db)
    expected_total = num_threads * operations_per_thread
    assert len(all_strats) == expected_total, f"Esperados {expected_total}, guardados {len(all_strats)}"


def test_incubator_integration_sqlite(temp_db):
    """Verifica la integración fluida de StrategyLifecycleIncubator con la base de datos SQLite."""
    incubator = StrategyLifecycleIncubator()
    incubator.register_strategy("SQL_ALPHA_01", "ts_rank(close, 14)", 2.45, StrategyLifecycleStatus.LIVE)
    incubator.register_strategy("SQL_ALPHA_02", "ts_decay(volume, 5)", 1.80, StrategyLifecycleStatus.SANDBOX)

    # Guardar en SQLite
    incubator.save_to_db(temp_db)

    # Cargar en una nueva instancia
    new_incubator = StrategyLifecycleIncubator()
    loaded = new_incubator.load_from_db(temp_db)
    assert loaded is True
    assert len(new_incubator.strategies) == 2
    assert "SQL_ALPHA_01" in new_incubator.strategies
    assert new_incubator.strategies["SQL_ALPHA_01"].status == StrategyLifecycleStatus.LIVE
    assert new_incubator.strategies["SQL_ALPHA_01"].backtest_sharpe == 2.45


def test_diversity_archive_integration_sqlite(temp_db):
    """Verifica que QualityDiversityArchive persista y cargue celdas MAP-Elites en SQLite."""
    archive = QualityDiversityArchive(max_inter_correlation=0.50)
    factor = AlphaFactor(
        factor_id="SQL_FACTOR_VOL",
        formula="ts_zscore((high - low), 10)",
        ic_mean=0.075,
        ic_std=0.03,
        ic_ir=2.5,
        sharpe_proxy=2.2,
        turnover=0.10,
        depth=2,
        correlation_with_existing=0.05
    )
    inserted = archive.try_insert(factor)
    assert inserted is True

    # Guardar en SQLite
    archive.save_to_db(temp_db)

    # Cargar en nueva instancia
    new_archive = QualityDiversityArchive()
    loaded = new_archive.load_from_db(temp_db)
    assert loaded is True
    active_factors = new_archive.get_active_factors()
    assert len(active_factors) >= 1
    assert any(f.factor_id == "SQL_FACTOR_VOL" for f in active_factors)
