"""Data models for PortWatch."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Host:
    """Represents a host/port to monitor."""

    name: str
    host: str
    port: int
    timeout: float = 5.0
    protocol: str = "tcp"  # tcp or http/https
    http_url: Optional[str] = None
    http_expected_status: int = 200
    tags: list = field(default_factory=list)

    def __post_init__(self):
        if self.protocol not in ("tcp", "http", "https"):
            raise ValueError(f"Invalid protocol '{self.protocol}'. Use tcp, http, or https.")
        if not (0 < self.port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}.")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive.")

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port}/{self.protocol})"


@dataclass
class CheckResult:
    """Result of a single availability check."""

    host: Host
    is_up: bool
    response_time_ms: Optional[float]
    checked_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    http_status: Optional[int] = None

    @property
    def status(self) -> str:
        return "UP" if self.is_up else "DOWN"

    def __str__(self):
        rt = f"{self.response_time_ms:.1f}ms" if self.response_time_ms is not None else "N/A"
        return (
            f"[{self.status}] {self.host.name} | {self.host.host}:{self.host.port} "
            f"| {rt} | {self.checked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )


@dataclass
class UptimeRecord:
    """Aggregated uptime statistics."""

    host_name: str
    total_checks: int
    up_checks: int
    down_checks: int
    last_checked: Optional[datetime]
    last_down: Optional[datetime]
    avg_response_ms: Optional[float]

    @property
    def uptime_percent(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return round(self.up_checks / self.total_checks * 100, 2)

    def __str__(self):
        return (
            f"{self.host_name}: {self.uptime_percent}% uptime "
            f"({self.up_checks}/{self.total_checks} checks)"
        )
