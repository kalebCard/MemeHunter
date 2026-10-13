"""
validation/ai_output_guard.py - Validador de Esquema de Salida de IA (Sprint 39: PB-129).
Actúa como aduana estricta de salida para respuestas de LLMs y agentes.
Extrae el bloque JSON descartando alucinaciones, texto libre o campos no contemplados (extra='forbid').
Si la salida es inválida, la descarta silenciosamente con un fallback seguro.
"""

import json
import re
import logging
from typing import Dict, Any, Tuple, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from validation.schemas import (
    AISentimentOutputSchema,
    AIOrderAuthorizationOutputSchema,
    MarketBiasPosture
)

logger = logging.getLogger("AIOutputGuard")
T = TypeVar("T", bound=BaseModel)


class AIOutputGuard:
    """
    Guardián de Salida de Modelos de Inteligencia Artificial.
    Evita que texto alucinado o parámetros manipulados alcancen la capa de ejecución.
    """

    def __init__(self):
        self.rejection_count: int = 0
        self.approved_count: int = 0
        self.violations_log: list = []

    @staticmethod
    def extract_json_payload(raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Extrae de forma robusta el primer objeto JSON válido de un bloque de texto,
        manejando markdown (```json ... ```) o texto conversacional.
        """
        if not raw_text or not isinstance(raw_text, str):
            return None

        text = raw_text.strip()

        # 1. Intento directo si es JSON puro
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 2. Buscar bloques ```json ... ```
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_block_match:
            try:
                parsed = json.loads(json_block_match.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        # 3. Buscar cualquier par de llaves { ... }
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return None

    def validate_sentiment_output(
        self,
        raw_output: str,
        fallback_sentiment: float = 0.0,
        fallback_confidence: float = 0.30
    ) -> Tuple[bool, AISentimentOutputSchema, str]:
        """
        Valida la respuesta de sentimiento de un LLM.
        Si falla o alucina campos ajenos, retorna el fallback neutral seguro.
        """
        payload = self.extract_json_payload(raw_output)
        if payload is None:
            self.rejection_count += 1
            reason = "PAYLOAD_EXTRACT_FAILED: No se encontró ningún JSON válido en la respuesta del modelo"
            self._record_violation(raw_output, reason)
            fallback = AISentimentOutputSchema(
                sentiment=fallback_sentiment,
                confidence=fallback_confidence,
                key_catalyst="FALLBACK_DUE_TO_JSON_PARSE_ERROR"
            )
            return False, fallback, reason

        try:
            validated = AISentimentOutputSchema(**payload)
            self.approved_count += 1
            return True, validated, "OK"
        except ValidationError as e:
            self.rejection_count += 1
            reason = f"SCHEMA_VALIDATION_ERROR: {e}"
            self._record_violation(raw_output, reason)
            fallback = AISentimentOutputSchema(
                sentiment=fallback_sentiment,
                confidence=fallback_confidence,
                key_catalyst="FALLBACK_DUE_TO_SCHEMA_VIOLATION"
            )
            return False, fallback, reason

    def validate_authorization_output(
        self,
        raw_output: str,
        fallback_posture: MarketBiasPosture = MarketBiasPosture.NEUTRAL_HOLD
    ) -> Tuple[bool, AIOrderAuthorizationOutputSchema, str]:
        """
        Valida una propuesta de autorización de un agente.
        Si la IA intenta colocar una orden o campos no permitidos, descarta la señal.
        """
        payload = self.extract_json_payload(raw_output)
        if payload is None:
            self.rejection_count += 1
            reason = "PAYLOAD_EXTRACT_FAILED: No se encontró JSON válido de autorización"
            self._record_violation(raw_output, reason)
            fallback = AIOrderAuthorizationOutputSchema(
                action=fallback_posture,
                confidence=0.0,
                reasoning_summary="Fallback seguro: JSON inválido descartado."
            )
            return False, fallback, reason

        try:
            validated = AIOrderAuthorizationOutputSchema(**payload)
            self.approved_count += 1
            return True, validated, "OK"
        except ValidationError as e:
            self.rejection_count += 1
            reason = f"AUTHORIZATION_SCHEMA_ERROR: {e}"
            self._record_violation(raw_output, reason)
            fallback = AIOrderAuthorizationOutputSchema(
                action=fallback_posture,
                confidence=0.0,
                reasoning_summary=f"Fallback seguro: {reason[:100]}"
            )
            return False, fallback, reason

    def _record_violation(self, raw_snippet: str, reason: str) -> None:
        snippet = (raw_snippet[:120] + "...") if len(raw_snippet) > 120 else raw_snippet
        entry = {
            "snippet": snippet,
            "reason": reason
        }
        self.violations_log.append(entry)
        if len(self.violations_log) > 50:
            self.violations_log.pop(0)
        logger.warning(f"🚨 GUARDIA DE SALIDA IA RECHAZÓ SALIDA: {reason}")
