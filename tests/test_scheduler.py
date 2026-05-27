"""Tests for the background Scheduler."""
import time
import threading
from portwatch.scheduler import Scheduler


class TestScheduler:
    def test_calls_func(self):
        counter = {"n": 0}

        def tick():
            counter["n"] += 1

        s = Scheduler(interval=0.05, func=tick)
        s.start()
        time.sleep(0.25)
        s.stop()
        assert counter["n"] >= 2

    def test_stop_halts_calls(self):
        counter = {"n": 0}

        def tick():
            counter["n"] += 1

        s = Scheduler(interval=0.05, func=tick)
        s.start()
        time.sleep(0.15)
        s.stop()
        before = counter["n"]
        time.sleep(0.2)
        assert counter["n"] == before  # no new calls after stop

    def test_double_start_raises(self):
        s = Scheduler(interval=10, func=lambda: None)
        s.start()
        try:
            import pytest
            with pytest.raises(RuntimeError):
                s.start()
        finally:
            s.stop()

    def test_running_property(self):
        s = Scheduler(interval=10, func=lambda: None)
        assert not s.running
        s.start()
        assert s.running
        s.stop()
        assert not s.running

    def test_exception_in_func_does_not_crash(self):
        def bad():
            raise ValueError("intentional error")

        s = Scheduler(interval=0.05, func=bad)
        s.start()
        time.sleep(0.2)
        assert s.running  # still alive despite exceptions
        s.stop()
