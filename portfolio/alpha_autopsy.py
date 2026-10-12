"""
Agente Forense de Autopsia de Alphas Cuantitativos (Alpha Autopsy Agent).
Sprint 2: Motor de Investigación Cuantitativa Aumentado por IA (US-2.5 y US-2.6).

Implementa:
- Diagnóstico causal y forense paso a paso cuando un factor o estrategia sufre decaimiento o ruptura de régimen.
- Extracción de causas raíz (volatilidad anómala, slippage excesivo, régimen tendencial vs lateral).
- Emisión de directivas y restricciones de búsqueda para la siguiente iteración de minería.
- Persistencia inmutable del historial de autopsias en JSON.
"""

import os
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from mining.llm_client import OpenRouterClient, OpenRouterModel
from portfolio.alpha_health_monitor import HealthReport, HealthStatus
from portfolio.atomic_io import atomic_write_json

logger = logging.getLogger("AlphaAutopsyAgent")


@dataclass
class AutopsyVerdict:
    """Dictamen forense detallado emitido por la IA para un factor degradado."""
    factor_id: str
    formula: str
    health_status: str
    diagnosis: str
    root_cause: str
    recommendation: str
    confidence_score: float
    suggested_actions: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlphaAutopsyAgent:
    """
    Agente cognitivo que realiza autopsias de factores cuantitativos que fallaron o decayeron.
    """

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        model: str = OpenRouterModel.DEEPSEEK_R1,
        history_path: str = "portfolio/autopsies.json"
    ):
        self.client = client or OpenRouterClient()
        self.model = model
        self.history_path = history_path
        self.autopsy_records: List[AutopsyVerdict] = []
        self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.autopsy_records = [AutopsyVerdict(**item) for item in data]
            except Exception as e:
                logger.warning(f"No se pudo cargar historial de autopsias previo: {e}")

    def save_history(self):
        atomic_write_json(self.history_path, [asdict(item) for item in self.autopsy_records])

    def conduct_autopsy(
        self,
        factor_id: str,
        formula: str,
        health_report: HealthReport,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> AutopsyVerdict:
        """
        Ejecuta el análisis forense estructurado enviando el reporte a OpenRouter.
        """
        metrics = additional_metrics or {}

        system_prompt = (
            "Eres un Chief Risk Officer y Especialista Forense en Estrategias Cuantitativas de Trading. "
            "Tu objetivo es realizar una autopsia rigurosa a un factor o estrategia algorítmica que "
            "ha sufrido degradación o quiebre estructural de rendimiento."
        )

        user_prompt = f"""
        Identificador del Factor: {factor_id}
        Fórmula Simbólica: {formula}
        Estado de Salud Diagnosticado: {health_report.status.value}
        Mensaje del Monitor: {health_report.message}
        Information Coefficient (IC) Rodante: {health_report.rolling_ic:.4f} (p-valor: {health_report.ic_pvalue:.4f})
        Information Ratio del IC (IC_IR): {health_report.ic_ir:.2f}
        Alerta de Quiebre CUSUM: {health_report.cusum_detected} (Estadístico: {health_report.cusum_stat:.2f})
        Alerta de Data Drift (KS-Test): {health_report.drift_detected} (p-valor: {health_report.ks_pvalue:.4f})
        Métricas de microestructura adicionales: {metrics}

        Genera una autopsia forense estricta respondiendo ÚNICAMENTE un objeto JSON con los siguientes campos:
        {{
            "diagnosis": "Título breve del diagnóstico (ej. ALPHA_DECAY_VOLATILITY_COMPRESSION)",
            "root_cause": "Explicación detallada de la causa raíz que invalidó el factor",
            "recommendation": "Recomendaciones precisas sobre qué variables/features evitar y cuáles buscar",
            "confidence_score": 0.90,
            "suggested_actions": ["ISOLATE_FACTOR", "REDUCE_WEIGHT_TO_ZERO", "SEARCH_NEW_ALPHA"]
        }}
        """

        response = self.client.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=0.2,
            json_mode=True
        )

        verdict = AutopsyVerdict(
            factor_id=factor_id,
            formula=formula,
            health_status=health_report.status.value,
            diagnosis=response.get("diagnosis", "DESCONOCIDO"),
            root_cause=response.get("root_cause", "Degradación estadística de señal detectada."),
            recommendation=response.get("recommendation", "Poner en cuarentena y buscar reemplazos."),
            confidence_score=float(response.get("confidence_score", 0.85)),
            suggested_actions=response.get("suggested_actions", ["QUARANTINE"])
        )

        self.autopsy_records.append(verdict)
        self.save_history()
        logger.info(f"Autopsia completada para {factor_id}: {verdict.diagnosis}")
        return verdict
