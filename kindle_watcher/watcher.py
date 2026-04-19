"""
watcher.py
Monitors Kindle mount on macOS and syncs My Clippings.txt to a remote server via SCP.

Run: python3 watcher.py
"""

import logging
import os
import subprocess
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

KINDLE_CLIPPINGS = "/Volumes/Kindle/documents/My Clippings.txt"
POLL_INTERVAL    = 10  # seconds between mount checks

SERVER_USER      = os.environ["SERVER_USER"]
SERVER_HOST      = os.environ["SERVER_HOST"]
SERVER_PATH      = os.environ.get("SERVER_PATH", "~/.typeshit/clippings.txt")
SSH_KEY          = os.environ.get("SSH_KEY", "")  # optional, e.g. ~/.ssh/id_ed25519


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
    logger.info("Kindle watcher started. Polling every %ds for %s", POLL_INTERVAL, KINDLE_CLIPPINGS)
    last_mtime = None

    while True:
        try:
            if os.path.exists(KINDLE_CLIPPINGS):
                mtime = os.path.getmtime(KINDLE_CLIPPINGS)
                if mtime != last_mtime:
                    logger.info("Kindle detected%s, syncing clippings...",
                                " (updated)" if last_mtime is not None else "")
                    sync_clippings(KINDLE_CLIPPINGS)
                    last_mtime = mtime
            else:
                if last_mtime is not None:
                    logger.info("Kindle disconnected.")
                    last_mtime = None
        except Exception as e:
            logger.error("Sync failed: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
