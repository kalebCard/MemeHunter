"""
Módulo Centinela Anti-Manipulación y Detección de Anomalías Adversarias.
US-5.1 (Sprint 5).

Implementa:
1. Volume-to-Depth Imbalance: Detección de volumen explosivo sin soporte genuino en el libro L2 (trampas de liquidez/spoofing).
2. Divergencia Cross-Exchange: Comparación entre precio de Futuros y precio índice Spot/DEX (umbral 0.8%).
3. Desbalance Severo de Financiación (Funding Rate): Exclusión de memecoins con tasa > 0.20% o < -0.20%.
4. Detección de Patrón Pump & Dump: Alzas parabólicas en libros estrechos con colapso de liquidez.
5. Compuerta previa de seguridad obligatoria antes de enrutar cualquier orden.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger("AdversarialMarketSentinel")


@dataclass
class AdversarialAuditResult:
    """Resultado formal de la evaluación de seguridad y microestructura adversaria."""
    symbol: str
    is_safe_to_trade: bool
    action_recommended: str           # "ALLOW", "SUSPEND_ENTRY", "FORCE_EXIT"
    reasons: List[str] = field(default_factory=list)
    volume_to_depth_ratio: float = 0.0
    price_divergence_pct: float = 0.0
    funding_rate_pct: float = 0.0
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdversarialMarketSentinel:
    """
    Centinela estadístico en tiempo real que protege el capital contra trampas de liquidez,
    manipulación de creadores de mercado, spoofing y burbujas pump & dump en memecoins.
    """

    def __init__(
        self,
        max_vol_to_depth_ratio: float = 10.0,
        max_price_divergence_pct: float = 0.80,
        max_funding_imbalance_pct: float = 0.20,
        pump_dump_price_threshold_pct: float = 15.0,
        pump_dump_rvol_threshold: float = 4.0,
        pump_dump_max_spread_bps: float = 45.0
    ):
        self.max_vol_to_depth = float(max_vol_to_depth_ratio)
        self.max_divergence = float(max_price_divergence_pct)
        self.max_funding = float(max_funding_imbalance_pct)
        self.pump_price_thresh = float(pump_dump_price_threshold_pct)
        self.pump_rvol_thresh = float(pump_dump_rvol_threshold)
        self.pump_spread_thresh = float(pump_dump_max_spread_bps)
        self.audit_history: List[AdversarialAuditResult] = []

    def check_volume_to_depth_imbalance(
        self,
        symbol: str,
        recent_volume_usd: float,
        l2_bids_usd: float,
        l2_asks_usd: float
    ) -> Tuple[bool, float, str]:
        """
        Calcula el ratio entre el volumen reciente (ej. últimos 5m) y la profundidad visible en L2.
        Un ratio desproporcionado indica que el volumen transado es artificial (wash trading/spoofing)
        o que una salida rápida de posición colapsará el libro por falta de profundidad real.
        """
        total_depth_usd = max(1.0, float(l2_bids_usd + l2_asks_usd))
        ratio = float(recent_volume_usd) / total_depth_usd

        if ratio > self.max_vol_to_depth:
            msg = (
                f"[{symbol}] ALERTA Volume-to-Depth Imbalance: ratio={ratio:.2f} "
                f"supera el umbral institucional de {self.max_vol_to_depth:.2f}x (Profundidad L2 insuficiente)."
            )
            return False, ratio, msg
        return True, ratio, "OK"

    def check_cross_exchange_divergence(
        self,
        futures_price: float,
        reference_index_price: float
    ) -> Tuple[bool, float, str]:
        """
        Comprueba la discrepancia entre el contrato perpetuo y el índice de referencia Spot/DEX.
        Una divergencia > 0.80% (80 bps) evidencia desacoplamiento o manipulación unilateral.
        """
        if reference_index_price <= 0.0 or futures_price <= 0.0:
            return True, 0.0, "OK"

        div_pct = abs(futures_price - reference_index_price) / reference_index_price * 100.0
        if div_pct > self.max_divergence:
            msg = (
                f"ALERTA Divergencia Cross-Exchange: futuros={futures_price:.6f} vs índice={reference_index_price:.6f} "
                f"(divergencia={div_pct:.3f}%, límite={self.max_divergence:.2f}%)."
            )
            return False, div_pct, msg
        return True, div_pct, "OK"

    def check_funding_rate_imbalance(
        self,
        funding_rate_pct: float
    ) -> Tuple[bool, float, str]:
        """
        Filtra memecoins con tasa de financiación extrema (> 0.20% o < -0.20% por intervalo de 8h).
        Tasas desproporcionadas señalan riesgo inminente de squeeze forzado y estrangulamiento de liquidez.
        """
        abs_funding = abs(float(funding_rate_pct))
        if abs_funding > self.max_funding:
            msg = (
                f"ALERTA Funding Rate Anómalo: {funding_rate_pct:+.4f}% excede el límite de seguridad "
                f"de +- {self.max_funding:.2f}% (Riesgo severo de liquidación en cascada)."
            )
            return False, funding_rate_pct, msg
        return True, funding_rate_pct, "OK"

    def check_pump_and_dump_signature(
        self,
        price_change_5m_pct: float,
        rvol_5m: float,
        bid_ask_spread_bps: float
    ) -> Tuple[bool, str]:
        """
        Detecta firmas de Pump & Dump: subida explosiva de precio con RVOL anómalo y spread dilatado.
        """
        if (
            abs(price_change_5m_pct) >= self.pump_price_thresh
            and rvol_5m >= self.pump_rvol_thresh
            and bid_ask_spread_bps >= self.pump_spread_thresh
        ):
            msg = (
                f"ALERTA Firma Pump & Dump detectada: cambio_5m={price_change_5m_pct:+.1f}%, "
                f"RVOL={rvol_5m:.1f}x, spread={bid_ask_spread_bps:.1f} bps."
            )
            return False, msg
        return True, "OK"

    def evaluate_market_health(
        self,
        symbol: str,
        metrics: Dict[str, Any]
    ) -> AdversarialAuditResult:
        """
        Evalúa de forma integral las condiciones de microestructura para un símbolo y decide
        si es seguro autorizar nuevas entradas o si debe suspenderse la operativa.
        """
        reasons: List[str] = []
        is_safe = True
        action = "ALLOW"

        # 1. Volume-to-depth
        recent_vol = metrics.get("recent_volume_5m_usd", 0.0)
        bids_usd = metrics.get("l2_bids_usd", 100000.0)
        asks_usd = metrics.get("l2_asks_usd", 100000.0)
        vol_safe, vol_ratio, vol_msg = self.check_volume_to_depth_imbalance(symbol, recent_vol, bids_usd, asks_usd)
        if not vol_safe:
            is_safe = False
            reasons.append(vol_msg)

        # 2. Cross-exchange divergence
        fut_p = metrics.get("futures_price", 0.0)
        idx_p = metrics.get("reference_index_price", fut_p)
        div_safe, div_pct, div_msg = self.check_cross_exchange_divergence(fut_p, idx_p)
        if not div_safe:
            is_safe = False
            reasons.append(div_msg)

        # 3. Funding rate
        funding_rate = metrics.get("funding_rate_pct", 0.0)
        fund_safe, _, fund_msg = self.check_funding_rate_imbalance(funding_rate)
        if not fund_safe:
            is_safe = False
            reasons.append(fund_msg)

        # 4. Pump & dump signature
        p_chg = metrics.get("price_change_5m_pct", 0.0)
        rvol = metrics.get("rvol_5m", 1.0)
        spread_bps = metrics.get("bid_ask_spread_bps", 5.0)
        pump_safe, pump_msg = self.check_pump_and_dump_signature(p_chg, rvol, spread_bps)
        if not pump_safe:
            is_safe = False
            reasons.append(pump_msg)
            action = "FORCE_EXIT"

        if not is_safe and action != "FORCE_EXIT":
            action = "SUSPEND_ENTRY"

        result = AdversarialAuditResult(
            symbol=symbol,
            is_safe_to_trade=is_safe,
            action_recommended=action,
            reasons=reasons,
            volume_to_depth_ratio=round(vol_ratio, 2),
            price_divergence_pct=round(div_pct, 4),
            funding_rate_pct=round(funding_rate, 5)
        )

        self.audit_history.append(result)
        if len(self.audit_history) > 1000:
            self.audit_history.pop(0)

        if not is_safe:
            logger.warning(f"Adversarial Sentinel Bloqueó {symbol}: acción={action}, causas={reasons}")

        return result
