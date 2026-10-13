"""
Meme Hunter - Technical & Microstructure Quantitative Agent (PB-105)
Sprint 30: Agente cuantitativo de microestructura, momentum y balance de flujo.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal


class TechnicalMicroAgent(BaseSignalAgent):
    """
    Agente cuantitativo especializado en microestructura y análisis técnico.
    Combina confirmación rápida de tendencia, RSI dinámico y desequilibrio de volumen (OFI).
    """

    def __init__(
        self,
        agent_id: str = "technical_micro_agent",
        weight: float = 1.0,
        active: bool = True,
        rsi_period: int = 14,
        fast_ema: int = 12,
        slow_ema: int = 26
    ):
        super().__init__(agent_id=agent_id, agent_type="technical", weight=weight, active=active)
        self.rsi_period = rsi_period
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema

    def _compute_proposal(self, market_data: Any) -> AgentProposal:
        """Calcula la propuesta técnica cuantitativa en alta fidelidad."""
        df = self._extract_dataframe(market_data)
        if df is None or len(df) < max(self.slow_ema, self.rsi_period) + 2:
            return self._build_neutral_proposal("INSUFFICIENT_BARS")

        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones_like(close)
        high = df["high"].values if "high" in df.columns else close
        low = df["low"].values if "low" in df.columns else close

        # 1. RSI Vectorial
        rsi_val = self._compute_rsi(close, self.rsi_period)

        # 2. EMAs y Cruce de Momentum
        ema_fast_series = pd.Series(close).ewm(span=self.fast_ema, adjust=False).mean().values
        ema_slow_series = pd.Series(close).ewm(span=self.slow_ema, adjust=False).mean().values
        macd_line = ema_fast_series[-1] - ema_slow_series[-1]
        macd_norm = macd_line / max(1e-6, close[-1]) * 100.0

        # 3. Micro-OFI (Proxy de desequilibrio de flujo por vela)
        ofi_proxy = self._compute_order_flow_imbalance_proxy(close, high, low, volume)

        # 4. Generación de Señal y Convicción
        # Composite score en [-1.0, 1.0]
        # Ponderación: 40% MACD normalizado, 30% RSI relativo a 50, 30% OFI proxy
        rsi_score = (rsi_val - 50.0) / 50.0  # [-1.0, 1.0]
        macd_score = np.clip(macd_norm / 1.5, -1.0, 1.0)
        composite = 0.40 * macd_score + 0.30 * rsi_score + 0.30 * ofi_proxy

        direction = 0
        confidence = float(np.abs(composite))

        if composite > 0.12 and rsi_val < 72.0:
            direction = 1
            confidence = min(0.95, max(0.55, 0.5 + abs(composite) * 0.45))
        elif composite < -0.12 and rsi_val > 28.0:
            direction = -1
            confidence = min(0.95, max(0.55, 0.5 + abs(composite) * 0.45))
        else:
            direction = 0
            confidence = 0.40

        metadata = {
            "rsi": float(np.round(rsi_val, 2)),
            "macd_norm_pct": float(np.round(macd_norm, 4)),
            "ofi_proxy": float(np.round(ofi_proxy, 4)),
            "composite_score": float(np.round(composite, 4)),
            "fast_ema": float(ema_fast_series[-1]),
            "slow_ema": float(ema_slow_series[-1])
        }

        return AgentProposal(
            agent_id=self.agent_id,
            direction=direction,
            confidence=float(np.round(confidence, 4)),
            raw_score=float(np.round(composite, 4)),
            metadata=metadata
        )

    def _compute_rsi(self, close: np.ndarray, period: int) -> float:
        """Cálculo rápido de RSI sobre array numpy."""
        deltas = np.diff(close)
        if len(deltas) < period:
            return 50.0
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0.0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _compute_order_flow_imbalance_proxy(
        self, close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray
    ) -> float:
        """
        Proxy rápido de desequilibrio de presión compradora/vendedora intradiario.
        Aproxime la posición del cierre relativo al rango de la vela ponderado por volumen.
        """
        n = min(5, len(close))
        ranges = high[-n:] - low[-n:]
        ranges = np.where(ranges <= 0, 1e-6, ranges)
        # Posición normalizada del cierre dentro del rango [-1.0, 1.0]
        pos = ((close[-n:] - low[-n:]) / ranges) * 2.0 - 1.0
        vol_weights = volume[-n:] / max(1e-6, np.sum(volume[-n:]))
        ofi = float(np.sum(pos * vol_weights))
        return np.clip(ofi, -1.0, 1.0)

    def _extract_dataframe(self, market_data: Any) -> Optional[pd.DataFrame]:
        if isinstance(market_data, pd.DataFrame):
            return market_data
        if isinstance(market_data, dict):
            if "df" in market_data and isinstance(market_data["df"], pd.DataFrame):
                return market_data["df"]
            if "close" in market_data:
                return pd.DataFrame(market_data)
        return None

    def _build_neutral_proposal(self, reason: str) -> AgentProposal:
        return AgentProposal(
            agent_id=self.agent_id,
            direction=0,
            confidence=0.30,
            raw_score=0.0,
            metadata={"status": reason}
        )
