"""Tests sin red para scripts/order_flow_imbalance.py."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import order_flow_imbalance as ofi  # noqa: E402


def test_calculate_order_book_metrics_bullish_imbalance():
    # Más liquidez en el lado comprador (bids)
    mock_book = {
        "bids": [[100.0, 50.0], [99.0, 30.0]],  # Total 80
        "asks": [[101.0, 10.0], [102.0, 10.0]],  # Total 20
    }
    metrics = ofi.calculate_order_book_metrics(mock_book, levels=2)

    assert metrics["best_bid"] == 100.0
    assert metrics["best_ask"] == 101.0
    assert metrics["total_bid_depth"] == 80.0
    assert metrics["total_ask_depth"] == 20.0
    # Imbalance = (80 - 20) / 100 = +0.60
    assert metrics["imbalance"] == pytest.approx(0.60)
    assert "FAVORABLE LONG" in metrics["maker_recommendation"]


def test_calculate_order_book_metrics_bearish_imbalance():
    # Más liquidez en el lado vendedor (asks)
    mock_book = {
        "bids": [[100.0, 10.0]],  # Total 10
        "asks": [[101.0, 40.0]],  # Total 40
    }
    metrics = ofi.calculate_order_book_metrics(mock_book, levels=1)

    # Imbalance = (10 - 40) / 50 = -0.60
    assert metrics["imbalance"] == pytest.approx(-0.60)
    assert "FAVORABLE SHORT" in metrics["maker_recommendation"]


def test_micro_price_calculation():
    # Si ask_vol es mayor, el micro price está más cerca de bid_price (presión vendedora)
    # L1: Bid = 100 (vol 10), Ask = 110 (vol 90)
    mock_book = {
        "bids": [[100.0, 10.0]],
        "asks": [[110.0, 90.0]],
    }
    metrics = ofi.calculate_order_book_metrics(mock_book, levels=1)
    # MicroPrice = (90 * 100 + 10 * 110) / 100 = (9000 + 1100) / 100 = 101.0
    # Mid = 105.0
    assert metrics["micro_price"] == pytest.approx(101.0)
    assert metrics["mid_price"] == pytest.approx(105.0)
    assert "BAJISTA" in metrics["pressure"]


def test_calculate_order_book_empty():
    assert ofi.calculate_order_book_metrics({}) == {}
