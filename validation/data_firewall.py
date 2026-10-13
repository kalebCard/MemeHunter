"""
validation/data_firewall.py - Cortafuegos de Datos y Validador de Integridad (Sprint 36: PB-121).
Protege los modelos y agentes de datos de mercado corruptos, series temporales con huecos (gaps)
y latencias excesivas. Activa el modo STANDBY automáticamente ante anomalías.
"""

from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import time
import logging

from validation.schemas import (
    MarketCandleSchema,
    OrderBookL2Schema,
    MarketTickSchema,
    MarketSeriesInput
)

logger = logging.getLogger("DataFirewallGuard")


class FirewallMode(str, Enum):
    NORMAL = "NORMAL"
    GAP_DETECTED_STANDBY = "GAP_DETECTED_STANDBY"
    DATA_FEED_STALE_STANDBY = "DATA_FEED_STALE_STANDBY"
    CORRUPTED_FEED_HALT = "CORRUPTED_FEED_HALT"


# Mapeo de timeframes estándar a milisegundos
TIMEFRAME_MS_MAP: Dict[str, int] = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}


class DataFirewallGuard:
    """
    Cortafuegos estricto de entrada para el flujo de mercado.
    Verifica que no existan huecos irreales, que los esquemas Pydantic se cumplan
    y que la frescura de los datos sea institucional.
    """

    def __init__(
        self,
        max_allowed_latency_ms: float = 1500.0,
        max_flash_spike_pct: float = 0.35,  # 35% de salto repentino en 1 vela
        stale_threshold_multiplier: float = 2.0
    ):
        self.max_allowed_latency_ms = max_allowed_latency_ms
        self.max_flash_spike_pct = max_flash_spike_pct
        self.stale_multiplier = stale_threshold_multiplier
        self.current_mode = FirewallMode.NORMAL
        self.last_rejection_reason: Optional[str] = None
        self.audit_log: List[Dict[str, Any]] = []

    def validate_tick(self, tick_data: Dict[str, Any]) -> Tuple[bool, Optional[MarketTickSchema], str]:
        """Valida un tick individual con el esquema Pydantic."""
        try:
            schema = MarketTickSchema(**tick_data)
            return True, schema, "OK"
        except Exception as e:
            self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
            self.last_rejection_reason = f"Tick corrupto rechazado: {e}"
            self._record_event("TICK_VALIDATION_ERROR", str(e))
            return False, None, str(e)

    def validate_candle(self, candle_data: Dict[str, Any]) -> Tuple[bool, Optional[MarketCandleSchema], str]:
        """Valida una vela individual asegurando consistencia geométrica OHLCV."""
        try:
            schema = MarketCandleSchema(**candle_data)
            return True, schema, "OK"
        except Exception as e:
            self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
            self.last_rejection_reason = f"Vela geométrica inválida: {e}"
            self._record_event("CANDLE_VALIDATION_ERROR", str(e))
            return False, None, str(e)

    def validate_orderbook(self, ob_data: Dict[str, Any]) -> Tuple[bool, Optional[OrderBookL2Schema], str]:
        """Valida un orderbook Level 2 certificando que no esté cruzado ni invertido."""
        try:
            schema = OrderBookL2Schema(**ob_data)
            return True, schema, "OK"
        except Exception as e:
            self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
            self.last_rejection_reason = f"Libro L2 corrupto o cruzado: {e}"
            self._record_event("ORDERBOOK_VALIDATION_ERROR", str(e))
            return False, None, str(e)

    def validate_timeseries(
        self,
        symbol: str,
        candles_raw: List[Dict[str, Any]],
        timeframe: str = "4h",
        current_time_ms: Optional[int] = None
    ) -> Tuple[bool, List[MarketCandleSchema], str]:
        """
        Audita una serie temporal completa antes de inyectarla al LLM o al orquestador.
        1. Valida esquema de cada vela.
        2. Verifica que no existan huecos temporales (gaps).
        3. Verifica frescura de los datos respecto al tiempo actual.
        4. Detecta anomalías flash spike irrealistas.
        """
        if not candles_raw or len(candles_raw) == 0:
            self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
            reason = f"[{symbol}] Serie temporal vacía provista al cortafuegos"
            self.last_rejection_reason = reason
            return False, [], reason

        step_ms = TIMEFRAME_MS_MAP.get(timeframe.lower())
        if step_ms is None:
            reason = f"Timeframe no soportado: '{timeframe}'"
            self.last_rejection_reason = reason
            return False, [], reason

        valid_candles: List[MarketCandleSchema] = []

        # 1. Validación de esquema individual
        for idx, c_dict in enumerate(candles_raw):
            ok, schema, err = self.validate_candle(c_dict)
            if not ok or schema is None:
                self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
                reason = f"[{symbol}] Vela {idx} corrupta: {err}"
                self.last_rejection_reason = reason
                return False, [], reason
            valid_candles.append(schema)

        # 2. Verificación de Gaps Temporales
        for i in range(1, len(valid_candles)):
            prev_ts = valid_candles[i - 1].timestamp_ms
            curr_ts = valid_candles[i].timestamp_ms
            diff_ms = curr_ts - prev_ts

            if diff_ms <= 0:
                self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
                reason = f"[{symbol}] Timestamp invertido o duplicado entre vela {i-1} ({prev_ts}) y {i} ({curr_ts})"
                self.last_rejection_reason = reason
                return False, [], reason

            if diff_ms != step_ms:
                # Se detectó un salto (falta al menos una vela en la serie)
                missing_count = int(round(diff_ms / step_ms)) - 1
                self.current_mode = FirewallMode.GAP_DETECTED_STANDBY
                reason = (
                    f"[{symbol}] GAP TEMPORAL DETECTADO: Salto de {diff_ms} ms entre vela {i-1} y {i} "
                    f"(esperado: {step_ms} ms para {timeframe}). Faltan ~{missing_count} velas. Standby activado."
                )
                self.last_rejection_reason = reason
                self._record_event("TIMESERIES_GAP_DETECTED", reason)
                return False, [], reason

            # 3. Detección de Anomalías / Flash Spikes Injustificados (> 35% en 1 sola vela)
            prev_close = valid_candles[i - 1].close
            curr_close = valid_candles[i].close
            pct_change = abs(curr_close - prev_close) / prev_close
            if pct_change >= self.max_flash_spike_pct:
                self.current_mode = FirewallMode.CORRUPTED_FEED_HALT
                reason = (
                    f"[{symbol}] FLASH SPIKE ANÓMALO DETECTADO: Cambio de {pct_change:.1%} entre velas {i-1} y {i} "
                    f"supera el umbral tolerable de {self.max_flash_spike_pct:.1%}. Abortando por seguridad."
                )
                self.last_rejection_reason = reason
                self._record_event("FLASH_SPIKE_ANOMALY", reason)
                return False, [], reason

        # 4. Verificación de Frescura y Latencia del Feed
        now_ms = current_time_ms if current_time_ms is not None else int(time.time() * 1000)
        last_candle_ts = valid_candles[-1].timestamp_ms
        age_ms = now_ms - last_candle_ts
        max_staleness = step_ms * self.stale_multiplier

        if age_ms > max_staleness:
            self.current_mode = FirewallMode.DATA_FEED_STALE_STANDBY
            reason = (
                f"[{symbol}] FEED OBSOLETO / RETRASO CRÍTICO: Última vela tiene antigüedad de "
                f"{age_ms / 1000 / 60:.1f} min (límite de frescura: {max_staleness / 1000 / 60:.1f} min). Modo espera."
            )
            self.last_rejection_reason = reason
            self._record_event("FEED_STALE_STANDBY", reason)
            return False, [], reason

        # Todo verificado exitosamente
        self.current_mode = FirewallMode.NORMAL
        self.last_rejection_reason = None
        return True, valid_candles, "OK"

    def _record_event(self, event_type: str, details: str) -> None:
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "mode": self.current_mode.value,
            "details": details
        }
        self.audit_log.append(event)
        if len(self.audit_log) > 100:
            self.audit_log.pop(0)
        logger.warning(f"🛡️ CORTAFUEGOS DE DATOS [{self.current_mode.value}]: {details}")
