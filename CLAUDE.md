# Kindle Greek Flashcard Bot — Project Context

## What this is
A Telegram bot that helps the owner learn Greek by turning Kindle highlights into flashcards.
The owner reads Harry Potter in Greek (sideloaded epub), highlights words/phrases in Kindle for Mac,
and the bot processes them into Quizlet-ready cards using Claude API.

## Owner's goal
Learn Greek vocabulary. Highlights are single words or short phrases. Cards need:
- Normalized (dictionary) form on the front
- English translation on the back
- A brief grammar/usage note

## How it works
1. Highlights are read from the Kindle for Mac SQLite annotation DB
2. The `shortPosition` char offset is used to find the highlight in the epub text
3. Surrounding sentence is extracted for context
4. Claude API generates a normalized flashcard from highlight + context
5. Bot sends the card to Telegram with Accept / Edit / Skip buttons
6. Accepted cards accumulate and can be exported as a Quizlet-compatible CSV

## Tech stack
- Python 3.11+
- `python-telegram-bot` 20.7 (async)
- `anthropic` SDK
- `ebooklib` + `beautifulsoup4` for epub parsing
- SQLite (no ORM) for reading Kindle DB
- JSON file for state persistence

## File map
```
bot.py            — Telegram bot entry point, all command/callback handlers
config.py         — All paths, tokens, and book ASIN→epub mappings
kindle_db.py      — Reads highlight records from Kindle annotation SQLite DB
epub_reader.py    — Extracts plain text from epub, resolves context around a position
card_generator.py — Calls Claude API to generate a flashcard JSON
state.py          — StateManager: persists progress + card queue to JSON file
exporter.py       — Dumps accepted cards to tab-separated CSV for Quizlet
requirements.txt  — Python dependencies
```

## Key data structures

### Highlight (kindle_db.py)
```python
@dataclass
class Highlight:
    annotation_id: str   # e.g. "kindle.highlight-32531"
    book_id: str         # full dataset_id string from DB
    asin: str            # e.g. "JF4A2E2AQFQVOKE4YGCCLORXHJOPOCU7"
    start_position: int  # char offset into epub plain text
    end_position: int
    created_time: int    # ms epoch
    modified_time: int
```

### Card (state.py)
```python
@dataclass
class Card:
    annotation_id: str
    asin: str
    highlight: str   # raw highlighted text from epub
    context: str     # surrounding sentence
    front: str       # normalized Greek form (e.g. infinitive for verbs)
    back: str        # English translation
    note: str        # grammar/usage note
    status: str      # "pending" | "accepted" | "skipped"
```

### BotState (state.py)
```python
@dataclass
class BotState:
    last_processed: dict        # asin -> {annotation_id, position}
    pending_cards: list[Card]   # cards waiting for user review
    accepted_cards: list[Card]  # cards the user approved
```
State is saved to `~/.kindle_greek_bot_state.json` after every mutation.

## Kindle DB details
- Path: `~/Library/Containers/com.amazon.Lassen/Data/Library/KSDK/amzn1.account.AE5JBCAZMWVHBRGAS2R2TZDIR3TA/ksdk_annotation_v1.db`
- Table: `server_view`, column `dataset=1` for highlights
- `serialized_payload` is JSON with `type`, `start_position.shortPosition`, `end_position.shortPosition`, `book_data.asin`
- Positions are **character offsets** (not byte offsets) into the epub plain text

## Books configured
| ASIN | Title | epub |
|------|-------|------|
| JF4A2E2AQFQVOKE4YGCCLORXHJOPOCU7 | HP2 - Η Κάμαρα με τα Μυστικά | ~/Downloads/hp2.epub |
| 4VXEGKBCREAAAR57QSG4TGW27HTARRA6 | HP1 - Η Φιλοσοφική Λίθος | ~/Downloads/hp1.epub |

HP2 has ~3871 highlights, HP1 has ~766. Both confirmed working with char offsets.

## Epub text extraction
`epub_reader.load_epub_text()` concatenates `get_text()` from all ITEM_DOCUMENT nodes in order.
The resulting string is ~550k–560k chars per book. This is what positions index into.
Context extraction walks outward from the highlight to find sentence boundaries (`.!?\n`).

## Telegram bot commands
| Command | Handler | Description |
|---------|---------|-------------|
| /next | cmd_next | Process next highlight, send card |
| /batch N | cmd_batch | Process N highlights (default 5, max 20) |
| /stats | cmd_stats | Show accepted/pending/remaining per book |
| /pending | cmd_pending | Re-show last 5 unreviewed cards |
| /export | cmd_export | Write accepted cards to ~/Desktop/greek_flashcards.csv |

Inline buttons: `accept:<id>` / `edit:<id>` / `skip:<id>`
Edit flow: bot stores `editing_id` in `context.user_data`, user replies `front | back | note`

## Environment variables required
```
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
ANTHROPIC_API_KEY
```

## Known issues / things not yet done
- The bot has not been run end-to-end yet — first run may surface bugs
- No file watcher yet (auto-trigger on new highlights); currently manual `/next` or `/batch`
- No deduplication guard if a highlight appears in both `server_view` and `local_edit`
- `/batch` sends all cards sequentially without waiting for user review between them — may want to change this to queue them and send one at a time
- Edit flow doesn't auto-advance if user sends plain text that isn't a card edit (falls through silently)
- `exporter.py` writes to a hardcoded desktop path; could be improved to send the file directly in Telegram

## How to run
```bash
pip3 install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export ANTHROPIC_API_KEY=...
python3 bot.py
```
