# Kindle Greek Flashcard Bot — Project Context

## What this is
A Telegram bot that helps the owner learn Greek by turning Kindle highlights into flashcards.
The owner reads Harry Potter in Greek on a Kindle device, highlights words/phrases, and the bot
processes them into Quizlet-ready cards using Claude API.

## Owner's goal
Learn Greek vocabulary. Highlights are single words or short phrases. Cards need:
- Normalized (dictionary) form on the front
- Russian translation on the back
- A brief grammar/usage note in Russian

## Architecture
Two separate components:

**Bot** (runs on a remote server):
- Reads `My Clippings.txt` stored locally (synced from Kindle)
- Extracts context from epub files
- Generates cards via Claude API
- Handles all Telegram interactions

**Kindle Watcher** (`kindle_watcher/`, runs on the owner's Mac):
- Polls for Kindle USB mount
- On detection, sends `My Clippings.txt` to the bot via Telegram
- Runs as a launchd background service

## How it works
1. Kindle connects → watcher sends `My Clippings.txt` to bot via Telegram
2. Bot saves the file to `~/.kindle_clippings.txt`
3. `/next` or `/batch` parses the clippings, finds unprocessed highlights
4. Highlight text is searched in the epub to extract surrounding sentence context
5. Claude API generates a normalized flashcard from highlight + context
6. Bot sends the card to Telegram with Accept / Edit / Skip buttons
7. Every 30 accepted cards, bot sends a Quizlet-ready TSV file in chat and clears the queue

## Tech stack
- Python 3.13
- `python-telegram-bot` 21.9 (async)
- `anthropic` SDK
- `ebooklib` + `beautifulsoup4` for epub parsing
- `python-dotenv` for environment variable loading
- JSON file for state persistence

## File map
```
bot.py               — Telegram bot entry point, all command/callback handlers
config.py            — All paths, tokens, book ASIN→epub mappings, thresholds
clippings_parser.py  — Parses My Clippings.txt, returns ClippingHighlight records
epub_reader.py       — Loads epub text, finds context around a highlight by text search
card_generator.py    — Calls Claude API to generate a flashcard JSON
state.py             — StateManager: persists progress + card queue to JSON file
exporter.py          — Dumps accepted cards to tab-separated CSV for Quizlet
requirements.txt     — Python dependencies

kindle_watcher/
  watcher.py                 — Polls for Kindle mount, sends clippings via Telegram
  requirements.txt           — Watcher dependencies (telegram + dotenv only)
  com.kindlewatcher.plist    — launchd agent for autostart (uses __DIR__ placeholder)
  README.md                  — Watcher setup instructions
```

## Key data structures

### ClippingHighlight (clippings_parser.py)
```python
@dataclass
class ClippingHighlight:
    annotation_id: str   # stable md5 hash of (book_title, location_start, text)
    asin: str
    book_title: str
    text: str            # the actual highlighted text from My Clippings.txt
    location_start: int  # Kindle location number (used for ordering)
    location_end: int
    added_date: str
```

### Card (state.py)
```python
@dataclass
class Card:
    annotation_id: str
    asin: str
    highlight: str   # highlighted text (from clippings)
    context: str     # surrounding sentence (from epub search)
    front: str       # normalized Greek form (e.g. infinitive for verbs)
    back: str        # Russian translation
    note: str        # grammar/usage note in Russian
    status: str      # "pending" | "accepted" | "skipped"
```

### BotState (state.py)
```python
@dataclass
class BotState:
    processed_ids: list[str]    # annotation_ids already turned into cards
    pending_cards: list[Card]   # cards waiting for user review
    accepted_cards: list[Card]  # cards the user approved (cleared every 30)
```
State is saved to `.kindle_greek_bot_state.json` (project root) after every mutation.

## My Clippings.txt format
```
BOOK TITLE (Author)
- Your Highlight on page X | Location Y-Z | Added on DAY, DD MONTH YYYY HH:MM:SS

highlighted text
==========
```
Only `Your Highlight` entries are parsed; bookmarks and notes are skipped.
Book matching uses a title substring configured per-book in `config.CLIPPINGS_TITLE_TO_ASIN`.

## Books configured
| ASIN | Title | Clippings fragment |
|------|-------|--------------------|
| JF4A2E2AQFQVOKE4YGCCLORXHJOPOCU7 | HP1 - Η Φιλοσοφική Λίθος | Φιλοσοφική Λίθος |
| 4VXEGKBCREAAAR57QSG4TGW27HTARRA6 | HP2 - Η Κάμαρα με τα Μυστικά | Κάμαρα με τα Μυστικά |

Epub files are read from `~/Downloads/hp1.epub` and `~/Downloads/hp2.epub` for context extraction only.

## Telegram bot commands
| Command | Handler | Description |
|---------|---------|-------------|
| /next | cmd_next | Show next pending card, or generate one from a new highlight |
| /batch N | cmd_batch | Generate N new cards (default 5, max 20) |
| /stats | cmd_stats | Show accepted/pending/remaining per book |
| /pending | cmd_pending | Re-show last 5 unreviewed cards |
| /export | cmd_export | Send accepted cards as TSV file in chat |

Inline buttons: `accept:<id>` / `edit:<id>` / `skip:<id>`
Edit flow: bot stores `editing_id` in `context.user_data`, user replies `front | back | note`

Document upload: sending `My Clippings.txt` to the bot saves it as the new clippings source.

## Auto-export
When `accepted_cards` reaches `config.AUTO_EXPORT_THRESHOLD` (default 30), the bot sends a
TSV file in chat and clears `accepted_cards`. Format: `front\tback | note` per line.

## Environment variables
```
TELEGRAM_BOT_TOKEN    — bot token from @BotFather
TELEGRAM_CHAT_ID      — your personal chat ID
ANTHROPIC_API_KEY     — Claude API key
```
Loaded via `.env` file using `python-dotenv`.

## Known issues / things not yet done
- Context search (`epub_reader.find_context`) uses a simple `str.find()` — will miss highlights
  if the epub text differs slightly from the clippings text (encoding, whitespace)
- `/batch` generates cards without waiting for review between them — queue is reviewed one at a time via `/next` afterwards
- Edit flow falls through silently if user sends plain text that isn't a card edit and no `editing_id` is set

## How to run
```bash
pip3 install -r requirements.txt
# create .env with the three vars above
python3 bot.py
```
