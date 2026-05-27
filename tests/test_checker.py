"""Tests for TCP/HTTP checkers using mock sockets."""
import socket
import unittest.mock as mock
from portwatch.models import Host
from portwatch.checker import check_tcp, check_http, check_host


def _tcp_host(**kwargs):
    return Host(name="Test", host="localhost", port=9999, **kwargs)


class TestCheckTcp:
    def test_success(self):
        with mock.patch("portwatch.checker.socket.create_connection"):
            result = check_tcp(_tcp_host())
        assert result.is_up is True
        assert result.error is None
        assert result.response_time_ms is not None

    def test_connection_refused(self):
        with mock.patch(
            "portwatch.checker.socket.create_connection",
            side_effect=ConnectionRefusedError("refused"),
        ):
            result = check_tcp(_tcp_host())
        assert result.is_up is False
        assert result.error is not None

    def test_timeout(self):
        with mock.patch(
            "portwatch.checker.socket.create_connection",
            side_effect=socket.timeout("timed out"),
        ):
            result = check_tcp(_tcp_host())
        assert result.is_up is False
        assert "timed out" in result.error

    def test_oserror(self):
        with mock.patch(
            "portwatch.checker.socket.create_connection",
            side_effect=OSError("network unreachable"),
        ):
            result = check_tcp(_tcp_host())
        assert result.is_up is False


class TestCheckHttp:
    def _http_host(self, status=200):
        return Host(
            name="Web",
            host="example.com",
            port=80,
            protocol="http",
            http_url="http://example.com/",
            http_expected_status=status,
        )

    def _mock_response(self, status=200):
        resp = mock.MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = mock.MagicMock(return_value=False)
        resp.status = status
        return resp

    def test_http_200_ok(self):
        with mock.patch(
            "portwatch.checker.urllib.request.urlopen",
            return_value=self._mock_response(200),
        ):
            result = check_http(self._http_host(200))
        assert result.is_up is True
        assert result.http_status == 200

    def test_http_unexpected_status(self):
        with mock.patch(
            "portwatch.checker.urllib.request.urlopen",
            return_value=self._mock_response(500),
        ):
            result = check_http(self._http_host(200))
        assert result.is_up is False
        assert "500" in result.error

    def test_http_exception(self):
        import urllib.error
        with mock.patch(
            "portwatch.checker.urllib.request.urlopen",
            side_effect=Exception("connection error"),
        ):
            result = check_http(self._http_host())
        assert result.is_up is False
        assert result.error is not None


class TestCheckHostDispatch:
    def test_dispatches_tcp(self):
        h = Host(name="T", host="h", port=22, protocol="tcp")
        with mock.patch("portwatch.checker.check_tcp") as m:
            m.return_value = mock.MagicMock()
            check_host(h)
            m.assert_called_once_with(h)

    def test_dispatches_http(self):
        h = Host(name="T", host="h", port=80, protocol="http")
        with mock.patch("portwatch.checker.check_http") as m:
            m.return_value = mock.MagicMock()
            check_host(h)
            m.assert_called_once_with(h)

    def test_dispatches_https(self):
        h = Host(name="T", host="h", port=443, protocol="https")
        with mock.patch("portwatch.checker.check_http") as m:
            m.return_value = mock.MagicMock()
            check_host(h)
            m.assert_called_once_with(h)
