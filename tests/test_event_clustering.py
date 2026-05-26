from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.aggregation.event_clusterer import cluster_event_articles
from src.aggregation.topic_timeline import build_timeline
from src.models import Article, TopicConfig


def _article(title: str, url: str, *, published_at: datetime | None, snippet: str = "") -> Article:
    return Article(
        title=title,
        url=url,
        source=url.split("/")[2],
        published_at=published_at,
        snippet=snippet,
        language="en",
        matched_keywords=["NVIDIA export controls"] if "NVIDIA" in title else [],
    )


def test_related_articles_are_grouped_into_one_event_cluster():
    now = datetime(2026, 5, 26, 10, tzinfo=UTC)
    topic = TopicConfig("Export controls", True, "Track chip policy.", ["NVIDIA export controls", "AI chips"])
    articles = [
        _article(
            "US updates NVIDIA export controls for advanced AI chips",
            "https://official.example/policy",
            published_at=now,
            snippet="Official notice covers advanced AI chip export controls.",
        ),
        _article(
            "NVIDIA AI chip export-control update draws industry reaction",
            "https://trade.example/chips",
            published_at=now + timedelta(hours=2),
            snippet="Industry groups responded to the US export control update.",
        ),
    ]

    clusters = cluster_event_articles(articles, topic)

    assert len(clusters) == 1
    assert clusters[0].article_count == 2
    assert "Grouped because 2 articles" in clusters[0].relation_reason
    assert all(article.event_cluster_id == clusters[0].cluster_id for article in articles)


def test_specific_topic_phrase_groups_multi_source_reports_with_low_title_overlap():
    now = datetime(2026, 5, 26, 10, tzinfo=UTC)
    topic = TopicConfig(
        "NVIDIA China licenses",
        True,
        "Track NVIDIA China license approvals.",
        ["NVIDIA H20 China export license review"],
    )
    articles = [
        _article(
            "Commerce filing outlines accelerator shipment process",
            "https://official.example/license",
            published_at=now,
            snippet=(
                "NVIDIA H20 China export license review covers agencies, compliance dates, "
                "customer screening, and shipment paperwork."
            ),
        ),
        _article(
            "Industry memo flags permit timing for datacenter buyers",
            "https://industry.example/permits",
            published_at=now + timedelta(hours=3),
            snippet=(
                "NVIDIA H20 China export license review is mentioned alongside vendor notices, "
                "customs planning, and datacenter procurement."
            ),
        ),
    ]

    clusters = cluster_event_articles(articles, topic)

    assert len(clusters) == 1
    assert clusters[0].article_count == 2


def test_unrelated_articles_are_not_grouped():
    now = datetime(2026, 5, 26, 10, tzinfo=UTC)
    topic = TopicConfig("Mixed", True, "Track relevant news.", ["NVIDIA export controls", "Taiwan election"])
    articles = [
        _article(
            "US updates NVIDIA export controls for advanced AI chips",
            "https://official.example/policy",
            published_at=now,
            snippet="Official notice covers advanced AI chip export controls.",
        ),
        _article(
            "Taiwan election officials publish polling-location update",
            "https://election.example/taiwan",
            published_at=now,
            snippet="Election officials updated voting logistics.",
        ),
    ]

    clusters = cluster_event_articles(articles, topic)

    assert len(clusters) == 2
    assert sorted(cluster.article_count for cluster in clusters) == [1, 1]


def test_broad_topic_term_alone_does_not_group_unrelated_articles():
    now = datetime(2026, 5, 26, 10, tzinfo=UTC)
    topic = TopicConfig("AI", True, "Track AI news.", ["AI"])
    articles = [
        _article(
            "Everyone is navigating AI security in real time",
            "https://tech.example/security",
            published_at=now,
            snippet="Security teams are responding to new AI risks.",
        ),
        _article(
            "Startup replaces sales workflow with AI agents",
            "https://tech.example/startup",
            published_at=now + timedelta(hours=1),
            snippet="A startup described operational changes involving AI agents.",
        ),
    ]

    clusters = cluster_event_articles(articles, topic)

    assert len(clusters) == 2
    assert sorted(cluster.article_count for cluster in clusters) == [1, 1]


def test_single_article_creates_one_event_cluster():
    topic = TopicConfig("AI", True, "Track AI.", ["AI"])
    article = _article("NVIDIA announces AI chip supply update", "https://example.com/one", published_at=None)

    clusters = cluster_event_articles([article], topic)

    assert len(clusters) == 1
    assert clusters[0].article_count == 1
    assert clusters[0].timeline[0].date == "unknown"
    assert "Single source event cluster" in clusters[0].relation_reason


def test_timeline_items_are_chronological_and_do_not_invent_missing_dates():
    late = _article("Later reaction", "https://example.com/later", published_at=datetime(2026, 5, 26, tzinfo=UTC))
    missing = _article("Undated source", "https://example.com/missing", published_at=None)
    early = _article("Early report", "https://example.com/early", published_at=datetime(2026, 5, 24, tzinfo=UTC))

    timeline = build_timeline([late, missing, early])

    assert [item.date for item in timeline] == ["2026-05-24", "2026-05-26", "unknown"]
    assert "Publication-time based" in timeline[0].description
    assert "Publication time unavailable" in timeline[-1].description


def test_timeline_extracts_exact_source_mentioned_dates_without_inventing_partial_dates():
    article = _article(
        "Official notice follows May 25, 2026 review",
        "https://example.com/notice",
        published_at=datetime(2026, 5, 26, tzinfo=UTC),
        snippet="The company said the implementation date is 2026-06-01. A later update may arrive May 27.",
    )

    timeline = build_timeline([article])

    assert [item.date for item in timeline] == ["2026-05-25", "2026-05-26", "2026-06-01"]
    assert timeline[0].label == "Source-mentioned date"
    assert "May 25, 2026" in timeline[0].description
    assert all("May 27" not in item.date for item in timeline)
