"""
portfolio/execution_gatekeeper.py - Interceptor de Broker y Guardián Inquebrantable de Ejecución (Sprint 39: PB-130).
Bloqueador final posicionado justo antes de la conexión física con la API del broker/exchange.
Impone las reglas inquebrantables de gestión de capital:
1. Corte inmediato ante drawdown intradía (Kill Switch Nivel 1, 2 o 3).
2. Límite rígido de posiciones simultáneas (slots concurrentes).
3. Inclusión OBLIGATORIA de stop-loss en código en cada orden enviada.
4. Cumplimiento de Min Notional de Binance ($5 USDT).
"""

from typing import Dict, Any, Tuple, Optional
import logging

from portfolio.kill_switch import EmergencyKillSwitch, KillSwitchLevel

logger = logging.getLogger("ExecutionGatekeeper")


class ExecutionGatekeeper:
    """
    Guardián final de salida hacia el exchange.
    Ninguna orden llega al broker sin la aprobación estricta de este módulo.
    """

    def __init__(
        self,
        kill_switch: Optional[EmergencyKillSwitch] = None,
        max_concurrent_slots: int = 3,       # 3 slots para Spot (100 USDT)
        min_notional_usdt: float = 5.0,      # Mínimo absoluto de Binance
        max_stoploss_pct: float = -0.010,    # Stoploss mínimo obligatorio (-1.0%)
        min_stoploss_pct: float = -0.100     # Stoploss máximo tolerable (-10.0%)
    ):
        self.kill_switch = kill_switch or EmergencyKillSwitch()
        self.max_slots = int(max_concurrent_slots)
        self.min_notional = float(min_notional_usdt)
        self.max_stoploss_pct = float(max_stoploss_pct)  # ej. -0.010 (-1%)
        self.min_stoploss_pct = float(min_stoploss_pct)  # ej. -0.100 (-10%)
        self.rejected_orders_count: int = 0
        self.approved_orders_count: int = 0

    def intercept_order(
        self,
        symbol: str,
        side: str,
        order_size_usdt: float,
        price: float,
        stoploss_pct: Optional[float],
        current_open_trades: int = 0,
        intraday_drawdown_pct: float = 0.0,
        rolling_1h_loss_pct: float = 0.0,
        exchange_adapter: Optional[Any] = None
    ) -> Tuple[bool, str]:
        """
        Audita una orden antes de enviarla a la API del broker.
        Retorna (True, 'APPROVED_FOR_DISPATCH') o (False, razón_del_bloqueo).
        """
        side_lower = side.lower()

        # REGLA 1: Evaluación Automática del Kill Switch
        trigger = self.kill_switch.evaluate_triggers(
            intraday_drawdown_pct=intraday_drawdown_pct,
            rolling_1h_loss_pct=rolling_1h_loss_pct
        )
        if trigger is not None:
            lvl, reason_trigger = trigger
            self.kill_switch.trigger(
                target_level=lvl,
                reason=reason_trigger,
                exchange_adapter=exchange_adapter
            )

        if not self.kill_switch.can_open_new_position() and side_lower in ("buy", "entry_long"):
            self.rejected_orders_count += 1
            reason = (
                f"KILL_SWITCH_ACTIVE: Bloqueo de emergencia activo en nivel "
                f"'{self.kill_switch.current_level.name}'. Motivo: {self.kill_switch.last_trigger_reason}"
            )
            logger.critical(f"🛑 ORDEN RECHAZADA POR KILL SWITCH: {reason}")
            return False, reason

        # REGLA 2: Límite Máximo de Operaciones Simultáneas (Slots Concurrentes)
        if side_lower in ("buy", "entry_long") and current_open_trades >= self.max_slots:
            self.rejected_orders_count += 1
            reason = (
                f"MAX_SLOTS_REACHED: Se alcanzó el límite de {self.max_slots} operaciones concurrentes "
                f"(actuales: {current_open_trades}). Nueva orden bloqueada para blindar capital."
            )
            logger.warning(f"⚠️ ORDEN RECHAZADA: {reason}")
            return False, reason

        # REGLA 3: Inclusión OBLIGATORIA de Stop-Loss en Código
        if side_lower in ("buy", "entry_long"):
            if stoploss_pct is None:
                self.rejected_orders_count += 1
                reason = "MANDATORY_STOPLOSS_MISSING: La orden carece de stop-loss obligatorio en código."
                logger.critical(f"🚨 ORDEN RECHAZADA: {reason}")
                return False, reason

            sl = float(stoploss_pct)
            # El stoploss debe ser estrictamente negativo (ej. -0.030)
            if sl >= 0.0:
                self.rejected_orders_count += 1
                reason = f"INVALID_STOPLOSS: Stop-loss ({sl}) debe ser un porcentaje negativo."
                logger.critical(f"🚨 ORDEN RECHAZADA: {reason}")
                return False, reason

            # El stoploss debe estar entre el límite ceñido y el de emergencia (ej. entre -1% y -10%)
            if sl > self.max_stoploss_pct or sl < self.min_stoploss_pct:
                self.rejected_orders_count += 1
                reason = (
                    f"STOPLOSS_OUT_OF_BOUNDS: Stop-loss ({sl:.2%}) fuera de rango permitido "
                    f"[{self.min_stoploss_pct:.1%}, {self.max_stoploss_pct:.1%}]."
                )
                logger.critical(f"🚨 ORDEN RECHAZADA: {reason}")
                return False, reason

        # REGLA 4: Validación de Min Notional y Parámetros Numéricos
        if order_size_usdt < self.min_notional:
            self.rejected_orders_count += 1
            reason = (
                f"MIN_NOTIONAL_VIOLATION: Tamaño (${order_size_usdt:.2f}) inferior al mínimo de Binance "
                f"(${self.min_notional:.2f} USDT)."
            )
            return False, reason

        if price <= 0.0:
            self.rejected_orders_count += 1
            return False, "INVALID_PRICE: El precio debe ser estrictamente positivo."

        # Todo aprobado: La orden puede transmitirse al exchange
        self.approved_orders_count += 1
        logger.info(
            f"✅ ORDEN APROBADA [{symbol} {side.upper()}]: Notional=${order_size_usdt:.2f}, "
            f"Price=${price:.6f}, SL={stoploss_pct}"
        )
        return True, "APPROVED_FOR_DISPATCH"
