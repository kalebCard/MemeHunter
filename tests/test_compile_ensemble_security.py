"""
tests/test_compile_ensemble_security.py - Suite de Seguridad y Zero-Eval para el Compilador de Estrategias.
PB-134 (Sprint 40): Valida que fórmulas maliciosas, imports arbitrarios y llamadas dunder
sean neutralizados deterministamente antes de generar código ejecutable.
"""

import pytest
import os
import ast
from pathlib import Path

from scripts.pipelines.compile_ensemble_strategy import (
    generate_ensemble_strategy_file,
    compile_ast_formula_to_python
)


def test_pb134_compilation_neutralizes_malicious_injections(tmp_path):
    """PB-134: Valida que intentos de inyección RCE sean neutralizados por FormulaASTParser."""
    fake_factor_lib = tmp_path / "fake_factors.json"
    fake_factor_lib.write_text("""[
        {
            "factor_id": "EXPLOIT_01",
            "formula": "__import__('os').system('malicious')",
            "sharpe_proxy": 5.0
        },
        {
            "factor_id": "SAFE_ALPHA",
            "formula": "ts_rank(close, 14)",
            "sharpe_proxy": 2.5
        }
    ]""", encoding="utf-8")

    out_strat = tmp_path / "TestMinedEnsemble.py"

    generated_path = generate_ensemble_strategy_file(
        factor_library_path=str(fake_factor_lib),
        incubator_state_path=str(tmp_path / "non_existent.json"),
        db_path=None,
        output_strategy_path=str(out_strat)
    )

    assert os.path.exists(generated_path)
    content = out_strat.read_text(encoding="utf-8")

    # La carga maliciosa NO debe figurar en el archivo generado
    assert "__import__" not in content
    assert "os.system" not in content
    assert "malicious" not in content

    # El archivo resultante debe ser sintácticamente válido en Python
    tree = ast.parse(content)
    assert tree is not None


def test_pb134_safe_formula_compilation_preserves_math(tmp_path):
    """PB-134: Valida que fórmulas cuantitativas legítimas se compilen y preserven."""
    fake_factor_lib = tmp_path / "legit_factors.json"
    fake_factor_lib.write_text("""[
        {
            "factor_id": "ALPHA_LEGIT_1",
            "formula": "ts_zscore((high - low), 10)",
            "sharpe_proxy": 2.1
        },
        {
            "factor_id": "ALPHA_LEGIT_2",
            "formula": "ts_rank(volume, 20)",
            "sharpe_proxy": 1.9
        }
    ]""", encoding="utf-8")

    out_strat = tmp_path / "LegitMinedEnsemble.py"

    generate_ensemble_strategy_file(
        factor_library_path=str(fake_factor_lib),
        incubator_state_path=str(tmp_path / "non_existent.json"),
        db_path=None,
        output_strategy_path=str(out_strat)
    )

    content = out_strat.read_text(encoding="utf-8")
    assert "f_val_ALPHA_LEGIT_1" in content
    assert "f_val_ALPHA_LEGIT_2" in content
    assert "dataframe['high']" in content
    assert "dataframe['volume']" in content
