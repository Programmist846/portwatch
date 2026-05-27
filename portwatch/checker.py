"""Low-level connectivity checkers: TCP and HTTP/HTTPS."""

import socket
import time
import urllib.request
import urllib.error
from typing import Tuple, Optional

from .models import Host, CheckResult


def check_tcp(host: Host) -> CheckResult:
    """Attempt a TCP connection and measure latency."""
    start = time.monotonic()
    error = None
    is_up = False
    response_ms = None

    try:
        with socket.create_connection((host.host, host.port), timeout=host.timeout):
            response_ms = (time.monotonic() - start) * 1000
            is_up = True
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        response_ms = (time.monotonic() - start) * 1000
        error = str(exc)

    return CheckResult(
        host=host,
        is_up=is_up,
        response_time_ms=response_ms,
        error=error,
    )


def check_http(host: Host) -> CheckResult:
    """Perform an HTTP/HTTPS GET request and check the status code."""
    url = host.http_url or f"{host.protocol}://{host.host}:{host.port}/"
    start = time.monotonic()
    error = None
    is_up = False
    response_ms = None
    http_status = None

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PortWatch/1.0"})
        with urllib.request.urlopen(req, timeout=host.timeout) as resp:
            http_status = resp.status
            response_ms = (time.monotonic() - start) * 1000
            is_up = http_status == host.http_expected_status
            if not is_up:
                error = f"Unexpected status: {http_status} (expected {host.http_expected_status})"
    except urllib.error.HTTPError as exc:
        http_status = exc.code
        response_ms = (time.monotonic() - start) * 1000
        is_up = http_status == host.http_expected_status
        if not is_up:
            error = f"HTTP {http_status}: {exc.reason}"
    except Exception as exc:
        response_ms = (time.monotonic() - start) * 1000
        error = str(exc)

    return CheckResult(
        host=host,
        is_up=is_up,
        response_time_ms=response_ms,
        error=error,
        http_status=http_status,
    )


def check_host(host: Host) -> CheckResult:
    """Dispatch to the correct checker based on protocol."""
    if host.protocol in ("http", "https"):
        return check_http(host)
    return check_tcp(host)
