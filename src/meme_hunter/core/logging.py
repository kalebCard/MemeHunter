"""
meme_hunter.core.logging - Trazabilidad y Logging JSON Estructurado con Correlation IDs (Sprint 55: PB-218).

Implementa:
- Formateo de logs JSON estructurados para ingestión en SIEM, Datadog y CloudWatch.
- Correlation IDs contextuales asíncronos vía ContextVars (viajan de FastAPI / Telegram a CCXT).
- Manejo thread-safe y coroutine-safe del contexto de trazabilidad distribuida.
"""

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ContextVar para aislamiento estricto por hilo y corrutina asyncio
CORRELATION_ID_CTX: ContextVar[str] = ContextVar("correlation_id", default="MH-SYS-CORE")


def generate_correlation_id(prefix: str = "MH") -> str:
    """Genera un identificador de correlación criptográficamente aleatorio y conciso."""
    short_uuid = uuid.uuid4().hex[:12]
    return f"{prefix}-{short_uuid}"


def get_correlation_id() -> str:
    """Recupera el correlation ID activo en el contexto actual."""
    return CORRELATION_ID_CTX.get()


def set_correlation_id(correlation_id: str) -> None:
    """Establece el correlation ID para el contexto de ejecución actual."""
    CORRELATION_ID_CTX.set(correlation_id)


class StructuredJsonFormatter(logging.Formatter):
    """
    Formateador de logs que serializa cada registro en formato JSON estandarizado
    incluyendo correlation_id, timestamp ISO8601 UTC, logger y nivel de severidad.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": get_correlation_id(),
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Adjuntar metadatos adicionales si están presentes en record
        if hasattr(record, "symbol"):
            log_payload["symbol"] = getattr(record, "symbol")
        if hasattr(record, "order_id"):
            log_payload["order_id"] = getattr(record, "order_id")
        if hasattr(record, "latency_ms"):
            log_payload["latency_ms"] = getattr(record, "latency_ms")

        # Serializar excepciones si existen
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, ensure_ascii=False)


class CorrelationIdAdapter(logging.LoggerAdapter):
    """Adaptador de logger que inyecta automáticamente el correlation ID activo."""

    def process(self, msg: str, kwargs: Any) -> tuple:
        extra = kwargs.setdefault("extra", {})
        extra["correlation_id"] = get_correlation_id()
        return msg, kwargs


def get_logger(name: str) -> CorrelationIdAdapter:
    """Obtiene un logger envuelto con el adaptador de correlation ID."""
    raw_logger = logging.getLogger(name)
    return CorrelationIdAdapter(raw_logger, {})


def configure_structured_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configura el manejador raíz de logs.
    Si json_format=True, usa StructuredJsonFormatter. De lo contrario, texto estándar.
    """
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Evitar duplicar handlers existentes
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s [%(correlation_id)s]: %(message)s"
        class PlainWithCorrelation(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                if not hasattr(record, "correlation_id"):
                    record.correlation_id = get_correlation_id()
                return super().format(record)
        handler.setFormatter(PlainWithCorrelation(fmt))

    root_logger.addHandler(handler)


__all__ = [
    "CORRELATION_ID_CTX",
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
    "StructuredJsonFormatter",
    "CorrelationIdAdapter",
    "get_logger",
    "configure_structured_logging",
]
