from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

import httpx

from src.aggregation.topic_timeline import build_timeline, cluster_to_llm_payload, source_links_from_articles
from src.diagnostics import (
    DiagnosticResult,
    classify_llm_http_error,
    diagnostic_error,
    diagnostic_ok,
    invalid_url_result,
    is_valid_http_url,
    missing_required_result,
)
from src.models import (
    Article,
    EventCluster,
    LLMAnalysis,
    LLMSettings,
    MarketWatchSuggestion,
    SourceLink,
    TimelineItem,
    TopicConfig,
)
from src.secrets import get_env_secret, sanitize_for_log
from src.utils.http_utils import request_with_retries
from src.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

VALID_DIRECTIONS = {"bullish", "bearish", "mixed", "unclear"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_RELIABILITY = {"low", "medium", "high"}
VALID_ACTIONS = {"watch_only", "research_further", "urgent_review", "ignore"}
ANALYSIS_ARTICLE_LIMIT = 8
ARTICLE_TITLE_LIMIT = 220
ARTICLE_SNIPPET_LIMIT = 900
TRANSLATION_SNIPPET_LIMIT = 700


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: LLMSettings, api_key: str | None = None, client: httpx.Client | None = None):
        self.settings = settings
        self.api_key = api_key if api_key is not None else get_env_secret(settings.api_key_env)
        self.client = client
        self._structured_outputs_supported: bool | None = None

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
        if self.settings.provider not in {"openai_compatible", "openai", "deepseek"}:
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
                retries=self.settings.max_retries,
                backoff_seconds=self.settings.retry_backoff_seconds,
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
                client,
                "GET",
                self.settings.base_url.rstrip("/") + "/models",
                headers=self._headers(),
                retries=self.settings.max_retries,
                backoff_seconds=self.settings.retry_backoff_seconds,
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
            "response_format": _json_object_response_format(),
        }

    def analyze_article(self, topic: TopicConfig, article: Article) -> LLMAnalysis:
        return self._analyze_messages(
            self._build_messages(topic, [article], event_payload=None),
            max_tokens=_analysis_token_budget(self.settings.max_tokens, topic, article_count=1),
            fallback_articles=[article],
            fallback_relation_reason="Single source event cluster; no related articles were available in this cycle.",
            fallback_article_count=1,
        )

    def analyze_event_cluster(self, topic: TopicConfig, cluster: EventCluster) -> LLMAnalysis:
        return self._analyze_messages(
            self._build_messages(topic, cluster.articles, event_payload=cluster_to_llm_payload(cluster)),
            max_tokens=_analysis_token_budget(self.settings.max_tokens, topic, article_count=cluster.article_count),
            fallback_articles=cluster.articles,
            fallback_relation_reason=cluster.relation_reason,
            fallback_article_count=cluster.article_count,
        )

    def _analyze_messages(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        fallback_articles: list[Article],
        fallback_relation_reason: str,
        fallback_article_count: int,
    ) -> LLMAnalysis:
        if not self.api_key:
            raise LLMError("LLM API key is missing.")
        content = ""
        try:
            content = self._chat(
                messages,
                max_tokens=max_tokens,
                response_schema=_analysis_response_schema(),
                response_name="ai_news_monitor_analysis",
            )
            return _with_event_defaults(
                parse_llm_analysis(content),
                fallback_articles,
                fallback_relation_reason,
                fallback_article_count,
                report_preferences=_report_preferences_from_messages(messages),
            )
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
            content = self._chat(
                repair_messages,
                max_tokens=max_tokens,
                response_schema=_analysis_response_schema(),
                response_name="ai_news_monitor_analysis_repair",
            )
            return _with_event_defaults(
                parse_llm_analysis(content),
                fallback_articles,
                fallback_relation_reason,
                fallback_article_count,
                report_preferences=_report_preferences_from_messages(messages),
            )

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
                        "title": _compact_text(article.title, ARTICLE_TITLE_LIMIT),
                        "snippet": _compact_text(article.snippet, TRANSLATION_SNIPPET_LIMIT),
                        "required_fields": list(schema),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        data = _json_from_text(
            self._chat(
                messages,
                max_tokens=_bounded_token_budget(self.settings.max_tokens, 320),
                response_schema=_translation_response_schema(),
                response_name="ai_news_monitor_translation",
            )
        )
        return {key: str(data.get(key, "")) for key in schema}

    def _build_messages(
        self,
        topic: TopicConfig,
        articles: list[Article],
        *,
        event_payload: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        system = (
            "You are an AI news monitoring analyst. You may receive one article or multiple related articles. "
            "Summarize them as one event, not as separate disconnected summaries. Build the timeline only from "
            "provided source text and metadata; do not invent dates, companies, policies, products, or causal "
            "relationships. When multiple sources describe the same event, synthesize the shared development once "
            "and avoid repeating near-identical facts source by source. Distinguish confirmed facts from "
            "interpretation, prefer official or primary sources when sources conflict, keep the output concise "
            "enough for phone notification channels, and include "
            "links to all important sources. Use natural Simplified Chinese when output_language is zh-CN and "
            "clean English when output_language is en. Technical names such as NVIDIA, TSMC, HBM, GDELT, RSS, "
            "and LLM may remain English. Respect report_preferences: when include_timeline is false, return an "
            "empty timeline array; when include_user_action is false, return an empty suggested_actions array and "
            "use watch_only unless urgency is clearly justified by the sources. Do not provide personalized "
            "financial advice. Return strict JSON only."
        )
        included_articles = [_article_payload(article) for article in articles[:ANALYSIS_ARTICLE_LIMIT]]
        user = {
            "topic_prompt": topic.prompt,
            "output_language": topic.output_language,
            "keywords": _limited_strings(topic.keywords, 20),
            "related_stock_watchlist_candidates": _limited_strings(topic.related_stocks, 20),
            "report_preferences": _topic_report_preferences(topic),
            "event_cluster": _compact_event_payload(event_payload) if event_payload else None,
            "article_count": len(articles),
            "articles_included": len(included_articles),
            "articles": included_articles,
            "output_contract": _analysis_prompt_contract(),
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(_drop_empty(user), ensure_ascii=False)},
        ]

    def _chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        response_schema: dict[str, Any] | None = None,
        response_name: str = "ai_news_monitor_response",
    ) -> str:
        body = self._chat_body(
            messages,
            max_tokens=max_tokens,
            response_format=_json_object_response_format(),
        )
        use_structured_outputs = (
            response_schema is not None
            and self.settings.structured_outputs
            and self._structured_outputs_supported is not False
        )
        if use_structured_outputs:
            body["response_format"] = _structured_response_format(response_name, response_schema)
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=self.settings.timeout_seconds)
        try:
            try:
                response = self._send_chat_request(client, body, retries=0 if use_structured_outputs else 2)
            except httpx.HTTPError as exc:
                if not use_structured_outputs or not _structured_outputs_unsupported(exc):
                    raise
                logger.warning(
                    "LLM provider rejected JSON Schema structured outputs; falling back to JSON object mode."
                )
                self._structured_outputs_supported = False
                body["response_format"] = _json_object_response_format()
                response = self._send_chat_request(client, body)
            else:
                if use_structured_outputs:
                    self._structured_outputs_supported = True
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

    def _chat_body(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        response_format: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "presence_penalty": self.settings.presence_penalty,
            **_token_limit_payload(self.settings.model, max_tokens or self.settings.max_tokens),
            "response_format": response_format,
        }

    def _send_chat_request(self, client: httpx.Client, body: dict[str, Any], *, retries: int = 2) -> httpx.Response:
        return request_with_retries(
            client,
            "POST",
            self._chat_url(),
            headers=self._headers(),
            json=body,
            retries=min(retries, self.settings.max_retries),
            backoff_seconds=self.settings.retry_backoff_seconds,
        )


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _bounded_token_budget(configured_max: int, target: int) -> int:
    return max(1, min(int(configured_max or target), target))


def _analysis_token_budget(configured_max: int, topic: TopicConfig, article_count: int) -> int:
    target = 900 if article_count > 1 else 760
    if not topic.report_include_timeline:
        target -= 120
    if not topic.report_include_source_comparison:
        target -= 80
    if not topic.report_include_user_action:
        target -= 40
    return _bounded_token_budget(configured_max, max(520, target))


def _token_limit_payload(model: str, max_tokens: int) -> dict[str, int]:
    if model.strip().casefold().startswith("gpt-5"):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


def _analysis_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "relevance_score",
            "is_actionable_alert",
            "should_notify",
            "event_type",
            "event_title",
            "event_summary",
            "current_status",
            "summary",
            "why_it_matters",
            "timeline",
            "key_facts",
            "affected_entities",
            "source_links",
            "relation_reason",
            "uncertainties",
            "suggested_actions",
            "market_watch_suggestions",
            "bullish_path",
            "bearish_path",
            "risk_notes",
            "uncertainty_notes",
            "source_reliability",
            "recommended_user_action",
            "notification_title",
        ],
        "properties": {
            "relevance_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "How relevant the article is to the configured topic.",
            },
            "is_actionable_alert": {
                "type": "boolean",
                "description": "Whether this event cluster should become a user-facing alert.",
            },
            "should_notify": {"type": "boolean"},
            "event_type": {"type": "string"},
            "event_title": {"type": "string"},
            "event_summary": {"type": "string"},
            "current_status": {"type": "string"},
            "summary": {"type": "string", "description": "Source-grounded concise event summary."},
            "why_it_matters": {"type": "string"},
            "timeline": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "date",
                        "time",
                        "label",
                        "description",
                        "source_title",
                        "source_url",
                        "confidence",
                    ],
                    "properties": {
                        "date": {"type": "string"},
                        "time": {"type": ["string", "null"]},
                        "label": {"type": "string"},
                        "description": {"type": "string"},
                        "source_title": {"type": "string"},
                        "source_url": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "key_facts": {"type": "array", "items": {"type": "string"}},
            "affected_entities": {"type": "array", "items": {"type": "string"}},
            "source_links": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "url", "publisher", "published_at"],
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "publisher": {"type": "string"},
                        "published_at": {"type": "string"},
                    },
                },
            },
            "relation_reason": {"type": "string"},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
            "suggested_actions": {"type": "array", "items": {"type": "string"}},
            "market_watch_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "ticker",
                        "name_or_theme",
                        "possible_direction",
                        "reason",
                        "confidence",
                    ],
                    "properties": {
                        "ticker": {"type": "string"},
                        "name_or_theme": {"type": "string"},
                        "possible_direction": {"type": "string", "enum": sorted(VALID_DIRECTIONS)},
                        "reason": {"type": "string"},
                        "confidence": {"type": "string", "enum": sorted(VALID_CONFIDENCE)},
                    },
                },
            },
            "bullish_path": {"type": "string"},
            "bearish_path": {"type": "string"},
            "risk_notes": {"type": "string"},
            "uncertainty_notes": {"type": "string"},
            "source_reliability": {"type": "string", "enum": sorted(VALID_RELIABILITY)},
            "recommended_user_action": {"type": "string", "enum": sorted(VALID_ACTIONS)},
            "notification_title": {"type": "string"},
        },
    }


def _translation_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["translated_title", "translated_snippet", "summary"],
        "properties": {
            "translated_title": {"type": "string"},
            "translated_snippet": {"type": "string"},
            "summary": {"type": "string"},
        },
    }


def _analysis_prompt_contract() -> dict[str, Any]:
    schema = _analysis_response_schema()
    return {
        "required_fields": schema["required"],
        "timeline_item_fields": schema["properties"]["timeline"]["items"]["required"],
        "source_link_fields": schema["properties"]["source_links"]["items"]["required"],
        "market_watch_fields": schema["properties"]["market_watch_suggestions"]["items"]["required"],
        "enum_constraints": {
            "market_watch_suggestions[].possible_direction": sorted(VALID_DIRECTIONS),
            "market_watch_suggestions[].confidence": sorted(VALID_CONFIDENCE),
            "source_reliability": sorted(VALID_RELIABILITY),
            "recommended_user_action": sorted(VALID_ACTIONS),
        },
    }


def _topic_report_preferences(topic: TopicConfig) -> dict[str, bool]:
    return {
        "include_timeline": topic.report_include_timeline,
        "include_source_comparison": topic.report_include_source_comparison,
        "include_user_action": topic.report_include_user_action,
    }


def _report_preferences_from_messages(messages: list[dict[str, str]]) -> dict[str, bool]:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        try:
            payload = json.loads(message.get("content") or "{}")
        except (TypeError, ValueError):
            continue
        preferences = payload.get("report_preferences") if isinstance(payload, dict) else None
        if isinstance(preferences, dict):
            return {
                "include_timeline": bool(preferences.get("include_timeline", True)),
                "include_source_comparison": bool(preferences.get("include_source_comparison", True)),
                "include_user_action": bool(preferences.get("include_user_action", True)),
            }
    return {
        "include_timeline": True,
        "include_source_comparison": True,
        "include_user_action": True,
    }


def _structured_response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }


def _json_object_response_format() -> dict[str, str]:
    return {"type": "json_object"}


def _structured_outputs_unsupported(exc: httpx.HTTPError) -> bool:
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    if exc.response.status_code not in {400, 422}:
        return False
    detail = exc.response.text.casefold()
    unsupported_markers = ("unsupported", "not supported", "not support", "invalid", "unknown", "unrecognized")
    structured_markers = ("json_schema", "response_format", "schema", "strict")
    return any(marker in detail for marker in unsupported_markers) and any(
        marker in detail for marker in structured_markers
    )


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
    data = _normalize_analysis_payload(data)
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
        event_title=str(data.get("event_title") or ""),
        event_summary=str(data.get("event_summary") or data.get("summary") or ""),
        current_status=str(data.get("current_status") or ""),
        timeline=[_timeline_from_dict(item) for item in data.get("timeline") or []],
        key_facts=_string_items(data.get("key_facts")),
        affected_entities=_string_items(data.get("affected_entities")),
        source_links=[_source_link_from_dict(item) for item in data.get("source_links") or []],
        relation_reason=str(data.get("relation_reason") or ""),
        uncertainties=_string_items(data.get("uncertainties")),
        suggested_actions=_string_items(data.get("suggested_actions")),
        grouped_article_count=max(1, int(data.get("grouped_article_count") or 1)),
    )


def _normalize_analysis_payload(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if "is_actionable_alert" not in normalized and "should_notify" in normalized:
        normalized["is_actionable_alert"] = bool(normalized["should_notify"])
    if "should_notify" not in normalized and "is_actionable_alert" in normalized:
        normalized["should_notify"] = bool(normalized["is_actionable_alert"])
    if "summary" not in normalized and "event_summary" in normalized:
        normalized["summary"] = normalized["event_summary"]
    if "event_summary" not in normalized and "summary" in normalized:
        normalized["event_summary"] = normalized["summary"]
    if "event_title" not in normalized:
        normalized["event_title"] = normalized.get("notification_title", "")
    if "notification_title" not in normalized:
        normalized["notification_title"] = normalized.get("event_title", "")
    normalized.setdefault("current_status", "")
    normalized.setdefault("timeline", [])
    normalized.setdefault("key_facts", [])
    normalized.setdefault("affected_entities", [])
    normalized.setdefault("source_links", [])
    normalized.setdefault("relation_reason", "")
    normalized.setdefault("uncertainties", [])
    normalized.setdefault("suggested_actions", [])
    normalized.setdefault("grouped_article_count", 1)
    return normalized


def _with_event_defaults(
    analysis: LLMAnalysis,
    articles: list[Article],
    relation_reason: str,
    article_count: int,
    *,
    report_preferences: dict[str, bool] | None = None,
) -> LLMAnalysis:
    preferences = report_preferences or {}
    analysis.report_include_timeline = bool(preferences.get("include_timeline", True))
    analysis.report_include_source_comparison = bool(preferences.get("include_source_comparison", True))
    analysis.report_include_user_action = bool(preferences.get("include_user_action", True))
    if not analysis.event_title:
        analysis.event_title = analysis.notification_title or (articles[0].title if articles else "")
    if not analysis.event_summary:
        analysis.event_summary = analysis.summary
    if not analysis.source_links:
        analysis.source_links = source_links_from_articles(articles)
    if analysis.report_include_timeline and not analysis.timeline:
        analysis.timeline = build_timeline(articles)
    if not analysis.report_include_timeline:
        analysis.timeline = []
    if not analysis.report_include_user_action:
        analysis.suggested_actions = []
    if not analysis.relation_reason:
        analysis.relation_reason = relation_reason
    analysis.grouped_article_count = max(article_count, len(articles), analysis.grouped_article_count)
    return analysis


def _timeline_from_dict(data: dict[str, Any]) -> TimelineItem:
    return TimelineItem(
        date=str(data.get("date") or "unknown"),
        time=str(data["time"]) if data.get("time") not in (None, "") else None,
        label=str(data.get("label") or ""),
        description=str(data.get("description") or ""),
        source_title=str(data.get("source_title") or ""),
        source_url=str(data.get("source_url") or ""),
        confidence=_float_between_zero_and_one(data.get("confidence")),
    )


def _source_link_from_dict(data: dict[str, Any]) -> SourceLink:
    return SourceLink(
        title=str(data.get("title") or ""),
        url=str(data.get("url") or ""),
        publisher=str(data.get("publisher") or ""),
        published_at=str(data.get("published_at") or ""),
    )


def _string_items(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _float_between_zero_and_one(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _article_payload(article: Article) -> dict[str, Any]:
    return _drop_empty(
        {
            "title": _compact_text(article.title, ARTICLE_TITLE_LIMIT),
            "snippet": _compact_text(article.snippet, ARTICLE_SNIPPET_LIMIT),
            "source": _compact_text(article.source, 120),
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "url": article.url,
            "language": article.language,
            "translated_title": _compact_text(article.translated_title, ARTICLE_TITLE_LIMIT),
            "translated_snippet": _compact_text(article.translated_snippet, ARTICLE_SNIPPET_LIMIT),
            "short_summary": _compact_text(article.short_summary, 520),
            "source_reliability_score": article.reliability_score,
            "source_ownership": _compact_text(article.ownership, 160),
            "source_bias_hint": _compact_text(article.bias_hint, 180),
            "source_role": article.source_role,
            "source_tier": article.source_tier,
            "ranking_score": article.ranking_score,
            "matched_keywords": _limited_strings(article.matched_keywords, 10),
            "match_reason": _compact_text(article.match_reason, 220),
            "selection_reason": _compact_text(article.selection_reason, 220),
            "bias_context": _compact_text((article.raw or {}).get("bias_summary") if article.raw else None, 420),
        }
    )


def _compact_event_payload(event_payload: dict[str, Any]) -> dict[str, Any]:
    timeline = event_payload.get("timeline_seed") or []
    return _drop_empty(
        {
            "cluster_id": event_payload.get("cluster_id"),
            "title": _compact_text(event_payload.get("title"), ARTICLE_TITLE_LIMIT),
            "article_count": event_payload.get("article_count"),
            "relation_reason": _compact_text(event_payload.get("relation_reason"), 420),
            "confidence": event_payload.get("confidence"),
            "entities": _limited_strings(event_payload.get("entities"), 12),
            "earliest_published_at": event_payload.get("earliest_published_at"),
            "latest_published_at": event_payload.get("latest_published_at"),
            "timeline_seed": [
                _drop_empty(
                    {
                        "date": item.get("date"),
                        "time": item.get("time"),
                        "label": _compact_text(item.get("label"), 140),
                        "description": _compact_text(item.get("description"), 260),
                        "source_title": _compact_text(item.get("source_title"), 180),
                        "source_url": item.get("source_url"),
                        "confidence": item.get("confidence"),
                    }
                )
                for item in timeline[:6]
                if isinstance(item, dict)
            ],
        }
    )


def _limited_strings(values: object, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    return [clean for value in values[:limit] if (clean := _compact_text(value, 120))]


def _compact_text(value: object, max_length: int) -> str:
    text = clean_text(value)
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3].rstrip() + "..."


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "", [], {})}


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
