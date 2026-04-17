# Greek Kindle Flashcard Bot

A Telegram bot that reads your Kindle highlights from Harry Potter in Greek,
enriches them with sentence context from the epub, and uses Claude to generate
flashcards — which you review and export to Quizlet.

## Setup

### 1. Install dependencies
```bash
cd kindle_greek_bot
pip3 install -r requirements.txt
```

### 2. Create a Telegram bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow instructions
3. Copy the token you receive

### 3. Get your Telegram Chat ID
1. Start your bot (send it `/start`)
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat": {"id": 123456789}` — that's your chat ID

### 4. Set environment variables
Create a `.env` file in the project root:
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 5. Update config.py
Edit `config.py` and set `EPUB_PATH` to point to your epub file:
```python
EPUB_PATH = os.path.expanduser("~/Downloads/hp2.epub")
```

### 6. Run the bot
```bash
python3 bot.py
```

## Usage

| Command | Description |
|---------|-------------|
| `/next` | Process the next highlight and send a card for review |
| `/batch 5` | Process 5 highlights at once |
| `/stats` | Show progress (accepted, pending, remaining) |
| `/pending` | Re-show the last 5 unreviewed cards |
| `/export` | Export accepted cards to CSV for Quizlet |

## Card Review Flow

When you receive a card:
- **✅ Accept** — save it as-is, move to next highlight
- **✏️ Edit** — correct the card, then type: `front | back | note`
- **⏭ Skip** — discard this highlight, move on

## Quizlet Import

After `/export`, a file appears at `~/Desktop/greek_flashcards.csv`.

In Quizlet:
1. Create set → Import
2. Paste file contents (or upload)
3. Set **"Between term and definition"** → Tab
4. Set **"Between rows"** → New line
5. Import ✓

## File Structure

```
kindle_greek_bot/
├── bot.py              # Telegram bot (main entry point)
├── config.py           # Paths and API keys
├── kindle_db.py        # Reads highlights from Kindle SQLite DB
├── epub_reader.py      # Extracts text + context from epub
├── card_generator.py   # Claude API call to generate cards
├── state.py            # Tracks progress (JSON file on disk)
├── exporter.py         # Exports to Quizlet CSV
└── requirements.txt    # Python dependencies
```

State is saved to `~/.kindle_greek_bot_state.json` automatically.
