from __future__ import annotations

import json
import logging
import os
import queue
import threading
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from src.config import ConfigError, load_config, save_config, validate_config
from src.diagnostics import (
    SUGGESTED_FIXES,
    DiagnosticResult,
    classify_feed_http_error,
    diagnostic_error,
    diagnostic_ok,
    invalid_url_result,
    is_valid_email_address,
    is_valid_http_url,
)
from src.i18n import catalog, text
from src.llm_client import LLMClient
from src.models import CustomNewsSourceConfig, RuntimeStatus, SourceLibraryItem, TopicConfig
from src.notifiers.email_notifier import EmailNotifier
from src.notifiers.generic_webhook_notifier import GenericWebhookNotifier
from src.notifiers.relay_webhook_notifier import RelayWebhookNotifier
from src.notifiers.telegram_notifier import TelegramNotifier
from src.notifiers.wecom_notifier import WeComNotifier
from src.secrets import read_env_values, sanitize_for_log, write_env_values
from src.source_reliability import source_package_status
from src.sources.gdelt import build_gdelt_query, gdelt_params_for_topic, parse_gdelt_json_response, validate_gdelt_query
from src.sources.library import SOURCE_PACKAGES, diagnose_feed_url, enabled_library_sources
from src.utils.http_utils import request_with_retries

logger = logging.getLogger(__name__)

PLACEHOLDER_SECRET_VALUES = {"", "replace_me", "change_me", "changeme", "your_token", "your_key", "your_secret"}

HELPER_LINKS = {
    "openai_keys": "https://platform.openai.com/api-keys",
    "openai_base_url": "https://platform.openai.com/docs/api-reference/introduction",
    "openai_models": "https://platform.openai.com/docs/models",
    "gmail_app_password": "https://support.google.com/accounts/answer/185833",
    "outlook_smtp": "https://support.microsoft.com/office/pop-imap-and-smtp-settings",
    "smtp_help": "https://support.google.com/mail/answer/7126229",
    "telegram_botfather": "https://t.me/BotFather",
    "telegram_chat_id": "https://api.telegram.org/",
    "wecom_bot": "https://developer.work.weixin.qq.com/document/path/91770",
    "serverchan": "https://sct.ftqq.com/",
    "chanify": "https://github.com/chanify/chanify",
    "qmsg": "https://qmsg.zendee.cn/",
    "rss": "https://en.wikipedia.org/wiki/RSS",
    "webhook": "https://en.wikipedia.org/wiki/Webhook",
}


class SseBroker:
    def __init__(self):
        self._subscribers: set[queue.Queue[dict[str, Any]]] = set()
        self._lock = threading.Lock()
        self.event_count = 0

    def publish(self, event: dict[str, Any]) -> None:
        payload = {"type": event.get("type", "message"), **event}
        with self._lock:
            self.event_count += 1
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                self.unsubscribe(subscriber)

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)


class LocalEventServer:
    def __init__(
        self,
        host: str,
        port: int,
        broker: SseBroker,
        status_provider: Callable[[], RuntimeStatus] | None = None,
        control_handlers: dict[str, Callable[[], None]] | None = None,
        config_path: Path | None = None,
        runtime_dir: Path | None = None,
    ):
        self.host = host
        self.port = port
        self.broker = broker
        self.status_provider = status_provider
        self.control_handlers = control_handlers or {}
        self.config_path = config_path
        self.runtime_dir = runtime_dir
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.last_error_category: str | None = None
        self.last_error_message: str | None = None
        self.test_results: dict[str, dict[str, Any]] = {}

    @property
    def url(self) -> str:
        display_host = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        return f"http://{display_host}:{self.port}"

    def start(self) -> None:
        if self._server:
            return
        handler = self._handler_class()
        last_error: OSError | None = None
        for offset in range(10):
            try:
                self._server = ThreadingHTTPServer((self.host, self.port + offset), handler)
                self.port = int(self._server.server_address[1])
                break
            except OSError as exc:
                last_error = exc
                if exc.errno not in {48, 98, 10048}:
                    self.last_error_category = "unknown_error"
                    self.last_error_message = sanitize_for_log(exc)
                    raise
                self.last_error_category = "local_server_port_in_use"
                self.last_error_message = sanitize_for_log(exc)
        if not self._server:
            self.last_error_category = "local_server_port_in_use"
            self.last_error_message = sanitize_for_log(last_error or "Could not bind local event server port.")
            raise last_error or OSError("Could not bind local event server port.")
        self._thread = threading.Thread(target=self._server.serve_forever, name="ai-news-monitor-sse", daemon=True)
        self._thread.start()
        logger.info("Local event server started at %s", self.url)

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None
        logger.info("Local event server stopped")

    def _handler_class(self):
        broker = self.broker
        status_provider = self.status_provider
        control_handlers = self.control_handlers
        config_path = self.config_path
        runtime_dir = self.runtime_dir
        server_ref = self
        test_results = self.test_results

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib signature
                if self.path in {"/", "/index.html"}:
                    self._write_html(_index_html())
                    return
                if self.path.startswith("/health"):
                    self._write_json(
                        {
                            "ok": True,
                            "events": broker.event_count,
                            "last_error_category": server_ref.last_error_category,
                            "last_error_message": server_ref.last_error_message,
                        }
                    )
                    return
                if self.path.startswith("/readiness") or self.path.startswith("/api/readiness"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    self._write_json(readiness_to_dict(status))
                    return
                if self.path.startswith("/status") or self.path.startswith("/api/status"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    self._write_json(_status_payload(status, config_path))
                    return
                if self.path.startswith("/source-health") or self.path.startswith("/api/source-health"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    self._write_json(
                        {
                            "source_health": status.source_health,
                            "source_states": status.source_states,
                            "source_summary": status.source_summary,
                            "source_cache_summary": status.source_cache_summary,
                            "source_backoff_summary": status.source_backoff_summary,
                            "source_tier_distribution": status.source_tier_distribution,
                            "top_failing_sources": status.top_failing_sources,
                        }
                    )
                    return
                if self.path.startswith("/intelligence-gaps") or self.path.startswith("/api/intelligence-gaps"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    self._write_json(status.intelligence_gaps)
                    return
                if self.path.startswith("/coverage-quality") or self.path.startswith("/api/coverage-quality"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    self._write_json(status.coverage_quality)
                    return
                if self.path.startswith("/source-packages") or self.path.startswith("/api/source-packages"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    if config_path:
                        config = load_config(config_path)
                        packages = source_package_status(config, status.source_states)
                    else:
                        packages = [{"id": key, "name": name} for key, name in SOURCE_PACKAGES.items()]
                    self._write_json({"enabled": status.source_packages_enabled, "packages": packages})
                    return
                if self.path.startswith("/api/locales"):
                    self._write_json({"en": catalog("en"), "zh-CN": catalog("zh-CN")})
                    return
                if self.path.startswith("/api/setup"):
                    status = status_provider() if status_provider else RuntimeStatus()
                    self._setup(status)
                    return
                if self.path.startswith("/events"):
                    self._events()
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802 - stdlib signature
                if self.path.startswith("/api/control"):
                    self._control()
                    return
                if self.path.startswith("/api/setup") or self.path.startswith("/api/test"):
                    self.send_error(
                        HTTPStatus.METHOD_NOT_ALLOWED,
                        "Browser console is read-only. Configure and test in the desktop app",
                    )
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
                logger.debug("LocalEventServer: " + format, *args)

            def _write_json(self, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_json_payload(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length") or "0")
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw.decode() or "{}")
                except json.JSONDecodeError as exc:
                    raise ValueError("Invalid JSON payload.") from exc
                if not isinstance(payload, dict):
                    raise ValueError("JSON payload must be an object.")
                return payload

            def _write_html(self, body: str) -> None:
                raw = body.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _control(self) -> None:
                try:
                    payload = self._read_json_payload()
                except ValueError as exc:
                    self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                action = str(payload.get("action", "")).strip().casefold()
                callback = control_handlers.get(action)
                if not callback:
                    self.send_error(HTTPStatus.BAD_REQUEST, "Unknown control action.")
                    return
                self._write_json({"ok": True, "action": action})
                if action == "stop":
                    threading.Thread(target=callback, name=f"local-control-{action}", daemon=True).start()
                else:
                    callback()

            def _setup(self, status: RuntimeStatus) -> None:
                if not config_path or not runtime_dir:
                    self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Configuration API is not available.")
                    return
                try:
                    self._write_json(_setup_snapshot(config_path, runtime_dir, status, test_results))
                except Exception as exc:  # noqa: BLE001 - user-facing local API error
                    logger.exception("Could not build setup snapshot")
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, sanitize_for_log(exc))

            def _save_setup(self) -> None:
                if not config_path or not runtime_dir:
                    self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Configuration API is not available.")
                    return
                try:
                    payload = self._read_json_payload()
                    snapshot = _apply_setup_payload(config_path, runtime_dir, payload)
                    self._write_json({"ok": True, "setup": snapshot})
                except (ValueError, ConfigError) as exc:
                    self.send_error(HTTPStatus.BAD_REQUEST, sanitize_for_log(exc))
                except Exception as exc:  # noqa: BLE001 - user-facing local API error
                    logger.exception("Could not save setup payload")
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, sanitize_for_log(exc))

            def _run_test(self) -> None:
                if not config_path or not runtime_dir:
                    self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Configuration API is not available.")
                    return
                try:
                    payload = self._read_json_payload()
                    result = _run_setup_test(config_path, runtime_dir, payload)
                    _remember_test_result(test_results, payload, result)
                    self._write_json(result)
                except (ValueError, ConfigError) as exc:
                    self.send_error(HTTPStatus.BAD_REQUEST, sanitize_for_log(exc))
                except Exception as exc:  # noqa: BLE001 - user-facing local API error
                    logger.exception("Could not run setup test")
                    self._write_json({"ok": False, "message": sanitize_for_log(exc)})

            def _events(self) -> None:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                subscriber = broker.subscribe()
                try:
                    self.wfile.write(b": connected\n\n")
                    self.wfile.flush()
                    while True:
                        try:
                            event = subscriber.get(timeout=30)
                        except queue.Empty:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                            continue
                        body = json.dumps(event, ensure_ascii=False, default=_json_default)
                        self.wfile.write(f"event: {event.get('type', 'message')}\n".encode())
                        self.wfile.write(f"data: {body}\n\n".encode())
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionError, TimeoutError):
                    return
                finally:
                    broker.unsubscribe(subscriber)

        return Handler


def status_to_dict(status: RuntimeStatus) -> dict[str, Any]:
    return {
        "state": status.state,
        "pause_reason": status.pause_reason,
        "next_cycle_time": status.next_cycle_time,
        "active_topics_count": status.active_topics_count,
        "last_fetch_time": status.last_fetch_time,
        "last_successful_source_fetch": status.last_successful_source_fetch,
        "last_llm_analysis_time": status.last_llm_analysis_time,
        "last_alert_sent_time": status.last_alert_sent_time,
        "latest_articles_fetched": status.latest_articles_fetched,
        "latest_candidates": status.latest_candidates,
        "total_articles_processed": status.total_articles_processed,
        "queue_length": status.queue_length,
        "alerts_sent_today": status.alerts_sent_today,
        "recent_matches": status.recent_matches[:25],
        "recent_event_clusters": status.recent_event_clusters[:25],
        "notifier_health": status.notifier_health,
        "notifier_states": status.notifier_states,
        "source_health": status.source_health,
        "source_states": status.source_states,
        "source_packages_enabled": status.source_packages_enabled,
        "source_summary": status.source_summary,
        "source_cache_summary": status.source_cache_summary,
        "source_backoff_summary": status.source_backoff_summary,
        "source_selection_summary": status.source_selection_summary[:50],
        "source_tier_distribution": status.source_tier_distribution,
        "top_failing_sources": status.top_failing_sources,
        "intelligence_gaps": status.intelligence_gaps,
        "coverage_quality": status.coverage_quality,
        "pipeline_funnel": status.pipeline_funnel,
        "e2e_result": status.e2e_result,
        "readiness": readiness_to_dict(status),
        "llm_health": status.llm_health,
        "local_server_url": status.local_server_url,
        "ui_debug_mode": status.ui_debug_mode,
        "output_language": status.output_language,
        "alert_mode": status.alert_mode,
        "last_service_check_time": status.last_service_check_time,
        "live_event_count": status.live_event_count,
        "error_message": status.error_message,
        "recent_alerts": [
            {
                "topic": alert.topic_name,
                "title": alert.title,
                "url": alert.article.url,
                "score": alert.analysis.relevance_score,
                "relevance_score": alert.analysis.relevance_score,
                "verification_status": alert.analysis.verification_status,
                "confidence_score": alert.analysis.confidence_score,
                "sent_at": alert.sent_at,
                "event_title": alert.analysis.event_title or alert.title,
                "current_status": alert.analysis.current_status,
                "summary": alert.analysis.event_summary or alert.analysis.summary,
                "grouped_article_count": alert.analysis.grouped_article_count,
                "relation_reason": alert.analysis.relation_reason,
                "timeline": [item.to_dict() for item in alert.analysis.timeline[:6]],
                "source_links": [item.to_dict() for item in alert.analysis.source_links],
                "source_comparison": alert.analysis.source_comparison,
                "uncertainties": alert.analysis.uncertainties,
                "suggested_actions": alert.analysis.suggested_actions,
                "report_include_timeline": alert.analysis.report_include_timeline,
                "report_include_source_comparison": alert.analysis.report_include_source_comparison,
                "report_include_user_action": alert.analysis.report_include_user_action,
            }
            for alert in status.recent_alerts[:10]
        ],
        "recent_logs": status.recent_logs[:50],
    }


def _status_payload(status: RuntimeStatus, config_path: Path | None = None) -> dict[str, Any]:
    payload = status_to_dict(status)
    if not config_path:
        return payload
    try:
        config = load_config(config_path)
        payload["ui_debug_mode"] = config.ui.debug_mode
        payload["output_language"] = config.app.output_language
        payload["alert_mode"] = config.alerts.default_mode
        payload["source_packages_enabled"] = list(config.sources.enabled_packages)
    except Exception as exc:  # noqa: BLE001 - status should remain available
        logger.debug("Could not refresh status runtime settings from config: %s", sanitize_for_log(exc))
    return payload


def readiness_to_dict(status: RuntimeStatus) -> dict[str, Any]:
    coverage = (status.coverage_quality or {}).get("global", {})
    quality = coverage.get("coverage_quality", "unknown")
    critical_gaps = int(coverage.get("critical_gap_count") or 0)
    enabled_notifiers = [state for state in (status.notifier_states or {}).values() if state.get("enabled")]
    ready_notifiers = [state for state in enabled_notifiers if str(state.get("health", "")).casefold() == "ok"]
    monitor_running = status.state == "Running"
    llm_ready = status.llm_health == "configured"
    notifier_ready = bool(ready_notifiers)
    source_coverage_ready = quality in {"high", "medium", "low"} and critical_gaps == 0
    can_send_alerts = monitor_running and llm_ready and notifier_ready and source_coverage_ready
    readiness = "ready" if can_send_alerts else "degraded"
    if not monitor_running or not llm_ready or not notifier_ready:
        readiness = "not_ready"
    return {
        "server_alive": True,
        "readiness": readiness,
        "monitor_running": monitor_running,
        "monitor_state": status.state,
        "llm_ready": llm_ready,
        "llm_health": status.llm_health,
        "notifier_ready": notifier_ready,
        "enabled_notifier_count": len(enabled_notifiers),
        "ready_notifier_count": len(ready_notifiers),
        "source_coverage_ready": source_coverage_ready,
        "coverage_quality": quality,
        "critical_gaps": critical_gaps,
        "last_cycle_status": (status.pipeline_funnel or {}).get("result"),
        "can_send_alerts": can_send_alerts,
        "recommended_action": _readiness_action(status, llm_ready, notifier_ready, source_coverage_ready),
    }


def _readiness_action(
    status: RuntimeStatus,
    llm_ready: bool,
    notifier_ready: bool,
    source_coverage_ready: bool,
) -> str:
    if status.state == "Paused":
        return "Resume monitoring or use Run Once to verify the pipeline now."
    if status.state not in {"Running", "Stopped"}:
        return "Check the latest runtime error and restart monitoring after fixing it."
    if not llm_ready:
        return "Configure and test the LLM provider before relying on alerts."
    if not notifier_ready:
        return "Configure and test at least one notification channel."
    if not source_coverage_ready:
        return "Fix critical source coverage gaps or enable another source package."
    if (status.pipeline_funnel or {}).get("result") == "failed":
        return "Run E2E Test Mode, then inspect the pipeline funnel for the first failed stage."
    if status.state == "Stopped":
        return "Start monitoring or use Run Once for a single cycle."
    return "System is ready for scheduled monitoring."


def _setup_snapshot(
    config_path: Path,
    runtime_dir: Path,
    status: RuntimeStatus | None = None,
    test_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    status = status or RuntimeStatus()
    test_results = test_results or {}
    env_path = runtime_dir / ".env"
    env_values = read_env_values(env_path)
    email_missing = _missing_fields_for_channel("email", config, env_values)
    notifiers = {
        "email": {
            "name": "Email",
            "enabled": config.notifiers.email.enabled,
            "configured": not email_missing,
            "to_addrs": config.notifiers.email.to_addrs,
            "smtp_host": config.notifiers.email.smtp_host,
            "smtp_port": config.notifiers.email.smtp_port,
            "use_tls": config.notifiers.email.use_tls,
            "from_addr_configured": _has_secret(config.notifiers.email.from_addr_env, env_values),
            "required_fields": _required_fields_for_channel("email"),
            "missing_fields": email_missing,
            "suggested_fix": _suggested_fix_for_missing(email_missing),
            "warnings": _email_setup_warnings(config, env_values),
            "help_link": HELPER_LINKS["gmail_app_password"],
            "last_test_result": test_results.get("email"),
            "fallback_priority": _fallback_priority(config.notifications.fallback_order, "email"),
            "health": _state_for_notifier(status, "Email"),
        },
        "telegram": {
            "name": "Telegram",
            "enabled": config.notifiers.telegram.enabled,
            "configured": _has_secret(config.notifiers.telegram.bot_token_env, env_values)
            and _has_secret(config.notifiers.telegram.chat_id_env, env_values),
            "required_fields": _required_fields_for_channel("telegram"),
            "missing_fields": _missing_fields_for_channel("telegram", config, env_values),
            "suggested_fix": _suggested_fix_for_missing(_missing_fields_for_channel("telegram", config, env_values)),
            "help_link": HELPER_LINKS["telegram_botfather"],
            "last_test_result": test_results.get("telegram"),
            "fallback_priority": _fallback_priority(config.notifications.fallback_order, "telegram"),
            "health": _state_for_notifier(status, "Telegram"),
        },
        "wecom": {
            "name": "WeCom",
            "enabled": config.notifiers.wecom.enabled,
            "configured": _has_secret(config.notifiers.wecom.webhook_url_env, env_values),
            "required_fields": _required_fields_for_channel("wecom"),
            "missing_fields": _missing_fields_for_channel("wecom", config, env_values),
            "suggested_fix": _suggested_fix_for_missing(_missing_fields_for_channel("wecom", config, env_values)),
            "help_link": HELPER_LINKS["wecom_bot"],
            "last_test_result": test_results.get("wecom"),
            "fallback_priority": _fallback_priority(config.notifications.fallback_order, "wecom"),
            "health": _state_for_notifier(status, "WeCom"),
        },
        "wechat": {
            "name": "WeChat Relay",
            "enabled": config.notifiers.wechat.enabled,
            "configured": _has_secret(config.notifiers.wechat.webhook_url_env, env_values),
            "provider": config.notifiers.wechat.provider,
            "required_fields": _required_fields_for_channel("wechat"),
            "missing_fields": _missing_fields_for_channel("wechat", config, env_values),
            "suggested_fix": _suggested_fix_for_missing(_missing_fields_for_channel("wechat", config, env_values)),
            "help_link": HELPER_LINKS["serverchan"],
            "last_test_result": test_results.get("wechat"),
            "fallback_priority": _fallback_priority(config.notifications.fallback_order, "wechat_relay"),
            "health": _state_for_notifier(status, "WeChat Relay"),
        },
        "qq": {
            "name": "QQ Relay",
            "enabled": config.notifiers.qq.enabled,
            "configured": _has_secret(config.notifiers.qq.webhook_url_env, env_values),
            "provider": config.notifiers.qq.provider,
            "required_fields": _required_fields_for_channel("qq"),
            "missing_fields": _missing_fields_for_channel("qq", config, env_values),
            "suggested_fix": _suggested_fix_for_missing(_missing_fields_for_channel("qq", config, env_values)),
            "help_link": HELPER_LINKS["qmsg"],
            "last_test_result": test_results.get("qq"),
            "fallback_priority": _fallback_priority(config.notifications.fallback_order, "qq_relay"),
            "health": _state_for_notifier(status, "QQ Relay"),
        },
        "generic_webhook": {
            "name": "Generic Webhook",
            "enabled": config.notifiers.generic_webhook.enabled,
            "configured": _has_secret(config.notifiers.generic_webhook.url_env, env_values),
            "required_fields": _required_fields_for_channel("generic_webhook"),
            "missing_fields": _missing_fields_for_channel("generic_webhook", config, env_values),
            "suggested_fix": _suggested_fix_for_missing(
                _missing_fields_for_channel("generic_webhook", config, env_values)
            ),
            "help_link": HELPER_LINKS["webhook"],
            "last_test_result": test_results.get("generic_webhook"),
            "fallback_priority": _fallback_priority(config.notifications.fallback_order, "generic_webhook"),
            "health": _state_for_notifier(status, "Generic Webhook"),
        },
    }
    enabled_configured_notifier = any(bool(item["enabled"]) and bool(item["configured"]) for item in notifiers.values())
    return {
        "setup_required": (
            not _has_secret(config.llm.api_key_env, env_values)
            or not enabled_configured_notifier
            or not any(topic.enabled for topic in config.topics)
        ),
        "helper_links": HELPER_LINKS,
        "llm": {
            "preset": config.llm.preset,
            "provider": config.llm.provider,
            "base_url": config.llm.base_url,
            "model": config.llm.model,
            "api_key_env": config.llm.api_key_env,
            "api_key_configured": _has_secret(config.llm.api_key_env, env_values),
            "required_fields": ["provider", "base_url", "model", "api_key"],
            "missing_fields": _missing_llm_fields(config, env_values),
            "suggested_fix": _suggested_fix_for_missing(_missing_llm_fields(config, env_values)),
            "help_links": {
                "api_key": HELPER_LINKS["openai_keys"],
                "base_url": HELPER_LINKS["openai_base_url"],
                "models": HELPER_LINKS["openai_models"],
            },
            "last_test_result": test_results.get("llm"),
        },
        "app": {
            "output_language": config.app.output_language,
            "alert_mode": config.alerts.default_mode,
            "local_server_url": status.local_server_url,
        },
        "ui": {
            "debug_mode": config.ui.debug_mode,
        },
        "notifications": {
            "fallback_enabled": config.notifications.fallback_enabled,
            "retry_attempts": config.notifications.retry_attempts,
            "retry_base_delay_seconds": config.notifications.retry_base_delay_seconds,
            "fallback_order": config.notifications.fallback_order,
            "channels": notifiers,
        },
        "sources": {
            "enabled_packages": config.sources.enabled_packages,
            "packages": source_package_status(config, status.source_states),
            "library": [_source_library_snapshot(item, status, test_results) for item in config.sources.library],
            "custom_sources": [_custom_source_snapshot(item, test_results) for item in config.sources.custom_sources],
            "last_bulk_test_result": test_results.get("sources_enabled"),
        },
        "topics": [
            {
                "name": topic.name,
                "enabled": topic.enabled,
                "keywords": topic.keywords,
                "output_language": topic.output_language,
                "min_relevance_score": topic.min_relevance_score,
            }
            for topic in config.topics
        ],
    }


def _apply_setup_payload(config_path: Path, runtime_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    config = load_config(config_path)
    env_updates: dict[str, str] = {}

    app = _object(payload.get("app"))
    output_language = app.get("output_language") or payload.get("output_language")
    if output_language:
        config.app.output_language = str(output_language)
        config.enrichment.target_language = str(output_language)

    llm = _object(payload.get("llm"))
    if llm:
        config.llm.preset = str(llm.get("preset") or config.llm.preset)
        config.llm.provider = str(llm.get("provider") or config.llm.provider)
        config.llm.base_url = str(llm.get("base_url") or config.llm.base_url)
        config.llm.model = str(llm.get("model") or config.llm.model)
        config.llm.api_key_env = str(llm.get("api_key_env") or config.llm.api_key_env)
        _secret_update(env_updates, config.llm.api_key_env, llm.get("api_key"))

    notifications = _object(payload.get("notifications"))
    if notifications:
        _apply_notification_payload(config, notifications, env_updates)

    sources = _object(payload.get("sources"))
    if sources:
        if "enabled_packages" in sources:
            packages = _string_list(sources.get("enabled_packages"))
            unknown = sorted(set(packages) - set(SOURCE_PACKAGES))
            if unknown:
                raise ValueError(f"Unknown source package: {', '.join(unknown)}")
            config.sources.enabled_packages = packages
        library_enabled = _object(sources.get("library_enabled"))
        if library_enabled:
            known_ids = {item.id for item in config.sources.library}
            unknown_ids = sorted(set(library_enabled) - known_ids)
            if unknown_ids:
                raise ValueError(f"Unknown source library id: {', '.join(unknown_ids)}")
            for item in config.sources.library:
                if item.id in library_enabled:
                    item.enabled = bool(library_enabled[item.id])
        if _object(sources.get("custom_source")):
            _upsert_custom_source(config.sources.custom_sources, _object(sources.get("custom_source")))
        if _object(sources.get("custom_source_delete")):
            _delete_custom_source(config.sources.custom_sources, _object(sources.get("custom_source_delete")))

    topic_payload = _object(payload.get("topic"))
    if topic_payload:
        _upsert_topic(config.topics, topic_payload, config.app.output_language)

    validate_config(config)
    save_config(config, config_path)
    if env_updates:
        env_path = runtime_dir / ".env"
        values = read_env_values(env_path)
        values.update(env_updates)
        write_env_values(env_path, values)
        os.environ.update(env_updates)
    return _setup_snapshot(config_path, runtime_dir)


def _run_setup_test(config_path: Path, runtime_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    config = load_config(config_path)
    env_values = read_env_values(runtime_dir / ".env")
    target = str(payload.get("target") or "").strip().casefold()
    if target == "llm":
        api_key = os.environ.get(config.llm.api_key_env) or env_values.get(config.llm.api_key_env)
        return LLMClient(config.llm, api_key=api_key).diagnose().to_dict()
    if target == "source":
        url = str(payload.get("url") or "").strip()
        diagnostic = diagnose_feed_url(url, config.monitor.request_timeout_seconds)
        body = diagnostic.to_dict()
        body["result"] = {"ok": diagnostic.ok, **diagnostic.details}
        return body
    if target == "sources_enabled":
        return _test_enabled_sources(config)
    notifier = _notifier_for_channel(target, config)
    if notifier is None:
        raise ValueError(text("error.unknown_test_target", config.app.output_language))
    if hasattr(notifier, "send_test_diagnostic"):
        return notifier.send_test_diagnostic().to_dict()
    health = notifier.health_check()
    if not health.success:
        return diagnostic_error(
            target,
            "missing_required_field",
            health.error_message or text("error.notification_not_configured", config.app.output_language),
        ).to_dict()
    result = notifier.send_test() if hasattr(notifier, "send_test") else health
    if result.success:
        return diagnostic_ok(
            target,
            result.error_message
            or text("test.notification_sent", config.app.output_language, notifier=result.notifier_name),
        ).to_dict()
    return diagnostic_error(target, "unknown_error", result.error_message or "Notification test failed.").to_dict()


def _apply_notification_payload(config, notifications: dict[str, Any], env_updates: dict[str, str]) -> None:
    if "fallback_enabled" in notifications:
        config.notifications.fallback_enabled = bool(notifications["fallback_enabled"])
    if "retry_attempts" in notifications:
        config.notifications.retry_attempts = int(notifications["retry_attempts"])
    if "retry_base_delay_seconds" in notifications:
        config.notifications.retry_base_delay_seconds = float(notifications["retry_base_delay_seconds"])
    if "fallback_order" in notifications:
        config.notifications.fallback_order = _string_list(notifications["fallback_order"])

    email = _object(notifications.get("email"))
    if email:
        config.notifiers.email.enabled = bool(email.get("enabled", config.notifiers.email.enabled))
        config.notifiers.email.smtp_host = str(email.get("smtp_host") or config.notifiers.email.smtp_host)
        if email.get("smtp_port") not in (None, ""):
            config.notifiers.email.smtp_port = int(email["smtp_port"])
        if "use_tls" in email:
            config.notifiers.email.use_tls = bool(email["use_tls"])
        if "to_addrs" in email:
            config.notifiers.email.to_addrs = _string_list(email["to_addrs"])
        _secret_update(env_updates, config.notifiers.email.username_env, email.get("username"))
        _secret_update(env_updates, config.notifiers.email.password_env, email.get("password"))
        _secret_update(env_updates, config.notifiers.email.from_addr_env, email.get("from_addr"))

    telegram = _object(notifications.get("telegram"))
    if telegram:
        config.notifiers.telegram.enabled = bool(telegram.get("enabled", config.notifiers.telegram.enabled))
        _secret_update(env_updates, config.notifiers.telegram.bot_token_env, telegram.get("bot_token"))
        _secret_update(env_updates, config.notifiers.telegram.chat_id_env, telegram.get("chat_id"))

    wecom = _object(notifications.get("wecom"))
    if wecom:
        config.notifiers.wecom.enabled = bool(wecom.get("enabled", config.notifiers.wecom.enabled))
        _secret_update(env_updates, config.notifiers.wecom.webhook_url_env, wecom.get("webhook_url"))

    wechat = _object(notifications.get("wechat"))
    if wechat:
        config.notifiers.wechat.enabled = bool(wechat.get("enabled", config.notifiers.wechat.enabled))
        config.notifiers.wechat.provider = str(wechat.get("provider") or config.notifiers.wechat.provider)
        _secret_update(env_updates, config.notifiers.wechat.webhook_url_env, wechat.get("webhook_url"))

    qq = _object(notifications.get("qq"))
    if qq:
        config.notifiers.qq.enabled = bool(qq.get("enabled", config.notifiers.qq.enabled))
        config.notifiers.qq.provider = str(qq.get("provider") or config.notifiers.qq.provider)
        _secret_update(env_updates, config.notifiers.qq.webhook_url_env, qq.get("webhook_url"))

    generic = _object(notifications.get("generic_webhook"))
    if generic:
        config.notifiers.generic_webhook.enabled = bool(
            generic.get("enabled", config.notifiers.generic_webhook.enabled)
        )
        _secret_update(env_updates, config.notifiers.generic_webhook.url_env, generic.get("url"))


def _upsert_custom_source(custom_sources: list[CustomNewsSourceConfig], payload: dict[str, Any]) -> None:
    name = str(payload.get("name") or "").strip()
    url = str(payload.get("url") or "").strip()
    if not name or not url:
        raise ValueError("Custom source name and URL are required.")
    source = CustomNewsSourceConfig(
        name=name,
        url=url,
        enabled=bool(payload.get("enabled", True)),
        kind=str(payload.get("kind") or "rss"),
        category=str(payload.get("category") or "Custom"),
        reliability_score=float(payload.get("reliability_score") or 0.6),
        ownership=str(payload.get("ownership")) if payload.get("ownership") else None,
        bias_hint=str(payload.get("bias_hint")) if payload.get("bias_hint") else None,
        default_language=str(payload.get("default_language")) if payload.get("default_language") else None,
        website_url=str(payload.get("website_url")) if payload.get("website_url") else None,
        help_url=str(payload.get("help_url")) if payload.get("help_url") else None,
    )
    for index, existing in enumerate(custom_sources):
        if existing.name.casefold() == name.casefold() or existing.url.casefold() == url.casefold():
            custom_sources[index] = source
            return
    custom_sources.append(source)


def _delete_custom_source(custom_sources: list[CustomNewsSourceConfig], payload: dict[str, Any]) -> None:
    name = str(payload.get("name") or "").strip().casefold()
    url = str(payload.get("url") or "").strip().casefold()
    if not name and not url:
        raise ValueError("Custom source name or URL is required.")
    custom_sources[:] = [
        source
        for source in custom_sources
        if not ((name and source.name.casefold() == name) or (url and source.url.casefold() == url))
    ]


def _upsert_topic(topics: list[TopicConfig], payload: dict[str, Any], default_language: str) -> None:
    name = str(payload.get("name") or "").strip()
    prompt = str(payload.get("prompt") or "").strip()
    if not name or not prompt:
        return
    keywords = _string_list(payload.get("keywords"))
    topic = TopicConfig(
        name=name,
        enabled=bool(payload.get("enabled", True)),
        prompt=prompt,
        keywords=keywords,
        related_stocks=_string_list(payload.get("related_stocks")),
        output_language=str(payload.get("output_language") or default_language),
        min_relevance_score=int(payload.get("min_relevance_score") or 80),
        cooldown_minutes=_optional_int(payload.get("cooldown_minutes")),
        poll_interval_seconds=_optional_int(payload.get("poll_interval_seconds")),
        official_rss_urls=_string_list(payload.get("official_rss_urls")),
        broad_search=bool(payload.get("broad_search", not keywords)),
    )
    for index, existing in enumerate(topics):
        if existing.name.casefold() == name.casefold():
            topics[index] = topic
            return
    topics.append(topic)


def _notifier_for_channel(channel: str, config):
    timeout = config.monitor.request_timeout_seconds
    if channel == "email":
        return EmailNotifier(config.notifiers.email)
    if channel == "telegram":
        return TelegramNotifier(config.notifiers.telegram, timeout)
    if channel == "wecom":
        return WeComNotifier(config.notifiers.wecom, timeout)
    if channel == "wechat":
        return RelayWebhookNotifier(config.notifiers.wechat, timeout)
    if channel == "qq":
        return RelayWebhookNotifier(config.notifiers.qq, timeout)
    if channel == "generic_webhook":
        return GenericWebhookNotifier(config.notifiers.generic_webhook, timeout)
    return None


def _test_enabled_sources(config) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for target in _enabled_source_targets(config):
        if target["kind"] == "json_api":
            diagnostic = _diagnose_json_source(target, config.monitor.request_timeout_seconds)
        else:
            diagnostic = diagnose_feed_url(str(target["url"]), config.monitor.request_timeout_seconds)
        body = diagnostic.to_dict()
        body.update({"name": target["name"], "url": target["url"], "kind": target["kind"]})
        results.append(body)
    total = len(results)
    passed = sum(1 for item in results if item["ok"])
    failed = total - passed
    details = {"summary": {"total": total, "passed": passed, "failed": failed}, "results": results}
    if total == 0:
        return diagnostic_error(
            "sources_enabled",
            "missing_required_field",
            "No enabled sources are available to test.",
            missing_fields=["enabled_sources"],
            required_fields=["enabled_sources"],
            configured=False,
            details=details,
        ).to_dict()
    if failed:
        return diagnostic_error(
            "sources_enabled",
            "unknown_error",
            f"{failed} of {total} enabled sources failed diagnostics.",
            suggested_fix="Open failed source details, check each URL, and disable or replace broken feeds.",
            details=details,
        ).to_dict()
    return diagnostic_ok("sources_enabled", f"{passed} enabled sources passed diagnostics.", details=details).to_dict()


def _remember_test_result(
    test_results: dict[str, dict[str, Any]],
    request_payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    target = str(result.get("target") or request_payload.get("target") or "").strip().casefold()
    if not target:
        return
    test_results[target] = result
    if target == "source":
        url = str(request_payload.get("url") or "").strip()
        if url:
            test_results[f"source:{url}"] = result


def _enabled_source_targets(config) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    if config.sources.gdelt.enabled:
        first_topic = next((topic for topic in config.topics if topic.enabled), None)
        try:
            params = gdelt_params_for_topic(
                first_topic
                or TopicConfig(name="GDELT Smoke", enabled=True, prompt="", keywords=["artificial intelligence"]),
                max_records=1,
            )
            query_error = None
        except ValueError as exc:
            params = {
                "query": build_gdelt_query(
                    TopicConfig(name="GDELT Smoke", enabled=True, prompt="", keywords=["artificial intelligence"])
                ),
                "mode": "ArtList",
                "format": "json",
                "maxrecords": "1",
                "sort": "HybridRel",
            }
            query_error = str(exc)
        targets.append(
            {
                "name": "GDELT Production Query",
                "kind": "json_api",
                "url": "https://api.gdeltproject.org/api/v2/doc/doc",
                "params": params,
                "diagnostic_shape": "production_topic",
                "query_error": query_error,
            }
        )
        targets.append(
            {
                "name": "GDELT Smoke Query",
                "kind": "json_api",
                "url": "https://api.gdeltproject.org/api/v2/doc/doc",
                "params": {
                    "query": "artificial intelligence",
                    "mode": "ArtList",
                    "format": "json",
                    "maxrecords": "1",
                    "sort": "HybridRel",
                },
                "diagnostic_shape": "smoke",
            }
        )
    if config.sources.google_news_rss.enabled:
        targets.append(
            {
                "name": "Google News RSS",
                "kind": "rss",
                "url": (
                    "https://news.google.com/rss/search?"
                    f"q={quote_plus(_sample_query(config))}&hl=en&gl=US&ceid=US:en"
                ),
            }
        )
    if config.sources.yahoo_finance_rss.enabled:
        targets.extend(
            [
                {"name": "Yahoo Finance RSS", "kind": "rss", "url": "https://finance.yahoo.com/news/rssindex"},
                {"name": "Yahoo Finance Top Stories", "kind": "rss", "url": "https://finance.yahoo.com/rss/topstories"},
            ]
        )
    if config.sources.public_rss.enabled and config.sources.public_rss.urls:
        targets.extend({"name": "Public RSS", "kind": "rss", "url": url} for url in config.sources.public_rss.urls)
    if config.sources.official_rss.enabled and config.sources.official_rss.urls:
        targets.extend({"name": "Official RSS", "kind": "rss", "url": url} for url in config.sources.official_rss.urls)
    targets.extend(
        {"name": source.name, "kind": "rss", "url": source.url} for source in enabled_library_sources(config.sources)
    )
    targets.extend(
        {"name": source.name, "kind": "rss", "url": source.url}
        for source in config.sources.custom_sources
        if source.enabled and source.kind == "rss"
    )
    return targets


def _sample_query(config) -> str:
    for topic in config.topics:
        if topic.enabled:
            return topic.keywords[0] if topic.keywords else topic.name
    return "artificial intelligence"


def _diagnose_json_source(target: dict[str, Any], timeout_seconds: int) -> DiagnosticResult:
    if not is_valid_http_url(target["url"]):
        return invalid_url_result("source", target["url"], required_fields=["url"])
    if target.get("query_error"):
        category = _category_from_prefixed_error(str(target["query_error"]))
        return diagnostic_error(
            "source",
            category,
            "Source API diagnostic query is invalid.",
            technical_detail=target["query_error"],
            details={"diagnostic_shape": target.get("diagnostic_shape")},
        )
    params = target.get("params") or {
        "query": target.get("query") or "artificial intelligence",
        "mode": "ArtList",
        "format": "json",
        "maxrecords": "1",
        "sort": "HybridRel",
    }
    client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        validate_gdelt_query(str(params.get("query") or ""))
        response = request_with_retries(client, "GET", target["url"], params=params)
        payload = parse_gdelt_json_response(response)
        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        details = {
            "entries": len(articles),
            "sample_titles": [str(item.get("title", "")) for item in articles[:3]],
            "query_length": len(str(params.get("query") or "")),
            "diagnostic_shape": target.get("diagnostic_shape", "custom"),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
        }
        if not articles:
            return diagnostic_error("source", "feed_empty", "Source API returned no entries.", details=details)
        return diagnostic_ok("source", "Source API test completed.", details=details)
    except httpx.HTTPError as exc:
        category = classify_feed_http_error(exc)
        return diagnostic_error(
            "source",
            category,
            _json_source_error_message(category),
            technical_detail=exc,
            details=_http_error_details(exc, target),
        )
    except ValueError as exc:
        return diagnostic_error(
            "source",
            _category_from_prefixed_error(str(exc)),
            _json_source_error_message(_category_from_prefixed_error(str(exc))),
            technical_detail=exc,
            details={"diagnostic_shape": target.get("diagnostic_shape", "custom")},
        )
    finally:
        client.close()


def _category_from_prefixed_error(value: str) -> str:
    prefix = value.split(":", 1)[0].strip()
    return prefix if prefix in SUGGESTED_FIXES else "feed_parse_failed"


def _json_source_error_message(category: str) -> str:
    return {
        "api_rate_limited": "Source API is rate limited.",
        "api_timeout": "Source API timed out.",
        "api_bad_response": "Source API returned an unexpected response.",
        "query_too_long": "Source API query is too long.",
        "unsupported_query_shape": "Source API query shape is unsupported.",
        "invalid_encoded_query": "Source API query encoding is invalid.",
        "feed_parse_failed": "Source API did not return valid JSON.",
    }.get(category, "Source API is unreachable.")


def _http_error_details(exc: httpx.HTTPError, target: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {"diagnostic_shape": target.get("diagnostic_shape", "custom")}
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        details.update(
            {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "response_preview": sanitize_for_log(response.text[:300].strip().replace("\n", " ")),
            }
        )
    return details


def _source_library_snapshot(
    item: SourceLibraryItem,
    status: RuntimeStatus,
    test_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state = status.source_states.get(item.name, {})
    test_results = test_results or {}
    return {
        "id": item.id,
        "name": item.name,
        "enabled": item.enabled,
        "kind": item.kind,
        "source_type": item.source_type,
        "category": item.category,
        "packages": item.packages,
        "language": item.language,
        "reliability_score": item.reliability_score,
        "source_tier": item.source_tier,
        "source_role": item.source_role,
        "state_affiliated": item.state_affiliated,
        "propaganda_risk": item.propaganda_risk,
        "editorial_context": item.editorial_context,
        "ownership": item.ownership,
        "bias_hint": item.bias_hint,
        "url": item.url,
        "website_url": item.website_url,
        "help_url": item.help_url,
        "health": state.get("health", "not_checked"),
        "freshness_state": state.get("freshness_state", "unknown"),
        "last_fetch_time": state.get("last_fetch_time"),
        "last_success_time": state.get("last_success_time"),
        "last_failure_time": state.get("last_failure_time"),
        "last_failure_reason": state.get("last_failure_reason"),
        "last_error_category": state.get("last_error_category"),
        "failure_count": state.get("failure_count", 0),
        "consecutive_failures": state.get("consecutive_failures", state.get("failure_count", 0)),
        "average_latency_ms": state.get("average_latency_ms"),
        "current_backoff_seconds": state.get("current_backoff_seconds", 0),
        "next_retry_at": state.get("next_retry_at"),
        "backoff_active": state.get("backoff_active", False),
        "cache_status": state.get("cache_status"),
        "cached_article_count": state.get("cached_article_count", 0),
        "recent_article_count": state.get("articles", 0),
        "last_test_result": test_results.get(f"source:{item.url}"),
    }


def _custom_source_snapshot(
    item: CustomNewsSourceConfig,
    test_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    data = asdict(item)
    data["freshness_state"] = "unknown"
    data["last_test_result"] = (test_results or {}).get(f"source:{item.url}")
    return data


def _state_for_notifier(status: RuntimeStatus, name: str) -> dict[str, Any]:
    state = status.notifier_states.get(name, {})
    return {
        "health": state.get("health", status.notifier_health.get(name, "not_checked")),
        "last_success_time": state.get("last_success_time"),
        "last_failure_time": state.get("last_failure_time"),
        "failure_count": state.get("failure_count", 0),
        "last_error": state.get("last_error_message"),
        "last_error_category": state.get("last_error_category"),
        "last_test_result": state.get("last_test_result"),
    }


def _missing_llm_fields(config, env_values: dict[str, str]) -> list[str]:
    missing = []
    if not _has_real_value(config.llm.provider):
        missing.append("provider")
    if not _has_real_value(config.llm.base_url):
        missing.append("base_url")
    elif not is_valid_http_url(config.llm.base_url):
        missing.append("base_url")
    if not _has_real_value(config.llm.model):
        missing.append("model")
    if not _has_secret(config.llm.api_key_env, env_values):
        missing.append("api_key")
    return missing


def _required_fields_for_channel(channel: str) -> list[str]:
    return {
        "email": [
            "enabled",
            "smtp_host",
            "smtp_port",
            "starttls",
            "smtp_username",
            "smtp_app_password",
            "from_address",
            "recipients",
        ],
        "telegram": ["enabled", "bot_token", "chat_id"],
        "wecom": ["enabled", "webhook_url"],
        "wechat": ["enabled", "provider", "webhook_url"],
        "qq": ["enabled", "provider", "webhook_url"],
        "generic_webhook": ["enabled", "url", "method"],
    }.get(channel, [])


def _missing_fields_for_channel(channel: str, config, env_values: dict[str, str]) -> list[str]:
    missing: list[str] = []
    if channel == "email":
        email = config.notifiers.email
        username = os.environ.get(email.username_env) or env_values.get(email.username_env, "")
        from_addr = os.environ.get(email.from_addr_env) or env_values.get(email.from_addr_env, "")
        if not _has_real_value(email.smtp_host):
            missing.append("smtp_host")
        if not email.smtp_port:
            missing.append("smtp_port")
        if not _has_secret(email.username_env, env_values):
            missing.append("smtp_username")
        elif not is_valid_email_address(username):
            missing.append("smtp_username")
        if not _has_secret(email.password_env, env_values):
            missing.append("smtp_app_password")
        if not _has_real_value(from_addr):
            missing.append("from_address")
        elif not is_valid_email_address(from_addr):
            missing.append("from_address")
        if not _has_real_value(email.to_addrs):
            missing.append("recipients")
        elif any(not is_valid_email_address(addr) for addr in email.to_addrs):
            missing.append("recipients")
        return missing
    if channel == "telegram":
        telegram = config.notifiers.telegram
        if not _has_secret(telegram.bot_token_env, env_values):
            missing.append("bot_token")
        if not _has_secret(telegram.chat_id_env, env_values):
            missing.append("chat_id")
        return missing
    if channel == "wecom" and not _has_secret(config.notifiers.wecom.webhook_url_env, env_values):
        return ["webhook_url"]
    if channel == "wechat" and not _has_secret(config.notifiers.wechat.webhook_url_env, env_values):
        return ["webhook_url"]
    if channel == "qq" and not _has_secret(config.notifiers.qq.webhook_url_env, env_values):
        return ["webhook_url"]
    if channel == "generic_webhook" and not _has_secret(config.notifiers.generic_webhook.url_env, env_values):
        return ["url"]
    return missing


def _email_setup_warnings(config, env_values: dict[str, str]) -> list[str]:
    email = config.notifiers.email
    username = os.environ.get(email.username_env) or env_values.get(email.username_env, "")
    from_addr = os.environ.get(email.from_addr_env) or env_values.get(email.from_addr_env, "")
    warnings = []
    if username and from_addr and username.casefold() != from_addr.casefold():
        warnings.append("From address differs from SMTP username; confirm the provider allows this sender alias.")
    if email.smtp_host == "smtp.gmail.com" and email.smtp_port != 587:
        warnings.append("Gmail usually uses smtp.gmail.com port 587 with STARTTLS.")
    return warnings


def _suggested_fix_for_missing(missing_fields: list[str]) -> str | None:
    if not missing_fields:
        return None
    return SUGGESTED_FIXES["missing_required_field"]


def _fallback_priority(order: list[str], key: str) -> int | None:
    try:
        return order.index(key) + 1
    except ValueError:
        return None


def _has_secret(env_name: str | None, env_values: dict[str, str]) -> bool:
    if not env_name:
        return False
    value = os.environ.get(env_name) or env_values.get(env_name) or ""
    return _has_real_value(value)


def _has_real_value(value: object) -> bool:
    if isinstance(value, list):
        return any(_has_real_value(item) for item in value)
    text = str(value or "").strip()
    lowered = text.casefold()
    if lowered in PLACEHOLDER_SECRET_VALUES:
        return False
    return not lowered.startswith("your_") and lowered not in {"your_email@example.com", "example@example.com"}


def _secret_update(target: dict[str, str], env_name: str | None, value: object) -> None:
    if not env_name:
        return
    text = str(value or "").strip()
    if text:
        target[env_name] = text


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.replace(",", "\n").splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def _index_html() -> str:
    locales = json.dumps({"en": catalog("en"), "zh-CN": catalog("zh-CN")}, ensure_ascii=True)
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI News Monitor</title>
  <style>
    :root{color-scheme:light;--bg:#eef5f2;--panel:#fbfcfd;--surface:#f7faf9;--text:#172033;--muted:#506176;--line:#d5e1df;--blue:#2563eb;--teal:#0f766e;--green:#067647;--red:#b42318;--amber:#a15c07}
    *{box-sizing:border-box}html{background:var(--bg)}body{margin:0;font:14px -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;line-height:1.45;background:var(--bg);color:var(--text);overflow-x:hidden;-webkit-tap-highlight-color:rgba(37,99,235,.12)}
    a{color:var(--blue)}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid rgba(37,99,235,.28);outline-offset:2px}
    body,.card,.list,.row,.hint,.value,.badge,pre,code,a,button,details,.safe-long-text,.safe-code-block,.safe-log-block,.diagnostic-row{overflow-wrap: anywhere;word-break: break-word;max-width: 100%}
    .skip-link{position:absolute;left:12px;top:12px;transform:translateY(-140%);background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 10px;z-index:20}.skip-link:focus-visible{transform:none}
    .shell{display:grid;grid-template-columns:232px minmax(0,1fr);min-height:100vh}
    aside{border-right:1px solid var(--line);background:rgba(247,250,249,.9);backdrop-filter:saturate(180%) blur(18px);padding:20px;position:sticky;top:0;height:100vh}
    main{min-width:0;padding:24px clamp(16px,3vw,36px)}
    h1{font-size:24px;margin:0 0 6px;text-wrap:balance}h2{font-size:18px;margin:0 0 12px}h3{font-size:14px;margin:0 0 8px}.sub{color:var(--muted);margin:0 0 18px}
    .brand{font-weight:700;font-size:17px;margin-bottom:18px}.nav{display:grid;gap:6px}.nav button{width:100%;text-align:left;border:0;background:transparent;color:#263244;border-radius:8px;padding:10px 12px;cursor:pointer;touch-action:manipulation}
    .nav button:hover,.nav button[aria-selected=true]{background:#e2f1ee;color:#0f5d57}.status-pill{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--line);border-radius:999px;padding:4px 9px;background:var(--panel);font-size:12px;color:var(--muted)}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr));gap:12px}.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;min-width:0;box-shadow:0 1px 2px rgba(20,32,51,.04)}.label{color:var(--muted);font-size:12px}.value{font-size:18px;font-weight:650;margin-top:6px;word-break:break-word;font-variant-numeric:tabular-nums}
    .section{display:none}.section.active{display:block}.panel-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:12px;margin-top:12px}.feedback-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))}.card.wide{grid-column:span 2}.list{white-space:pre-wrap;max-height:420px;overflow:auto;word-break:break-word}.list.tall{min-height:clamp(220px,42vh,360px);max-height:62vh}.table{display:grid;gap:8px}.row{display:grid;grid-template-columns:minmax(120px,1.2fr) minmax(90px,.8fr) minmax(0,2fr);gap:10px;border-bottom:1px solid var(--line);padding:8px 0;align-items:start}.row:last-child{border-bottom:0}.ok{color:var(--green)}.bad{color:var(--red)}.empty{color:var(--muted)}
    .wizard{border:1px solid #b9d8d1;background:#e7f3f0}.steps{margin:0;padding-left:18px}.steps li{margin:6px 0}
    form{display:grid;gap:14px}.field{display:grid;gap:6px}.field label{font-weight:600}.field input,.field select,.field textarea{width:100%;border:1px solid var(--line);border-radius:8px;padding:9px 10px;background:#fff;color:var(--text);font:inherit}.field textarea{min-height:110px;resize:vertical}.hint{color:var(--muted);font-size:12px;line-height:1.45}.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:12px}.card-head{display:flex;gap:10px;justify-content:space-between;align-items:start;margin-bottom:10px}.channel-card{display:grid;gap:10px}.channel-meta{display:flex;flex-wrap:wrap;gap:6px}.badge{border:1px solid var(--line);border-radius:999px;padding:2px 8px;font-size:12px;color:var(--muted);background:#fff}.badge.bad{border-color:#f4b7ae;color:var(--red);background:#fff6f4}.badge.ok{border-color:#a9e7ca;color:var(--green);background:#f3fcf7}.diagnostic-box{border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:8px;background:#fff;padding:10px;white-space:pre-wrap;word-break:break-word}.diagnostic-box.bad{border-left-color:var(--red)}.diagnostic-box.ok{border-left-color:var(--green)}.toast{position:fixed;right:18px;bottom:18px;max-width:min(680px,calc(100vw - 36px));min-height:72px;border:1px solid var(--line);border-radius:8px;background:#fff;padding:14px 16px;box-shadow:0 18px 42px rgba(20,32,51,.16);z-index:10;white-space:pre-wrap}.toast[hidden]{display:none}.small-button{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:7px 10px;cursor:pointer;touch-action:manipulation}.debug-details{border:1px solid var(--line);border-radius:8px;padding:10px;background:#fff}.debug-details summary{cursor:pointer;font-weight:650}.safe-code-block,.safe-log-block{white-space:pre-wrap;margin:8px 0 0;font-size:12px;overflow:auto}.safe-long-text{min-width:0}.diagnostic-row{display:grid;grid-template-columns:minmax(120px,1.2fr) minmax(90px,.8fr) minmax(0,2fr);gap:10px;border-bottom:1px solid var(--line);padding:8px 0;align-items:start}.diagnostic-row:last-child{border-bottom:0}
    .package-row{display:grid;grid-template-columns:minmax(140px,1fr) minmax(0,2fr);gap:12px;border-bottom:1px solid var(--line);padding:10px 0;align-items:start}.package-row:last-child{border-bottom:0}.package-title{display:block;font:inherit;font-weight:650;line-height:1.35;color:var(--text);letter-spacing:0}.package-status{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}.package-detail{font-size:13px;line-height:1.5;color:var(--text);letter-spacing:0}.package-detail .hint,.package-warning{display:block;margin-top:4px;font-size:12px;line-height:1.45;letter-spacing:0}.package-warning{color:var(--amber)}.package-action{margin-top:8px;font-size:12px;line-height:1.2;cursor:default;color:var(--muted)}
    .actions{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}.actions button,.actions a{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:9px 12px;cursor:pointer;text-decoration:none;touch-action:manipulation}.actions button[data-action=start],.actions button[data-action=run_once]{background:var(--blue);border-color:var(--blue);color:#fff}.actions button[data-action=stop]{background:#fff6f4;border-color:#f4b7ae;color:var(--red)}.actions button:hover,.actions a:hover,.small-button:hover{border-color:var(--blue);color:var(--blue)}.actions button[data-action=start]:hover,.actions button[data-action=run_once]:hover{background:#1d4ed8;color:#fff}.actions button[data-action=stop]:hover{border-color:#e4897e;color:#912018}.actions button:disabled{cursor:wait;opacity:.62}
    .notice{border-left:4px solid var(--amber);background:#fffaf0}.metric-line{font-weight:650;margin-bottom:8px}.event-row{border-bottom:1px solid var(--line);padding:10px 0}.event-row:last-child{border-bottom:0}.compact-kv{display:grid;grid-template-columns:minmax(120px,.8fr) minmax(0,1.2fr);gap:6px 10px}.compact-kv div:nth-child(odd){color:var(--muted)}pre{white-space:pre-wrap;margin:8px 0 0;font-size:12px}
    @media (max-width:980px){.card.wide{grid-column:auto}}@media (max-width:820px){.shell{grid-template-columns:1fr}aside{position:static;height:auto}.nav{grid-template-columns:repeat(2,minmax(0,1fr))}.row,.diagnostic-row,.package-row{grid-template-columns:1fr}.list.tall{min-height:clamp(180px,36vh,260px)}}@media (max-width:520px){main{padding:16px 12px}.nav{grid-template-columns:1fr}.actions button,.actions a{width:100%}.toast{left:12px;right:12px;bottom:12px;max-width:none}}
  </style>
</head>
<body>
<a class="skip-link" href="#main" data-i18n="skip_to_main">Skip to main content</a>
<div class="shell">
  <aside>
    <div class="brand" translate="no">AI News Monitor</div>
    <nav class="nav" aria-label="Console sections" data-i18n-aria-label="console_sections">
      <button type="button" data-tab="dashboard" aria-selected="true">Dashboard</button>
      <button type="button" data-tab="sources">Sources</button>
      <button type="button" data-tab="notifications">Notifications</button>
      <button type="button" data-tab="topics">Topics</button>
      <button type="button" data-tab="alerts">Alerts</button>
      <button type="button" data-tab="diagnostics">Diagnostics</button>
      <button type="button" data-tab="logs">Logs</button>
    </nav>
  </aside>
  <main id="main" tabindex="-1">
    <section id="dashboard" class="section active" aria-labelledby="dashboard-title">
      <h1 id="dashboard-title" data-i18n="local_control_console">Local Control Console</h1>
      <p class="sub" data-i18n="local_console_subtitle">Live status for the local monitor server.</p>
      <div class="actions" aria-label="Monitor controls" data-i18n-aria-label="monitor_controls">
        <button type="button" data-action="start">Start</button>
        <button type="button" data-action="pause">Pause</button>
        <button type="button" data-action="resume">Resume</button>
        <button type="button" data-action="stop">Stop</button>
        <button type="button" data-action="run_once">Run Once</button>
        <button type="button" data-action="e2e_test">E2E Test</button>
      </div>
      <div class="card notice" id="pauseWarning" data-i18n="monitoring_paused_warning" hidden>Monitoring is paused. No new alerts will be sent until you resume.</div>
      <div class="card wizard" id="wizard" hidden>
        <h2 data-i18n="setup.title">First-run Setup</h2>
        <ol class="steps">
          <li data-i18n="setup.step_llm">Add an LLM API key.</li>
          <li data-i18n="setup.step_sources">Choose source packages and add at least one topic.</li>
          <li data-i18n="setup.step_notifications">Configure and test one notification channel.</li>
          <li data-i18n="setup.step_start">Start monitoring and keep this computer awake.</li>
        </ol>
      </div>
      <section class="grid" id="stats" aria-live="polite"></section>
      <section class="panel-grid feedback-grid">
        <div class="card"><h2 data-i18n="connection_health">Connection Health</h2><div class="list" id="health">-</div></div>
        <div class="card"><h2 data-i18n="pipeline_funnel">Pipeline Funnel</h2><div class="list" id="pipelineFunnel">-</div></div>
        <div class="card"><h2 data-i18n="notification_health">Notification Health</h2><div class="list" id="notificationSummary">-</div></div>
        <div class="card"><h2 data-i18n="coverage_quality">Coverage Quality</h2><div class="list" id="coverageQuality">-</div></div>
        <div class="card"><h2 data-i18n="intelligence_gaps">Intelligence Gaps</h2><div class="list" id="gapRows">-</div></div>
        <div class="card wide"><h2 data-i18n="live_events">Real-time Events</h2><div class="list tall" id="events" aria-live="polite">Connecting...</div></div>
      </section>
    </section>
    <section id="sources" class="section" aria-labelledby="sources-title">
      <h1 id="sources-title" data-i18n="sources">Sources</h1>
      <p class="sub" data-i18n="monitoring_console_readonly">This browser console is read-only. Configure sources, topics, LLM, and notifications in the desktop app before starting monitoring.</p>
      <div class="panel-grid">
        <div class="card"><h2 data-i18n="source_health">Source Health</h2><div class="table" id="sourceRows"></div></div>
        <div class="card"><h2 data-i18n="source_packages">Source Packages</h2><div class="table" id="packageRows"></div></div>
        <div class="card"><h2 data-i18n="source_freshness_summary">Source Freshness Summary</h2><div class="list" id="sourceSummary">-</div></div>
        <div class="card"><h2 data-i18n="source_cache_backoff">Source Cache and Backoff</h2><div class="list" id="cacheBackoffSummary">-</div></div>
        <div class="card"><h2 data-i18n="source_selection">Source Selection</h2><div class="table" id="sourceSelectionRows"></div></div>
        <div class="card"><h2 data-i18n="source_tier_distribution">Source Tier Distribution</h2><div class="list" id="tierRows">-</div></div>
        <div class="card"><h2 data-i18n="top_failing_sources">Top Failing Sources</h2><div class="list" id="topFailingSources">-</div></div>
        <div class="card"><h2 data-i18n="settings.source_library">Source Library</h2><div class="table" id="sourceLibraryCards"></div></div>
        <div class="card"><h2 data-i18n="settings.custom_sources">Custom Sources</h2><div class="table" id="customSourceCards"></div></div>
      </div>
    </section>
    <section id="notifications" class="section" aria-labelledby="notifications-title">
      <h1 id="notifications-title" data-i18n="notifications">Notifications</h1>
      <p class="sub" data-i18n="monitoring_console_readonly">This browser console is read-only. Configure sources, topics, LLM, and notifications in the desktop app before starting monitoring.</p>
      <div class="panel-grid" id="notifierCards"></div>
    </section>
    <section id="topics" class="section" aria-labelledby="topics-title">
      <h1 id="topics-title" data-i18n="topics">Topics</h1>
      <p class="sub" data-i18n="monitoring_console_readonly">This browser console is read-only. Configure sources, topics, LLM, and notifications in the desktop app before starting monitoring.</p>
      <div class="panel-grid">
        <div class="card"><div id="topicSummary" class="value">-</div><p class="sub" data-i18n="topic_browser_hint">Create or update a first topic here.</p></div>
        <div class="card"><h2 data-i18n="topic_overview">Topic Overview</h2><div class="table" id="topicCards"></div></div>
      </div>
    </section>
    <section id="alerts" class="section" aria-labelledby="alerts-title"><h1 id="alerts-title" data-i18n="alerts">Alerts</h1><div class="panel-grid feedback-grid"><div class="card wide"><h2 data-i18n="event_clusters">Event Clusters</h2><div class="list tall" id="eventRows"></div></div><div class="card"><h2 data-i18n="recent_alerts">Recent Alerts</h2><div class="list tall" id="alertRows"></div></div><div class="card"><h2 data-i18n="recent_matches">Recent Matches</h2><div class="list tall" id="matchRows"></div></div></div></section>
    <section id="diagnostics" class="section" aria-labelledby="diagnostics-title"><h1 id="diagnostics-title" data-i18n="diagnostics">Diagnostics</h1><div class="panel-grid feedback-grid"><div class="card wide"><h2 data-i18n="runtime">Runtime</h2><div class="list tall" id="diagnosticsRows"></div></div><div class="card"><h2 data-i18n="errors">Errors</h2><div class="list tall" id="errorRows"></div></div></div></section>
    <section id="logs" class="section" aria-labelledby="logs-title"><h1 id="logs-title" data-i18n="logs">Logs</h1><div class="card list tall" id="logRows"></div></section>
  </main>
</div>
<div class="toast" id="toast" role="status" aria-live="polite" hidden></div>
<script>
const localeCatalog = __LOCALES__;
const stats = document.getElementById('stats');
const health = document.getElementById('health');
const coverageQuality = document.getElementById('coverageQuality');
const gapRows = document.getElementById('gapRows');
const events = document.getElementById('events');
const sourceRows = document.getElementById('sourceRows');
const packageRows = document.getElementById('packageRows');
const sourceSummary = document.getElementById('sourceSummary');
const cacheBackoffSummary = document.getElementById('cacheBackoffSummary');
const sourceSelectionRows = document.getElementById('sourceSelectionRows');
const tierRows = document.getElementById('tierRows');
const topFailingSources = document.getElementById('topFailingSources');
const sourceLibraryCards = document.getElementById('sourceLibraryCards');
const customSourceCards = document.getElementById('customSourceCards');
const notifierCards = document.getElementById('notifierCards');
const topicSummary = document.getElementById('topicSummary');
const topicCards = document.getElementById('topicCards');
const eventRows = document.getElementById('eventRows');
const matchRows = document.getElementById('matchRows');
const alertRows = document.getElementById('alertRows');
const diagnosticsRows = document.getElementById('diagnosticsRows');
const errorRows = document.getElementById('errorRows');
const logRows = document.getElementById('logRows');
const wizard = document.getElementById('wizard');
const toast = document.getElementById('toast');
const pauseWarning = document.getElementById('pauseWarning');
const pipelineFunnel = document.getElementById('pipelineFunnel');
const notificationSummary = document.getElementById('notificationSummary');
let setupState = null;
let currentLang = 'en';
let debugMode = false;
let eventItems = [];
const STATUS_REFRESH_MS = 1500;
const SETUP_REFRESH_MS = 5000;
const reliabilityEndpoints = ['/api/readiness','/api/source-health','/api/intelligence-gaps','/api/coverage-quality','/api/source-packages'];
function esc(value){return String(value ?? '-').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function t(key, lang){ return (localeCatalog[lang] || localeCatalog.en || {})[key] || (localeCatalog.en || {})[key] || key; }
function normalizedKey(value){return String(value ?? '').trim().replace(/[\\s-]+/g, '_').toLowerCase();}
function labelFor(value, lang){
  const key = normalizedKey(value);
  const translated = t(key, lang);
  return translated === key ? String(value ?? '-') : translated;
}
function displayValueFor(key, value, lang){
  if(key === 'output_language') return value === 'zh-CN' ? t('language_zh_cn', lang) : t('language_en', lang);
  if(['state','alert_mode','llm_health','coverage_quality','readiness'].includes(key)) return labelFor(value, lang);
  if(typeof value === 'boolean') return value ? t('yes', lang) : t('no', lang);
  return value ?? '-';
}
function row(name, state, detail){return `<div class="diagnostic-row"><strong class="safe-long-text">${esc(name)}</strong><span class="safe-long-text">${esc(labelFor(state, currentLang))}</span><span class="safe-long-text">${esc(detail || '-')}</span></div>`;}
function statusBadge(value, lang){
  const key = normalizedKey(value);
  const label = labelFor(value, lang);
  const stateClass = ['ok','healthy','configured','enabled','fresh','high','ready','success','running'].includes(key) ? 'ok' : (['error','failed','unconfigured','missing_api_key','very_stale','critical','low','not_ready','stopped'].includes(key) ? 'bad' : '');
  return `<span class="badge ${stateClass}">${esc(label)}</span>`;
}
function safeJson(value){ try { return JSON.stringify(value || {}, null, 2); } catch(err) { return String(value || '-'); } }
function detailsBlock(value){
  if(!debugMode) return '';
  return `<details class="debug-details"><summary>${esc(t('show_details', currentLang))}</summary><button type="button" class="small-button" data-copy="${esc(safeJson(value))}">${esc(t('copy_diagnostics', currentLang))}</button><pre class="safe-code-block">${esc(safeJson(value))}</pre></details>`;
}
function kvRows(value){
  const entries = Object.entries(value || {});
  if(!entries.length) return '<span class="empty">-</span>';
  return `<div class="compact-kv">${entries.map(([k,v])=>`<div>${esc(labelFor(k, currentLang))}</div><div>${esc(labelFor(v, currentLang))}</div>`).join('')}</div>`;
}
function formatTime(value, lang){
  if(!value) return '-';
  const date = new Date(value);
  if(Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(lang, { dateStyle: 'short', timeStyle: 'medium' }).format(date);
}
function showToast(message){
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(()=>{ toast.hidden = true; }, 6000);
}
function sourceSummaryLine(name, state){
  if(typeof state === 'string') return `${name}: ${state}`;
  const health = labelFor(state.health || state.freshness_state || 'unknown', currentLang);
  const category = state.last_error_category ? ` · ${state.last_error_category}` : '';
  const retry = state.next_retry_at ? ` · ${t('retry', currentLang)} ${formatTime(state.next_retry_at, currentLang)}` : '';
  const count = Number.isFinite(Number(state.articles || state.last_article_count)) ? ` · ${state.articles || state.last_article_count || 0} ${t('articles', currentLang)}` : '';
  return `${name}: ${health}${category}${retry}${count}`;
}
function renderPipeline(funnel){
  if(!funnel || !Object.keys(funnel).length) return '<span class="empty">-</span>';
  const reasons = (funnel.top_rejection_reasons || []).map(item => `${item.count} ${item.reason}`).join('\\n') || '-';
  const main = funnel.concise_summary || `Fetched ${funnel.articles_fetched || 0} -> Alerts ${funnel.alerts_saved || 0}`;
  const result = funnel.result ? statusBadge(funnel.result, currentLang) : '';
  const counts = funnel.diagnostic_counts ? `<div class="hint">${esc(t('pipeline_stage_details', currentLang))}</div>${kvRows(funnel.diagnostic_counts)}` : '';
  return `<div class="metric-line safe-long-text">${esc(main)} ${result}</div><div class="safe-long-text">${esc(funnel.zero_alert_explanation || '-')}</div><div class="hint safe-long-text">${esc(funnel.recommended_action || '-')}</div><div class="hint safe-long-text">${esc(reasons)}</div>${counts}${detailsBlock(funnel)}`;
}
function renderTimelinePreview(items, lang){
  const rows = (items || []).slice(0, 4).map(item => {
    const time = item.time ? ` ${item.time}` : '';
    const label = item.description || item.label || '-';
    return `- ${esc(item.date || 'unknown')}${esc(time)}: ${esc(label)}`;
  });
  return rows.join('<br>') || esc(t('empty_timeline', lang));
}
function renderSourceLinks(items, lang){
  const links = (items || []).slice(0, 5).map(item => {
    const title = item.title || item.source_title || item.url || '-';
    const publisher = item.publisher ? `${item.publisher} — ` : '';
    const url = item.url || item.source_url || '#';
    return `<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(publisher + title)}</a>`;
  });
  return links.join('<br>') || esc(t('empty_sources', lang));
}
function renderEventCards(items, lang){
  return (items || []).map(event => {
    const latest = formatTime(event.latest_update_time || event.sent_at, lang);
    const articleCount = event.article_count || event.grouped_article_count || 1;
    const summary = event.summary || event.current_status || '-';
    const sources = renderSourceLinks(event.sources || event.source_links, lang);
    const verificationStatus = event.verification_status || (event.confidence_score ? 'developing' : '');
    const confidence = event.confidence_score ?? event.confidence ?? '-';
    const relevance = event.relevance_score ?? event.score ?? '-';
    const includeTimeline = event.report_include_timeline !== false;
    const includeSourceComparison = event.report_include_source_comparison !== false;
    const timelineSection = includeTimeline ? `<br><span class="hint">${esc(t('timeline', lang))}</span><br>${renderTimelinePreview(event.timeline_preview || event.timeline, lang)}` : '';
    const sourceComparison = includeSourceComparison ? ((event.source_comparison || []).slice(0, 4).map(item => `${esc(item.source || '-')}: ${esc(item.confidence || '-')} (${esc(item.score ?? '-')})`).join('<br>') || '-') : '';
    const sourceComparisonSection = includeSourceComparison ? `<br><span class="hint">${esc(t('source_comparison', lang))}</span><br>${sourceComparison}` : '';
    const badges = `${verificationStatus ? statusBadge(verificationStatus, lang) : ''}<span class="badge">${esc(t('relevance_score', lang))}: ${esc(relevance)}</span><span class="badge">${esc(t('confidence_score', lang))}: ${esc(confidence)}</span>`;
    return `<div class="event-row"><strong class="safe-long-text">${esc(event.event_title || event.title || '-')}</strong><br><div class="channel-meta">${badges}</div><span class="hint">${esc(t('grouped_articles', lang))}: ${esc(articleCount)} · ${esc(t('latest_update_time', lang))}: ${esc(latest)}</span><br><span class="safe-long-text">${esc(summary)}</span>${timelineSection}${sourceComparisonSection}<br><span class="hint">${esc(t('sources', lang))}</span><br>${sources}<br><span class="hint">${esc(t('relation_reason', lang))}: ${esc(event.relation_reason || '-')}</span>${detailsBlock(event)}</div>`;
  }).join('') || `<span class="empty">${esc(t('empty_event_clusters', lang))}</span>`;
}
function renderNotificationSummary(status){
  const states = status.notifier_states || {};
  const entries = Object.entries(states).filter(([, state]) => state.enabled);
  if(!entries.length) return `<span class="empty">${esc(t('no_enabled_notification_channels', currentLang))}</span>`;
  return entries.map(([name,state]) => {
    const health = state.health || status.notifier_health?.[name] || 'not_checked';
    const detail = state.last_error_category || state.last_error_message || state.last_success_time || '-';
    return row(name, health, detail);
  }).join('');
}
function renderSourceSelection(items, lang){
  return (items || []).slice(0, 20).map(item => {
    const mode = item.auto_selected ? t('auto_selected_source', lang) : t('manual_source', lang);
    const risk = item.risk ? `<br>${esc(t('risk', lang))}: ${esc(item.risk)}` : '';
    const priority = item.priority ?? '-';
    const detail = `${esc(mode)} · ${esc(t('priority', lang))}: ${esc(priority)}<br>${esc(t('selection_reason', lang))}: ${esc(item.reason || '-')}<br>${esc(t('expected_value', lang))}: ${esc(item.expected_value || '-')}${risk}`;
    return `<div class="diagnostic-row"><strong class="safe-long-text">${esc(item.source || '-')}</strong><span class="safe-long-text">${esc(item.topic || '-')}<br>${statusBadge(item.source_mode || '-', lang)}</span><span class="safe-long-text">${detail}</span></div>`;
  }).join('') || `<div class="empty">${esc(t('empty_source_selection', lang))}</div>`;
}
function renderReadiness(readiness){
  if(!readiness) return '<span class="empty">-</span>';
  return `${statusBadge(readiness.readiness || 'unknown', currentLang)}<br>${kvRows({
    server_alive: readiness.server_alive,
    monitor: readiness.monitor_state,
    llm_ready: readiness.llm_ready,
    notifier_ready: readiness.notifier_ready,
    source_coverage_ready: readiness.source_coverage_ready,
    coverage_quality: readiness.coverage_quality,
    critical_gaps: readiness.critical_gaps,
    last_cycle_status: readiness.last_cycle_status || '-',
    can_send_alerts: readiness.can_send_alerts,
  })}<div class="hint">${esc(readiness.recommended_action || '-')}</div>`;
}
function applyLocale(lang){
  currentLang = lang === 'zh-CN' ? 'zh-CN' : 'en';
  document.documentElement.lang = currentLang;
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n, currentLang); });
  document.querySelectorAll('[data-i18n-aria-label]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel, currentLang)); });
  document.querySelectorAll('[data-tab]').forEach(el => { el.textContent = t(el.dataset.tab, currentLang); });
  document.querySelectorAll('[data-action]').forEach(el => { el.textContent = t(el.dataset.action, currentLang); });
  if(!events.dataset.live){ events.textContent = t('connecting', currentLang); }
  if(events.dataset.live){ renderEvents(); }
}
function renderStatus(s){
  debugMode = s.ui_debug_mode === true;
  const lang = s.output_language === 'zh-CN' ? 'zh-CN' : 'en';
  const previousLang = currentLang;
  applyLocale(lang);
  if(previousLang !== currentLang){ loadSetup(); }
  wizard.hidden = setupState ? !setupState.setup_required : Boolean(s.active_topics_count);
  pauseWarning.hidden = s.state !== 'Paused';
  const items = [
    ['state', s.state], ['active_topics_count', s.active_topics_count], ['latest_articles_fetched', s.latest_articles_fetched],
    ['latest_candidates', s.latest_candidates], ['total_articles_processed', s.total_articles_processed],
    ['queue_length', s.queue_length], ['alerts_sent_today', s.alerts_sent_today], ['live_event_count', s.live_event_count],
    ['output_language', s.output_language], ['alert_mode', s.alert_mode]
  ];
  stats.innerHTML = items.map(([k,v])=>`<div class="card"><div class="label">${esc(t(k, lang))}</div><div class="value">${esc(displayValueFor(k, v, lang))}</div></div>`).join('');
  health.innerHTML = renderReadiness(s.readiness);
  pipelineFunnel.innerHTML = renderPipeline(s.pipeline_funnel || s.e2e_result);
  notificationSummary.innerHTML = renderNotificationSummary(s);
  const coverage = s.coverage_quality?.global || {};
  coverageQuality.innerHTML = `${statusBadge(coverage.coverage_quality || 'unknown', lang)}\\n${esc(coverage.reason || '-')}\\n${esc(t('recommended_action', lang))}: ${esc(coverage.recommended_action || '-')}`;
  const gaps = s.intelligence_gaps || {};
  const critical = gaps.critical_gaps || [];
  const degraded = gaps.degraded_groups || [];
  gapRows.innerHTML = [...critical, ...degraded].slice(0, 8).map(g=>`${esc(g.name)}: ${esc(labelFor(g.severity, lang))} - ${esc(g.reason)}\\n${esc(t('recommended_action', lang))}: ${esc(g.recommended_action)}`).join('\\n\\n') || esc(t('no_intelligence_gaps', lang));
  sourceRows.innerHTML = Object.entries(s.source_states || s.source_health || {}).map(([k,v])=>row(k, v.freshness_state || v.health || v, sourceSummaryLine(k, v))).join('') || `<div class="empty">${esc(t('empty_sources', lang))}</div>`;
  sourceSummary.innerHTML = kvRows(s.source_summary || {});
  cacheBackoffSummary.innerHTML = `<div class="metric-line">${esc(t('cache', lang))}</div>${kvRows(s.source_cache_summary || {})}<div class="metric-line">${esc(t('backoff', lang))}</div>${kvRows(s.source_backoff_summary || {})}`;
  sourceSelectionRows.innerHTML = renderSourceSelection(s.source_selection_summary || [], lang);
  tierRows.innerHTML = kvRows(s.source_tier_distribution || {});
  topFailingSources.textContent = (s.top_failing_sources || []).map(item=>`${item.source}: ${labelFor(item.freshness_state, lang)} (${item.failure_count}) ${item.last_error_category || ''}`).join('\\n') || t('empty_errors', lang);
  topicSummary.textContent = `${s.active_topics_count || 0} ${t('active_topics_count', lang)}`;
  eventRows.innerHTML = renderEventCards([...(s.recent_alerts || []), ...(s.recent_event_clusters || [])], lang);
  matchRows.innerHTML = (s.recent_matches || []).map(a=>`[${esc(a.score)}] ${esc(a.topic)} - <a href="${esc(a.url)}" target="_blank" rel="noreferrer">${esc(a.title)}</a>\\n${esc(a.source || '-')} - ${esc(a.reason || '-')}`).join('\\n\\n') || t('empty_matches', lang);
  alertRows.innerHTML = renderEventCards(s.recent_alerts || [], lang);
  diagnosticsRows.innerHTML = kvRows({server:s.local_server_url,state:s.state,llm_health:s.llm_health,last_fetch_time:formatTime(s.last_fetch_time, lang),last_llm_analysis_time:formatTime(s.last_llm_analysis_time, lang),last_alert_sent_time:formatTime(s.last_alert_sent_time, lang)}) + detailsBlock({coverage:s.coverage_quality,endpoints:reliabilityEndpoints,pipeline:s.pipeline_funnel});
  errorRows.textContent = s.error_message || t('empty_errors', lang);
  logRows.textContent = (s.recent_logs || []).join('\\n') || t('empty_logs', lang);
  if(events.dataset.live){ renderEvents(); }
}
function renderSetup(setup){
  setupState = setup;
  debugMode = setup.ui?.debug_mode === true;
  const lang = setup.app?.output_language === 'zh-CN' ? 'zh-CN' : 'en';
  applyLocale(lang);
  wizard.hidden = !setup.setup_required;
  packageRows.innerHTML = (setup.sources?.packages || []).map(pkg => {
    const detail = `${pkg.enabled_source_count || 0}/${pkg.source_count || 0} ${t('sources', lang)} · ${pkg.fresh_source_count || 0} ${t('fresh_count', lang)} · ${pkg.failing_source_count || 0} ${t('failing_count', lang)}`;
    const action = pkg.enabled ? t('enabled_in_desktop_app', lang) : t('enable_in_desktop_app', lang);
    const warning = (pkg.warnings || []).join('; ');
    const note = warning || pkg.recommended_action || pkg.expected_coverage || '';
    const noteClass = warning ? 'package-warning' : 'hint';
    const description = pkg.description || pkg.expected_coverage || '';
    return `<div class="package-row"><div><strong class="package-title safe-long-text">${esc(pkg.name || pkg.id)}</strong><div class="package-status">${statusBadge(pkg.enabled ? 'enabled' : 'disabled', lang)}</div></div><div class="package-detail safe-long-text"><span>${esc(detail)}</span>${description ? `<span class="hint">${esc(description)}</span>` : ''}${note ? `<span class="${noteClass}">${esc(note)}</span>` : ''}${pkg.recommended_use_case ? `<span class="hint">${esc(pkg.recommended_use_case)}</span>` : ''}<span class="hint">${esc(t('last_package_test', lang))}: ${esc(formatTime(pkg.last_package_test, lang))}</span><button type="button" class="small-button package-action" disabled>${esc(action)}</button></div></div>`;
  }).join('') || `<div class="empty">${esc(t('empty_sources', lang))}</div>`;
  const enabledPackages = new Set(setup.sources?.enabled_packages || []);
  const enabledLibrary = (setup.sources?.library || []).filter(source => source.enabled || (source.packages || []).some(id => enabledPackages.has(id)));
  sourceLibraryCards.innerHTML = enabledLibrary.map(source => {
    const website = source.website_url || source.url;
    const help = source.help_url ? `<a class="small-button" href="${esc(source.help_url)}" target="_blank" rel="noreferrer">${esc(t('help_info', lang))}</a>` : '';
    const lastTest = source.last_test_result?.message || '-';
    return `<div class="card channel-card"><div class="card-head"><div><h3>${esc(source.name)}</h3><div class="channel-meta"><span class="badge">${esc(t('tier', lang))} ${esc(source.source_tier)}</span><span class="badge">${esc(source.source_role)}</span><span class="badge">${esc(source.category)}</span><span class="badge">${esc(source.language)}</span><span class="badge">${esc(source.propaganda_risk)}</span>${statusBadge(source.freshness_state || source.health || 'not_checked', lang)}</div></div></div><div class="hint">${esc(sourceSummaryLine(source.name, source))}</div>${detailsBlock(source)}<div class="actions"><a class="small-button" href="${esc(website)}" target="_blank" rel="noreferrer">${esc(t('settings.open_source_website', lang))}</a>${help}</div></div>`;
  }).join('') || `<div class="empty">${esc(t('empty_sources', lang))}</div>`;
  customSourceCards.innerHTML = (setup.sources?.custom_sources || []).map(source => {
    return `<div class="diagnostic-row"><strong class="safe-long-text">${esc(source.name)}</strong><span class="safe-long-text">${esc(source.default_language || source.kind || 'rss')}</span><span class="safe-long-text"><a href="${esc(source.url)}" target="_blank" rel="noreferrer">${esc(t('source_url', lang))}</a></span></div>`;
  }).join('') || `<div class="empty">${esc(t('empty_custom_sources', lang))}</div>`;
  notifierCards.innerHTML = Object.entries(setup.notifications?.channels || {}).map(([key, ch]) => {
    const health = ch.health || {};
    const missing = (ch.missing_fields || []).join(', ') || '-';
    const required = (ch.required_fields || []).join(', ') || '-';
    const help = ch.help_link ? `<a class="small-button" href="${esc(ch.help_link)}" target="_blank" rel="noreferrer">${esc(t('help_info', lang))}</a>` : '';
    const lastTest = ch.last_test_result?.message || health.last_test_result || '-';
    return `<div class="card channel-card"><div class="card-head"><div><h2>${esc(ch.name)}</h2><div class="channel-meta">${statusBadge(ch.enabled ? 'enabled' : 'disabled', lang)}${statusBadge(ch.configured ? 'configured' : 'unconfigured', lang)}${statusBadge(health.health || 'not_checked', lang)}</div></div></div><div class="hint">${esc(t('required_fields', lang))}: ${esc(required)}<br>${esc(t('missing_fields', lang))}: ${esc(missing)}<br>${esc(t('suggested_fix', lang))}: ${esc(ch.suggested_fix || '-')}<br>${esc((ch.warnings || []).join('; ') || '-')}<br>${esc(t('last_test_result', lang))}: ${esc(lastTest)}</div>${detailsBlock(ch)}<div class="actions">${help}</div></div>`;
  }).join('');
  topicCards.innerHTML = (setup.topics || []).map(topic => {
    const keywords = (topic.keywords || []).join(', ') || '-';
    const score = topic.min_relevance_score ?? '-';
    return `<div class="card channel-card"><div class="card-head"><div><h3>${esc(topic.name || '-')}</h3><div class="channel-meta">${statusBadge(topic.enabled ? 'enabled' : 'disabled', lang)}<span class="badge">${esc(topic.output_language || '-')}</span><span class="badge">${esc(t('topic_min_relevance', lang))}: ${esc(score)}</span></div></div></div><div class="hint">${esc(t('topic_keywords', lang))}: ${esc(keywords)}</div></div>`;
  }).join('') || `<div class="empty">${esc(t('empty_topics', lang))}</div>`;
}
async function loadSetup(){ const r = await fetch('/api/setup'); if(r.ok){ renderSetup(await r.json()); } }
async function refresh(){ const r = await fetch('/api/status'); renderStatus(await r.json()); }
refresh(); loadSetup(); setInterval(refresh, STATUS_REFRESH_MS); setInterval(loadSetup, SETUP_REFRESH_MS);
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', async () => {
  button.disabled = true;
  try {
    const response = await fetch('/api/control', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:button.dataset.action})});
    if(!response.ok){ throw new Error(await response.text()); }
    await refresh();
  } catch(err) {
    showToast(err.message);
  } finally {
    button.disabled = false;
  }
}));
document.addEventListener('click', async event => {
  const button = event.target.closest('[data-copy]');
  if(!button) return;
  await navigator.clipboard.writeText(button.dataset.copy || '');
  showToast(t('diagnostics_copied', currentLang));
});
document.querySelectorAll('.nav button').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.nav button').forEach(item => item.setAttribute('aria-selected', String(item === button)));
  document.querySelectorAll('.section').forEach(section => section.classList.toggle('active', section.id === button.dataset.tab));
  history.replaceState(null, '', `#${button.dataset.tab}`);
}));
if(location.hash){const target=document.querySelector(`[data-tab="${location.hash.slice(1)}"]`);if(target)target.click();}
const es = new EventSource('/events');
function eventSummary(name, payload){
  if(name === 'source_fetch') return `${name} · ${payload.source || '-'} · ${payload.ok ? t('ok', currentLang) : t('failed', currentLang)}${payload.category ? ' · ' + payload.category : ''}`;
  if(name === 'cycle_completed') return `${name} · ${payload.pipeline || '-'} · ${labelFor(payload.result || '-', currentLang)}`;
  if(name === 'notification_result') return `${name} · ${payload.notifier || '-'} · ${payload.ok ? t('ok', currentLang) : t('failed', currentLang)}`;
  if(name === 'alert_sent') return `${name} · ${payload.topic || '-'} · ${payload.relevance_score || '-'} · ${labelFor(payload.verification_status || '-', currentLang)}`;
  if(name === 'candidate_ranked') return `${name} · ${payload.source || '-'} · ${payload.ranking_score || '-'}`;
  if(name === 'status') return `${name} · ${labelFor(payload.status || '-', currentLang)}`;
  return name;
}
function addEvent(name, data){
  let payload = {};
  try { payload = typeof data === 'string' ? JSON.parse(data) : (data || {}); } catch(err) { payload = {message:data}; }
  eventItems.unshift({name, at:new Date().toISOString(), details:payload});
  eventItems = eventItems.slice(0, 50);
  renderEvents();
}
function renderEvents(){
  events.dataset.live = 'true';
  events.innerHTML = eventItems.map(item => {
    const summary = eventSummary(item.name, item.details || {});
    return `<div class="event-row"><div>${esc(formatTime(item.at, currentLang))} ${esc(summary)}</div>${detailsBlock(item.details)}</div>`;
  }).join('') || esc(t('empty_logs', currentLang));
}
es.onmessage = e => { addEvent('message', e.data); };
['cycle_started','candidate_ranked','alert_sent','notification_result','source_fetch','status','cycle_completed'].forEach(name=>{
  es.addEventListener(name, e => { addEvent(name, e.data); refresh(); });
});
es.onerror = () => { addEvent('sse_connection_failed', {message:t('sse_reconnecting', currentLang)}); };
</script>
</body>
</html>"""
    return html.replace("__LOCALES__", locales)
