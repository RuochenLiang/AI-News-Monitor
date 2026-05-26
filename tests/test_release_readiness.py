from __future__ import annotations

import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from src.config import parse_config
from src.dependency_check import DependencyReport, check_runtime_dependencies, dependency_guidance
from src.realtime import _index_html
from src.sources.library import SOURCE_PACKAGES, default_source_library

ROOT = Path(__file__).resolve().parents[1]
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
ALLOWED_HAN_PATHS = {
    ROOT / "locales" / "zh-CN.json",
    ROOT / "README.zh-CN.md",
}
IGNORED_PARTS = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__", ".mypy_cache", ".cache"}
SECRET_PATTERNS = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "telegram_token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{30,}\b"),
    "wecom_webhook": re.compile(r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[A-Za-z0-9_-]{16,}"),
}
SECRET_SCAN_SUFFIXES = {".py", ".ps1", ".sh", ".yml", ".yaml", ".toml", ".md", ".txt", ".json", ".example"}
RUNTIME_ARTIFACT_PATTERNS = {
    ".env",
    "config.yaml",
    "user_config.yaml",
    "CURRENT_RUNTIME_STATUS.json",
    "data",
    "logs",
}
PROMPT_ARCHIVE_ORDER = (
    "01-build-lightweight-desktop-ai-news-monitor.md",
    "02-expand-into-24-7-global-information-agent.md",
    "03-add-presets-minimal-ui-and-source-management.md",
    "04-improve-fast-alerts-ui-i18n-sources-notifications.md",
    "05-prepare-v0-9-open-source-release-candidate.md",
    "06-stabilize-llm-email-source-diagnostics-and-setup-ux.md",
    "07-add-source-reliability-freshness-and-intelligence-gaps.md",
    "08-finalize-github-upload-readiness-and-release-gates.md",
    "09-prove-e2e-alert-delivery-and-clean-browser-console.md",
    "10-clean-root-for-final-github-upload.md",
    "11-verify-next-phase-features-and-runtime-stability.md",
    "12-structured-outputs-upgrade.md",
    "13-runtime-web-ui-stabilization.md",
    "14-event-synthesis-timeline.md",
    "15-intelligent-source-discovery-verification-social-deepseek.md",
)


def test_source_code_is_english_only():
    checked_suffixes = {".py", ".ps1", ".sh", ".yml", ".yaml", ".toml"}
    for path in ROOT.rglob("*"):
        if IGNORED_PARTS.intersection(path.parts):
            continue
        if not path.is_file() or path in ALLOWED_HAN_PATHS:
            continue
        if "docs/zh-CN" in path.as_posix():
            continue
        if path.suffix not in checked_suffixes:
            continue
        assert not HAN_RE.search(path.read_text(encoding="utf-8", errors="ignore")), path.relative_to(ROOT)


def test_public_release_files_and_links():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    simplified_chinese = "".join(chr(codepoint) for codepoint in [0x7B80, 0x4F53, 0x4E2D, 0x6587])
    assert f"[{simplified_chinese}](README.zh-CN.md)" in readme
    assert "[English](README.md)" in readme_zh
    assert "GPL-3.0-only" in readme
    assert "GPL-3.0-only" in readme_zh
    assert 'license = "GPL-3.0-only"' in pyproject
    assert "AI_DISCLOSURE.md" in readme
    assert "AI_DISCLOSURE.md" in readme_zh
    development_and_packaging_heading = "## " + "".join(
        chr(codepoint) for codepoint in [0x5F00, 0x53D1, 0x548C, 0x6253, 0x5305]
    )
    prompt_archive_heading = "".join(
        chr(codepoint) for codepoint in [0x5F00, 0x53D1, 0x63D0, 0x793A, 0x8BCD, 0x6863, 0x6848]
    )
    assert "## Packaging" not in readme
    assert development_and_packaging_heading not in readme_zh
    assert "Development Prompt Archive" in readme
    assert prompt_archive_heading in readme_zh
    for prompt in PROMPT_ARCHIVE_ORDER:
        archive_link = f"docs/dev-history/prompts/{prompt}"
        assert archive_link in readme
        assert archive_link in readme_zh
    assert "GNU GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "AI assistance" in (ROOT / "AI_DISCLOSURE.md").read_text(encoding="utf-8")
    for relative in [
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "SOURCE_GUIDE.md",
        "NOTIFICATION_GUIDE.md",
        "docs/INSTALL.md",
        "docs/ARCHITECTURE.md",
        "docs/ROADMAP.md",
        "docs/RELEASE_CHECKLIST.md",
        ".env.example",
        "config.example.yaml",
    ]:
        assert (ROOT / relative).is_file(), relative


def test_gitignore_blocks_runtime_private_files():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in [
        ".env",
        ".env.*",
        "!.env.example",
        "config.yaml",
        "CURRENT_RUNTIME_STATUS.json",
        "data/",
        "logs/",
        "*.sqlite",
        "*.db",
        "*.log",
        ".cache/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        "__pycache__/",
        "dist/",
        "build/",
        "*.spec",
        ".DS_Store",
    ]:
        assert pattern in ignore


def test_no_obvious_secrets_in_public_files():
    violations = []
    for path in _release_candidate_paths():
        if not _should_scan_public_file(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                violations.append(f"{path.relative_to(ROOT)}:{name}")
    assert violations == []


def test_no_runtime_artifacts_in_release_file_candidates():
    violations = []
    for path in _release_candidate_paths():
        if not path.is_file() or IGNORED_PARTS.intersection(path.parts):
            continue
        relative = path.relative_to(ROOT)
        parts = set(relative.parts)
        if path.suffix in {".sqlite", ".sqlite3", ".db", ".log"}:
            violations.append(str(relative))
        if parts.intersection(RUNTIME_ARTIFACT_PATTERNS) and path.name != ".env.example":
            violations.append(str(relative))
    assert violations == []


def test_root_directory_has_no_prompt_scratch_or_generated_artifacts():
    root_files = [path for path in _release_candidate_paths() if path.parent == ROOT and path.is_file()]
    prompt_files = [path.name for path in root_files if "prompt" in path.name.lower() and path.suffix == ".md"]
    generated = [
        path.name
        for path in root_files
        if path.suffix in {".zip", ".pyc"} or path.name == ".coverage" or path.name.endswith(".spec")
    ]

    assert prompt_files == []
    assert generated == []
    dev_history = ROOT / "docs" / "dev-history"
    prompts_dir = dev_history / "prompts"
    assert (dev_history / "README.md").is_file()
    assert prompts_dir.is_dir()
    assert tuple(path.name for path in sorted(prompts_dir.glob("*.md"))) == PROMPT_ARCHIVE_ORDER
    for prompt in PROMPT_ARCHIVE_ORDER:
        prompt_text = (prompts_dir / prompt).read_text(encoding="utf-8")
        assert prompt_text.lstrip().startswith("#"), prompt
    prompt_file = dev_history / "prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert prompt_file.is_file()
    for index, prompt in enumerate(PROMPT_ARCHIVE_ORDER, 1):
        assert f"{index:02d}." in prompt_text
        assert f"Archive file: [`prompts/{prompt}`](prompts/{prompt})" in prompt_text


def test_no_unexpected_font_assets_are_committed():
    font_suffixes = {".ttf", ".otf", ".woff", ".woff2", ".eot"}
    fonts = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts) and path.suffix.lower() in font_suffixes
    ]
    assert fonts == []


def test_dependency_check_reports_missing_dependency_guidance(monkeypatch):
    def fake_import_module(name):
        if name == "feedparser":
            raise ModuleNotFoundError(name)
        return object()

    monkeypatch.setattr("importlib.import_module", fake_import_module)

    report = check_runtime_dependencies((("feedparser", "feedparser"), ("httpx", "httpx")))
    guidance = dependency_guidance(report)

    assert report.ok is False
    assert report.missing == ["feedparser"]
    assert "Missing required runtime dependencies" in guidance
    assert "python -m pip install -r requirements.txt" in guidance
    assert "Virtual environment:" in guidance


def test_dependency_check_success_message():
    assert (
        dependency_guidance(DependencyReport([], "python", True)) == "All required runtime dependencies are installed."
    )


def test_runtime_and_dev_requirements_are_separated():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    for package in ["PySide6", "httpx", "feedparser", "beautifulsoup4", "PyYAML", "python-dotenv"]:
        assert package in runtime
    for dev_package in ["pytest", "pytest-cov", "pyinstaller", "ruff", "black"]:
        assert dev_package in dev
    assert "pyinstaller" not in runtime
    assert "pytest" not in runtime


def test_source_library_has_packages_and_target_size():
    library = default_source_library()
    assert len(library) >= 50
    assert set(SOURCE_PACKAGES) >= {
        "global-news-starter",
        "finance-starter",
        "official-gov-starter",
        "china-taiwan-starter",
        "us-policy-starter",
        "semiconductor-ai-starter",
        "company-ir-starter",
    }
    assert all(item.packages for item in library if item.category != "Custom")


def test_quality_config_parses_final_target_fields():
    config = parse_config(
        {
            "quality": {
                "official_source_boost": 0.10,
                "company_ir_boost": 0.10,
                "multi_source_confirmation_boost": 0.15,
                "low_quality_source_penalty": 0.20,
                "duplicate_rewrite_penalty": 0.10,
                "event_cluster_strength_boost": 0.05,
                "whitelist_boost": 0.20,
                "blacklist_exclude": True,
            },
            "sources": {"enabled_packages": ["company-ir-starter"]},
        }
    )
    assert config.quality.company_ir_boost == 0.10
    assert config.quality.event_cluster_strength_boost == 0.05
    assert config.sources.enabled_packages == ["company-ir-starter"]


def test_local_console_contains_required_sections():
    html = _index_html()
    for section in ["dashboard", "sources", "notifications", "topics", "alerts", "diagnostics", "logs"]:
        assert f'data-tab="{section}"' in html
        assert f'id="{section}"' in html
    assert 'data-tab="settings"' not in html
    assert "First-run Setup" in html
    assert "monitoring_console_readonly" in html
    assert "Recent Matches" in html
    assert "llm_health" in html
    assert "Pipeline Funnel" in html
    assert "E2E Test" in html
    assert "Run Once" in html
    assert "/api/readiness" in html or "/readiness" in html
    assert "sourceLibraryCards" in html
    assert "customSourceCards" in html
    assert "data-source-id" not in html
    assert "data-custom-source-delete" not in html
    assert "sourceTestResult" not in html
    assert "testLlmButton" not in html
    for api_path in ["/api/setup", "/api/control"]:
        assert api_path in html
    for api_path in ["/api/source-health", "/api/intelligence-gaps", "/api/coverage-quality", "/api/source-packages"]:
        assert api_path in html or api_path.replace("/api", "") in html
    assert "/api/test" not in html


def test_locale_resources_have_matching_keys():
    english = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    chinese = json.loads((ROOT / "locales" / "zh-CN.json").read_text(encoding="utf-8"))

    assert set(english) == set(chinese)
    for key in [
        "setup.title",
        "monitoring_console_readonly",
        "llm_settings",
        "notification_setup",
        "source_wizard",
        "topic_overview",
        "empty_topics",
        "source_category",
        "source_reliability",
        "source_freshness_summary",
        "coverage_quality",
        "intelligence_gaps",
        "pipeline_funnel",
        "notification_health",
        "show_details",
        "copy_diagnostics",
        "monitoring_paused_warning",
        "alert.confirmation",
        "fresh",
        "stale",
        "very_stale",
        "no_data",
        "critical",
        "remove_source",
        "save_settings",
    ]:
        assert key in english


def test_state_documents_are_synchronized_with_e2e_readiness():
    required = [
        "Run Once",
        "E2E Test Mode",
        "Pipeline Funnel",
        "/readiness",
        "GitHub Actions",
        "Windows",
    ]
    for relative in ["CHATBOT_CONTEXT.md", "HANDOFF.md", "NEXT_VERSION_MONITORING_REPORT.md"]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in required:
            assert phrase in text, f"{relative} missing {phrase}"


def test_release_checklist_covers_private_github_upload_flow():
    checklist = (ROOT / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    for phrase in [
        "Install dependencies",
        "dependency check",
        "Launch app",
        "local console",
        "Test LLM",
        "Gmail App Password",
        "Test Email",
        "fallback notifier",
        "E2E Test",
        "test alert",
        "Run Once",
        "Pipeline Funnel",
        "/health",
        "/readiness",
        "source packages",
        "private repo",
        "GitHub Actions",
        "Windows artifact",
        "Make repo public",
    ]:
        assert phrase in checklist


def test_github_workflows_reference_release_readiness_commands():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    build = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    for command in [
        "ruff check",
        "black --check",
        "pytest",
        "compileall",
        "config.example.yaml",
        ".env.example",
        "assert_runtime_dependencies",
        "test_release_readiness.py",
    ]:
        assert command in ci
    assert "macos-latest" in build
    assert "windows-latest" in build
    assert "upload-artifact" in build
    assert "softprops/action-gh-release" in release
    assert "AI-News-Monitor-macOS.zip" in release
    assert "AI-News-Monitor-Windows.zip" in release


def _should_scan_public_file(path: Path) -> bool:
    if not path.is_file() or IGNORED_PARTS.intersection(path.parts):
        return False
    if path.suffix == ".zip" or path.suffix == ".pyc":
        return False
    if path.name == "LICENSE":
        return False
    return path.suffix in SECRET_SCAN_SUFFIXES or path.name in {".env.example", ".gitignore"}


def _release_candidate_paths() -> list[Path]:
    tracked = _tracked_files()
    if tracked is not None:
        return [path for path in tracked if path.is_file()]
    return [path for path in ROOT.rglob("*") if path.is_file()]


@lru_cache(maxsize=1)
def _tracked_files() -> tuple[Path, ...] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    files = [item for item in result.stdout.split("\0") if item]
    if not files:
        return None
    return tuple(ROOT / item for item in files)
