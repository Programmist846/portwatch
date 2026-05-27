"""
Basic PortWatch usage example.
Run: python examples/basic_usage.py
"""
import time
import logging
from portwatch import PortWatch, Host, TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

hosts = [
    Host(name="Google DNS",    host="8.8.8.8",       port=53,   protocol="tcp"),
    Host(name="Cloudflare DNS",host="1.1.1.1",       port=53,   protocol="tcp"),
    Host(name="Google HTTPS",  host="google.com",    port=443,  protocol="https"),
]

# Optional: add Telegram notifier
# tg = TelegramNotifier(token="BOT_TOKEN", chat_id="CHAT_ID")
# watcher = PortWatch(hosts=hosts, interval=30, notifiers=[tg], db_path=":memory:")

watcher = PortWatch(
    hosts=hosts,
    interval=30,
    db_path=":memory:",
    on_result=lambda r: print(f"  → {r}"),
)

# One-shot check
print("=== One-shot check ===")
results = watcher.check_now()

print("\n=== Stats ===")
for stat in watcher.get_all_stats():
    print(f"  {stat}")

watcher.stop()
