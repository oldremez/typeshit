# Greek Kindle Flashcard Bot

A Telegram bot that reads your Kindle highlights from Harry Potter in Greek,
enriches them with sentence context from the epub, and uses Claude to generate
flashcards — which you review and export to Quizlet.

## Architecture

The project is split into two components:

- **Bot** (runs on a remote server) — handles Telegram interactions, generates cards with Claude, tracks review state
- **Kindle Watcher** (`kindle_watcher/`, runs on your Mac) — monitors for Kindle USB connection and syncs `My Clippings.txt` to the bot via Telegram

When you plug in your Kindle, the watcher automatically sends the clippings file to the bot. The bot saves it locally and uses it as the source for new highlights. No manual file handling needed.

## Bot Setup

### 1. Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create a Telegram bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow instructions
3. Copy the token you receive

### 3. Get your Telegram Chat ID
1. Start your bot (send it `/start`)
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat": {"id": 123456789}` — that's your chat ID

### 4. Create a `.env` file
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 5. Run the bot

For a quick test:
```bash
python3 bot.py
```

For persistent background execution on a Linux server, use systemd. Run this from the project directory — it uses `$PWD` and `$USER` so nothing needs to be edited manually:

```bash
sudo tee /etc/systemd/system/kindlebot.service > /dev/null << EOF
[Unit]
Description=Kindle Greek Flashcard Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=$PWD/venv/bin/python3 bot.py
Restart=on-failure
RestartSec=10
StandardOutput=append:$PWD/bot.log
StandardError=append:$PWD/bot.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable kindlebot
sudo systemctl start kindlebot
```

Check status and follow logs:
```bash
sudo systemctl status kindlebot
tail -f bot.log
```

## Kindle Watcher Setup

See [`kindle_watcher/README.md`](kindle_watcher/README.md) for full instructions. Short version:

```bash
cd kindle_watcher
python3 -m venv venv
venv/bin/pip install -r requirements.txt
# create .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
sed "s|__DIR__|$(pwd)|g" com.kindlewatcher.plist > ~/Library/LaunchAgents/com.kindlewatcher.plist
launchctl load ~/Library/LaunchAgents/com.kindlewatcher.plist
```

## Usage

| Command | Description |
|---------|-------------|
| `/next` | Review next pending card, or generate one from a new highlight |
| `/batch 5` | Generate 5 new cards at once |
| `/stats` | Show progress (accepted, pending, remaining) |
| `/pending` | Re-show the last 5 unreviewed cards |
| `/export` | Export accepted cards to CSV for Quizlet |

Cards are also exported automatically as a Telegram file every 30 accepted cards.

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
├── config.py            # Paths, tokens, book mappings
├── clippings_parser.py  # Parses My Clippings.txt from Kindle
├── epub_reader.py       # Extracts context from epub
├── card_generator.py    # Claude API call to generate cards
├── state.py             # Tracks progress (JSON file on disk)
├── exporter.py          # Exports to Quizlet-compatible CSV
├── requirements.txt     # Python dependencies
└── kindle_watcher/      # Local Mac agent for Kindle sync
    ├── watcher.py
    ├── requirements.txt
    ├── com.kindlewatcher.plist
    └── README.md
```
