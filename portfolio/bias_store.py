"""
portfolio/bias_store.py - Almacenamiento Atómico y Auditoría de Sesgo del Mercado (Sprint 37: PB-125).
Gestiona la persistencia segura de las autorizaciones directivas del Cerebro Lento,
con soporte multi-símbolo, control estricto de TTL y lecturas concurrentes libres de bloqueos.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from validation.schemas import MarketBiasSchema, MarketBiasPosture

try:
    from filelock import FileLock, Timeout
except ImportError:
    class FileLock:  # type: ignore
        def __init__(self, lock_file, timeout=None):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
    class Timeout(Exception):  # type: ignore
        pass

logger = logging.getLogger("BiasStore")


class BiasStore:
    """
    Repositorio atómico para autorizaciones y sesgos directivos emitidos por el Cerebro Lento.
    Permite que el Cerebro Rápido consulte en microsegundos si un par está autorizado para operar,
    protegido por FileLock para evitar WinError 32 y colisiones entre procesos.
    """

    DEFAULT_PATH = os.path.join("portfolio", "market_bias.json")
    DEFAULT_DB_PATH = os.path.join("portfolio", "alpha_factory.db")

    def __init__(self, filepath: Optional[str] = None, db_path: Optional[str] = None):
        self.filepath = filepath or self.DEFAULT_PATH
        self.lock_path = f"{self.filepath}.lock"
        self.db_path = db_path if db_path is not None else self.DEFAULT_DB_PATH

    def save_bias(self, bias: MarketBiasSchema) -> bool:
        """
        Persiste una autorización de forma atómica en el archivo JSON multi-símbolo.
        Garantiza que no existan lecturas concurrentes corruptas utilizando FileLock.
        """
        try:
            os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
            lock = FileLock(self.lock_path, timeout=5.0)

            with lock:
                existing_data: Dict[str, Any] = {}
                if os.path.exists(self.filepath):
                    try:
                        with open(self.filepath, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                    except Exception:
                        existing_data = {}

                if "biases" not in existing_data or not isinstance(existing_data["biases"], dict):
                    existing_data["biases"] = {}

                # Almacenar o actualizar el sesgo del símbolo
                symbol_key = bias.symbol.upper()
                existing_data["biases"][symbol_key] = bias.model_dump()
                existing_data["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

                # Escritura atómica vía archivo temporal y rename protegido
                temp_file = f"{self.filepath}.tmp.{os.getpid()}"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, indent=2)

                # Intentos de reemplazo ante bloqueos transitorios en Windows
                replaced = False
                for attempt in range(5):
                    try:
                        os.replace(temp_file, self.filepath)
                        replaced = True
                        break
                    except PermissionError:
                        import time
                        time.sleep(0.02 * (attempt + 1))

                if not replaced and os.path.exists(temp_file):
                    os.replace(temp_file, self.filepath)

            # Sincronización canónica en SQLite WAL (PB-139)
            if self.db_path:
                try:
                    from portfolio.db_schema import upsert_market_bias_db, init_alpha_factory_db
                    init_alpha_factory_db(self.db_path)
                    upsert_market_bias_db(
                        symbol=bias.symbol,
                        posture=bias.posture.value if hasattr(bias.posture, 'value') else str(bias.posture),
                        confidence=bias.confidence,
                        valid_until_utc=bias.valid_until_utc,
                        db_path=self.db_path
                    )
                except Exception as dbe:
                    logger.debug(f"Sync a SQLite no completada: {dbe}")

            logger.info(
                f"🎯 SESGO ACTUALIZADO [{bias.symbol}]: Postura={bias.posture.value}, "
                f"Confianza={bias.confidence:.1%}, Vence={bias.valid_until_utc}"
            )
            return True
        except Exception as e:
            logger.error(f"Error persistiendo sesgo en {self.filepath}: {e}", exc_info=True)
            return False

    def get_bias(self, symbol: str) -> Optional[MarketBiasSchema]:
        """Recupera la directiva activa de un símbolo validada con Pydantic."""
        if not os.path.exists(self.filepath):
            # Fallback a SQLite WAL si el archivo JSON no existe (PB-139)
            if self.db_path and os.path.exists(self.db_path):
                try:
                    from portfolio.db_schema import get_market_bias_db
                    row = get_market_bias_db(symbol, db_path=self.db_path)
                    if row:
                        return MarketBiasSchema(
                            symbol=row["symbol"],
                            posture=MarketBiasPosture(row["posture"]),
                            confidence=float(row["confidence"]),
                            consensus_score=float(row.get("consensus_score", row["confidence"])),
                            valid_until_utc=row["valid_until_utc"]
                        )
                except Exception as ex:
                    logger.debug(f"Error parseando fallback de SQLite: {ex}")
            return None

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            biases_dict = data.get("biases", {})
            symbol_key = symbol.upper()
            raw_bias = biases_dict.get(symbol_key)

            if not raw_bias:
                return None

            return MarketBiasSchema(**raw_bias)
        except Exception as e:
            logger.warning(f"No se pudo cargar sesgo para {symbol}: {e}")
            return None

    def get_all_biases(self) -> Dict[str, MarketBiasSchema]:
        """Retorna todos los sesgos almacenados."""
        if not os.path.exists(self.filepath):
            return {}

        result: Dict[str, MarketBiasSchema] = {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            biases_dict = data.get("biases", {})
            for sym, raw in biases_dict.items():
                try:
                    result[sym] = MarketBiasSchema(**raw)
                except Exception:
                    pass
        except Exception:
            pass
        return result

    def is_authorized(
        self,
        symbol: str,
        side: str = "LONG",
        min_confidence: float = 0.70,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Consulta rápida de autorización de alta velocidad para el Cerebro Rápido.
        Retorna (True, "AUTHORIZED") si se cumplen todas las condiciones, o (False, razón) si se deniega.
        """
        bias = self.get_bias(symbol)
        if bias is None:
            return False, f"NO_BIAS_REGISTERED: No hay directiva registrada para {symbol}"

        # 1. Comprobar caducidad temporal (TTL)
        now = current_time or datetime.now(timezone.utc)
        try:
            valid_until = datetime.fromisoformat(bias.valid_until_utc.replace("Z", "+00:00"))
            if now > valid_until:
                return False, f"BIAS_EXPIRED: La autorización expiró a las {bias.valid_until_utc} (actual: {now.isoformat()})"
        except Exception as e:
            return False, f"INVALID_EXPIRY_TIMESTAMP: {e}"

        # 2. Veto estricto por régimen adverso
        if bias.posture == MarketBiasPosture.STRICT_VETO:
            return False, f"STRICT_VETO: Régimen de alto riesgo/pánico vetó cualquier operación en {symbol}"

        # 3. Alineación de lado de la operación
        side_upper = side.upper()
        if side_upper in ("LONG", "BUY"):
            if bias.posture != MarketBiasPosture.ALLOW_LONG:
                return False, f"POSTURE_MISMATCH: Se solicitó LONG pero la postura es {bias.posture.value}"
        elif side_upper in ("SHORT", "SELL"):
            if bias.posture != MarketBiasPosture.ALLOW_SHORT:
                return False, f"POSTURE_MISMATCH: Se solicitó SHORT pero la postura es {bias.posture.value}"
        else:
            return False, f"INVALID_SIDE: Lado '{side}' no reconocido"

        # 4. Comprobación de umbral de convicción
        if bias.confidence < min_confidence:
            return False, f"INSUFFICIENT_CONFIDENCE: Confianza {bias.confidence:.1%} < umbral mínimo {min_confidence:.1%}"

        return True, "AUTHORIZED"

    def clear(self) -> None:
        """Limpia el almacén de sesgos y sus bloqueos (útil para tests)."""
        for p in (self.filepath, self.lock_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
