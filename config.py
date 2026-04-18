import json
import os
from dotenv import load_dotenv

load_dotenv()

# === CREDENTIALS ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")

# === KINDLE ===
CLIPPINGS_PATH = os.path.expanduser("~/.kindle_clippings.txt")

# === BOOKS ===
# Loaded from books.json. Each entry: { "title", "epub", "clippings_title" }
# epub paths support ~ expansion.
_books_file = os.path.join(os.path.dirname(__file__), "books.json")
with open(_books_file, encoding="utf-8") as _f:
    _raw = json.load(_f)

BOOKS = {asin: {**book, "epub": os.path.expanduser(book["epub"])} for asin, book in _raw.items()}
CLIPPINGS_TITLE_TO_ASIN = {book["clippings_title"]: asin for asin, book in BOOKS.items()}

# === STATE & EXPORT ===
STATE_FILE            = os.path.expanduser("~/.kindle_greek_bot_state.json")
EXPORT_CSV            = os.path.expanduser("~/Desktop/greek_flashcards.csv")
AUTO_EXPORT_THRESHOLD = 30
