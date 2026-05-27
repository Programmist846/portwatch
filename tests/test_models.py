"""Tests for data models."""

import pytest
from datetime import datetime
from portwatch.models import Host, CheckResult, UptimeRecord


class TestHost:
    def test_valid_tcp(self):
        h = Host(name="Test", host="localhost", port=80)
        assert h.protocol == "tcp"
        assert str(h) == "Test (localhost:80/tcp)"

    def test_valid_http(self):
        h = Host(name="Web", host="example.com", port=443, protocol="https")
        assert h.protocol == "https"

    def test_invalid_protocol(self):
        with pytest.raises(ValueError, match="Invalid protocol"):
            Host(name="X", host="h", port=80, protocol="udp")

    def test_invalid_port_zero(self):
        with pytest.raises(ValueError, match="Port must be between"):
            Host(name="X", host="h", port=0)

    def test_invalid_port_too_large(self):
        with pytest.raises(ValueError, match="Port must be between"):
            Host(name="X", host="h", port=99999)

    def test_invalid_timeout(self):
        with pytest.raises(ValueError, match="Timeout must be positive"):
            Host(name="X", host="h", port=80, timeout=-1)

    def test_tags(self):
        h = Host(name="X", host="h", port=80, tags=["web", "prod"])
        assert "web" in h.tags


class TestCheckResult:
    def _make(self, is_up=True, response_ms=42.5, error=None):
        host = Host(name="Test", host="localhost", port=8080)
        return CheckResult(
            host=host,
            is_up=is_up,
            response_time_ms=response_ms,
            error=error,
        )

    def test_status_up(self):
        r = self._make(is_up=True)
        assert r.status == "UP"

    def test_status_down(self):
        r = self._make(is_up=False)
        assert r.status == "DOWN"

    def test_str_contains_host(self):
        r = self._make()
        assert "Test" in str(r)
        assert "localhost:8080" in str(r)

    def test_str_no_response_time(self):
        r = self._make(response_ms=None)
        assert "N/A" in str(r)


class TestUptimeRecord:
    def _make(self, total=100, up=99):
        return UptimeRecord(
            host_name="srv",
            total_checks=total,
            up_checks=up,
            down_checks=total - up,
            last_checked=datetime.utcnow(),
            last_down=None,
            avg_response_ms=12.3,
        )

    def test_uptime_percent(self):
        r = self._make(100, 99)
        assert r.uptime_percent == 99.0

    def test_uptime_zero_total(self):
        r = self._make(0, 0)
        assert r.uptime_percent == 0.0

    def test_str(self):
        r = self._make(100, 95)
        assert "95.0%" in str(r)
