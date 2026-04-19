# Kindle Watcher

Runs on your Mac in the background. When a Kindle is connected, it detects `My Clippings.txt` and sends it to the remote Telegram bot, which stores it and uses it for flashcard generation.

## Setup

### 1. Create a virtualenv and install dependencies

```bash
cd kindle_watcher
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Create a `.env` file

```
SERVER_USER=your_ssh_username
SERVER_HOST=your.server.address
SERVER_PATH=~/.typeshit/clippings.txt   # optional, this is the default
SSH_KEY=~/.ssh/id_ed25519               # optional, omit to use SSH default
```

Make sure your SSH key is added to `~/.ssh/authorized_keys` on the server so SCP runs without a password prompt.

### 3. Test it manually

Plug in your Kindle, then run:

```bash
venv/bin/python3 watcher.py
```

You should see a log line like `Kindle detected, sending clippings...` and the bot should reply with a sync confirmation. Logs are printed to stdout.

### 4. Install as a background service

The included `com.kindlewatcher.plist` registers the watcher as a launchd user agent — it starts on login and restarts automatically if it crashes.

```bash
sed "s|__DIR__|$(pwd)|g" com.kindlewatcher.plist > ~/Library/LaunchAgents/com.kindlewatcher.plist
launchctl load ~/Library/LaunchAgents/com.kindlewatcher.plist
```

Run this from the `kindle_watcher` directory so that `$(pwd)` resolves to the correct path.

Logs are written to `/tmp/kindlewatcher.log`:

```bash
tail -f /tmp/kindlewatcher.log
```

### Stopping / uninstalling

```bash
launchctl unload ~/Library/LaunchAgents/com.kindlewatcher.plist
rm ~/Library/LaunchAgents/com.kindlewatcher.plist
```

## How it works

- Polls every 10 seconds for `/Volumes/Kindle/documents/My Clippings.txt`
- Sends the file to the bot on first detection and again whenever the file changes (i.e. new highlights were added during the session)
- The remote bot saves the file to `~/.kindle_clippings.txt` and uses it as the clippings source
