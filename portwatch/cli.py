"""Command-line interface for PortWatch."""

import argparse
import logging
import signal
import sys
import time

from . import PortWatch, __version__
from .config import from_file, load_hosts, load_notifiers


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_run(args):
    cfg = from_file(args.config)
    hosts = load_hosts(cfg)
    notifiers = load_notifiers(cfg)
    interval = cfg.get("interval", 60)
    db = cfg.get("db_path", "portwatch.db")

    watcher = PortWatch(hosts=hosts, interval=interval, notifiers=notifiers, db_path=db)
    watcher.start()

    def _shutdown(sig, frame):
        print("\nShutting down…")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print(f"PortWatch {__version__} running. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)


def cmd_check(args):
    cfg = from_file(args.config)
    hosts = load_hosts(cfg)
    watcher = PortWatch(hosts=hosts, db_path=":memory:")
    results = watcher.check_now()
    for r in results:
        print(r)
    watcher.stop()


def cmd_stats(args):
    cfg = from_file(args.config)
    db = cfg.get("db_path", "portwatch.db")
    watcher = PortWatch(hosts=[], db_path=db)
    stats = watcher.get_all_stats()
    if not stats:
        print("No data yet.")
        return
    for s in stats:
        last = s.last_checked.strftime("%Y-%m-%d %H:%M") if s.last_checked else "never"
        avg = f"{s.avg_response_ms:.1f}ms" if s.avg_response_ms else "N/A"
        print(f"  {s.host_name:<30} {s.uptime_percent:>6.2f}%  avg={avg}  last={last}")
    watcher.stop()


def main():
    parser = argparse.ArgumentParser(prog="portwatch", description="Network port & service monitor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Start continuous monitoring")
    p_run.add_argument("-c", "--config", default="portwatch.yaml", help="Config file path")
    p_run.set_defaults(func=cmd_run)

    # check
    p_check = sub.add_parser("check", help="Run one-shot check and print results")
    p_check.add_argument("-c", "--config", default="portwatch.yaml")
    p_check.set_defaults(func=cmd_check)

    # stats
    p_stats = sub.add_parser("stats", help="Print uptime statistics")
    p_stats.add_argument("-c", "--config", default="portwatch.yaml")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    _setup_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
