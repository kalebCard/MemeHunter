"""
regime_detector.py - Motor Cuantitativo de Inferencia de Régimen de Mercado (Sprint 52: PB-183).

Evalúa el estado macro, la tendencia de BTC/ETH, la tasa de financiación
y la dispersión de volatilidad para clasificar el régimen de mercado en:
1. BEAR_CASCADE (Cascada bajista / desinflado agresivo: máxima afinidad Short)
2. BULL_PARABOLIC (Frenesí alcista / rally: suspender shorts, evitar squeeze)
3. RANGE_CHOP (Lateralización / compresión de volatilidad: tamaño reducido)
4. PANIC_VOLATILITY (Shock de liquidez / volatilidad extrema: defensivo Kelly)
"""

from enum import Enum
from typing import Dict, Any, Optional
import urllib.request
import urllib.error
import json
import logging

logger = logging.getLogger("HermesRegimeDetector")


class MarketRegime(str, Enum):
    BEAR_CASCADE = "BEAR_CASCADE"
    BULL_PARABOLIC = "BULL_PARABOLIC"
    RANGE_CHOP = "RANGE_CHOP"
    PANIC_VOLATILITY = "PANIC_VOLATILITY"


class HermesRegimeDetector:
    """
    Detector cuantitativo de régimen de mercado para la orquestación autónoma.
    """

    def __init__(self, fapi_base_url: str = "https://fapi.binance.com"):
        self.fapi_base_url = fapi_base_url.rstrip("/")

    def fetch_market_snapshot(self) -> Dict[str, Any]:
        """
        Obtiene métricas en vivo de Binance Futures:
        - Precio y cambio 24h de BTCUSDT y ETHUSDT
        - Funding Rate promedio de las principales memecoins
        """
        snapshot = {
            "btc_price": 0.0,
            "btc_change_24h": 0.0,
            "eth_price": 0.0,
            "eth_change_24h": 0.0,
            "avg_funding_rate": 0.0,
            "status": "ok"
        }

        try:
            # 1. 24h Ticker para BTC y ETH
            url_ticker = f"{self.fapi_base_url}/fapi/v1/ticker/24hr"
            req = urllib.request.Request(url_ticker, headers={"User-Agent": "MemeHunter-Hermes/1.0"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                tickers = json.loads(resp.read().decode("utf-8"))
                for t in tickers:
                    sym = t.get("symbol")
                    if sym == "BTCUSDT":
                        snapshot["btc_price"] = float(t.get("lastPrice", 0))
                        snapshot["btc_change_24h"] = float(t.get("priceChangePercent", 0))
                    elif sym == "ETHUSDT":
                        snapshot["eth_price"] = float(t.get("lastPrice", 0))
                        snapshot["eth_change_24h"] = float(t.get("priceChangePercent", 0))

            # 2. Funding Rate de memecoins representativas
            url_funding = f"{self.fapi_base_url}/fapi/v1/premiumIndex"
            req_f = urllib.request.Request(url_funding, headers={"User-Agent": "MemeHunter-Hermes/1.0"})
            with urllib.request.urlopen(req_f, timeout=4.0) as resp_f:
                premiums = json.loads(resp_f.read().decode("utf-8"))
                meme_symbols = {"1000PEPEUSDT", "DOGEUSDT", "SHIBUSDT", "SOLUSDT"}
                funding_rates = []
                for p in premiums:
                    if p.get("symbol") in meme_symbols:
                        funding_rates.append(float(p.get("lastFundingRate", 0)))
                if funding_rates:
                    snapshot["avg_funding_rate"] = sum(funding_rates) / len(funding_rates)

        except Exception as e:
            logger.warning(f"No se pudo consultar Binance FAPI directa: {e}. Usando fallback seguro.")
            snapshot["status"] = "fallback"

        return snapshot

    def detect_regime(self, snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Clasifica el régimen en base al snapshot macro y devuelve la recomendación de pesos.
        """
        snap = snapshot or self.fetch_market_snapshot()
        btc_chg = snap.get("btc_change_24h", 0.0)
        funding = snap.get("avg_funding_rate", 0.0)

        # 1. Detección de Cascada Bajista (Liquidaciones masivas / momentum Short)
        if btc_chg <= -3.0 or funding < -0.0003:
            regime = MarketRegime.BEAR_CASCADE
            confidence = 0.85
            allocations = {
                "bot_v5_ablation": 0.50,      # Prioridad al francotirador Short
                "bot_v7_quantum": 0.40,       # Ancla de estabilidad y Kelly
                "bot_mined_ensemble": 0.10     # Exposición mínima al ensamble
            }
            rationale = "Mercado en desinflado rápido o funding fuertemente negativo. Ideal para Ablation V5 y Quantum V7."

        # 2. Detección de Frenesí Alcista (Bull Parabolic / Riesgo de Squeeze en Shorts)
        elif btc_chg >= +4.0 or funding > +0.0006:
            regime = MarketRegime.BULL_PARABOLIC
            confidence = 0.80
            allocations = {
                "bot_v5_ablation": 0.00,      # Pausa total de shorts para evitar squeeze
                "bot_v7_quantum": 0.20,       # Posición mínima defensiva
                "bot_mined_ensemble": 0.80     # Asignación a estrategias con capacidad Long
            }
            rationale = "Fuerte impulso alcista macro. Se pausan o reducen los bots 100% Short para proteger capital."

        # 3. Detección de Pánico o Volatilidad Extrema (Swings brutales intradía)
        elif abs(btc_chg) > 6.0:
            regime = MarketRegime.PANIC_VOLATILITY
            confidence = 0.90
            allocations = {
                "bot_v5_ablation": 0.15,
                "bot_v7_quantum": 0.65,       # El dimensionamiento de Kelly gestiona el pánico
                "bot_mined_ensemble": 0.20
            }
            rationale = "Volatilidad extrema y descontrolada. Quantum V7 toma el mando por su menor drawdown histórico."

        # 4. Rango / Choppy (Mercado lateral estándar)
        else:
            regime = MarketRegime.RANGE_CHOP
            confidence = 0.70
            allocations = {
                "bot_v5_ablation": 0.25,
                "bot_v7_quantum": 0.45,
                "bot_mined_ensemble": 0.30
            }
            rationale = "Mercado lateral sin tendencia clara. Distribución balanceada con sesgo hacia bajo drawdown."

        return {
            "regime": regime.value,
            "confidence": confidence,
            "snapshot": snap,
            "recommended_allocations": allocations,
            "rationale": rationale
        }
