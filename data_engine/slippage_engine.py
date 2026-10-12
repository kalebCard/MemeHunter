"""
Módulo de Simulación de Microestructura, Deslizamiento (Slippage) e Impacto de Mercado.
Implementa el modelo de impacto de mercado de Almgren & Chriss (2000) adaptado a contratos de futuros perpetuos.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import numpy as np


@dataclass
class ExecutionResult:
    """Resultado detallado de la simulación de ejecución de una orden."""
    order_type: str            # 'maker' o 'market'
    side: str                  # 'buy' o 'sell'
    requested_price: float
    executed_price: float
    effective_spread_bps: float
    slippage_bps: float
    market_impact_bps: float
    fill_ratio: float          # 1.0 = fill total, <1.0 = fill parcial
    liquidity_cost_usdt: float
    is_filled: bool


class MicrostructureSlippageEngine:
    """
    Simulador microestructural que calcula el costo real de liquidez y deslizamiento
    considerando:
    1. Spread instantáneo dependiente de la volatilidad.
    2. Impacto de mercado permanente y temporal de Almgren-Chriss (raíz cuadrada de participación).
    3. Probabilidad de ejecución Maker en caídas violentas o pumps.
    """

    def __init__(
        self,
        base_maker_fee: float = 0.0002,     # 0.02% Binance VIP0 Futures Maker
        base_taker_fee: float = 0.0005,     # 0.05% Binance VIP0 Futures Taker
        gamma_impact_coeff: float = 0.25,   # Coeficiente de impacto Almgren-Chriss
        base_spread_bps: float = 3.0        # 3 basis points (0.03%) spread base típico
    ):
        self.maker_fee = base_maker_fee
        self.taker_fee = base_taker_fee
        self.gamma = gamma_impact_coeff
        self.base_spread_bps = base_spread_bps

    def compute_dynamic_spread(self, volatility_4h: float, rvol: float = 1.0) -> float:
        """
        Calcula el bid-ask spread en basis points en función del régimen de volatilidad y RVOL.
        """
        # A mayor RVOL y volatilidad, los creadores de mercado ensanchan el spread
        vol_factor = max(1.0, volatility_4h * 100.0)
        rvol_factor = max(1.0, rvol**0.5)
        spread_bps = self.base_spread_bps * (0.6 + 0.4 * vol_factor) * rvol_factor
        return float(np.clip(spread_bps, 1.0, 50.0))  # Máx 50 bps (0.50%)

    def simulate_order_execution(
        self,
        side: str,
        order_type: str,
        price: float,
        order_size_usdt: float,
        daily_volume_usdt: float,
        volatility: float = 0.02,
        rvol: float = 1.0,
        is_breakdown_candle: bool = False
    ) -> ExecutionResult:
        """
        Simula la ejecución de una orden pasiva (Maker) o agresiva (Market).
        
        :param side: 'buy' o 'sell'
        :param order_type: 'maker' o 'market'
        :param price: Precio de referencia actual
        :param order_size_usdt: Tamaño notional de la orden
        :param daily_volume_usdt: Volumen 24h del par en USDT
        :param volatility: Volatilidad estimada
        :param rvol: Volumen relativo (spikes)
        :param is_breakdown_candle: Si la vela es de alta velocidad / liquidaciones
        """
        side = side.lower()
        order_type = order_type.lower()
        spread_bps = self.compute_dynamic_spread(volatility, rvol)
        half_spread_pct = (spread_bps / 10_000.0) / 2.0

        participation_rate = order_size_usdt / max(100_000.0, daily_volume_usdt)

        # 1. Simulación para orden MAKER (Límite Pasiva)
        if order_type == 'maker':
            # Si el mercado está en un quiebre súbito (breakdown o short squeeze):
            # La probabilidad de fill de un Maker en la dirección opuesta colapsa (riesgo de no-fill)
            if is_breakdown_candle and rvol > 2.0:
                fill_prob = max(0.20, 1.0 - (participation_rate * 50.0) - (rvol * 0.15))
            else:
                fill_prob = max(0.60, 1.0 - (participation_rate * 20.0))

            is_filled = bool(fill_prob >= 0.50)
            fill_ratio = fill_prob if is_filled else 0.0

            # En orden Maker se asume captura de medio spread pero riesgo de selección adversa
            slippage_bps = 0.0
            market_impact_bps = 0.0
            executed_price = price  # Se asume ejecutado al precio límite si fill=True
            liquidity_cost = order_size_usdt * self.maker_fee

            return ExecutionResult(
                order_type='maker',
                side=side,
                requested_price=price,
                executed_price=executed_price,
                effective_spread_bps=spread_bps,
                slippage_bps=slippage_bps,
                market_impact_bps=market_impact_bps,
                fill_ratio=fill_ratio,
                liquidity_cost_usdt=liquidity_cost,
                is_filled=is_filled
            )

        # 2. Simulación para orden MARKET (Agresiva / Taker / Stoploss)
        # Modelo de Almgren-Chriss: Impacto = gamma * sigma * sqrt(Order / ADV)
        market_impact_pct = self.gamma * volatility * np.sqrt(max(1e-6, participation_rate))
        market_impact_bps = float(market_impact_pct * 10_000.0)
        
        # Deslizamiento total = Medio spread + Impacto de mercado
        slippage_pct = half_spread_pct + market_impact_pct
        slippage_bps = float(slippage_pct * 10_000.0)

        # El precio empeora según la dirección
        if side == 'buy':
            executed_price = price * (1.0 + slippage_pct)
        else:
            executed_price = price * (1.0 - slippage_pct)

        liquidity_cost = (order_size_usdt * self.taker_fee) + (order_size_usdt * slippage_pct)

        return ExecutionResult(
            order_type='market',
            side=side,
            requested_price=price,
            executed_price=executed_price,
            effective_spread_bps=spread_bps,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps,
            fill_ratio=1.0,  # Las órdenes market siempre se completan (consumiendo liquidez)
            liquidity_cost_usdt=liquidity_cost,
            is_filled=True
        )
