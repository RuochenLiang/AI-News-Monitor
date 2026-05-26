from __future__ import annotations

from src.diagnostics import diagnostic_ok
from src.doctor import run_doctor
from src.models import Article
from src.utils.time_utils import utc_now
from tests.test_config import CONFIG_TEXT


class FakeLlmClient:
    def __init__(self, settings):
        self.settings = settings

    def diagnose(self):
        return diagnostic_ok("llm", "LLM smoke test passed.")


class FakeSource:
    name = "Fake Source"

    def fetch(self, topic):
        return [Article("news", "https://example.com/news", self.name, published_at=utc_now())]


def test_doctor_checks_llm_and_sources_with_injected_adapters(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")

    result = run_doctor(
        config_path,
        check_llm=True,
        check_sources=True,
        source_factory=lambda config: [FakeSource()],
        llm_client_factory=FakeLlmClient,
    )

    assert result["ok"] is True
    assert result["summary"] == {"passed": 2, "failed": 0, "total": 2}
    assert {item["target"] for item in result["checks"]} == {"llm:openai_compatible", "source:Fake Source"}


def test_doctor_reports_missing_sources(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_TEXT, encoding="utf-8")

    result = run_doctor(
        config_path,
        check_llm=False,
        check_sources=True,
        source_factory=lambda config: [],
    )

    assert result["ok"] is False
    assert result["checks"][0]["target"] == "sources"
    assert result["checks"][0]["category"] == "missing_required_field"


def test_doctor_reports_enabled_x_without_bearer_token(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        CONFIG_TEXT + """
social_sources:
  x:
    enabled: true
    bearer_token_env: X_BEARER_TOKEN
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)

    result = run_doctor(
        config_path,
        check_llm=False,
        check_sources=True,
        source_factory=lambda config: [],
    )

    assert result["ok"] is False
    assert result["checks"][0]["target"] == "source:X.com Recent Search"
    assert result["checks"][0]["category"] == "missing_required_field"
    assert result["checks"][0]["missing_fields"] == ["X_BEARER_TOKEN"]


def test_app_main_routes_doctor_without_qt_startup(monkeypatch):
    from src import app

    calls = []

    def fake_doctor_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr("src.doctor.main", fake_doctor_main)

    assert app.main(["doctor", "--check-llm"]) == 0
    assert calls == [["--check-llm"]]
