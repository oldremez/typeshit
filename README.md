# Greek Kindle Flashcard Bot

A Telegram bot that reads your Kindle highlights from Harry Potter in Greek,
enriches them with sentence context from the epub, and uses Claude to generate
flashcards — which you review and export to Quizlet.

## Architecture

The project is split into two components:

- **Bot** (runs on a remote server) — handles Telegram interactions, generates cards with Claude, tracks review state
- **Kindle Watcher** (`kindle_watcher/`, runs on your Mac) — monitors for Kindle USB connection and syncs `My Clippings.txt` to the server via SCP

When you plug in your Kindle, the watcher automatically syncs the clippings file to the server. The bot reads it from there on every `/next`.

## Bot Setup

### 1. Create a Telegram bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow instructions
3. Copy the token you receive

### 2. Get your Telegram Chat ID
1. Start your bot (send it `/start`)
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat": {"id": 123456789}` — that's your chat ID

### 3. Create a `.env` file
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ANTHROPIC_API_KEY=your_anthropic_key_here
LOG_LEVEL=INFO
```

### 4. Run with Docker

```bash
docker compose up -d
```

The data directory `~/.typeshit` is bind-mounted into the container so state, clippings, epubs, and books survive restarts and rebuilds.

Follow logs:
```bash
docker compose logs -f
```

Restart / stop:
```bash
docker compose restart
docker compose down
```

Rebuild after code changes:
```bash
docker compose up -d --build
```

## Kindle Watcher Setup

See [`kindle_watcher/README.md`](kindle_watcher/README.md) for full instructions. The watcher runs on your Mac as a cron job and syncs clippings to the server via SCP whenever the Kindle is connected.

## Usage

| Command | Description |
|---------|-------------|
| `/next` | Review next pending card, or generate one from a new highlight |
| `/stats` | Show progress (accepted, pending, remaining per book) |
| `/pending` | Re-show the last 5 unreviewed cards |
| `/setepub` | Upload an epub file for a book |

Cards are exported automatically as a Telegram file every 30 accepted cards.

## Card Review Flow

When you receive a card:
- **✅ Accept** — save it, move to next
- **✏️ Edit** — correct the card, then type: `front | back | note`
- **⏭ Skip** — discard this highlight, move on

## Quizlet Import

After `/export` or an automatic export, you receive a `.txt` file in chat.

In Quizlet:
1. Create set → Import
2. Upload or paste the file contents
3. Set **"Between term and definition"** → Tab
4. Set **"Between rows"** → New line
5. Import ✓

## File Structure

```
├── bot.py               # Telegram bot (main entry point)
├── config.py            # Paths, tokens, thresholds
├── clippings_parser.py  # Parses My Clippings.txt from Kindle
├── epub_reader.py       # Extracts context from epub
├── card_generator.py    # Claude API call to generate cards
├── state.py             # Tracks progress (JSON file on disk)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Bot container image
├── docker-compose.yml   # Compose config (bind-mounts ~/.typeshit)
└── kindle_watcher/      # Local Mac agent for Kindle sync
    ├── watcher.py
    ├── requirements.txt
    └── README.md
```
