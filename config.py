import os

# === FILL THESE IN ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")

# === KINDLE DB ===
KINDLE_ACCOUNT_ID = "amzn1.account.AE5JBCAZMWVHBRGAS2R2TZDIR3TA"
ANNOTATION_DB = os.path.expanduser(
    f"~/Library/Containers/com.amazon.Lassen/Data/Library/KSDK"
    f"/{KINDLE_ACCOUNT_ID}/ksdk_annotation_v1.db"
)

# === BOOK LIBRARY ===
# Maps Kindle ASIN → local epub path and friendly title.
# Add more books here as you sideload them.
BOOKS = {
    "JF4A2E2AQFQVOKE4YGCCLORXHJOPOCU7": {
        "title": "HP2 - Η Κάμαρα με τα Μυστικά",
        "epub":  os.path.expanduser("~/Downloads/hp2.epub"),
    },
    "4VXEGKBCREAAAR57QSG4TGW27HTARRA6": {
        "title": "HP1 - Η Φιλοσοφική Λίθος",
        "epub":  os.path.expanduser("~/Downloads/hp1.epub"),
    },
}

# === STATE & EXPORT ===
STATE_FILE  = os.path.expanduser("~/.kindle_greek_bot_state.json")
EXPORT_CSV  = os.path.expanduser("~/Desktop/greek_flashcards.csv")
