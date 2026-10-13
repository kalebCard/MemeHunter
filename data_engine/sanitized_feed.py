"""
data_engine/sanitized_feed.py - Middleware de Ingesta Sanitizada (Sprint 36: PB-122).
Encapsula llamadas a feeds externos pasando cada registro por el DataFirewallGuard
antes de entregarlo a los agentes de IA o estrategias cuantitativas.
"""

from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import logging

from validation.data_firewall import DataFirewallGuard, FirewallMode
from validation.schemas import MarketCandleSchema

logger = logging.getLogger("SanitizedFeedAdapter")


class SanitizedFeedAdapter:
    """
    Adaptador institucional de ingesta limpia.
    Filtra y sanitiza DataFrames y feeds en tiempo real antes de que cualquier modelo
    tome decisiones sobre ellos.
    """

    def __init__(self, firewall: Optional[DataFirewallGuard] = None):
        self.firewall = firewall or DataFirewallGuard()

    @property
    def mode(self) -> FirewallMode:
        return self.firewall.current_mode

    @property
    def is_healthy(self) -> bool:
        return self.firewall.current_mode == FirewallMode.NORMAL

    def sanitize_dataframe(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str = "4h",
        current_time_ms: Optional[int] = None
    ) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        Toma un DataFrame estándar de pandas (con columnas timestamp, open, high, low, close, volume),
        lo audita con DataFirewallGuard y retorna un DataFrame limpio y ordenado o rechaza la serie.
        """
        if df is None or df.empty:
            return False, None, f"[{symbol}] DataFrame nulo o vacío provisto al adaptador"

        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(set(df.columns)):
            missing = required_cols - set(df.columns)
            return False, None, f"[{symbol}] Faltan columnas obligatorias: {missing}"

        # Extraer timestamp
        records: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            ts = None
            if "timestamp_ms" in df.columns:
                ts = int(row["timestamp_ms"])
            elif "timestamp" in df.columns:
                val = row["timestamp"]
                if isinstance(val, (int, float)):
                    ts = int(val if val > 1e11 else val * 1000)
                elif hasattr(val, "timestamp"):
                    ts = int(val.timestamp() * 1000)
            elif hasattr(idx, "timestamp"):
                ts = int(idx.timestamp() * 1000)
            elif isinstance(idx, (int, float)):
                ts = int(idx if idx > 1e11 else idx * 1000)
            else:
                # Si no hay timestamp identificable, usar índice secuencial aproximado
                ts = int(idx * 3600 * 1000)

            rec = {
                "timestamp_ms": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
            records.append(rec)

        # Pasar por el cortafuegos
        ok, valid_candles, reason = self.firewall.validate_timeseries(
            symbol=symbol,
            candles_raw=records,
            timeframe=timeframe,
            current_time_ms=current_time_ms
        )

        if not ok:
            return False, None, reason

        # Reconstruir DataFrame validado y garantizado
        clean_df = pd.DataFrame([c.model_dump() for c in valid_candles])
        clean_df.set_index("timestamp_ms", inplace=False)
        return True, clean_df, "OK"

    def get_firewall_status(self) -> Dict[str, Any]:
        """Reporte de estado para la API REST del Cockpit y telemetría."""
        return {
            "mode": self.firewall.current_mode.value,
            "is_healthy": self.is_healthy,
            "last_rejection_reason": self.firewall.last_rejection_reason,
            "recent_audit_events": len(self.firewall.audit_log)
        }
