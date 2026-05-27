"""Notification backends: Telegram Bot API and SMTP Email."""

import smtplib
import urllib.request
import urllib.parse
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from .models import CheckResult

logger = logging.getLogger(__name__)


class BaseNotifier:
    """Abstract base for notifiers."""

    def send(self, result: CheckResult, message: str) -> bool:
        raise NotImplementedError

    def _format_default_message(self, result: CheckResult) -> str:
        emoji = "✅" if result.is_up else "🔴"
        rt = f"{result.response_time_ms:.1f}ms" if result.response_time_ms else "N/A"
        return (
            f"{emoji} *{result.host.name}* is *{result.status}*\n"
            f"Host: `{result.host.host}:{result.host.port}`\n"
            f"Response time: {rt}\n"
            f"Time: {result.checked_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            + (f"\nError: `{result.error}`" if result.error else "")
        )


class TelegramNotifier(BaseNotifier):
    """
    Send alerts via the Telegram Bot API.

    Parameters
    ----------
    token : str
        Bot token from @BotFather.
    chat_id : str or int
        Target chat/channel/group ID.
    notify_on_recovery : bool
        Also send a message when a host comes back up. Default True.
    """

    API_BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, chat_id, notify_on_recovery: bool = True):
        self.token = token
        self.chat_id = str(chat_id)
        self.notify_on_recovery = notify_on_recovery

    def send(self, result: CheckResult, message: Optional[str] = None) -> bool:
        """Send a Telegram message. Returns True on success."""
        if result.is_up and not self.notify_on_recovery:
            return True  # silently skip recovery messages

        text = message or self._format_default_message(result)
        url = self.API_BASE.format(token=self.token, method="sendMessage")
        payload = json.dumps(
            {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
        ).encode()

        try:
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
                if not data.get("ok"):
                    logger.error("Telegram API error: %s", data)
                    return False
            return True
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)
            return False


class EmailNotifier(BaseNotifier):
    """
    Send alerts via SMTP (works with Gmail, Yandex, custom SMTP).

    Parameters
    ----------
    smtp_host : str
        SMTP server hostname (e.g. ``smtp.gmail.com``).
    smtp_port : int
        SMTP port. Use 587 for STARTTLS, 465 for SSL.
    username : str
        SMTP login username / sender address.
    password : str
        SMTP login password or app-specific password.
    recipients : list[str]
        List of recipient email addresses.
    use_tls : bool
        Use STARTTLS (port 587). Set False for plain SSL (port 465).
    notify_on_recovery : bool
        Also send a message when a host comes back up. Default True.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        recipients: list,
        use_tls: bool = True,
        notify_on_recovery: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
        self.use_tls = use_tls
        self.notify_on_recovery = notify_on_recovery

    def _build_email(self, result: CheckResult, text: str) -> MIMEMultipart:
        subject = f"[PortWatch] {result.host.name} is {result.status}"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(text, "plain"))
        return msg

    def send(self, result: CheckResult, message: Optional[str] = None) -> bool:
        """Send an email. Returns True on success."""
        if result.is_up and not self.notify_on_recovery:
            return True

        text = message or self._format_default_message(result).replace("*", "").replace("`", "")
        msg = self._build_email(result, text)

        try:
            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(self.username, self.password)
                    server.sendmail(self.username, self.recipients, msg.as_string())
            else:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15) as server:
                    server.login(self.username, self.password)
                    server.sendmail(self.username, self.recipients, msg.as_string())
            return True
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            return False
