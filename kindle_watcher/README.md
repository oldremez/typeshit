# Kindle Watcher

Runs on your Mac. When a Kindle is connected, it detects `My Clippings.txt` and syncs it to the remote server via SCP. Designed to be called from cron — it exits immediately if the Kindle isn't mounted or if nothing has changed.

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
LOG_LEVEL=INFO                          # optional, default INFO (use DEBUG to trace skips)
```

Make sure your SSH key is added to `~/.ssh/authorized_keys` on the server so SCP runs without a password prompt.

### 3. Test it manually

Plug in your Kindle, then run:

```bash
venv/bin/python3 watcher.py
```

You should see a log line like `Kindle detected, syncing clippings...`. Run it a second time — it should log nothing (clippings unchanged).

### 4. Install as a cron job

```bash
crontab -e
```

Add a line to run every minute:

```
* * * * * cd /path/to/typeshit/kindle_watcher && venv/bin/python3 watcher.py >> /tmp/kindlewatcher.log 2>&1
```

Replace `/path/to/typeshit` with the actual path. The script exits in milliseconds when the Kindle isn't connected, so running every minute is cheap.

To check logs:

```bash
tail -f /tmp/kindlewatcher.log
```

### Removing

```bash
crontab -e  # delete the line
```

## How it works

- On each run, checks for `/Volumes/Kindle/documents/My Clippings.txt`
- If found, compares mtime against `~/.typeshit/kindle_last_mtime`
- Syncs via SCP only if the file is new or has changed; updates the stored mtime on success
- Exits with code 0 on success or no-op, code 1 on sync failure
