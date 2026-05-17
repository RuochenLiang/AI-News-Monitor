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
