"""
test_autonomous_refinement_loop.py - Pruebas Unitarias del Bucle Autónomo de Refinamiento Cuantitativo de Hermes.
Sprint 53: Hermes Quantitative Alter Ego, Backtesting Iterativo y Despliegue en Cuenta Simulada.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.meme_hunter.hermes.hermes_operator import HermesOperator


class MockCandidate:
    def __init__(self, formula, sharpe=2.1, winrate=58.0, roi=42.0):
        self.formula = formula
        self.sharpe = sharpe
        self.winrate = winrate
        self.roi = roi


def test_refinement_loop_end_to_end(tmp_path):
    """Verifica que el bucle autónomo ejecuta iteraciones, backtestea y genera el reporte ejecutivo."""
    memory_file = str(tmp_path / "hermes_mem.json")
    operator = HermesOperator(memory_path=memory_file)

    progress_messages = []

    def mock_progress(msg: str):
        progress_messages.append(msg)

    # Mock del sintetizador para devolver fórmulas controladas
    mock_synthesizer = MagicMock()
    mock_synthesizer.synthesize_alphas.side_effect = [
        # Iteración 1: Fórmulas que serán evaluadas
        [
            ("ts_rank(returns, 14) * (close - vwap)", MagicMock()),
            ("ts_delta(close, 2) / (ts_std(close, 10) + 1e-6)", MagicMock())
        ],
        # Iteración 2: Fórmulas refinadas con mejor Sharpe
        [
            ("ts_zscore(returns, 8) * ts_rank(rvol, 12)", MagicMock())
        ]
    ]

    with patch("mining.llm_alpha_generator.LLMAlphaSynthesizer", return_value=mock_synthesizer):
        res = operator.run_autonomous_refinement_loop(
            goal_text="Pasar de 10 a 100 USDT en 1 semana (Moonshot 10x)",
            initial_wallet=10.0,
            timeframe="15m",
            leverage=10.0,
            max_iterations=2,
            target_sharpe=1.8,
            target_winrate=50.0,
            progress_callback=mock_progress
        )

    assert res["status"] == "ok"
    assert "winning_factor" in res
    assert "best_candidate" in res
    assert res["timeframe"] == "15m"
    assert res["leverage"] == 10.0
    assert len(progress_messages) >= 1
    assert "🧪 *BUCLE AUTÓNOMO DE INVESTIGACIÓN Y BACKTESTING COMPLETADO*" in res["report_md"]
    assert "10.00 USDT" in res["report_md"]

    # Verificar que se registró en memoria
    assert os.path.exists(memory_file)
    with open(memory_file, "r", encoding="utf-8") as f:
        mem = json.load(f)
    assert "refinement_experiments_history" in mem
    assert len(mem["refinement_experiments_history"]) == 1


def test_mine_facade_delegates_to_refinement_loop():
    """Verifica que mine_and_evaluate_new_alpha delega en el bucle de refinamiento."""
    operator = HermesOperator()
    operator.run_autonomous_refinement_loop = MagicMock(return_value={"status": "ok", "report_md": "Mocked Report"})

    res = operator.mine_and_evaluate_new_alpha(
        pair="DOGE_USDT_USDT",
        goal_text="Pasar de 10 a 100 USDT"
    )

    assert res["status"] == "ok"
    operator.run_autonomous_refinement_loop.assert_called_once()
    call_kwargs = operator.run_autonomous_refinement_loop.call_args[1]
    assert call_kwargs["goal_text"] == "Pasar de 10 a 100 USDT"
    assert call_kwargs["pair"] == "DOGE"
