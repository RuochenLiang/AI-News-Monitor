from __future__ import annotations

import pytest

from src.llm_client import parse_llm_analysis

VALID_JSON = {
    "relevance_score": 91,
    "is_actionable_alert": True,
    "event_type": "policy",
    "summary": "Summary",
    "why_it_matters": "Why",
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


def test_valid_llm_schema_parses():
    analysis = parse_llm_analysis(VALID_JSON)
    assert analysis.relevance_score == 91
    assert analysis.market_watch_suggestions[0].ticker == "TSM"


def test_llm_schema_rejects_bad_score():
    bad = dict(VALID_JSON)
    bad["relevance_score"] = 101
    with pytest.raises(ValueError):
        parse_llm_analysis(bad)


def test_llm_schema_extracts_json_from_fenced_text():
    text = """```json
{"relevance_score": 1, "is_actionable_alert": false, "event_type": "", "summary": "", "why_it_matters": "", "market_watch_suggestions": [], "bullish_path": "", "bearish_path": "", "risk_notes": "", "uncertainty_notes": "", "source_reliability": "low", "recommended_user_action": "ignore", "notification_title": ""}
```"""
    assert parse_llm_analysis(text).recommended_user_action == "ignore"
