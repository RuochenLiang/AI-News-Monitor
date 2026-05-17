from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

import httpx

from src.diagnostics import (
    DiagnosticResult,
    classify_llm_http_error,
    diagnostic_error,
    diagnostic_ok,
    invalid_url_result,
    is_valid_http_url,
    missing_required_result,
)
from src.models import Article, LLMAnalysis, LLMSettings, MarketWatchSuggestion, TopicConfig
from src.secrets import get_env_secret, sanitize_for_log
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)

VALID_DIRECTIONS = {"bullish", "bearish", "mixed", "unclear"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_RELIABILITY = {"low", "medium", "high"}
VALID_ACTIONS = {"watch_only", "research_further", "urgent_review", "ignore"}


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: LLMSettings, api_key: str | None = None, client: httpx.Client | None = None):
        self.settings = settings
        self.api_key = api_key if api_key is not None else get_env_secret(settings.api_key_env)
        self.client = client

    def test(self) -> bool:
        diagnostic = self.diagnose()
        if not diagnostic.ok:
            raise LLMError(diagnostic.message)
        return True

    def diagnose(self) -> DiagnosticResult:
        required_fields = ["provider", "base_url", "model", "api_key"]
        missing = []
        if not self.settings.provider:
            missing.append("provider")
        if not self.settings.base_url:
            missing.append("base_url")
        if not self.settings.model:
            missing.append("model")
        if not self.api_key:
            missing.append("api_key")
        if missing:
            if missing == ["api_key"]:
                return diagnostic_error(
                    "llm",
                    "missing_required_field",
                    "LLM API key is missing.",
                    missing_fields=missing,
                    required_fields=required_fields,
                    configured=False,
                )
            return missing_required_result("llm", missing, required_fields=required_fields)
        if self.settings.provider != "openai_compatible":
            return diagnostic_error(
                "llm",
                "unsupported_model_api",
                "Only OpenAI-compatible chat completions are supported.",
                required_fields=required_fields,
            )
        if not is_valid_http_url(self.settings.base_url):
            return invalid_url_result("llm", self.settings.base_url, required_fields=required_fields)

        started = perf_counter()
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.settings.timeout_seconds)
        details: dict[str, Any] = {}
        try:
            model_ids = self._fetch_model_ids(client)
            if model_ids:
                details["available_models_sample"] = model_ids[:20]
                if self.settings.model not in model_ids:
                    return diagnostic_error(
                        "llm",
                        "model_not_found",
                        f"Model '{self.settings.model}' was not returned by the provider models endpoint.",
                        suggested_fix="Use one of the available models or check the provider account permissions.",
                        required_fields=required_fields,
                        latency_ms=_latency_ms(started),
                        details=details,
                    )
            elif model_ids == []:
                details["models_endpoint"] = "empty"
            else:
                details["models_endpoint"] = "not_available"

            response = request_with_retries(
                client,
                "POST",
                self._chat_url(),
                headers=self._headers(),
                json=self._test_chat_body(),
            )
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            if not str(content).strip():
                return diagnostic_error(
                    "llm",
                    "unsupported_model_api",
                    "LLM response did not contain chat content.",
                    required_fields=required_fields,
                    latency_ms=_latency_ms(started),
                    details=details,
                )
            details["chat_endpoint"] = "ok"
            return diagnostic_ok(
                "llm",
                "LLM connection test succeeded.",
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details=details,
            )
        except httpx.HTTPError as exc:
            category = classify_llm_http_error(exc)
            return diagnostic_error(
                "llm",
                category,
                _llm_error_message(category),
                technical_detail=exc,
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details=details,
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return diagnostic_error(
                "llm",
                "unsupported_model_api",
                "LLM response did not match the expected OpenAI-compatible chat format.",
                technical_detail=exc,
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details=details,
            )
        finally:
            if close_client:
                client.close()

    def _fetch_model_ids(self, client: httpx.Client) -> list[str] | None:
        try:
            response = request_with_retries(
                client, "GET", self.settings.base_url.rstrip("/") + "/models", headers=self._headers()
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 405}:
                return None
            raise
        payload = response.json()
        data = payload.get("data", [])
        if not isinstance(data, list):
            return None
        model_ids = [str(item.get("id", "")) for item in data if isinstance(item, dict) and item.get("id")]
        return model_ids

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _chat_url(self) -> str:
        return self.settings.base_url.rstrip("/") + "/chat/completions"

    def _test_chat_body(self) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": '{"ping":"pong"}'},
        ]
        return {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "presence_penalty": self.settings.presence_penalty,
            **_token_limit_payload(self.settings.model, 64),
            "response_format": {"type": "json_object"},
        }

    def analyze_article(self, topic: TopicConfig, article: Article) -> LLMAnalysis:
        if not self.api_key:
            raise LLMError("LLM API key is missing.")
        messages = self._build_messages(topic, article)
        content = ""
        try:
            content = self._chat(messages)
            return parse_llm_analysis(content)
        except (LLMError, ValueError) as first_error:
            logger.warning("LLM returned invalid JSON, trying repair once: %s", first_error)
            repair_messages = [
                {
                    "role": "system",
                    "content": "You repair model output into strict JSON matching the requested schema. Return JSON only.",
                },
                {
                    "role": "user",
                    "content": (
                        "Repair this output into valid JSON for the AI News Monitor schema. "
                        f"Invalid output: {content}\nError: {first_error}"
                    ),
                },
            ]
            content = self._chat(repair_messages)
            return parse_llm_analysis(content)

    def translate_and_summarize(self, article: Article, target_language: str) -> dict[str, str]:
        if not self.api_key:
            raise LLMError("LLM API key is missing.")
        schema = {"translated_title": "", "translated_snippet": "", "summary": ""}
        messages = [
            {
                "role": "system",
                "content": (
                    "Translate and summarize news article metadata. Preserve factual meaning, "
                    "do not add facts, and return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "target_language": target_language,
                        "source_language": article.language,
                        "title": article.title,
                        "snippet": article.snippet,
                        "required_schema": schema,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        data = _json_from_text(self._chat(messages, max_tokens=512))
        return {key: str(data.get(key, "")) for key in schema}

    def _build_messages(self, topic: TopicConfig, article: Article) -> list[dict[str, str]]:
        article_payload = {
            "title": article.title,
            "snippet": article.snippet,
            "source": article.source,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "url": article.url,
            "language": article.language,
            "translated_title": article.translated_title,
            "translated_snippet": article.translated_snippet,
            "short_summary": article.short_summary,
            "source_reliability_score": article.reliability_score,
            "source_ownership": article.ownership,
            "source_bias_hint": article.bias_hint,
            "ranking_score": article.ranking_score,
            "bias_context": (article.raw or {}).get("bias_summary") if article.raw else None,
        }
        schema = {
            "relevance_score": 0,
            "is_actionable_alert": False,
            "event_type": "",
            "summary": "",
            "why_it_matters": "",
            "market_watch_suggestions": [
                {
                    "ticker": "",
                    "name_or_theme": "",
                    "possible_direction": "bullish|bearish|mixed|unclear",
                    "reason": "",
                    "confidence": "low|medium|high",
                }
            ],
            "bullish_path": "",
            "bearish_path": "",
            "risk_notes": "",
            "uncertainty_notes": "",
            "source_reliability": "low|medium|high",
            "recommended_user_action": "watch_only|research_further|urgent_review|ignore",
            "notification_title": "",
        }
        system = (
            "You are an AI news monitoring analyst. Use only the provided article content and links. "
            "Do not fabricate facts. If information is incomplete, state uncertainty. "
            "Do not provide personalized financial advice. Return strict JSON only."
        )
        user = {
            "topic_prompt": topic.prompt,
            "output_language": topic.output_language,
            "keywords": topic.keywords,
            "related_stock_watchlist_candidates": topic.related_stocks,
            "article": article_payload,
            "required_schema": schema,
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ]

    def _chat(self, messages: list[dict[str, str]], max_tokens: int | None = None) -> str:
        body = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "presence_penalty": self.settings.presence_penalty,
            **_token_limit_payload(self.settings.model, max_tokens or self.settings.max_tokens),
            "response_format": {"type": "json_object"},
        }
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.settings.timeout_seconds)
        try:
            response = request_with_retries(client, "POST", self._chat_url(), headers=self._headers(), json=body)
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise LLMError("LLM request timed out.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {sanitize_for_log(exc)}") from exc
        finally:
            if close_client:
                client.close()
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM response did not contain chat content.") from exc


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _token_limit_payload(model: str, max_tokens: int) -> dict[str, int]:
    if model.strip().casefold().startswith("gpt-5"):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


def _llm_error_message(category: str) -> str:
    return {
        "missing_required_field": "LLM settings are missing required fields.",
        "invalid_url": "LLM base URL is invalid.",
        "invalid_api_key": "LLM API key was rejected by the provider.",
        "model_not_found": "LLM model was not found by the provider.",
        "unsupported_model_api": "LLM provider does not support the expected chat completions API.",
        "base_url_unreachable": "LLM base URL is unreachable.",
        "api_auth_failed": "LLM authentication failed.",
        "api_rate_limited": "LLM provider rate limit was reached.",
        "api_timeout": "LLM request timed out.",
        "tls_or_certificate_error": "LLM request failed because of a TLS or certificate issue.",
        "network_unreachable": "Network is unreachable for the LLM provider.",
        "proxy_or_firewall_issue": "Proxy or firewall blocked the LLM provider request.",
    }.get(category, "LLM connection test failed.")


def parse_llm_analysis(content: str | dict[str, Any]) -> LLMAnalysis:
    data = content if isinstance(content, dict) else _json_from_text(content)
    return analysis_from_dict(data)


def analysis_from_dict(data: dict[str, Any]) -> LLMAnalysis:
    required = [
        "relevance_score",
        "is_actionable_alert",
        "event_type",
        "summary",
        "why_it_matters",
        "market_watch_suggestions",
        "bullish_path",
        "bearish_path",
        "risk_notes",
        "uncertainty_notes",
        "source_reliability",
        "recommended_user_action",
        "notification_title",
    ]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"LLM JSON missing keys: {', '.join(missing)}")
    score = int(data["relevance_score"])
    if not 0 <= score <= 100:
        raise ValueError("relevance_score must be between 0 and 100")
    suggestions = [_suggestion_from_dict(item) for item in data.get("market_watch_suggestions") or []]
    reliability = _choice(data["source_reliability"], VALID_RELIABILITY, "source_reliability")
    action = _choice(data["recommended_user_action"], VALID_ACTIONS, "recommended_user_action")
    return LLMAnalysis(
        relevance_score=score,
        is_actionable_alert=bool(data["is_actionable_alert"]),
        event_type=str(data["event_type"]),
        summary=str(data["summary"]),
        why_it_matters=str(data["why_it_matters"]),
        market_watch_suggestions=suggestions,
        bullish_path=str(data["bullish_path"]),
        bearish_path=str(data["bearish_path"]),
        risk_notes=str(data["risk_notes"]),
        uncertainty_notes=str(data["uncertainty_notes"]),
        source_reliability=reliability,  # type: ignore[arg-type]
        recommended_user_action=action,  # type: ignore[arg-type]
        notification_title=str(data["notification_title"]),
    )


def _suggestion_from_dict(data: dict[str, Any]) -> MarketWatchSuggestion:
    direction = _choice(data.get("possible_direction", "unclear"), VALID_DIRECTIONS, "possible_direction")
    confidence = _choice(data.get("confidence", "low"), VALID_CONFIDENCE, "confidence")
    return MarketWatchSuggestion(
        ticker=str(data.get("ticker", "")),
        name_or_theme=str(data.get("name_or_theme", "")),
        possible_direction=direction,  # type: ignore[arg-type]
        reason=str(data.get("reason", "")),
        confidence=confidence,  # type: ignore[arg-type]
    )


def _json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response is not valid JSON") from exc
        data = json.loads(stripped[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("LLM response JSON must be an object")
    return data


def _choice(value: Any, allowed: set[str], field_name: str) -> str:
    text = str(value)
    if text not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
    return text
