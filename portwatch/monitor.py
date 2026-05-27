"""Main PortWatch orchestrator."""

import logging
import threading
from typing import List, Optional, Callable

from .checker import check_host
from .history import UptimeHistory
from .models import Host, CheckResult, UptimeRecord
from .notifiers import BaseNotifier
from .scheduler import Scheduler

logger = logging.getLogger(__name__)


class PortWatch:
    """
    Main entry point for PortWatch.

    Parameters
    ----------
    hosts : list[Host]
        Hosts to monitor.
    interval : float
        Check interval in seconds. Default 60.
    notifiers : list[BaseNotifier]
        Notification backends (Telegram, Email, etc.).
    db_path : str
        Path to SQLite database. Use ``:memory:`` for tests.
    alert_on_recovery : bool
        Notify when a down host comes back up. Default True.
    on_result : Callable[[CheckResult], None] | None
        Optional callback invoked after every check.
    """

    def __init__(
        self,
        hosts: List[Host],
        interval: float = 60.0,
        notifiers: Optional[List[BaseNotifier]] = None,
        db_path: str = "portwatch.db",
        alert_on_recovery: bool = True,
        on_result: Optional[Callable[[CheckResult], None]] = None,
    ):
        self.hosts = hosts
        self.interval = interval
        self.notifiers = notifiers or []
        self.alert_on_recovery = alert_on_recovery
        self.on_result = on_result

        self._history = UptimeHistory(db_path)
        self._scheduler = Scheduler(interval=interval, func=self._run_checks, name="portwatch")
        self._lock = threading.Lock()

        # track last known state to detect state changes
        self._last_state: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start background monitoring."""
        logger.info("PortWatch starting — %d host(s), interval=%ss", len(self.hosts), self.interval)
        self._run_checks()          # immediate first check
        self._scheduler.start()

    def stop(self) -> None:
        """Stop background monitoring."""
        self._scheduler.stop()
        self._history.close()
        logger.info("PortWatch stopped.")

    def check_now(self) -> List[CheckResult]:
        """Run a single synchronous check of all hosts and return results."""
        results = []
        for host in self.hosts:
            result = check_host(host)
            self._history.record(result)
            results.append(result)
            if self.on_result:
                try:
                    self.on_result(result)
                except Exception as exc:
                    logger.warning("on_result callback error: %s", exc)
        return results

    def get_stats(self, host_name: str) -> UptimeRecord:
        """Return uptime statistics for a single host by name."""
        return self._history.get_stats(host_name)

    def get_all_stats(self) -> List[UptimeRecord]:
        """Return uptime statistics for all tracked hosts."""
        return [self._history.get_stats(name) for name in self._history.all_host_names()]

    def get_recent(self, host_name: str, limit: int = 100) -> List[dict]:
        """Return recent check results for a host."""
        return self._history.get_recent(host_name, limit)

    def add_host(self, host: Host) -> None:
        """Dynamically add a host to the monitoring list."""
        with self._lock:
            self.hosts.append(host)

    def remove_host(self, host_name: str) -> None:
        """Remove a host from the monitoring list by name."""
        with self._lock:
            self.hosts = [h for h in self.hosts if h.name != host_name]

    @property
    def running(self) -> bool:
        return self._scheduler.running

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_checks(self) -> None:
        with self._lock:
            hosts_snapshot = list(self.hosts)

        for host in hosts_snapshot:
            try:
                result = check_host(host)
            except Exception as exc:
                logger.error("Unexpected error checking %s: %s", host, exc)
                continue

            self._history.record(result)

            prev_state = self._last_state.get(host.name)
            state_changed = prev_state is None or prev_state != result.is_up
            self._last_state[host.name] = result.is_up

            log_fn = logger.info if result.is_up else logger.warning
            log_fn("%s", result)

            # Notify on DOWN, and optionally on recovery (UP after DOWN)
            should_notify = (not result.is_up) or (result.is_up and self.alert_on_recovery and state_changed and prev_state is False)

            if should_notify and self.notifiers:
                self._send_notifications(result)

            if self.on_result:
                try:
                    self.on_result(result)
                except Exception as exc:
                    logger.warning("on_result callback error: %s", exc)

    def _send_notifications(self, result: CheckResult) -> None:
        for notifier in self.notifiers:
            try:
                notifier.send(result)
            except Exception as exc:
                logger.error("Notifier %s failed: %s", type(notifier).__name__, exc)

    # Context manager support
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
