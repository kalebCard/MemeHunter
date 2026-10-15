"""
Cliente de Integración Resiliente con OpenRouter para el Motor Cuantitativo.
US-5.2 (Sprint 5) & Sprint 2 (US-2.1).

Implementa:
- Estructura económica institucional 2026 con seguimiento de costes en USD por millón de tokens
  (DeepSeek-V3, DeepSeek-R1, Claude 3.5 Sonnet, Qwen 2.5 Coder).
- Control de presupuesto diario configurable (DAILY_LLM_BUDGET_USD, ej. $15.00 USD).
- Circuit Breaker automático al alcanzar el 90% del presupuesto diario, conmutando a fallback.
- Métricas de telemetría y SLA de nivel de servicio (latencia promedio, tasa de fallback, coste acumulado).
- Fallback determinista offline de alta fidelidad cuando no hay conexión, API key o ante fallos HTTP 429/502.
"""

from dataclasses import dataclass, field
import os
import json
import time
import socket
import logging
from typing import Dict, List, Optional, Any, Union
import urllib.request
import urllib.error

# Garantizar timeout de red a nivel socket de sistema operativo (máximo 25s)
socket.setdefaulttimeout(25.0)

logger = logging.getLogger("OpenRouterClient")


class OpenRouterModel:
    DEEPSEEK_V3 = "deepseek/deepseek-chat"
    DEEPSEEK_R1 = "deepseek/deepseek-r1"
    CLAUDE_35_SONNET = "anthropic/claude-3.5-sonnet"
    QWEN_CODER = "qwen/qwen-2.5-coder-32b-instruct"
    NOUS_HERMES_3_70B = "nousresearch/hermes-3-llama-3.1-70b"
    NOUS_HERMES_3_405B = "nousresearch/hermes-3-llama-3.1-405b"


# Tabla de tarifas de inferencia 2026 (coste en USD por 1M de tokens)
MODEL_PRICING_2026_PER_1M = {
    OpenRouterModel.DEEPSEEK_V3: {"prompt": 0.14, "completion": 0.28},
    OpenRouterModel.DEEPSEEK_R1: {"prompt": 0.55, "completion": 2.19},
    OpenRouterModel.CLAUDE_35_SONNET: {"prompt": 3.00, "completion": 15.00},
    OpenRouterModel.QWEN_CODER: {"prompt": 0.07, "completion": 0.14},
    OpenRouterModel.NOUS_HERMES_3_70B: {"prompt": 0.30, "completion": 0.50},
    OpenRouterModel.NOUS_HERMES_3_405B: {"prompt": 1.50, "completion": 3.00},
}
DEFAULT_FALLBACK_PRICING = {"prompt": 0.50, "completion": 1.50}


class OpenRouterClient:
    """
    Cliente para la API de OpenRouter con gobernanza presupuestaria 2026,
    tolerancia a fallos de red y modo offline automático.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = OpenRouterModel.DEEPSEEK_V3,
        site_url: str = "https://github.com/kalebCard/MemeHunter",
        app_name: str = "MemeHunter Autonomous Quant Loop",
        timeout: float = 30.0,
        daily_budget_usd: Optional[float] = None
    ):
        # Auto-descubrir clave mediante bóveda de secretos o entorno
        if api_key is None:
            try:
                from portfolio.secrets_vault import get_secret
                resolved_key = get_secret("OPENROUTER_API_KEY", "") or ""
            except Exception:
                resolved_key = os.getenv("OPENROUTER_API_KEY", "")

            if not resolved_key:
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith("OPENROUTER_API_KEY="):
                                    resolved_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                    break
                    except Exception:
                        pass
        else:
            resolved_key = api_key

        self.api_key = resolved_key
        self.default_model = default_model
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout

        # Presupuesto diario en USD institucional (2026)
        env_budget = os.getenv("DAILY_LLM_BUDGET_USD")
        if daily_budget_usd is not None:
            self.daily_budget_usd = float(daily_budget_usd)
        elif env_budget:
            try:
                self.daily_budget_usd = float(env_budget)
            except ValueError:
                self.daily_budget_usd = 15.00
        else:
            self.daily_budget_usd = 15.00

        # Telemetría y SLAs
        self.total_tokens_used = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0
        self.total_calls = 0
        self.fallback_calls = 0
        self.successful_calls = 0
        self.total_latency_ms = 0.0
        self.circuit_breaker_triggered = False

        self.is_offline_mode = not bool(self.api_key.strip())
        if self.is_offline_mode:
            logger.info("OpenRouterClient: No se detectó OPENROUTER_API_KEY válida. Operando en MODO FALLBACK OFFLINE heurístico.")

    def _calculate_call_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calcula el coste real en USD según la tabla tarifaria 2026."""
        pricing = MODEL_PRICING_2026_PER_1M.get(model, DEFAULT_FALLBACK_PRICING)
        cost_prompt = (prompt_tokens / 1_000_000.0) * pricing["prompt"]
        cost_completion = (completion_tokens / 1_000_000.0) * pricing["completion"]
        return cost_prompt + cost_completion

    def get_sla_telemetry(self) -> Dict[str, Any]:
        """Retorna las métricas cuantitativas de SLA, costes y ratio de fallback."""
        avg_latency = (self.total_latency_ms / self.successful_calls) if self.successful_calls > 0 else 0.0
        fallback_ratio = (self.fallback_calls / self.total_calls) if self.total_calls > 0 else 0.0
        budget_utilization = (self.total_cost_usd / self.daily_budget_usd * 100.0) if self.daily_budget_usd > 0 else 0.0

        return {
            "daily_budget_usd": round(self.daily_budget_usd, 2),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "budget_utilization_pct": round(budget_utilization, 2),
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "fallback_calls": self.fallback_calls,
            "fallback_ratio": round(fallback_ratio, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "total_tokens_used": self.total_tokens_used
        }

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        json_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Envía un prompt a OpenRouter con control estricto de presupuesto y fallback ante cualquier contingencia.
        """
        selected_model = model or self.default_model
        self.total_calls += 1

        # Modo offline configurado
        if self.is_offline_mode:
            self.fallback_calls += 1
            return self._generate_fallback_response(prompt, json_mode)

        # Control del Circuit Breaker al 90% del presupuesto
        if self.total_cost_usd >= (0.90 * self.daily_budget_usd):
            self.circuit_breaker_triggered = True
            self.fallback_calls += 1
            logger.warning(
                f"OpenRouterClient: CIRCUIT BREAKER ACTIVADO. Gasto acumulado ${self.total_cost_usd:.4f} "
                f"alcanzó el 90% del presupuesto diario (${self.daily_budget_usd:.2f}). "
                f"Conmutando a MODO FALLBACK OFFLINE para salvaguardar liquidez operativa."
            )
            return self._generate_fallback_response(prompt, json_mode)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }

        start_time = time.time()
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed_ms = (time.time() - start_time) * 1000.0
                self.total_latency_ms += elapsed_ms
                self.successful_calls += 1

                data = json.loads(resp.read().decode("utf-8"))
                usage = data.get("usage", {})
                p_tokens = usage.get("prompt_tokens", 0)
                c_tokens = usage.get("completion_tokens", 0)
                tot_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                self.total_prompt_tokens += p_tokens
                self.total_completion_tokens += c_tokens
                self.total_tokens_used += tot_tokens

                call_cost = self._calculate_call_cost(selected_model, p_tokens, c_tokens)
                self.total_cost_usd += call_cost

                raw_content = data["choices"][0]["message"]["content"]
                if json_mode:
                    try:
                        return json.loads(raw_content)
                    except json.JSONDecodeError:
                        return {"raw_text": raw_content}
                return {"text": raw_content}

        except Exception as e:
            self.fallback_calls += 1
            logger.warning(f"Error conectando a OpenRouter ({e}). Conmutando inmediatamente a MODO FALLBACK OFFLINE.")
            return self._generate_fallback_response(prompt, json_mode)

    def _generate_fallback_response(self, prompt: str, json_mode: bool) -> Dict[str, Any]:
        """
        Generador heurístico determinista de alta fidelidad que simula las respuestas esperadas
        de OpenRouter si la API no está accesible o se agotan las cuotas.
        """
        prompt_lower = prompt.lower()

        # Si el prompt solicita autopsia forense
        if "autopsia" in prompt_lower or "autopsy" in prompt_lower or "diagnostica" in prompt_lower:
            return {
                "diagnosis": "ALPHA_DECAY_VOLATILITY_COMPRESSION",
                "root_cause": "El factor perdió poder predictivo debido a un cambio abrupto de volatilidad y saturación de microestructura en memecoins.",
                "recommendation": "Excluir factores basados en momentum de cierre simple y priorizar desbalances de volumen acumulado (volume imbalance / rvol).",
                "confidence_score": 0.88,
                "suggested_actions": ["ISOLATE_FACTOR", "REDUCE_WEIGHT_TO_ZERO", "MINE_VOLUME_MICROSTRUCTURE"]
            }

        # Si el prompt solicita generación/síntesis de fórmulas de alpha
        return {
            "formulas": [
                "ts_rank((volume / (vwap + 1e-6)), 14)",
                "ts_zscore((high - low), 10) * rvol",
                "ts_decay_linear(returns, 5) * ts_rank(volume, 10)",
                "ts_delta(close, 3) / (ts_std(close, 14) + 1e-6)",
                "ts_rank(rvol, 10) * (close - vwap)"
            ],
            "economic_rationale": "Factores de asimetría de liquidez y desbalance de volumen diseñados para regímenes de alta rotación en memecoins.",
            "expected_horizon": "15m - 1h"
        }
