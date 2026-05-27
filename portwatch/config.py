"""YAML/JSON config loader for PortWatch."""

import json
import logging
from pathlib import Path
from typing import List

from .models import Host
from .notifiers import TelegramNotifier, EmailNotifier, BaseNotifier

logger = logging.getLogger(__name__)


def _load_raw(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            raise ImportError("PyYAML is required for YAML configs: pip install pyyaml")
    return json.loads(text)


def load_hosts(config: dict) -> List[Host]:
    hosts = []
    for item in config.get("hosts", []):
        hosts.append(
            Host(
                name=item["name"],
                host=item["host"],
                port=int(item["port"]),
                timeout=float(item.get("timeout", 5.0)),
                protocol=item.get("protocol", "tcp"),
                http_url=item.get("http_url"),
                http_expected_status=int(item.get("http_expected_status", 200)),
                tags=item.get("tags", []),
            )
        )
    return hosts


def load_notifiers(config: dict) -> List[BaseNotifier]:
    notifiers = []
    notify_cfg = config.get("notifications", {})

    tg = notify_cfg.get("telegram")
    if tg and tg.get("enabled", True):
        notifiers.append(
            TelegramNotifier(
                token=tg["token"],
                chat_id=tg["chat_id"],
                notify_on_recovery=tg.get("notify_on_recovery", True),
            )
        )

    email = notify_cfg.get("email")
    if email and email.get("enabled", True):
        notifiers.append(
            EmailNotifier(
                smtp_host=email["smtp_host"],
                smtp_port=int(email.get("smtp_port", 587)),
                username=email["username"],
                password=email["password"],
                recipients=email["recipients"],
                use_tls=email.get("use_tls", True),
                notify_on_recovery=email.get("notify_on_recovery", True),
            )
        )

    return notifiers


def from_file(path: str) -> dict:
    """Load raw config dict from a YAML or JSON file."""
    return _load_raw(path)
