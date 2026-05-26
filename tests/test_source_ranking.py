from __future__ import annotations

from src.models import SourceCandidate, TopicConfig
from src.sources.source_ranker import rank_source_candidates


def test_source_ranker_prioritizes_primary_sources_and_region_match():
    topic = TopicConfig(
        name="US policy",
        enabled=True,
        prompt="Track official policy.",
        keywords=["policy"],
        domains=["politics", "public_policy"],
        preferred_regions=["US"],
    )
    candidates = [
        SourceCandidate("blog", "Blog", "https://example.com/blog", "rss", ["politics"], credibility_hint=0.4),
        SourceCandidate(
            "gov",
            "Agency",
            "https://example.com/gov",
            "gov",
            ["politics", "public_policy"],
            country_or_region="US",
            credibility_hint=0.92,
        ),
    ]

    selected = rank_source_candidates(topic, candidates)

    assert selected[0].candidate.id == "gov"
    assert "primary or official source" in selected[0].reason


def test_social_sources_are_excluded_until_topic_enables_social():
    candidate = SourceCandidate("x", "X Search", "https://api.x.com/2", "x", ["politics"], requires_api_key=True)
    topic = TopicConfig("Topic", True, "Prompt", ["policy"], domains=["politics"], social_enabled=False)

    assert rank_source_candidates(topic, [candidate]) == []

    topic.social_enabled = True
    selected = rank_source_candidates(topic, [candidate])
    assert selected[0].candidate.id == "x"
    assert "requires API key" in selected[0].risk
