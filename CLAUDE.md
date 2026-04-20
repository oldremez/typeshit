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
- Reads `My Clippings.txt` stored at `~/.typeshit/clippings.txt` (synced from Kindle via SCP)
- Extracts context from epub files stored at `~/.typeshit/epubs/<book_id>.epub`
- Generates cards via Claude API
- Handles all Telegram interactions
- Only processes highlights from books that have an epub configured

**Kindle Watcher** (`kindle_watcher/`, runs on the owner's Mac):
- One-shot script, designed to be called from cron (every minute)
- Checks if Kindle is mounted at `/Volumes/Kindle/documents/My Clippings.txt`
- Syncs via SCP if the file is new or changed (tracks last mtime in `~/.typeshit/kindle_last_mtime`)
- Exits immediately if Kindle not mounted or nothing changed

## How it works
1. Kindle connects → cron fires watcher → SCP syncs `My Clippings.txt` to server `~/.typeshit/clippings.txt`
2. `/next` parses clippings, finds first unprocessed highlight from a book with an epub
3. Highlight text is searched in the epub to extract surrounding sentence context
4. Claude API generates a normalized flashcard from highlight + context
5. Bot sends the card to Telegram with Accept / Edit / Skip buttons
6. While user reviews the card, the next card is pre-generated in the background (prefetch)
7. Every 30 accepted cards, bot sends a Quizlet-ready TSV file in chat and clears the queue

## Tech stack
- Python 3.13
- `python-telegram-bot` 21.9 (async)
- `anthropic` SDK (`claude-sonnet-4-6`)
- `ebooklib` + `beautifulsoup4` for epub parsing
- `python-dotenv` for environment variable loading
- JSON file for state persistence

## File map
```
bot.py               — Telegram bot entry point, all command/callback handlers
config.py            — Paths, tokens, thresholds; auto-creates data dir and files on import
clippings_parser.py  — Parses My Clippings.txt, returns ClippingHighlight records
epub_reader.py       — Loads epub text, finds context around a highlight by text search
card_generator.py    — Calls Claude API to generate a flashcard JSON
state.py             — StateManager: persists progress + card queue to JSON file
requirements.txt     — Python dependencies

kindle_watcher/
  watcher.py         — One-shot script: checks Kindle mount, syncs via SCP if changed
  requirements.txt   — Watcher dependencies (python-dotenv only)
  README.md          — Watcher setup instructions (cron-based)
```

## Key data structures

### ClippingHighlight (clippings_parser.py)
```python
@dataclass
class ClippingHighlight:
    annotation_id: str   # "cl-" + md5(book_title|location_start|text)[:12]
    book_id: str         # md5(book_title)[:12] — stable key for books.json
    book_title: str
    text: str            # the actual highlighted text from My Clippings.txt
    location_start: int  # Kindle location number
    location_end: int
    added_date: str
```

### Card (state.py)
```python
@dataclass
class Card:
    annotation_id: str
    asin: str            # actually book_id (md5 hash), field name kept for compat
    highlight: str       # highlighted text (from clippings)
    context: str         # surrounding sentence (from epub search)
    front: str           # normalized Greek form (e.g. infinitive for verbs)
    back: str            # Russian translation
    note: str            # grammar/usage note in Russian
    status: str          # "pending" | "accepted" | "skipped"
```

### BotState (state.py)
```python
@dataclass
class BotState:
    processed_ids: list[str]    # annotation_ids already turned into cards
    pending_cards: list[Card]   # cards waiting for user review
    accepted_cards: list[Card]  # cards the user approved (cleared every 30)
```
State is saved to `~/.typeshit/state.json` after every mutation.

## Books (books.json)
Stored at `~/.typeshit/books.json`. Auto-discovered from clippings on bot startup and on `/setepub`.
Keyed by `book_id` (md5 hash of clippings title):
```json
{
  "<book_id>": {
    "title": "HP1 - Η Φιλοσοφική Λίθος",
    "clippings_title": "full title as it appears in My Clippings.txt",
    "epub": "~/.typeshit/epubs/<book_id>.epub"
  }
}
```
Only books with a non-empty `epub` field are eligible for card generation.

## My Clippings.txt format
```
BOOK TITLE (Author)
- Your Highlight on page X | Location Y-Z | Added on DAY, DD MONTH YYYY HH:MM:SS

highlighted text
==========
```
Only `Your Highlight` entries are parsed; bookmarks and notes are skipped.

## Telegram bot commands
Commands are defined once in the `COMMANDS` list in `bot.py` and automatically registered
with BotFather via `set_my_commands()` on startup.

| Command | Handler | Description |
|---------|---------|-------------|
| /next | cmd_next | Review next card or generate from a new highlight |
| /stats | cmd_stats | Show progress per book |
| /pending | cmd_pending | Re-show last 5 unreviewed cards |
| /setepub | cmd_setepub | Upload an epub for a book |

Inline buttons: `accept:<id>` / `edit:<id>` / `skip:<id>`
Edit flow: bot stores `editing_id` in `context.user_data`, user replies `front | back | note`

## Prefetch
After showing any card, the bot fires `_prefetch_next_card()` as a background asyncio task.
It generates the next card via `asyncio.to_thread(generate_card, ...)` so the event loop
is never blocked. When the user accepts/skips and the bot calls `process_next_highlight`,
the prefetched card is already in `pending_cards` and is shown instantly.

## Auto-export
When `accepted_cards` reaches `config.AUTO_EXPORT_THRESHOLD` (default 30), the bot sends a
TSV file in chat and clears `accepted_cards`. Format: `front\tback | note` per line.

## Environment variables

**Bot (.env on server):**
```
TELEGRAM_BOT_TOKEN    — bot token from @BotFather
TELEGRAM_CHAT_ID      — your personal chat ID
ANTHROPIC_API_KEY     — Claude API key
LOG_LEVEL             — optional, default INFO
```

**Watcher (.env on Mac, kindle_watcher/.env):**
```
SERVER_USER           — SSH username on the server
SERVER_HOST           — server hostname or IP
SERVER_PATH           — optional, default ~/.typeshit/clippings.txt
SSH_KEY               — optional, path to SSH key (e.g. ~/.ssh/id_ed25519)
LOG_LEVEL             — optional, default INFO (use DEBUG to trace skips)
```

## Data directory layout
```
~/.typeshit/
  clippings.txt        — My Clippings.txt synced from Kindle
  books.json           — auto-maintained book registry
  state.json           — bot progress (processed IDs, pending/accepted cards)
  epubs/               — uploaded epub files, named <book_id>.epub
  kindle_last_mtime    — last synced mtime (used by watcher, on Mac)
```

## Known issues
- Context search (`epub_reader.find_context`) uses `str.find()` — will miss highlights
  if the epub text differs slightly from clippings text (encoding, whitespace)
- Edit flow falls through silently if user sends plain text with no active `editing_id`

## How to run
```bash
pip3 install -r requirements.txt
# create .env with TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ANTHROPIC_API_KEY
python3 bot.py
```
