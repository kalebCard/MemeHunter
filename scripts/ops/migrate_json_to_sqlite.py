#!/usr/bin/env python3
"""
scripts/migrate_json_to_sqlite.py
---------------------------------
Script de migración atómica y unificación de datos legados JSON hacia SQLite WAL (PB-89: Sprint 25).
Migra:
- portfolio/incubator_state.json -> tabla `strategies`
- mining/diversity_archive.json  -> tabla `diversity_archive`
- portfolio/autopsies.json       -> tabla `alpha_autopsies`
- portfolio/cycle_history.json   -> tabla `cycle_history`
Hacia la base de datos central: portfolio/alpha_factory.db
"""

import os
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio.db_schema import (
    init_alpha_factory_db,
    upsert_strategy_db,
    upsert_diversity_cell_db,
    insert_autopsy_db,
    record_cycle_history_db,
    DEFAULT_DB_PATH
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MigrateJSONtoSQLite")


def migrate_incubator_state(json_path: Path, db_path: str) -> int:
    """Migra el estado de la incubadora a la tabla strategies."""
    if not json_path.exists():
        logger.info(f"[-] No existe {json_path}, omitiendo.")
        return 0
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for sid, entry in data.items():
        upsert_strategy_db(entry, db_path=db_path)
        count += 1
    logger.info(f"[+] Migradas {count} estrategias desde {json_path.name}")
    return count


def migrate_diversity_archive(json_path: Path, db_path: str) -> int:
    """Migra el archivo de diversidad MAP-Elites a la tabla diversity_archive."""
    if not json_path.exists():
        logger.info(f"[-] No existe {json_path}, omitiendo.")
        return 0
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for niche_id, entry in data.items():
        upsert_diversity_cell_db(entry, db_path=db_path)
        count += 1
    logger.info(f"[+] Migrados {count} nichos desde {json_path.name}")
    return count


def migrate_autopsies(json_path: Path, db_path: str) -> int:
    """Migra las autopsias forenses a la tabla alpha_autopsies."""
    if not json_path.exists():
        logger.info(f"[-] No existe {json_path}, omitiendo.")
        return 0
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for entry in data:
        insert_autopsy_db(entry, db_path=db_path)
        count += 1
    logger.info(f"[+] Migradas {count} autopsias forenses desde {json_path.name}")
    return count


def migrate_cycle_history(json_path: Path, db_path: str) -> int:
    """Migra el historial de ciclos a la tabla cycle_history."""
    if not json_path.exists():
        logger.info(f"[-] No existe {json_path}, omitiendo.")
        return 0
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for entry in reversed(data):  # Insertar en orden cronológico
        record_cycle_history_db(entry, db_path=db_path)
        count += 1
    logger.info(f"[+] Migradas {count} entradas de historial de ciclos desde {json_path.name}")
    return count


def run_migration(db_path: str = DEFAULT_DB_PATH) -> None:
    logger.info(f"Iniciando migración JSON -> SQLite en {db_path}...")
    init_alpha_factory_db(db_path)

    p_dir = ROOT / "portfolio"
    m_dir = ROOT / "mining"

    s_count = migrate_incubator_state(p_dir / "incubator_state.json", db_path)
    d_count = migrate_diversity_archive(m_dir / "diversity_archive.json", db_path)
    a_count = migrate_autopsies(p_dir / "autopsies.json", db_path)
    c_count = migrate_cycle_history(p_dir / "cycle_history.json", db_path)

    logger.info(f"Migración completada con éxito. Total registros: {s_count + d_count + a_count + c_count}")


if __name__ == "__main__":
    db_target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    run_migration(db_target)
