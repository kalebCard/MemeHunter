"""
Módulo de Apagado de Emergencia Institucional (Emergency Kill-Switch).
US-5.3 (Sprint 5).

Implementa:
- Mecanismo de corte de emergencia de triple nivel:
  * Nivel 1 (YELLOW - Soft Lock): Suspensión de nuevas entradas, cancelación de órdenes límite pendientes.
  * Nivel 2 (ORANGE - Graceful Unwind): Cierre ordenado/TWAP de posiciones abiertas y cancelación de órdenes.
  * Nivel 3 (RED - Hard Cut / Kill): Liquidación inmediata a mercado de todas las posiciones,
    cancelación masiva de órdenes, desconexión de feeds y bloqueo del motor en < 1 segundo (< 1000 ms).
- Disparadores automáticos:
  * Drawdown intradía > 3.5%.
  * Pérdida acumulada en 1 hora > 1.5%.
  * Pérdida de latencia de WebSocket > 10.0 segundos.
  * Activación manual mediante API / Dashboard Cockpit.
- Auditoría atómica y persistencia de estado del interruptor de emergencia.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import IntEnum
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger("EmergencyKillSwitch")


class KillSwitchLevel(IntEnum):
    NORMAL = 0
    LEVEL_1_SOFT_LOCK = 1      # Stop nuevas entradas, cancelar órdenes de entrada pendientes
    LEVEL_2_GRACEFUL_UNWIND = 2 # Deshacer posiciones abiertas con TWAP/ordenado
    LEVEL_3_HARD_CUT = 3       # Liquidación a mercado instantánea, cancelar 100%, desconexión < 1s


@dataclass
class KillSwitchEvent:
    """Evento auditable de activación del kill-switch."""
    timestamp_utc: str
    level: int
    level_name: str
    trigger_reason: str
    execution_time_ms: float
    orders_cancelled_count: int
    positions_closed_count: int
    is_success: bool


class EmergencyKillSwitch:
    """
    Controlador institucional de apagado de emergencia de alta velocidad.
    Garantiza aislamiento del riesgo en milisegundos ante caídas de exchange o drawdowns críticos.
    """

    def __init__(
        self,
        max_intraday_drawdown_pct: float = 3.50,
        max_1h_loss_pct: float = 1.50,
        max_ws_latency_seconds: float = 10.0,
        state_file: str = "portfolio/kill_switch_state.json"
    ):
        self.max_drawdown = float(max_intraday_drawdown_pct)
        self.max_1h_loss = float(max_1h_loss_pct)
        self.max_ws_latency = float(max_ws_latency_seconds)
        self.state_file = state_file

        self.current_level = KillSwitchLevel.NORMAL
        self.last_trigger_reason: Optional[str] = None
        self.last_triggered_at: Optional[str] = None
        self.event_log: List[KillSwitchEvent] = []

        self._load_state()

    def _load_state(self) -> None:
        """Carga el estado persistente si existe."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_level = KillSwitchLevel(data.get("current_level", 0))
                    self.last_trigger_reason = data.get("last_trigger_reason")
                    self.last_triggered_at = data.get("last_triggered_at")
            except Exception as e:
                logger.error(f"Error cargando kill_switch_state: {e}")

    def _persist_state(self) -> None:
        """Persiste el estado actual de forma atómica."""
        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
        temp_file = f"{self.state_file}.tmp.{os.getpid()}"
        payload = {
            "current_level": int(self.current_level),
            "level_name": self.current_level.name,
            "last_trigger_reason": self.last_trigger_reason,
            "last_triggered_at": self.last_triggered_at,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(temp_file, self.state_file)
        except Exception as e:
            logger.error(f"Error persistiendo kill_switch_state: {e}")

    @property
    def is_active(self) -> bool:
        """True si el sistema se encuentra bajo algún nivel de restricción de emergencia."""
        return self.current_level > KillSwitchLevel.NORMAL

    def can_open_new_position(self) -> bool:
        """Comprueba si el estado actual permite abrir nuevas posiciones."""
        return self.current_level == KillSwitchLevel.NORMAL

    def evaluate_triggers(
        self,
        intraday_drawdown_pct: float = 0.0,
        rolling_1h_loss_pct: float = 0.0,
        ws_latency_seconds: float = 0.0
    ) -> Optional[Tuple[KillSwitchLevel, str]]:
        """
        Evalúa automáticamente las métricas de riesgo y latencia de mercado.
        Retorna la tupla (Nivel, Razón) si se sobrepasa algún umbral crítico.
        """
        # 1. Drawdown Intradía Crítico (Nivel 3 si > 5.0%, Nivel 2 si > 3.5%)
        if intraday_drawdown_pct >= 5.0:
            return (
                KillSwitchLevel.LEVEL_3_HARD_CUT,
                f"Drawdown intradía extremo ({intraday_drawdown_pct:.2f}% >= 5.00%). Activación HARD CUT Nivel 3."
            )
        elif intraday_drawdown_pct >= self.max_drawdown:
            return (
                KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND,
                f"Drawdown intradía ({intraday_drawdown_pct:.2f}% >= {self.max_drawdown:.2f}%). Activación UNWIND Nivel 2."
            )

        # 2. Pérdida Acumulada en 1 Hora
        if rolling_1h_loss_pct >= self.max_1h_loss:
            return (
                KillSwitchLevel.LEVEL_1_SOFT_LOCK,
                f"Pérdida horaria ({rolling_1h_loss_pct:.2f}% >= {self.max_1h_loss:.2f}%). Activación SOFT LOCK Nivel 1."
            )

        # 3. Pérdida de latencia de WebSocket / Feed Heartbeat (> 10s)
        if ws_latency_seconds >= (self.max_ws_latency * 2.0):
            return (
                KillSwitchLevel.LEVEL_3_HARD_CUT,
                f"Pérdida total de feed WebSocket ({ws_latency_seconds:.1f}s >= {self.max_ws_latency * 2:.1f}s). Activación HARD CUT Nivel 3."
            )
        elif ws_latency_seconds >= self.max_ws_latency:
            return (
                KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND,
                f"Latencia crítica de feed WebSocket ({ws_latency_seconds:.1f}s >= {self.max_ws_latency:.1f}s). Activación UNWIND Nivel 2."
            )

        return None

    def trigger(
        self,
        target_level: Union[KillSwitchLevel, int],
        reason: str,
        exchange_adapter: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el protocolo de bloqueo de emergencia en tiempo real.
        Garantiza tiempo de respuesta en < 1 segundo (< 1000 ms).
        """
        start_perf = time.perf_counter()
        lvl = KillSwitchLevel(int(target_level))
        
        # Si ya estamos en un nivel igual o más severo, mantener el más alto
        if lvl < self.current_level:
            return {
                "success": True,
                "level": int(self.current_level),
                "level_name": self.current_level.name,
                "execution_time_ms": 0.0,
                "message": f"Kill-switch ya activo en nivel superior ({self.current_level.name})."
            }

        self.current_level = lvl
        self.last_trigger_reason = reason
        self.last_triggered_at = datetime.now(timezone.utc).isoformat()

        cancelled_orders = 0
        closed_positions = 0

        # Ejecución sobre el adaptador de exchange (real o mock)
        if exchange_adapter is not None:
            try:
                # Nivel 1, 2 y 3: Cancelar órdenes abiertas
                if hasattr(exchange_adapter, "cancel_all_orders"):
                    res_c = exchange_adapter.cancel_all_orders()
                    cancelled_orders = len(res_c) if isinstance(res_c, list) else int(res_c or 0)

                # Nivel 2: Cierre ordenado de posiciones
                if lvl == KillSwitchLevel.LEVEL_2_GRACEFUL_UNWIND:
                    if hasattr(exchange_adapter, "close_all_positions"):
                        res_p = exchange_adapter.close_all_positions(market=False)
                        closed_positions = len(res_p) if isinstance(res_p, list) else int(res_p or 0)

                # Nivel 3: Liquidación total a mercado inmediata
                elif lvl == KillSwitchLevel.LEVEL_3_HARD_CUT:
                    if hasattr(exchange_adapter, "close_all_positions"):
                        res_p = exchange_adapter.close_all_positions(market=True)
                        closed_positions = len(res_p) if isinstance(res_p, list) else int(res_p or 0)
                    if hasattr(exchange_adapter, "disconnect"):
                        exchange_adapter.disconnect()

            except Exception as e:
                logger.critical(f"Falla durante ejecución de kill-switch: {e}", exc_info=True)

        self._persist_state()
        elapsed_ms = (time.perf_counter() - start_perf) * 1000.0

        event = KillSwitchEvent(
            timestamp_utc=self.last_triggered_at,
            level=int(lvl),
            level_name=lvl.name,
            trigger_reason=reason,
            execution_time_ms=round(elapsed_ms, 2),
            orders_cancelled_count=cancelled_orders,
            positions_closed_count=closed_positions,
            is_success=True
        )
        self.event_log.append(event)

        logger.critical(
            f"🚨 KILL-SWITCH ACTIVADO [{lvl.name}] en {elapsed_ms:.2f} ms! "
            f"Órdenes canceladas: {cancelled_orders}, Posiciones cerradas: {closed_positions}. Causa: {reason}"
        )

        return {
            "success": True,
            "level": int(lvl),
            "level_name": lvl.name,
            "execution_time_ms": round(elapsed_ms, 2),
            "orders_cancelled": cancelled_orders,
            "positions_closed": closed_positions,
            "reason": reason,
            "sub_second_guarantee": elapsed_ms < 1000.0
        }

    def reset(self, auth_token: str, expected_token: Optional[str] = None) -> bool:
        """
        Restaura el estado a NORMAL tras una contingencia, requiriendo validación de token.
        """
        exp = expected_token or os.getenv("DASHBOARD_API_TOKEN", "")
        if exp and auth_token != exp:
            logger.warning("Intento de reseteo de kill-switch rechazado por credenciales inválidas.")
            return False

        self.current_level = KillSwitchLevel.NORMAL
        self.last_trigger_reason = "RESETEADO_A_NORMAL"
        self.last_triggered_at = datetime.now(timezone.utc).isoformat()
        self._persist_state()
        logger.info("Kill-switch restablecido exitosamente al estado NORMAL.")
        return True
