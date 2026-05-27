"""Tests for UptimeHistory (in-memory SQLite)."""
from datetime import datetime
from portwatch.models import Host, CheckResult
from portwatch.history import UptimeHistory


def _host(name="srv1"):
    return Host(name=name, host="192.168.1.1", port=22)


def _result(host, is_up=True, ms=10.0, error=None):
    return CheckResult(host=host, is_up=is_up, response_time_ms=ms, error=error)


class TestUptimeHistory:
    def setup_method(self):
        self.db = UptimeHistory(":memory:")
        self.host = _host()

    def teardown_method(self):
        self.db.close()

    def test_record_and_retrieve(self):
        self.db.record(_result(self.host, is_up=True, ms=15.0))
        rows = self.db.get_recent("srv1", limit=10)
        assert len(rows) == 1
        assert rows[0]["is_up"] == 1
        assert rows[0]["response_ms"] == 15.0

    def test_stats_uptime_100(self):
        for _ in range(10):
            self.db.record(_result(self.host, is_up=True, ms=5.0))
        stats = self.db.get_stats("srv1")
        assert stats.total_checks == 10
        assert stats.up_checks == 10
        assert stats.uptime_percent == 100.0

    def test_stats_partial_uptime(self):
        for i in range(10):
            self.db.record(_result(self.host, is_up=(i < 7), ms=5.0))
        stats = self.db.get_stats("srv1")
        assert stats.uptime_percent == 70.0
        assert stats.down_checks == 3

    def test_stats_no_data(self):
        stats = self.db.get_stats("nonexistent")
        assert stats.total_checks == 0
        assert stats.uptime_percent == 0.0
        assert stats.last_checked is None

    def test_all_host_names(self):
        h2 = _host("srv2")
        self.db.record(_result(self.host))
        self.db.record(_result(h2))
        names = self.db.all_host_names()
        assert "srv1" in names
        assert "srv2" in names

    def test_get_recent_limit(self):
        for _ in range(20):
            self.db.record(_result(self.host))
        rows = self.db.get_recent("srv1", limit=5)
        assert len(rows) == 5

    def test_last_down_tracked(self):
        self.db.record(_result(self.host, is_up=False))
        stats = self.db.get_stats("srv1")
        assert stats.last_down is not None
        assert isinstance(stats.last_down, datetime)

    def test_avg_response_ms(self):
        for ms in [10.0, 20.0, 30.0]:
            self.db.record(_result(self.host, ms=ms))
        stats = self.db.get_stats("srv1")
        assert stats.avg_response_ms == 20.0

    def test_context_manager(self):
        with UptimeHistory(":memory:") as db:
            db.record(_result(_host()))
            assert len(db.get_recent("srv1")) == 1
