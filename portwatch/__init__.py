"""
PortWatch — Network port & service monitor.
"""

from .monitor import PortWatch
from .models import Host, CheckResult, UptimeRecord
from .notifiers import TelegramNotifier, EmailNotifier
from .scheduler import Scheduler
from .history import UptimeHistory

__version__ = "1.0.0"
__author__ = "PortWatch Contributors"
__all__ = [
    "PortWatch",
    "Host",
    "CheckResult",
    "UptimeRecord",
    "TelegramNotifier",
    "EmailNotifier",
    "Scheduler",
    "UptimeHistory",
]
