"""Integration-style tests for the PortWatch orchestrator."""
import unittest.mock as mock
from portwatch import PortWatch, Host
from portwatch.models import CheckResult


def _host(name="srv"):
    return Host(name=name, host="localhost", port=9999)


def _up_result(host):
    return CheckResult(host=host, is_up=True, response_time_ms=5.0)


def _down_result(host):
    return CheckResult(host=host, is_up=False, response_time_ms=None, error="refused")


def _make(hosts=None, notifiers=None, on_result=None):
    return PortWatch(
        hosts=[_host()] if hosts is None else hosts,
        interval=999,
        notifiers=notifiers if notifiers is not None else [],
        db_path=":memory:",
        on_result=on_result,
    )


class TestPortWatch:
    def test_check_now_returns_results(self):
        pw = _make()
        with mock.patch("portwatch.monitor.check_host", return_value=_up_result(_host())):
            results = pw.check_now()
        assert len(results) == 1
        assert results[0].is_up is True
        pw.stop()

    def test_check_now_records_to_db(self):
        pw = _make()
        with mock.patch("portwatch.monitor.check_host", return_value=_up_result(_host())):
            pw.check_now()
        stats = pw.get_stats("srv")
        assert stats.total_checks == 1
        pw.stop()

    def test_notification_sent_on_down(self):
        notifier = mock.MagicMock()
        notifier.send.return_value = True
        h = _host()
        pw = _make(hosts=[h], notifiers=[notifier])
        with mock.patch("portwatch.monitor.check_host", return_value=_down_result(h)):
            pw._run_checks()
        notifier.send.assert_called_once()
        pw.stop()

    def test_no_notification_when_stays_up(self):
        notifier = mock.MagicMock()
        h = _host()
        pw = _make(hosts=[h], notifiers=[notifier])
        with mock.patch("portwatch.monitor.check_host", return_value=_up_result(h)):
            pw._run_checks()
            pw._run_checks()
        notifier.send.assert_not_called()
        pw.stop()

    def test_on_result_callback(self):
        called = []
        pw = _make(on_result=lambda r: called.append(r))
        with mock.patch("portwatch.monitor.check_host", return_value=_up_result(_host())):
            pw.check_now()
        assert len(called) == 1
        pw.stop()

    def test_add_remove_host(self):
        pw = _make(hosts=[])
        pw.add_host(_host("A"))
        pw.add_host(_host("B"))
        assert len(pw.hosts) == 2
        pw.remove_host("A")
        assert len(pw.hosts) == 1
        assert pw.hosts[0].name == "B"
        pw.stop()

    def test_get_all_stats(self):
        pw = _make(hosts=[_host("s1"), _host("s2")])
        with mock.patch("portwatch.monitor.check_host") as m:
            m.side_effect = lambda host: _up_result(host)
            pw.check_now()
        stats = pw.get_all_stats()
        names = {s.host_name for s in stats}
        assert "s1" in names and "s2" in names
        pw.stop()

    def test_context_manager(self):
        with mock.patch("portwatch.monitor.check_host", return_value=_up_result(_host())):
            with PortWatch(hosts=[_host()], interval=999, db_path=":memory:") as pw:
                assert pw.running
        assert not pw.running

    def test_recovery_notification_after_down(self):
        notifier = mock.MagicMock()
        notifier.send.return_value = True
        h = _host()
        pw = _make(hosts=[h], notifiers=[notifier], )
        with mock.patch("portwatch.monitor.check_host", return_value=_down_result(h)):
            pw._run_checks()  # DOWN — notify
        with mock.patch("portwatch.monitor.check_host", return_value=_up_result(h)):
            pw._run_checks()  # UP after DOWN — notify recovery
        assert notifier.send.call_count == 2
        pw.stop()
