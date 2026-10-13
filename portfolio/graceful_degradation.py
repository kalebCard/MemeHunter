"""
Meme Hunter - Graceful Degradation & Black Swan Guard (PB-109)
Sprint 31: Monitor de microestructura Level 2, mitigación de spread tóxico y degradación elegante.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import numpy as np


@dataclass
class DegradationReport:
    """Reporte de estado de degradación elegante y microestructura."""
    mode: str                           # 'NORMAL', 'DEGRADED_SPREAD', 'PAUSE_NEW_ENTRIES', 'SURVIVAL_MODE'
    size_multiplier: float              # [0.0, 1.0] Factor atenuador del tamaño de posición
    execution_type: str                 # 'MAKER_ONLY', 'HYBRID', 'MARKET_PROTECTIVE', 'HALTED'
    reason: str                         # Causa del cambio de modo
    spread_pct: float = 0.0             # Spread bid-ask actual en porcentaje
    latency_ms: float = 0.0             # Latencia observada de feed/WebSocket
    book_depth_ratio: float = 1.0       # Ratio de liquidez en el libro Level 2
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GracefulDegradationGuard:
    """
    Guardián de degradación elegante ante anomalías de microestructura y Cisnes Negros.
    En lugar de colapsar o apagar el sistema abruptamente, atenúa el tamaño de posición
    y restringe las órdenes a modo pasivo (Maker al Bid) cuando la liquidez se degrada.
    """

    def __init__(
        self,
        warning_spread_pct: float = 0.15,       # 0.15% (Spread normal memecoins)
        toxic_spread_pct: float = 0.35,         # 0.35% (Spread tóxico que destruye el edge)
        extreme_spread_pct: float = 0.70,       # 0.70% (Iliquidez severa / flash crash)
        warning_latency_ms: float = 400.0,      # 400 ms de latencia en WebSockets
        critical_latency_ms: float = 1500.0     # 1,500 ms (Desconexión de datos inminente)
    ):
        self.warning_spread_pct = float(warning_spread_pct)
        self.toxic_spread_pct = float(toxic_spread_pct)
        self.extreme_spread_pct = float(extreme_spread_pct)
        self.warning_latency_ms = float(warning_latency_ms)
        self.critical_latency_ms = float(critical_latency_ms)

        self.last_report = DegradationReport(
            mode="NORMAL",
            size_multiplier=1.0,
            execution_type="HYBRID",
            reason="INITIAL_STATE_HEALTHY"
        )

    def evaluate_microstructure(
        self,
        spread_pct: float,
        latency_ms: float = 50.0,
        book_depth_ratio: float = 1.0
    ) -> DegradationReport:
        """
        Evalúa el estado del libro de órdenes y canal de red para decidir la degradación.
        """
        spread = max(0.0, float(spread_pct))
        lat = max(0.0, float(latency_ms))
        depth = max(0.0, float(book_depth_ratio))

        # 1. Cisne Negro Extremo o Flash Crash (Spread > 0.70% o Latencia > 1500ms o Libro vacío)
        if spread >= self.extreme_spread_pct or lat >= self.critical_latency_ms or depth < 0.10:
            report = DegradationReport(
                mode="SURVIVAL_MODE",
                size_multiplier=0.0,
                execution_type="HALTED",
                reason=f"BLACK_SWAN_DEFENSE: Spread={spread:.3f}%, Latency={lat:.1f}ms, Depth={depth:.2f}",
                spread_pct=spread,
                latency_ms=lat,
                book_depth_ratio=depth
            )
        # 2. Spread Tóxico (> 0.35%): Pausar nuevas entradas pero mantener telemetría
        elif spread >= self.toxic_spread_pct:
            report = DegradationReport(
                mode="PAUSE_NEW_ENTRIES",
                size_multiplier=0.0,
                execution_type="PAUSED",
                reason=f"TOXIC_SPREAD: Spread actual ({spread:.3f}%) supera umbral tolerable ({self.toxic_spread_pct:.3f}%)",
                spread_pct=spread,
                latency_ms=lat,
                book_depth_ratio=depth
            )
        # 3. Spread Advertencia (0.15% - 0.35%) o Latencia Alta (> 400ms): Reducir tamaño al 50% y Maker Only
        elif spread >= self.warning_spread_pct or lat >= self.warning_latency_ms:
            report = DegradationReport(
                mode="DEGRADED_SPREAD",
                size_multiplier=0.50,
                execution_type="MAKER_ONLY",
                reason=f"DEGRADED_CONDITIONS: Spread moderado ({spread:.3f}%) o Latencia ({lat:.1f}ms)",
                spread_pct=spread,
                latency_ms=lat,
                book_depth_ratio=depth
            )
        # 4. Condiciones Normales Institucionales
        else:
            report = DegradationReport(
                mode="NORMAL",
                size_multiplier=1.0,
                execution_type="HYBRID",
                reason="HEALTHY_MICROSTRUCTURE",
                spread_pct=spread,
                latency_ms=lat,
                book_depth_ratio=depth
            )

        self.last_report = report
        return report
