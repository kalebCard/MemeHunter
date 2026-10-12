"""
tests/test_delta_neutral_vault.py - Tests unitarios de la Bóveda Delta-Neutral (PB-69).
Valida:
1. Recepción de depósitos transferidos desde el motor de trinquete.
2. Asignación simétrica 50% Long Spot + 50% Short Futuros (Delta neto = 0).
3. Liquidación y acumulación pasiva de cobros de Funding Rates.
"""

import pytest
from pathlib import Path
from scripts.delta_neutral_vault import DeltaNeutralVault


def test_vault_deposit_and_allocation(tmp_path):
    state_file = tmp_path / "vault_state_test.json"
    vault = DeltaNeutralVault(initial_capital=0.0, state_file=state_file)

    # 1. Simular depósito de $4,000 USDT cosechados
    vault.deposit(4000.0)
    assert vault.total_capital == 4000.0

    # 2. Asignar a 2 oportunidades de mercado
    dummy_opps = [
        {"symbol": "PEPE/USDT:USDT", "apr": 30.0, "funding_rate": 0.0274},
        {"symbol": "WIF/USDT:USDT", "apr": 20.0, "funding_rate": 0.0182},
    ]
    vault.allocate_capital(dummy_opps)

    assert len(vault.positions) == 2
    # $4,000 / 2 = $2,000 por par -> 50% Spot ($1,000) y 50% Futuros ($1,000)
    pepe_pos = vault.positions["PEPE/USDT:USDT"]
    assert pepe_pos["spot_long_usdt"] == 1000.0
    assert pepe_pos["futures_short_usdt"] == 1000.0


def test_vault_settlement_cycle(tmp_path):
    state_file = tmp_path / "vault_settlement_test.json"
    vault = DeltaNeutralVault(initial_capital=2000.0, state_file=state_file)

    dummy_opps = [
        {"symbol": "PEPE/USDT:USDT", "apr": 30.0, "funding_rate": 0.0274},
    ]
    vault.allocate_capital(dummy_opps)

    # Simular liquidación de 1 ciclo de 8h
    # Notional Short = 1,000 USDT | Rate = 0.000274 (0.0274%) -> Payout = 0.274 USDT
    cycle_yield = vault.simulate_settlement_cycle()

    assert cycle_yield > 0.0
    assert vault.total_income_collected > 0.0
    assert vault.total_capital > 2000.0
