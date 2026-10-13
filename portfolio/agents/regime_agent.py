"""
Meme Hunter - Regime HMM & Volatility Classifier Agent (PB-104)
Sprint 30: Detección dinámica y probabilística de régimen de mercado para el DAG.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from scripts.research.regime_classifier import (
    REGIME_BULL_MOMENTUM,
    REGIME_BEAR_BLEED,
    REGIME_CHOPPY_RANGE,
    compute_regime_features,
    classify_current_regime
)
try:
    from data_engine.openbb_provider import MacroOnChainContext, OpenBBDataProvider
except ImportError:
    MacroOnChainContext = None
    OpenBBDataProvider = None


class RegimeHMMAgent(BaseSignalAgent):
    """
    Agente especializado en detección dinámica de regímenes de mercado.
    Emite un vector continuo de probabilidades [p_bull, p_bear, p_range]
    que condiciona los pesos de todos los demás agentes en el Orquestador DAG.
    """

    def __init__(
        self,
        agent_id: str = "regime_hmm_agent",
        weight: float = 1.0,
        active: bool = True,
        volatility_window: int = 20,
        trend_threshold_pct: float = 2.0,
        openbb_provider: Optional[Any] = None
    ):
        super().__init__(agent_id=agent_id, agent_type="regime", weight=weight, active=active)
        self.volatility_window = volatility_window
        self.trend_threshold_pct = trend_threshold_pct
        self.openbb_provider = openbb_provider
        self.last_detected_regime = REGIME_CHOPPY_RANGE
        self.last_probabilities: Dict[str, float] = {
            "p_bull": 0.33,
            "p_bear": 0.33,
            "p_range": 0.34
        }

    def _compute_proposal(self, market_data: Any) -> AgentProposal:
        """
        Calcula las probabilidades de régimen a partir de datos OHLCV y contexto macro on-chain.
        """
        if market_data is None:
            return self._build_default_proposal("EMPTY_DATA")

        # 0. Extraer contexto macro si está disponible
        macro_ctx = None
        if isinstance(market_data, dict) and "macro_context" in market_data:
            macro_ctx = market_data["macro_context"]
        elif self.openbb_provider:
            macro_ctx = self.openbb_provider.get_macro_context()

        # Aceptar DataFrame o dict con close/high/low/volume
        if isinstance(market_data, dict):
            if "df" in market_data:
                df = market_data["df"]
            elif "close" in market_data and isinstance(market_data["close"], (list, np.ndarray, pd.Series)):
                df = pd.DataFrame(market_data)
            else:
                return self._build_default_proposal("INVALID_DATA_FORMAT")
        elif isinstance(market_data, pd.DataFrame):
            df = market_data
        else:
            return self._build_default_proposal("UNSUPPORTED_DATA_TYPE")

        if df.empty or len(df) < 5:
            return self._build_default_proposal("INSUFFICIENT_BARS")

        # Cómputo robusto de características
        try:
            df_feat = compute_regime_features(df)
            last_row = df_feat.iloc[-1]
            regime = classify_current_regime(last_row)
        except Exception:
            # Fallback rápido si faltan columnas completas (ej. sólo hay close)
            return self._heuristic_fallback(df)

        self.last_detected_regime = regime

        # Estimación de probabilidades continuas condicionadas por datos macro
        probs = self._estimate_regime_probabilities(last_row, regime, macro_context=macro_ctx)
        self.last_probabilities = probs

        p_bull = probs["p_bull"]
        p_bear = probs["p_bear"]
        p_range = probs["p_range"]

        # Determinación de dirección y convicción
        if regime == REGIME_BULL_MOMENTUM and p_bull >= 0.50:
            direction = 1
            confidence = float(np.clip(p_bull, 0.5, 0.99))
            raw_score = float(p_bull - p_bear)
        elif regime == REGIME_BEAR_BLEED and p_bear >= 0.50:
            direction = -1
            confidence = float(np.clip(p_bear, 0.5, 0.99))
            raw_score = float(p_bull - p_bear)
        else:
            direction = 0
            confidence = float(np.clip(p_range, 0.4, 0.95))
            raw_score = 0.0

        metadata = {
            "detected_regime": regime,
            "probabilities": probs,
            "realized_vol_20": float(last_row.get("realized_vol_20", 0.0)) if not pd.isna(last_row.get("realized_vol_20", 0.0)) else 0.0,
            "ema_dispersion_pct": float(last_row.get("ema_dispersion_pct", 0.0)) if not pd.isna(last_row.get("ema_dispersion_pct", 0.0)) else 0.0,
            "natr_14": float(last_row.get("natr_14", 0.0)) if not pd.isna(last_row.get("natr_14", 0.0)) else 0.0
        }

        if macro_ctx is not None:
            metadata["macro_onchain"] = (
                macro_ctx.to_dict() if hasattr(macro_ctx, "to_dict") else str(macro_ctx)
            )

        regime_compatibility = {
            "BULL_MOMENTUM": p_bull,
            "BEAR_BLEED": p_bear,
            "CHOPPY_RANGE": p_range
        }

        return AgentProposal(
            agent_id=self.agent_id,
            direction=direction,
            confidence=confidence,
            raw_score=raw_score,
            regime_compatibility=regime_compatibility,
            metadata=metadata
        )

    def _estimate_regime_probabilities(
        self,
        last_row: pd.Series,
        regime: str,
        macro_context: Optional[Any] = None
    ) -> Dict[str, float]:
        """Calcula probabilidades normalizadas continuas basadas en métricas cuantitativas y macro."""
        disp = float(last_row.get("ema_dispersion_pct", 0.0))
        if pd.isna(disp):
            disp = 0.0
        vol = float(last_row.get("natr_14", 2.0))
        if pd.isna(vol) or vol <= 0.0:
            vol = 2.0

        # Logits suaves
        logit_bull = np.clip((disp / 5.0) + (1.0 if regime == REGIME_BULL_MOMENTUM else -0.5), -5.0, 5.0)
        logit_bear = np.clip((-disp / 5.0) + (1.0 if regime == REGIME_BEAR_BLEED else -0.5), -5.0, 5.0)
        logit_range = np.clip((vol / 4.0) + (1.0 if regime == REGIME_CHOPPY_RANGE else -0.2), -5.0, 5.0)

        # Condicionamiento PB-120 por liquidez macro y DeFi
        if macro_context is not None:
            is_contraction = getattr(macro_context, "is_bear_contraction", False)
            macro_sent = getattr(macro_context, "macro_sentiment_score", 0.0)
            if is_contraction or macro_sent < -0.2:
                # Contracción de TVL / liquidez: penalizar fuertemente falsas rupturas alcistas
                logit_bull -= 1.2
                logit_bear += 0.8
                logit_range += 0.4
            elif macro_sent > 0.2:
                # Entorno de expansión de liquidez
                logit_bull += 0.6
                logit_bear -= 0.4

        exp_vals = np.exp([logit_bull, logit_bear, logit_range])
        probs = exp_vals / np.sum(exp_vals)

        return {
            "p_bull": float(np.round(probs[0], 4)),
            "p_bear": float(np.round(probs[1], 4)),
            "p_range": float(np.round(probs[2], 4))
        }

    def _heuristic_fallback(self, df: pd.DataFrame) -> AgentProposal:
        """Fallback ultrarrápido con sólo la columna de cierre."""
        closes = df["close"].values
        ret = (closes[-1] - closes[0]) / max(1e-6, closes[0])
        disp_pct = ret * 100.0

        if disp_pct > 2.0:
            regime = REGIME_BULL_MOMENTUM
            p_bull, p_bear, p_range = 0.65, 0.15, 0.20
            direction = 1
            confidence = 0.65
        elif disp_pct < -2.0:
            regime = REGIME_BEAR_BLEED
            p_bull, p_bear, p_range = 0.15, 0.65, 0.20
            direction = -1
            confidence = 0.65
        else:
            regime = REGIME_CHOPPY_RANGE
            p_bull, p_bear, p_range = 0.25, 0.25, 0.50
            direction = 0
            confidence = 0.55

        probs = {"p_bull": p_bull, "p_bear": p_bear, "p_range": p_range}
        return AgentProposal(
            agent_id=self.agent_id,
            direction=direction,
            confidence=confidence,
            raw_score=float(p_bull - p_bear),
            regime_compatibility={"BULL_MOMENTUM": p_bull, "BEAR_BLEED": p_bear, "CHOPPY_RANGE": p_range},
            metadata={"detected_regime": regime, "probabilities": probs, "fallback": True}
        )

    def _build_default_proposal(self, reason: str) -> AgentProposal:
        return AgentProposal(
            agent_id=self.agent_id,
            direction=0,
            confidence=0.33,
            raw_score=0.0,
            regime_compatibility={"BULL_MOMENTUM": 0.33, "BEAR_BLEED": 0.33, "CHOPPY_RANGE": 0.34},
            metadata={"status": reason, "detected_regime": REGIME_CHOPPY_RANGE}
        )
