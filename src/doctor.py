from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.config import load_config
from src.diagnostics import diagnostic_error, diagnostic_ok
from src.llm_client import LLMClient
from src.models import AppConfig, LLMProviderSettings, LLMSettings, TopicConfig
from src.monitor import build_sources
from src.secrets import get_env_secret
from src.sources.base import NewsSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-news-monitor doctor")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.yaml.")
    parser.add_argument("--check-llm", action="store_true", help="Check configured LLM provider(s).")
    parser.add_argument("--check-sources", action="store_true", help="Check enabled source adapters.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    check_llm = args.check_llm or not args.check_sources
    check_sources = args.check_sources or not args.check_llm
    result = run_doctor(args.config, check_llm=check_llm, check_sources=check_sources)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_format_text_result(result))
    return 0 if result["ok"] else 1


def run_doctor(
    config_path: Path | None = None,
    *,
    check_llm: bool = True,
    check_sources: bool = True,
    source_factory=build_sources,
    llm_client_factory=LLMClient,
) -> dict[str, Any]:
    config = load_config(config_path, load_env=config_path is not None)
    checks: list[dict[str, Any]] = []
    if check_llm:
        checks.extend(_check_llm(config, llm_client_factory))
    if check_sources:
        checks.extend(_check_sources(config, source_factory))
    return {
        "ok": all(item.get("ok") for item in checks),
        "checks": checks,
        "summary": {
            "passed": sum(1 for item in checks if item.get("ok")),
            "failed": sum(1 for item in checks if not item.get("ok")),
            "total": len(checks),
        },
    }


def _check_llm(config: AppConfig, llm_client_factory) -> list[dict[str, Any]]:
    names = list(dict.fromkeys([config.llm.provider, *config.llm.fallback_providers]))
    results: list[dict[str, Any]] = []
    for name in names:
        provider = config.llm.providers.get(name)
        if provider is not None and not provider.enabled:
            results.append(
                diagnostic_ok(
                    f"llm:{name}",
                    f"LLM provider {name} is disabled; skipped.",
                    enabled=False,
                ).to_dict()
            )
            continue
        settings = _llm_settings_for_provider(config.llm, name, provider)
        diagnostic = llm_client_factory(settings).diagnose().to_dict()
        diagnostic["target"] = f"llm:{name}"
        results.append(diagnostic)
    return results


def _llm_settings_for_provider(
    settings: LLMSettings,
    name: str,
    provider: LLMProviderSettings | None,
) -> LLMSettings:
    if provider is None:
        return replace(settings, provider="openai_compatible")
    return replace(
        settings,
        provider="openai_compatible",
        base_url=provider.base_url,
        model=provider.model,
        api_key_env=provider.api_key_env,
        structured_outputs=provider.structured_outputs,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        retry_backoff_seconds=provider.retry_backoff_seconds,
    )


def _check_sources(config: AppConfig, source_factory) -> list[dict[str, Any]]:
    topic = _diagnostic_topic(config)
    results: list[dict[str, Any]] = _check_social_source_configuration(config)
    for source in source_factory(config):
        results.append(_check_source(source, topic))
    if not results:
        results.append(
            diagnostic_error(
                "sources",
                "missing_required_field",
                "No enabled source adapters were found.",
                missing_fields=["sources"],
                required_fields=["sources"],
            ).to_dict()
        )
    return results


def _check_social_source_configuration(config: AppConfig) -> list[dict[str, Any]]:
    x = config.social_sources.x
    if not x.enabled:
        return []
    if not get_env_secret(x.bearer_token_env):
        return [
            diagnostic_error(
                "source:X.com Recent Search",
                "missing_required_field",
                f"X.com bearer token is missing from {x.bearer_token_env}.",
                missing_fields=[x.bearer_token_env],
                required_fields=[x.bearer_token_env],
                configured=False,
                enabled=True,
            ).to_dict()
        ]
    return [
        diagnostic_ok(
            "source:X.com Recent Search",
            "X.com bearer token is configured. Live recent-search fetch depends on topic social/source mode.",
            enabled=True,
        ).to_dict()
    ]


def _diagnostic_topic(config: AppConfig) -> TopicConfig:
    active = next((topic for topic in config.topics if topic.enabled), None)
    if active:
        return active
    return TopicConfig(
        name="Doctor source check",
        enabled=True,
        prompt="Check whether enabled sources can return recent public items.",
        keywords=["news"],
        broad_search=True,
        output_language=config.app.output_language,
    )


def _check_source(source: NewsSource, topic: TopicConfig) -> dict[str, Any]:
    try:
        articles = source.fetch(topic)
    except Exception as exc:  # noqa: BLE001 - diagnostics should report adapter failures
        return diagnostic_error(
            f"source:{getattr(source, 'name', 'unknown')}",
            "unknown_error",
            "Source check failed.",
            technical_detail=exc,
        ).to_dict()
    return diagnostic_ok(
        f"source:{getattr(source, 'name', 'unknown')}",
        f"Source check returned {len(articles)} article(s).",
        details={"article_count": len(articles)},
    ).to_dict()


def _format_text_result(result: dict[str, Any]) -> str:
    lines = [
        f"AI News Monitor doctor: {'ok' if result['ok'] else 'failed'}",
        f"Passed {result['summary']['passed']} / {result['summary']['total']} checks.",
    ]
    for item in result["checks"]:
        state = "ok" if item.get("ok") else "failed"
        target = item.get("target", "unknown")
        message = item.get("message") or item.get("category") or "-"
        lines.append(f"- {target}: {state} - {message}")
    return "\n".join(lines)
