from __future__ import annotations

import json
from copy import deepcopy

import httpx
import pytest

from src.llm_client import (
    VALID_ACTIONS,
    VALID_CONFIDENCE,
    VALID_DIRECTIONS,
    VALID_RELIABILITY,
    LLMClient,
    _analysis_response_schema,
    _translation_response_schema,
    parse_llm_analysis,
)
from src.models import Article, LLMSettings, TopicConfig

VALID_JSON = {
    "relevance_score": 91,
    "is_actionable_alert": True,
    "event_type": "policy",
    "event_title": "Event Title",
    "event_summary": "Event summary",
    "current_status": "Developing",
    "summary": "Summary",
    "why_it_matters": "Why",
    "timeline": [
        {
            "date": "2026-05-25",
            "time": None,
            "label": "Official source published",
            "description": "Official notice published.",
            "source_title": "Notice",
            "source_url": "https://example.com/notice",
            "confidence": 0.9,
        }
    ],
    "key_facts": ["Fact"],
    "affected_entities": ["TSMC"],
    "source_links": [
        {
            "title": "Notice",
            "url": "https://example.com/notice",
            "publisher": "Example",
            "published_at": "2026-05-25T00:00:00+00:00",
        }
    ],
    "relation_reason": "Shared policy topic.",
    "uncertainties": ["Uncertainty"],
    "suggested_actions": ["Follow official source"],
    "should_notify": True,
    "market_watch_suggestions": [
        {
            "ticker": "TSM",
            "name_or_theme": "Semiconductors",
            "possible_direction": "mixed",
            "reason": "Reason",
            "confidence": "medium",
        }
    ],
    "bullish_path": "Bull",
    "bearish_path": "Bear",
    "risk_notes": "Risk",
    "uncertainty_notes": "Uncertainty",
    "source_reliability": "medium",
    "recommended_user_action": "research_further",
    "notification_title": "Title",
}


class RecordingClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append(deepcopy({"method": method, "url": url, **kwargs}))
        if not self.responses:
            raise AssertionError("No fake response configured")
        return self.responses.pop(0)


def _chat_response(content: str, status_code: int = 200) -> httpx.Response:
    request = httpx.Request("POST", "https://example.com/v1/chat/completions")
    if status_code >= 400:
        return httpx.Response(status_code, text=content, request=request)
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": content}}]},
        request=request,
    )


def test_valid_llm_schema_parses():
    analysis = parse_llm_analysis(VALID_JSON)
    assert analysis.relevance_score == 91
    assert analysis.market_watch_suggestions[0].ticker == "TSM"
    assert analysis.event_title == "Event Title"
    assert analysis.timeline[0].date == "2026-05-25"
    assert analysis.source_links[0].url == "https://example.com/notice"


def test_llm_schema_rejects_bad_score():
    bad = dict(VALID_JSON)
    bad["relevance_score"] = 101
    with pytest.raises(ValueError):
        parse_llm_analysis(bad)


def test_llm_schema_rejects_missing_keys():
    bad = dict(VALID_JSON)
    bad.pop("summary")
    bad.pop("event_summary")
    with pytest.raises(ValueError, match="summary"):
        parse_llm_analysis(bad)


def test_llm_schema_rejects_invalid_enums():
    bad = dict(VALID_JSON)
    bad["recommended_user_action"] = "buy_now"
    with pytest.raises(ValueError, match="recommended_user_action"):
        parse_llm_analysis(bad)


def test_llm_schema_extracts_json_from_fenced_text():
    payload = dict(VALID_JSON, relevance_score=1, is_actionable_alert=False, should_notify=False)
    payload["recommended_user_action"] = "ignore"
    text = f"""```json
{json.dumps(payload)}
```"""
    assert parse_llm_analysis(text).recommended_user_action == "ignore"


def test_analysis_response_schema_matches_local_validation_constants():
    schema = _analysis_response_schema()
    required = set(VALID_JSON)
    suggestion_schema = schema["properties"]["market_watch_suggestions"]["items"]

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == required
    assert set(schema["properties"]) == required
    assert suggestion_schema["additionalProperties"] is False
    assert set(suggestion_schema["properties"]["possible_direction"]["enum"]) == VALID_DIRECTIONS
    assert set(suggestion_schema["properties"]["confidence"]["enum"]) == VALID_CONFIDENCE
    assert set(schema["properties"]["source_reliability"]["enum"]) == VALID_RELIABILITY
    assert set(schema["properties"]["recommended_user_action"]["enum"]) == VALID_ACTIONS


def test_translation_response_schema_is_strict():
    schema = _translation_response_schema()

    assert schema == {
        "type": "object",
        "additionalProperties": False,
        "required": ["translated_title", "translated_snippet", "summary"],
        "properties": {
            "translated_title": {"type": "string"},
            "translated_snippet": {"type": "string"},
            "summary": {"type": "string"},
        },
    }


def test_chat_sends_structured_response_format_when_enabled():
    client = RecordingClient([_chat_response(json.dumps(VALID_JSON))])
    llm = LLMClient(LLMSettings(structured_outputs=True), api_key="test-key", client=client)

    llm._chat(
        [{"role": "user", "content": "Analyze"}],
        response_schema=_analysis_response_schema(),
        response_name="ai_news_monitor_analysis",
    )

    response_format = client.requests[0]["json"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "ai_news_monitor_analysis"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False


def test_translate_and_summarize_uses_structured_response_schema():
    client = RecordingClient(
        [
            _chat_response(
                json.dumps(
                    {
                        "translated_title": "Translated",
                        "translated_snippet": "Snippet",
                        "summary": "Summary",
                    }
                )
            )
        ]
    )
    llm = LLMClient(LLMSettings(structured_outputs=True), api_key="test-key", client=client)
    article = Article("Title", "https://example.com/a", "Example", snippet="Original", language="zh-CN")

    result = llm.translate_and_summarize(article, "en")

    user_payload = json.loads(client.requests[0]["json"]["messages"][1]["content"])
    response_format = client.requests[0]["json"]["response_format"]
    assert result == {"translated_title": "Translated", "translated_snippet": "Snippet", "summary": "Summary"}
    assert client.requests[0]["json"]["max_tokens"] == 320
    assert user_payload["required_fields"] == ["translated_title", "translated_snippet", "summary"]
    assert "required_schema" not in user_payload
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "ai_news_monitor_translation"
    assert response_format["json_schema"]["schema"] == _translation_response_schema()


def test_structured_outputs_can_be_disabled_for_json_mode():
    client = RecordingClient([_chat_response(json.dumps(VALID_JSON))])
    llm = LLMClient(LLMSettings(structured_outputs=False), api_key="test-key", client=client)

    llm._chat(
        [{"role": "user", "content": "Analyze"}],
        response_schema=_analysis_response_schema(),
        response_name="ai_news_monitor_analysis",
    )

    assert client.requests[0]["json"]["response_format"] == {"type": "json_object"}


def test_structured_output_unsupported_response_falls_back_to_json_object():
    client = RecordingClient(
        [
            _chat_response("unsupported response_format json_schema parameter", status_code=400),
            _chat_response(json.dumps(VALID_JSON)),
        ]
    )
    llm = LLMClient(LLMSettings(structured_outputs=True), api_key="test-key", client=client)
    article = Article("Title", "https://example.com/a", "Example", snippet="Snippet", language="en")
    topic = TopicConfig("Topic", True, "Prompt", ["chip"])

    analysis = llm.analyze_article(topic, article)

    assert analysis.summary == "Summary"
    assert [request["json"]["response_format"]["type"] for request in client.requests] == [
        "json_schema",
        "json_object",
    ]


def test_analysis_prompt_uses_compact_contract_and_token_budget():
    client = RecordingClient([_chat_response(json.dumps(VALID_JSON))])
    llm = LLMClient(LLMSettings(structured_outputs=True), api_key="test-key", client=client)
    article = Article(
        "Long Title",
        "https://example.com/a",
        "Example",
        snippet=" ".join(["word"] * 500),
        language="en",
        raw={"bias_summary": " ".join(["bias"] * 200)},
        matched_keywords=[f"kw-{index}" for index in range(20)],
    )
    topic = TopicConfig("Topic", True, "Prompt", ["chip"], related_stocks=["NVDA"])

    llm.analyze_article(topic, article)

    body = client.requests[0]["json"]
    user_payload = json.loads(body["messages"][1]["content"])
    first_article = user_payload["articles"][0]

    assert body["max_tokens"] == 760
    assert "required_schema" not in user_payload
    assert user_payload["output_contract"]["required_fields"] == _analysis_response_schema()["required"]
    assert user_payload["article_count"] == 1
    assert user_payload["articles_included"] == 1
    assert len(first_article["snippet"]) <= 900
    assert len(first_article["bias_context"]) <= 420
    assert len(first_article["matched_keywords"]) == 10
    assert "translated_title" not in first_article


def test_topic_report_style_preferences_are_sent_and_applied_to_analysis():
    client = RecordingClient([_chat_response(json.dumps(VALID_JSON))])
    llm = LLMClient(LLMSettings(structured_outputs=False), api_key="test-key", client=client)
    article = Article("Title", "https://example.com/a", "Example", snippet="Snippet", language="en")
    topic = TopicConfig(
        "Topic",
        True,
        "Prompt",
        ["chip"],
        report_include_timeline=False,
        report_include_source_comparison=False,
        report_include_user_action=False,
    )

    analysis = llm.analyze_article(topic, article)
    user_payload = json.loads(client.requests[0]["json"]["messages"][1]["content"])

    assert user_payload["report_preferences"] == {
        "include_timeline": False,
        "include_source_comparison": False,
        "include_user_action": False,
    }
    assert analysis.timeline == []
    assert analysis.suggested_actions == []
    assert analysis.report_include_timeline is False
    assert analysis.report_include_source_comparison is False
    assert analysis.report_include_user_action is False
