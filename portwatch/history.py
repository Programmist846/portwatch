"""Uptime history storage using SQLite."""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import CheckResult, UptimeRecord


class UptimeHistory:
    """
    Thread-safe SQLite-backed history of check results.

    Parameters
    ----------
    db_path : str or Path
        Path to the SQLite database file. Use ``:memory:`` for in-memory storage.
    """

    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS check_results (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            host_name     TEXT    NOT NULL,
            host_address  TEXT    NOT NULL,
            port          INTEGER NOT NULL,
            protocol      TEXT    NOT NULL,
            is_up         INTEGER NOT NULL,
            response_ms   REAL,
            http_status   INTEGER,
            error         TEXT,
            checked_at    TEXT    NOT NULL
        )
    """

    def __init__(self, db_path: str = "portwatch.db"):
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute(self._CREATE_TABLE)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, result: CheckResult) -> None:
        """Persist a single CheckResult."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO check_results
                    (host_name, host_address, port, protocol,
                     is_up, response_ms, http_status, error, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.host.name,
                    result.host.host,
                    result.host.port,
                    result.host.protocol,
                    int(result.is_up),
                    result.response_time_ms,
                    result.http_status,
                    result.error,
                    result.checked_at.isoformat(),
                ),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_recent(self, host_name: str, limit: int = 100) -> List[dict]:
        """Return the most recent *limit* records for a given host."""
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT * FROM check_results
                WHERE host_name = ?
                ORDER BY checked_at DESC
                LIMIT ?
                """,
                (host_name, limit),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_stats(self, host_name: str) -> UptimeRecord:
        """Compute aggregated uptime statistics for a host."""
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT
                    COUNT(*)            AS total,
                    SUM(is_up)          AS up_total,
                    MAX(checked_at)     AS last_checked,
                    AVG(response_ms)    AS avg_ms
                FROM check_results
                WHERE host_name = ?
                """,
                (host_name,),
            )
            row = cur.fetchone()
            total, up_total, last_checked, avg_ms = row

            # last DOWN
            cur2 = self._conn.execute(
                """
                SELECT checked_at FROM check_results
                WHERE host_name = ? AND is_up = 0
                ORDER BY checked_at DESC LIMIT 1
                """,
                (host_name,),
            )
            down_row = cur2.fetchone()

        up_total = up_total or 0
        return UptimeRecord(
            host_name=host_name,
            total_checks=total or 0,
            up_checks=up_total,
            down_checks=(total or 0) - up_total,
            last_checked=datetime.fromisoformat(last_checked) if last_checked else None,
            last_down=datetime.fromisoformat(down_row[0]) if down_row else None,
            avg_response_ms=round(avg_ms, 2) if avg_ms else None,
        )

    def all_host_names(self) -> List[str]:
        """Return a list of all tracked host names."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT DISTINCT host_name FROM check_results ORDER BY host_name"
            )
            return [row[0] for row in cur.fetchall()]

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
