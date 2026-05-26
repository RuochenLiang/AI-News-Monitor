from __future__ import annotations

from datetime import UTC, datetime

from src.models import Article
from src.verification.claim_extraction import extract_claims
from src.verification.corroboration import corroborate_claims


def test_claim_extraction_and_corroboration_merges_matching_entities():
    article_a = Article(
        "Company X announced a new AI accelerator.",
        "https://example.com/a",
        "Official",
        published_at=datetime(2026, 5, 26, tzinfo=UTC),
        reliability_score=0.9,
    )
    article_b = Article(
        "Company X announced a new AI accelerator for data centers.",
        "https://example.com/b",
        "Media",
        published_at=datetime(2026, 5, 26, tzinfo=UTC),
        reliability_score=0.7,
    )

    claims = corroborate_claims([*extract_claims(article_a), *extract_claims(article_b)])

    assert len(claims) == 1
    assert sorted(claims[0].supporting_sources) == ["Media", "Official"]
    assert claims[0].confidence > 0.9


def test_contradictory_claims_are_surfaced_not_hidden():
    article_a = Article(
        "Company X confirmed a new AI accelerator.",
        "https://example.com/a",
        "Official",
        reliability_score=0.9,
    )
    article_b = Article(
        "Company X denied a new AI accelerator report.",
        "https://example.com/b",
        "Wire",
        reliability_score=0.8,
    )

    claims = corroborate_claims([*extract_claims(article_a), *extract_claims(article_b)])

    assert len(claims) == 1
    assert claims[0].supporting_sources == ["Official"]
    assert claims[0].contradicting_sources == ["Wire"]
    assert claims[0].confidence < 0.9
