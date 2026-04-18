import os
from dotenv import load_dotenv

load_dotenv()

# === FILL THESE IN ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")

# === KINDLE DEVICE ===
CLIPPINGS_PATH = "/Volumes/Kindle/documents/My Clippings.txt"

# === BOOK LIBRARY ===
# Maps Kindle ASIN → epub for context extraction + title fragment for matching clippings.
BOOKS = {
    "JF4A2E2AQFQVOKE4YGCCLORXHJOPOCU7": {
        "title": "HP1 - Η Φιλοσοφική Λίθος",
        "epub":  os.path.expanduser("~/Downloads/hp1.epub"),
        "clippings_title": "Φιλοσοφική Λίθος",
    },
    "4VXEGKBCREAAAR57QSG4TGW27HTARRA6": {
        "title": "HP2 - Η Κάμαρα με τα Μυστικά",
        "epub":  os.path.expanduser("~/Downloads/hp2.epub"),
        "clippings_title": "Κάμαρα με τα Μυστικά",
    },
}

CLIPPINGS_TITLE_TO_ASIN = {v["clippings_title"]: k for k, v in BOOKS.items()}

# === STATE & EXPORT ===
STATE_FILE  = os.path.expanduser(".kindle_greek_bot_state.json")
EXPORT_CSV  = os.path.expanduser("~/Desktop/greek_flashcards.csv")
AUTO_EXPORT_THRESHOLD = 30
