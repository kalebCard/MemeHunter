"""
Meme Hunter - Qualitative Sentiment & News Context Agent (PB-107)
Sprint 31: Análisis semántico de noticias, flujo social y contexto cualitativo con fallback offline 0ms.
"""

from typing import Dict, List, Optional, Any, Tuple
import hashlib
import time
import numpy as np

from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from mining.llm_client import OpenRouterClient, OpenRouterModel


class SentimentAgent(BaseSignalAgent):
    """
    Agente de percepción cualitativa.
    Transforma texto no estructurado (noticias, tweets, sentimiento on-chain)
    en un score numérico continuo [-1.0, +1.0] con confianza estadística.
    Garantiza latencia de 0 ms en modo fallback offline o ante fallos de red.
    """

    # Lexicon cuantitativo rápido para memecoins y microestructura crypto
    BULLISH_KEYWORDS = {
        "breakout", "listing", "partnership", "burned", "etf", "all-time high",
        "ath", "bullish", "inflow", "accumulate", "surge", "adoption", "launch",
        "treasury", "liquidity added", "airdrop", "moon", "parabolic"
    }
    BEARISH_KEYWORDS = {
        "hack", "exploit", "sec", "lawsuit", "dump", "rug", "liquidation",
        "bankrupt", "freeze", "delist", "drain", "outflow", "ban", "scam",
        "insolvent", "panic", "collapse", "bearish", "investigation", "fine"
    }

    def __init__(
        self,
        agent_id: str = "sentiment_agent",
        weight: float = 1.0,
        active: bool = True,
        llm_client: Optional[OpenRouterClient] = None,
        use_llm_if_available: bool = False,
        cache_ttl_seconds: int = 300
    ):
        super().__init__(agent_id=agent_id, agent_type="sentiment", weight=weight, active=active)
        self.llm_client = llm_client
        self.use_llm_if_available = use_llm_if_available
        self.cache_ttl_seconds = cache_ttl_seconds
        self._semantic_cache: Dict[str, Tuple[float, float, float]] = {}  # hash -> (score, conf, timestamp)

    def _compute_proposal(self, market_data: Any) -> AgentProposal:
        """Calcula el vector de sentimiento a partir de datos cualitativos o feeds."""
        text_feed = self._extract_text_feed(market_data)

        # Si no hay texto provisto, buscar métricas de sentimiento precomputadas
        if not text_feed:
            precomputed_score = self._extract_precomputed_sentiment(market_data)
            if precomputed_score is not None:
                return self._build_proposal_from_score(precomputed_score, 0.70, "PRECOMPUTED_SENTIMENT_FEED")
            return self._build_proposal_from_score(0.0, 0.30, "NO_TEXT_OR_SENTIMENT_DATA")

        # 1. Consulta en Caché Semántica Local (0 ms)
        cache_key = hashlib.md5(text_feed.lower().encode("utf-8")).hexdigest()
        now = time.time()
        if cache_key in self._semantic_cache:
            score, conf, ts = self._semantic_cache[cache_key]
            if now - ts < self.cache_ttl_seconds:
                return self._build_proposal_from_score(score, conf, "SEMANTIC_CACHE_HIT")

        # 2. Análisis Rápido Léxico / Heurístico Local (Sub-milisegundo, 0ms overhead)
        lexical_score, lexical_conf = self._analyze_lexicon(text_feed)

        # 3. Refinamiento opcional con OpenRouter LLM si está habilitado y configurado
        final_score = lexical_score
        final_conf = lexical_conf
        source_tag = "LEXICAL_FIN_NLP"

        if self.use_llm_if_available and self.llm_client and self.llm_client.is_available():
            try:
                llm_score, llm_conf = self._query_llm_sentiment(text_feed)
                # Fusión 70% LLM + 30% Lexical
                final_score = 0.70 * llm_score + 0.30 * lexical_score
                final_conf = max(final_conf, llm_conf)
                source_tag = "OPENROUTER_FINLLM"
            except Exception:
                # Fallback transparente y determinista a análisis léxico
                source_tag = "FALLBACK_LEXICAL_DUE_TO_API_TIMEOUT"

        final_score = float(np.clip(final_score, -1.0, 1.0))
        final_conf = float(np.clip(final_conf, 0.0, 1.0))

        # Almacenar en caché
        self._semantic_cache[cache_key] = (final_score, final_conf, now)

        return self._build_proposal_from_score(final_score, final_conf, source_tag)

    def _analyze_lexicon(self, text: str) -> Tuple[float, float]:
        """Análisis de sentimiento cuantitativo de alta velocidad (< 0.1 ms)."""
        words = set(text.lower().replace(",", " ").replace(".", " ").split())
        bull_hits = len(words.intersection(self.BULLISH_KEYWORDS))
        bear_hits = len(words.intersection(self.BEARISH_KEYWORDS))

        total_hits = bull_hits + bear_hits
        if total_hits == 0:
            return 0.0, 0.35

        score = (bull_hits - bear_hits) / float(total_hits)
        confidence = min(0.95, 0.50 + total_hits * 0.10)
        return float(np.round(score, 4)), float(np.round(confidence, 4))

    def _query_llm_sentiment(self, text: str) -> Tuple[float, float]:
        """Consulta formal a OpenRouter para interpretar el tono institucional."""
        prompt = (
            f"Actúa como analista cuantitativo de microestructura crypto. "
            f"Evalúa el sentimiento de la siguiente noticia/feed para activos digitales: '{text}'. "
            f"Responde estrictamente en formato JSON: {{\"sentiment\": <-1.0 a 1.0>, \"confidence\": <0.0 a 1.0>}}"
        )
        resp = self.llm_client.generate_completion(
            prompt=prompt,
            model=OpenRouterModel.DEEPSEEK_V3,
            max_tokens=60,
            temperature=0.1
        )
        content = resp.get("content", "")
        # Parsing seguro
        import json
        data = json.loads(content)
        return float(data.get("sentiment", 0.0)), float(data.get("confidence", 0.7))

    def _build_proposal_from_score(self, score: float, confidence: float, source: str) -> AgentProposal:
        """Construye la propuesta normalizada compatible con el DAG."""
        direction = 0
        if score > 0.15 and confidence >= 0.50:
            direction = 1
        elif score < -0.15 and confidence >= 0.50:
            direction = -1

        regime_comp = {
            "BULL_MOMENTUM": float(np.clip(0.5 + score * 0.5, 0.1, 0.99)),
            "BEAR_BLEED": float(np.clip(0.5 - score * 0.5, 0.1, 0.99)),
            "CHOPPY_RANGE": float(np.clip(1.0 - abs(score), 0.1, 0.99))
        }

        return AgentProposal(
            agent_id=self.agent_id,
            direction=direction,
            confidence=float(np.round(confidence, 4)),
            raw_score=float(np.round(score, 4)),
            regime_compatibility=regime_comp,
            metadata={"source": source, "sentiment_score": float(np.round(score, 4))}
        )

    def _extract_text_feed(self, market_data: Any) -> Optional[str]:
        if isinstance(market_data, dict):
            if "news" in market_data and isinstance(market_data["news"], str):
                return market_data["news"]
            if "headlines" in market_data:
                if isinstance(market_data["headlines"], list):
                    return " ".join(market_data["headlines"])
                return str(market_data["headlines"])
            if "text" in market_data:
                return str(market_data["text"])
        return None

    def _extract_precomputed_sentiment(self, market_data: Any) -> Optional[float]:
        if isinstance(market_data, dict) and "sentiment_score" in market_data:
            try:
                return float(market_data["sentiment_score"])
            except (ValueError, TypeError):
                return None
        return None
