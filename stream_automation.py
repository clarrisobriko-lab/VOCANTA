"""Run automation continuously while discovery is still adding eligible jobs."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from config.settings import AUTOMATION_MINIMUM_SCORE, STREAM_AUTOMATION_POLL_SECONDS
from core.database import Database


def queue_count() -> int:
    database = Database()
    try:
        return database.automation_queue_count(AUTOMATION_MINIMUM_SCORE)
    finally:
        database.close()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: stream_automation.py <completion-marker>")
    marker = Path(sys.argv[1])
    idle_after_done = 0
    while True:
        pending = queue_count()
        if pending:
            subprocess.run([sys.executable, "automated_apply.py"], check=False)
            idle_after_done = 0
            continue
        if marker.exists():
            idle_after_done += 1
            if idle_after_done >= 2:
                return 0
        time.sleep(STREAM_AUTOMATION_POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
