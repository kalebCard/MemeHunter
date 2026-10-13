"""
Módulo del Demonio Asíncrono de Minería Genética y Archivo de Diversidad (Quality-Diversity Archive).
Sprint 1: Motor Cuantitativo Auto-Evolutivo (US-2.1 y US-2.2).

Implementa:
1. `QualityDiversityArchive`: Archivo de factores categorizados en nichos multidimensionales (MAP-Elites),
   evitando el sobre-poblamiento con clones o factores sobre-correlacionados.
2. `AlphaMinerDaemon`: Demonio de minería continua en segundo plano, capaz de activarse periódicamente
   o dispararse ante alertas del `AlphaHealthMonitor`.
"""

import os
import json
import time
import logging
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Callable
import numpy as np
import pandas as pd

from portfolio.atomic_io import atomic_write_json

from mining.genetic_search import GeneticAlphaMiner, AlphaFactor
from mining.alpha_grammar import AlphaGrammar

logger = logging.getLogger("AlphaMinerDaemon")


@dataclass
class QualityDiversityCell:
    """Nicho fenotípico en el archivo de diversidad."""
    niche_id: str
    feature_type: str        # 'MOMENTUM_PRICE' | 'MICROSTRUCTURE_VOLUME' | 'VOLATILITY'
    complexity_tier: str     # 'LOW_DEPTH' | 'HIGH_DEPTH'
    best_factor: Optional[AlphaFactor] = None
    fitness_score: float = -1.0


class QualityDiversityArchive:
    """
    Catálogo de factores que preserva la diversidad fenotípica (Quality-Diversity / MAP-Elites).
    Garantiza que el catálogo tenga alfas ortogonales listos para sustitución.
    """

    def __init__(self, max_inter_correlation: float = 0.50):
        self.max_inter_correlation = max_inter_correlation
        self.cells: Dict[str, QualityDiversityCell] = {}
        self._init_cells()

    def _init_cells(self):
        """Inicializa las celdas de nicho ortogonales."""
        feature_types = ['MOMENTUM_PRICE', 'MICROSTRUCTURE_VOLUME', 'VOLATILITY']
        complexities = ['LOW_DEPTH', 'HIGH_DEPTH']
        for ft in feature_types:
            for comp in complexities:
                niche_id = f"{ft}_{comp}"
                self.cells[niche_id] = QualityDiversityCell(
                    niche_id=niche_id,
                    feature_type=ft,
                    complexity_tier=comp
                )

    def classify_factor(self, factor: AlphaFactor) -> str:
        """Determina el nicho según la fórmula y la profundidad del AST."""
        formula_lower = factor.formula.lower()
        if 'volume' in formula_lower or 'vwap' in formula_lower:
            ft = 'MICROSTRUCTURE_VOLUME'
        elif 'std' in formula_lower or 'abs' in formula_lower or 'delta' in formula_lower:
            ft = 'VOLATILITY'
        else:
            ft = 'MOMENTUM_PRICE'

        complexity = 'LOW_DEPTH' if factor.depth <= 2 else 'HIGH_DEPTH'
        return f"{ft}_{complexity}"

    def try_insert(self, factor: AlphaFactor) -> bool:
        """
        Intenta insertar un factor en el archivo si supera el fitness del nicho actual
        y respeta el umbral de descorrelación con los existentes.
        """
        niche_id = self.classify_factor(factor)
        cell = self.cells.get(niche_id)
        if not cell:
            return False

        # Fitness multidimensional: penalizar rotación excesiva y premiar IC_IR
        fitness = factor.ic_ir * 0.7 + factor.sharpe_proxy * 0.3

        if factor.correlation_with_existing > self.max_inter_correlation:
            logger.debug(f"Factor {factor.factor_id} rechazado por alta correlación ({factor.correlation_with_existing:.2f})")
            return False

        if cell.best_factor is None or fitness > cell.fitness_score:
            cell.best_factor = factor
            cell.fitness_score = fitness
            logger.info(f"Nuevo líder en nicho [{niche_id}]: {factor.factor_id} (Fitness: {fitness:.3f})")
            return True
        return False

    def get_active_factors(self) -> List[AlphaFactor]:
        """Retorna todos los mejores factores de cada celda ocupada."""
        return [cell.best_factor for cell in self.cells.values() if cell.best_factor is not None]

    def save_to_db(self, db_path: str = "portfolio/alpha_factory.db"):
        """Persiste las celdas del archivo de diversidad en SQLite WAL."""
        try:
            from portfolio.db_schema import init_alpha_factory_db, upsert_diversity_cell_db
            init_alpha_factory_db(db_path)
            for niche_id, c in self.cells.items():
                cell_dict = {
                    'niche_id': c.niche_id,
                    'feature_type': c.feature_type,
                    'complexity_tier': c.complexity_tier,
                    'fitness_score': c.fitness_score,
                    'factor': asdict(c.best_factor) if c.best_factor else None
                }
                upsert_diversity_cell_db(cell_dict, db_path=db_path)
        except Exception as e:
            logger.warning(f"Error guardando QualityDiversityArchive en SQLite {db_path}: {e}")

    def load_from_db(self, db_path: str = "portfolio/alpha_factory.db") -> bool:
        """Carga las celdas del archivo de diversidad desde SQLite WAL."""
        if not os.path.exists(db_path):
            return False
        try:
            from portfolio.db_schema import get_diversity_archive_db
            data = get_diversity_archive_db(db_path)
            if not data:
                return False
            for niche_id, entry in data.items():
                if niche_id in self.cells and entry.get('factor'):
                    f_data = entry['factor']
                    factor = AlphaFactor(**f_data)
                    self.cells[niche_id].best_factor = factor
                    self.cells[niche_id].fitness_score = entry['fitness_score']
            return True
        except Exception:
            return False

    def save_archive(self, file_path: str, db_path: Optional[str] = "portfolio/alpha_factory.db"):
        """Persiste el archivo de diversidad en SQLite WAL y JSON."""
        if db_path:
            self.save_to_db(db_path)
        if file_path:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            data = {
                niche_id: {
                    'niche_id': c.niche_id,
                    'feature_type': c.feature_type,
                    'complexity_tier': c.complexity_tier,
                    'fitness_score': c.fitness_score,
                    'factor': asdict(c.best_factor) if c.best_factor else None
                }
                for niche_id, c in self.cells.items()
            }
            atomic_write_json(file_path, data)

    def load_archive(self, file_path: str, db_path: Optional[str] = "portfolio/alpha_factory.db"):
        """Carga el archivo desde SQLite si existe o desde JSON como fallback."""
        loaded = False
        if db_path and os.path.exists(db_path):
            loaded = self.load_from_db(db_path)
        if not loaded and file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for niche_id, entry in data.items():
                    if niche_id in self.cells and entry.get('factor'):
                        f_data = entry['factor']
                        factor = AlphaFactor(**f_data)
                        self.cells[niche_id].best_factor = factor
                        self.cells[niche_id].fitness_score = entry['fitness_score']
            except Exception:
                pass


class AlphaMinerDaemon:
    """
    Demonio de minería continua que corre en segundo plano y alimenta el QualityDiversityArchive.
    """

    def __init__(
        self,
        archive_path: str = "mining/diversity_archive.json",
        pop_size: int = 25,
        generations: int = 4,
        check_interval_seconds: float = 60.0
    ):
        self.archive_path = archive_path
        self.pop_size = pop_size
        self.generations = generations
        self.check_interval = check_interval_seconds

        self.archive = QualityDiversityArchive()
        self.archive.load_archive(self.archive_path)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._trigger_event = threading.Event()
        self._latest_bars_supplier: Optional[Callable[[], pd.DataFrame]] = None

    def set_bars_supplier(self, supplier: Callable[[], pd.DataFrame]):
        """Configura la función proveedora de los datos más recientes (Dollar Bars)."""
        self._latest_bars_supplier = supplier

    def trigger_immediate_mining(self, reason: str = "Manual/HealthTrigger"):
        """Dispara un ciclo de minería inmediato (ej. por alerta CUSUM o decay de factor)."""
        logger.info(f"Disparo de minería forzado: {reason}")
        self._trigger_event.set()

    def run_mining_cycle(self, bars_df: pd.DataFrame) -> List[AlphaFactor]:
        """Ejecuta una ronda de minería genética e inserta los candidatos en el archivo."""
        miner = GeneticAlphaMiner(
            population_size=self.pop_size,
            generations=self.generations,
            target_forward_bars=1,
            max_tree_depth=3,
            correlation_penalty_threshold=0.60
        )
        candidates = miner.run_mining(bars_df, max_factors_to_keep=6)
        promoted = []
        for cand in candidates:
            if self.archive.try_insert(cand):
                promoted.append(cand)

        self.archive.save_archive(self.archive_path)
        return promoted

    def _worker_loop(self):
        """Bucle principal del trabajador en segundo plano."""
        while self._running:
            # Esperar hasta el próximo intervalo o hasta que ocurra un trigger
            triggered = self._trigger_event.wait(timeout=self.check_interval)
            if not self._running:
                break

            if triggered:
                self._trigger_event.clear()

            if self._latest_bars_supplier is not None:
                try:
                    df = self._latest_bars_supplier()
                    if df is not None and len(df) >= 40:
                        self.run_mining_cycle(df)
                except Exception as e:
                    logger.error(f"Error durante el ciclo de minería en background: {e}", exc_info=True)

    def start(self):
        """Inicia el demonio en un hilo en segundo plano."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="AlphaMinerDaemonWorker")
        self._thread.start()
        logger.info("AlphaMinerDaemon iniciado en background.")

    def stop(self):
        """Detiene limpiamente el demonio."""
        self._running = False
        self._trigger_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("AlphaMinerDaemon detenido.")
