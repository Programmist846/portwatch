"""Tests for Telegram and Email notifiers."""
import json
import unittest.mock as mock
from portwatch.models import Host, CheckResult
from portwatch.notifiers import TelegramNotifier, EmailNotifier


def _result(is_up=True):
    host = Host(name="TestHost", host="192.168.1.1", port=80)
    return CheckResult(host=host, is_up=is_up, response_time_ms=42.0)


class TestTelegramNotifier:
    def _notifier(self, recovery=True):
        return TelegramNotifier(token="tok:abc", chat_id="123", notify_on_recovery=recovery)

    def test_send_down_success(self):
        notifier = self._notifier()
        mock_resp = mock.MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()

        with mock.patch("portwatch.notifiers.urllib.request.urlopen", return_value=mock_resp) as m:
            # simulate json.load
            with mock.patch("portwatch.notifiers.json.load", return_value={"ok": True}):
                result = notifier.send(_result(is_up=False))
        assert result is True

    def test_skip_recovery_when_disabled(self):
        notifier = self._notifier(recovery=False)
        result = notifier.send(_result(is_up=True))
        assert result is True  # returns True without sending

    def test_send_failure_returns_false(self):
        notifier = self._notifier()
        with mock.patch(
            "portwatch.notifiers.urllib.request.urlopen",
            side_effect=Exception("network error"),
        ):
            result = notifier.send(_result(is_up=False))
        assert result is False

    def test_api_error_returns_false(self):
        notifier = self._notifier()
        mock_resp = mock.MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("portwatch.notifiers.urllib.request.urlopen", return_value=mock_resp):
            with mock.patch("portwatch.notifiers.json.load", return_value={"ok": False, "description": "bad token"}):
                result = notifier.send(_result(is_up=False))
        assert result is False

    def test_format_message_contains_host_name(self):
        notifier = self._notifier()
        r = _result(is_up=False)
        msg = notifier._format_default_message(r)
        assert "TestHost" in msg
        assert "DOWN" in msg


class TestEmailNotifier:
    def _notifier(self, recovery=True):
        return EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="secret",
            recipients=["admin@example.com"],
            notify_on_recovery=recovery,
        )

    def test_send_down_success(self):
        notifier = self._notifier()
        mock_smtp = mock.MagicMock()
        mock_smtp.__enter__ = lambda s: s
        mock_smtp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("portwatch.notifiers.smtplib.SMTP", return_value=mock_smtp):
            result = notifier.send(_result(is_up=False))
        assert result is True

    def test_send_failure_returns_false(self):
        notifier = self._notifier()
        with mock.patch("portwatch.notifiers.smtplib.SMTP", side_effect=Exception("SMTP error")):
            result = notifier.send(_result(is_up=False))
        assert result is False

    def test_skip_recovery_when_disabled(self):
        notifier = self._notifier(recovery=False)
        result = notifier.send(_result(is_up=True))
        assert result is True
