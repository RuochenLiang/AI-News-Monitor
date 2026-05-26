from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta
from pathlib import Path

from src.config import load_config
from src.models import RuntimeStatus
from src.monitor import LogCallback, NewsMonitor, StatusCallback
from src.realtime import LocalEventServer, SseBroker
from src.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class MonitorWorker:
    def __init__(
        self,
        config_path: Path,
        runtime_dir: Path,
        status_callback: StatusCallback | None = None,
        log_callback: LogCallback | None = None,
    ):
        self.config_path = config_path
        self.runtime_dir = runtime_dir
        self.status_callback = status_callback
        self.log_callback = log_callback
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._force_cycle_event = threading.Event()
        self._e2e_test_event = threading.Event()
        self._manual_lock = threading.Lock()
        self.status = RuntimeStatus()
        self.broker = SseBroker()
        self._event_server: LocalEventServer | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ensure_event_server()
        self._stop_event.clear()
        self._pause_event.clear()
        self.status.state = "Running"
        self.status.pause_reason = None
        self._emit()
        self._publish_event({"type": "control", "action": "start", "state": self.status.state})
        self._thread = threading.Thread(target=self._run, name="ai-news-monitor-worker", daemon=True)
        self._thread.start()

    def start_event_server(self) -> None:
        self._ensure_event_server()
        self._emit()

    def reload_runtime_settings(self) -> None:
        try:
            config = load_config(self.config_path)
        except Exception as exc:  # noqa: BLE001 - UI language changes should not interrupt monitoring
            logger.warning("Could not reload runtime settings: %s", exc)
            return
        self._apply_runtime_config_to_status(config)
        self._emit()
        if self._event_server:
            self._publish_event(
                {
                    "type": "status",
                    "status": self.status.state,
                    "output_language": self.status.output_language,
                    "alert_mode": self.status.alert_mode,
                }
            )

    def pause(self) -> None:
        self._pause_event.set()
        self.status.state = "Paused"
        self.status.pause_reason = "User paused monitoring."
        self.status.next_cycle_time = None
        self._emit()
        self._publish_event({"type": "control", "action": "pause", "state": self.status.state})

    def resume(self) -> None:
        self._pause_event.clear()
        self.status.state = "Running"
        self.status.pause_reason = None
        self._emit()
        self._publish_event({"type": "control", "action": "resume", "state": self.status.state})

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()
        self.status.state = "Stopped"
        self.status.pause_reason = None
        self.status.next_cycle_time = None
        self._emit()
        self._publish_event({"type": "control", "action": "stop", "state": self.status.state})
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._stop_event_server()

    def run_once(self) -> None:
        if self._thread and self._thread.is_alive():
            self._pause_event.clear()
            self._force_cycle_event.set()
            self.status.state = "Running"
            self.status.pause_reason = None
            self.status.next_cycle_time = None
            self._emit()
            self._publish_event({"type": "control", "action": "run_once", "state": self.status.state})
            return
        self._run_manual_cycle("run_once")

    def run_e2e_test(self) -> None:
        if self._thread and self._thread.is_alive():
            self._pause_event.clear()
            self._e2e_test_event.set()
            self.status.state = "Running"
            self.status.pause_reason = None
            self.status.next_cycle_time = None
            self._emit()
            self._publish_event({"type": "control", "action": "e2e_test", "state": self.status.state})
            return
        self._run_manual_cycle("e2e_test")

    def _run(self) -> None:
        self._ensure_event_server()
        monitor = NewsMonitor(
            self.config_path,
            self.runtime_dir,
            status_callback=self._status_from_monitor,
            log_callback=self.log_callback,
            event_callback=self._publish_event,
        )
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.5)
                continue
            try:
                self.status.state = "Running"
                self._emit()
                run_e2e = self._e2e_test_event.is_set()
                self._e2e_test_event.clear()
                self._force_cycle_event.clear()
                status = monitor.run_e2e_test() if run_e2e else monitor.run_cycle()
                self._status_from_monitor(status)
                config = load_config(self.config_path)
                interval = _next_interval_seconds(config)
                self.status.next_cycle_time = utc_now() + timedelta(seconds=interval)
                self._emit()
            except Exception as exc:  # noqa: BLE001 - background worker should recover
                logger.exception("Monitor cycle failed")
                self.status.state = "Error"
                self.status.error_message = str(exc)
                self.status.next_cycle_time = utc_now() + timedelta(seconds=30)
                self._emit()
                interval = 30
            self._sleep_interruptibly(interval)
        self.status.state = "Stopped"
        self._emit()

    def _sleep_interruptibly(self, seconds: int) -> None:
        end = time.monotonic() + max(1, seconds)
        while time.monotonic() < end and not self._stop_event.is_set() and not self._pause_event.is_set():
            if self._force_cycle_event.is_set() or self._e2e_test_event.is_set():
                break
            time.sleep(0.5)

    def _status_from_monitor(self, status: RuntimeStatus) -> None:
        state = self.status.state
        self.status = status
        self.status.state = state
        if self._event_server:
            self.status.local_server_url = self._event_server.url
        try:
            self._apply_runtime_config_to_status(load_config(self.config_path))
        except Exception as exc:  # noqa: BLE001 - stale runtime settings are preferable to dropping status
            logger.debug("Could not refresh runtime settings from config: %s", exc)
        self.status.live_event_count = self.broker.event_count
        self._emit()
        self._publish_event(
            {
                "type": "status",
                "status": self.status.state,
                "output_language": self.status.output_language,
                "alert_mode": self.status.alert_mode,
            }
        )

    def _emit(self) -> None:
        if self.status_callback:
            self.status_callback(self.status)

    def _ensure_event_server(self) -> None:
        try:
            config = load_config(self.config_path)
        except Exception as exc:  # noqa: BLE001 - server should not block monitor startup
            logger.warning("Could not load config for local event server: %s", exc)
            return
        if not config.local_server.enabled or not config.local_server.sse_enabled:
            return
        self._apply_runtime_config_to_status(config)
        if self._event_server:
            return
        self._event_server = LocalEventServer(
            config.local_server.host,
            config.local_server.port,
            self.broker,
            status_provider=lambda: self.status,
            control_handlers={
                "start": self.start,
                "pause": self.pause,
                "resume": self.resume,
                "stop": self.stop,
                "run_once": self.run_once,
                "e2e_test": self.run_e2e_test,
            },
            config_path=self.config_path,
            runtime_dir=self.runtime_dir,
        )
        try:
            self._event_server.start()
            self.status.local_server_url = self._event_server.url
            if self.log_callback:
                self.log_callback(f"Local event server running at {self._event_server.url}")
        except Exception as exc:  # noqa: BLE001 - background worker should keep monitoring
            logger.exception("Local event server failed to start")
            self.status.error_message = f"Local event server failed: {exc}"
            self._event_server = None
            self._emit()

    def _stop_event_server(self) -> None:
        if self._event_server:
            self._event_server.stop()
            self._event_server = None

    def _apply_runtime_config_to_status(self, config) -> None:
        self.status.output_language = config.app.output_language
        self.status.alert_mode = config.alerts.default_mode
        self.status.ui_debug_mode = config.ui.debug_mode
        self.status.source_packages_enabled = list(config.sources.enabled_packages)

    def _publish_event(self, event: dict) -> None:
        self.broker.publish(event)
        self.status.live_event_count = self.broker.event_count

    def _run_manual_cycle(self, action: str) -> None:
        def target() -> None:
            if not self._manual_lock.acquire(blocking=False):
                return
            try:
                self._ensure_event_server()
                self.status.state = "Running"
                self.status.pause_reason = None
                self.status.next_cycle_time = None
                self._emit()
                self._publish_event({"type": "control", "action": action, "state": self.status.state})
                monitor = NewsMonitor(
                    self.config_path,
                    self.runtime_dir,
                    status_callback=self._status_from_monitor,
                    log_callback=self.log_callback,
                    event_callback=self._publish_event,
                )
                status = monitor.run_e2e_test() if action == "e2e_test" else monitor.run_cycle()
                self._status_from_monitor(status)
                self.status.state = "Stopped"
                self.status.next_cycle_time = None
                self._emit()
                self._publish_event({"type": "control", "action": f"{action}_completed", "state": self.status.state})
            finally:
                self._manual_lock.release()

        threading.Thread(target=target, name=f"ai-news-monitor-{action}", daemon=True).start()


def _next_interval_seconds(config) -> int:
    intervals = [config.monitor.default_interval_seconds]
    intervals.extend(
        topic.poll_interval_seconds for topic in config.topics if topic.enabled and topic.poll_interval_seconds
    )
    return max(1, min(intervals))
