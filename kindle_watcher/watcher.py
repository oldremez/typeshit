"""
watcher.py
Monitors Kindle mount on macOS and syncs My Clippings.txt to the remote bot via Telegram.

Run: python3 watcher.py
"""

import asyncio
import logging
import os
import time

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

KINDLE_CLIPPINGS = "/Volumes/Kindle/documents/My Clippings.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]
POLL_INTERVAL = 10  # seconds between mount checks


async def send_clippings(path: str):
    bot = Bot(token=BOT_TOKEN)
    with open(path, "rb") as f:
        await bot.send_document(
            chat_id=CHAT_ID,
            document=f,
            filename="My Clippings.txt",
            caption="kindle_sync",
        )
    logger.info("Clippings sent to bot.")


def main():
    logger.info("Kindle watcher started. Polling every %ds for %s", POLL_INTERVAL, KINDLE_CLIPPINGS)
    last_mtime = None

    while True:
        try:
            if os.path.exists(KINDLE_CLIPPINGS):
                mtime = os.path.getmtime(KINDLE_CLIPPINGS)
                if mtime != last_mtime:
                    logger.info("Kindle detected%s, sending clippings...",
                                " (updated)" if last_mtime is not None else "")
                    asyncio.run(send_clippings(KINDLE_CLIPPINGS))
                    last_mtime = mtime
            else:
                if last_mtime is not None:
                    logger.info("Kindle disconnected.")
                    last_mtime = None
        except TelegramError as e:
            logger.error("Telegram error: %s", e)
        except Exception as e:
            logger.exception("Unexpected error: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
