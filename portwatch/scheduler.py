"""Simple background scheduler for recurring checks."""

import threading
import time
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Run a callable on a fixed interval in a background daemon thread.

    Parameters
    ----------
    interval : float
        Seconds between each invocation.
    func : Callable
        The function to call on each tick.
    name : str
        Thread name (helpful for debugging).
    """

    def __init__(self, interval: float, func: Callable, name: str = "portwatch-scheduler"):
        self.interval = interval
        self.func = func
        self.name = name
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Scheduler is already running.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=self.name, daemon=True)
        self._thread.start()
        logger.info("Scheduler '%s' started (interval=%ss)", self.name, self.interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the scheduler to stop and wait for it."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("Scheduler '%s' stopped.", self.name)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.func()
            except Exception as exc:
                logger.exception("Scheduler callback raised an exception: %s", exc)
            self._stop_event.wait(self.interval)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
