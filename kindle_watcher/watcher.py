"""
watcher.py
One-shot script: syncs My Clippings.txt to a remote server via SCP if the file
is new or has changed since last run. Designed to be called from cron.

Run: python3 watcher.py
"""

import logging
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

KINDLE_CLIPPINGS = "/Volumes/Kindle/documents/My Clippings.txt"
MTIME_FILE       = os.path.expanduser("~/.typeshit/kindle_last_mtime")

SERVER_USER = os.environ["SERVER_USER"]
SERVER_HOST = os.environ["SERVER_HOST"]
SERVER_PATH = os.environ.get("SERVER_PATH", "~/.typeshit/clippings.txt")
SSH_KEY     = os.environ.get("SSH_KEY", "")


def last_synced_mtime() -> float:
    try:
        return float(open(MTIME_FILE).read().strip())
    except (FileNotFoundError, ValueError):
        return 0.0


def save_mtime(mtime: float):
    os.makedirs(os.path.dirname(MTIME_FILE), exist_ok=True)
    with open(MTIME_FILE, "w") as f:
        f.write(str(mtime))


def sync_clippings(path: str):
    dest = f"{SERVER_USER}@{SERVER_HOST}:{SERVER_PATH}"
    cmd = ["scp"]
    if SSH_KEY:
        cmd += ["-i", os.path.expanduser(SSH_KEY)]
    cmd += [path, dest]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    logger.info("Clippings synced to %s", dest)


def main():
    if not os.path.exists(KINDLE_CLIPPINGS):
        logger.debug("Kindle not mounted, nothing to do.")
        sys.exit(0)

    mtime = os.path.getmtime(KINDLE_CLIPPINGS)
    if mtime <= last_synced_mtime():
        logger.debug("Clippings unchanged, skipping.")
        sys.exit(0)

    logger.info("Kindle detected, syncing clippings...")
    try:
        sync_clippings(KINDLE_CLIPPINGS)
        save_mtime(mtime)
    except Exception as e:
        logger.error("Sync failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
