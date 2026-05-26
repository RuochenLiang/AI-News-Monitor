from __future__ import annotations

from src.models import Article, NotificationResult, TopicConfig
from src.monitor import NewsMonitor
from src.storage import SQLiteStore
from tests.test_config import CONFIG_TEXT
from tests.test_llm_schema import VALID_JSON


class FakeSource:
    name = "Fake Source"

    def __init__(self):
        self.calls = 0

    def fetch(self, topic: TopicConfig):
        self.calls += 1
        return [Article("chip partnership news", "https://example.com/chip", self.name, snippet="chip")]


class FakeLlm:
    def __init__(self):
        self.calls = 0

    def analyze_article(self, topic, article):
        self.calls += 1
        from src.llm_client import parse_llm_analysis

        return parse_llm_analysis(VALID_JSON)


class FakeNotifier:
    name = "Fake Notifier"

    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)
        return NotificationResult(self.name, True)


class SequencedSource:
    def __init__(self, name: str, batches: list[list[Article]]):
        self.name = name
        self.batches = batches
        self.calls = 0

    def fetch(self, topic: TopicConfig):
        index = min(self.calls, len(self.batches) - 1)
        self.calls += 1
        return self.batches[index]


class ClusterLlm:
    api_key = "test-key"

    def __init__(self):
        self.calls = 0
        self.cluster_sizes = []

    def analyze_event_cluster(self, topic, cluster):
        self.calls += 1
        self.cluster_sizes.append(cluster.article_count)
        from src.llm_client import parse_llm_analysis

        payload = dict(
            VALID_JSON,
            event_title="NVIDIA H20 China export license review",
            notification_title="NVIDIA H20 China export license review",
            summary="NVIDIA H20 China export license review affects chip shipment paperwork.",
            event_summary="NVIDIA H20 China export license review affects chip shipment paperwork.",
            source_reliability="high",
        )
        analysis = parse_llm_analysis(payload)
        analysis.grouped_article_count = cluster.article_count
        analysis.relation_reason = cluster.relation_reason
        return analysis

    def translate_and_summarize(self, article, target_language):
        return {"translated_title": article.title, "translated_snippet": article.snippet or "", "summary": ""}


def test_monitor_loop_uses_filtering_llm_and_notifications(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    fake_llm = FakeLlm()
    fake_notifier = FakeNotifier()
    fake_source = FakeSource()

    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [fake_source],
        llm_factory=lambda config: fake_llm,
        notifier_factory=lambda settings, timeout: [fake_notifier],
    )

    status = monitor.run_cycle()

    assert fake_llm.calls == 1
    assert fake_source.calls == 1
    assert len(fake_notifier.sent) == 1
    assert status.latest_articles_fetched == 1
    assert status.latest_candidates == 1
    assert store.alerts_sent_today() == 1

    monitor.run_cycle()
    assert fake_source.calls == 1
    assert fake_llm.calls == 1


def test_monitor_summarizes_multi_source_same_event_once_and_skips_later_repeats(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        CONFIG_TEXT
        + """
source_cache:
  enabled: false
""",
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    fake_llm = ClusterLlm()
    fake_notifier = FakeNotifier()
    source_a = SequencedSource(
        "Official Source",
        [
            [
                Article(
                    "Commerce filing outlines H20 chip shipment process",
                    "https://official.example/h20-license",
                    "Official Source",
                    snippet="NVIDIA H20 China export license review covers chip shipment paperwork.",
                    language="en",
                    reliability_score=0.9,
                    source_tier=1,
                    source_role="official",
                )
            ],
            [
                Article(
                    "Agency posts follow-up on accelerator permit timing",
                    "https://official.example/h20-license-followup",
                    "Official Source",
                    snippet="NVIDIA H20 China export license review adds chip permit timing details.",
                    language="en",
                    reliability_score=0.9,
                    source_tier=1,
                    source_role="official",
                )
            ],
        ],
    )
    source_b = SequencedSource(
        "Industry Source",
        [
            [
                Article(
                    "Industry memo flags China datacenter permit planning",
                    "https://industry.example/h20-permits",
                    "Industry Source",
                    snippet="NVIDIA H20 China export license review affects chip datacenter procurement.",
                    language="en",
                    reliability_score=0.75,
                    source_tier=2,
                    source_role="major_media",
                )
            ],
            [
                Article(
                    "Suppliers prepare paperwork for H20 accelerator buyers",
                    "https://industry.example/h20-buyers",
                    "Industry Source",
                    snippet="NVIDIA H20 China export license review keeps chip shipment paperwork in focus.",
                    language="en",
                    reliability_score=0.75,
                    source_tier=2,
                    source_role="major_media",
                )
            ],
        ],
    )

    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [source_a, source_b],
        llm_factory=lambda config: fake_llm,
        notifier_factory=lambda settings, timeout: [fake_notifier],
    )

    first_status = monitor.run_cycle()
    second_status = monitor.run_cycle()

    assert fake_llm.calls == 1
    assert fake_llm.cluster_sizes == [2]
    assert len(fake_notifier.sent) == 1
    assert first_status.recent_alerts[0].analysis.grouped_article_count == 2
    assert store.alerts_sent_today() == 1
    assert second_status.pipeline_funnel["diagnostic_counts"]["rejected_as_duplicate"] >= 2


def test_monitor_honors_topic_poll_interval(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        CONFIG_TEXT.replace('keywords: ["chip"]', 'keywords: ["chip"]\n    poll_interval_seconds: 3600'),
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "data" / "monitor.sqlite")
    fake_llm = FakeLlm()
    fake_notifier = FakeNotifier()
    fake_source = FakeSource()

    monitor = NewsMonitor(
        config_path,
        tmp_path,
        store=store,
        source_factory=lambda config: [fake_source],
        llm_factory=lambda config: fake_llm,
        notifier_factory=lambda settings, timeout: [fake_notifier],
    )

    monitor.run_cycle()
    monitor.run_cycle()

    assert fake_source.calls == 1
