"""
test_order_router.py - Pruebas Unitarias del Enrutador de Órdenes y Fills Realistas (Sprint 3).
Verifica:
1. Enrutamiento adaptativo ADR-004.1 (Maker Post-Only, Sliced TWAP y Hard Stop Market).
2. Reducción de impacto de mercado de Almgren-Chriss mediante TWAP fraccionado.
3. Activación inmediata de orden Market de emergencia cuando la pérdida supera el stop-loss duro.
4. Métricas de microestructura (slippage drag, comisiones, funding rates) en strategy_tester.
"""

import pytest
import numpy as np

from data_engine.slippage_engine import MicrostructureSlippageEngine
from portfolio.order_router import (
    SmartExitRouter,
    ExitUrgency,
    OrderExecutionStage,
    SmartExitOrder
)
from meme_hunter.alpha.tester import run_strategy_backtest


def test_order_router_stage_determination():
    """Valida la selección de etapa según nivel de pérdida y régimen de urgencia."""
    router = SmartExitRouter(hard_stoploss_pct=-0.08)

    # 1. Pérdida leve (-2%) y urgencia normal -> Maker Post-Only
    stage1 = router.determine_stage(unrealized_pnl_pct=-0.02, urgency=ExitUrgency.LOW, rvol=1.0)
    assert stage1 == OrderExecutionStage.MAKER_POST_ONLY

    # 2. Urgencia media o spike de volumen RVOL >= 3.0 -> Sliced TWAP
    stage2 = router.determine_stage(unrealized_pnl_pct=-0.04, urgency=ExitUrgency.MEDIUM, rvol=1.0)
    assert stage2 == OrderExecutionStage.SLICED_TWAP

    stage2_vol = router.determine_stage(unrealized_pnl_pct=-0.02, urgency=ExitUrgency.LOW, rvol=3.5)
    assert stage2_vol == OrderExecutionStage.SLICED_TWAP

    # 3. Stop loss duro superado (-9% <= -8%) -> Hard Stop Market inmediato
    stage3 = router.determine_stage(unrealized_pnl_pct=-0.09, urgency=ExitUrgency.LOW, rvol=1.0)
    assert stage3 == OrderExecutionStage.HARD_STOP_MARKET

    # 4. Emergencia explícita -> Hard Stop Market
    stage3_emerg = router.determine_stage(unrealized_pnl_pct=-0.01, urgency=ExitUrgency.EMERGENCY, rvol=1.0)
    assert stage3_emerg == OrderExecutionStage.HARD_STOP_MARKET


def test_maker_execution_zero_slippage():
    """Valida que una orden Maker exitosa no incurra en deslizamiento."""
    router = SmartExitRouter()
    order = router.route_exit(
        symbol="DOGE/USDT",
        side="buy",
        current_price=0.20,
        order_size_usdt=5_000.0,
        unrealized_pnl_pct=0.05,
        daily_volume_usdt=50_000_000.0,
        volatility=0.02,
        rvol=1.0,
        urgency=ExitUrgency.LOW,
        force_stage=OrderExecutionStage.MAKER_POST_ONLY
    )

    assert order.stage == OrderExecutionStage.MAKER_POST_ONLY
    assert order.executed_price == 0.20
    assert order.effective_slippage_bps == 0.0
    assert order.slippage_drag_usdt == 0.0
    assert order.total_fees_usdt == 5_000.0 * 0.0002  # 0.02% Maker fee


def test_sliced_twap_reduces_impact_vs_single_block():
    """Valida que Sliced TWAP reduzca el impacto de mercado frente a una sola orden de bloque."""
    engine = MicrostructureSlippageEngine(gamma_impact_coeff=0.5)
    router = SmartExitRouter(slippage_engine=engine, default_slices=4)

    order_size = 200_000.0   # Orden grande
    daily_adv = 1_000_000.0  # Mercado ilíquido (20% de participación)
    price = 1.0

    # 1. Ejecución TWAP fraccionada
    twap_order = router.route_exit(
        symbol="BONK/USDT",
        side="sell",
        current_price=price,
        order_size_usdt=order_size,
        unrealized_pnl_pct=-0.03,
        daily_volume_usdt=daily_adv,
        volatility=0.04,
        urgency=ExitUrgency.MEDIUM,
        force_stage=OrderExecutionStage.SLICED_TWAP
    )

    # 2. Ejecución única de bloque a mercado
    block_order = router.route_exit(
        symbol="BONK/USDT",
        side="sell",
        current_price=price,
        order_size_usdt=order_size,
        unrealized_pnl_pct=-0.03,
        daily_volume_usdt=daily_adv,
        volatility=0.04,
        urgency=ExitUrgency.EMERGENCY,
        force_stage=OrderExecutionStage.HARD_STOP_MARKET
    )

    # El slippage drag del TWAP debe ser sustancialmente inferior al de la orden en bloque
    assert twap_order.effective_slippage_bps < block_order.effective_slippage_bps
    assert twap_order.slippage_drag_usdt < block_order.slippage_drag_usdt


def test_strategy_tester_reports_microstructure_metrics():
    """Valida que run_strategy_backtest reporte métricas realistas de slippage drag, fees y funding."""
    formula = "ts_decay_linear(returns, 5) * ts_rank(volume, 10)"
    res = run_strategy_backtest(
        formula=formula,
        pair="1000PEPE",
        timeframe="4h",
        direction="short_only",
        leverage=1.5,
        stoploss_pct=0.10,
        trailing_stop_pct=0.04
    )

    assert res["success"] is True
    m = res["metrics"]
    assert "total_slippage_drag_usd" in m
    assert "total_fees_paid_usd" in m
    assert "total_funding_pnl_usd" in m
    assert "effective_spread_bps" in m
    assert m["total_fees_paid_usd"] >= 0.0
