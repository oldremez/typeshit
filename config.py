import json
import os
from dotenv import load_dotenv

load_dotenv()

# === CREDENTIALS ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")

# === DATA DIR ===
DATA_DIR = os.path.expanduser("~/.typeshit")
os.makedirs(DATA_DIR, exist_ok=True)

# === KINDLE ===
CLIPPINGS_PATH = os.path.join(DATA_DIR, "clippings.txt")

# === BOOKS ===
# Loaded from books.json. Each entry: { "title", "epub", "clippings_title" }
# epub paths support ~ expansion.
BOOKS_FILE = os.path.join(DATA_DIR, "books.json")
EPUBS_DIR  = os.path.join(DATA_DIR, "epubs")
os.makedirs(EPUBS_DIR, exist_ok=True)

if not os.path.exists(BOOKS_FILE):
    with open(BOOKS_FILE, "w", encoding="utf-8") as _f:
        json.dump({}, _f)
with open(BOOKS_FILE, encoding="utf-8") as _f:
    _raw = json.load(_f)

BOOKS = {book_id: {**book, "epub": os.path.expanduser(book["epub"]) if book.get("epub") else ""} for book_id, book in _raw.items()}

# === LOGGING ===
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# === STATE ===
STATE_FILE            = os.path.join(DATA_DIR, "state.json")
AUTO_EXPORT_THRESHOLD = 30
