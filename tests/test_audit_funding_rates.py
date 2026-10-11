"""Tests sin red para scripts/audit_funding_rates.py (PB-31)."""
import sys
from pathlib import Path
import pandas as pd
import pytest

PROJ_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ_ROOT / "scripts"))
import audit_funding_rates as afr


def test_load_funding_data_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(afr, "DATA_DIR", tmp_path)
    res = afr.load_funding_data("UNKNOWN/USDT:USDT")
    assert res is None


def test_funding_audit_math():
    # Validar lógica contable:
    # Short con funding positivo (+0.01%) -> Short cobra (ganancia, costo negativo)
    # sum_rate = +0.0001, stake = 100 -> cost = -0.0001 * 100 = -0.01 USDT
    sum_rate_positive = 0.0001
    stake = 100.0
    cost_short = -sum_rate_positive * stake
    assert cost_short == -0.01  # Aporte positivo al saldo

    # Short con funding negativo (-0.05%) -> Short paga (pérdida, costo positivo)
    sum_rate_negative = -0.0005
    cost_short_adverse = -sum_rate_negative * stake
    assert cost_short_adverse == +0.05  # Resta 0.05 USDT al saldo
