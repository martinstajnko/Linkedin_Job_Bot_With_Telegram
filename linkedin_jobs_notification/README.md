# linkedin_jobs_notification

Cron-based app that watches LinkedIn for new job postings matching your search profiles and sends a Telegram notification for each new match.

## Prerequisites

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A LinkedIn account
- A Telegram bot (see [BotFather](https://t.me/BotFather))
- Playwright browsers installed

## Setup

### 1. Install dependencies

```bash
cd linkedin_jobs_notification
uv sync --extra dev
uv run playwright install chromium
```

### 2. Create your LinkedIn session file

Run the helper script **once** to log in interactively and save the session:

```bash
cd ../linkedin_scraper
uv run python samples/create_session.py
```

This saves a `linkedin_session.json` file. Keep it secret — it contains your auth cookies.

### 3. Configure search profiles

Copy the example config and edit it:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
linkedin:
  session_file: linkedin_session.json   # path to your session file

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"    # resolved from .env or environment
  chat_id: "${TELEGRAM_CHAT_ID}"

searches:
  - name: "QA Engineer Remote"
    keywords: "QA Engineer"
    location: "Worldwide"
    remote: true
    posted_within_hours: 24
    limit: 25
```

### 4. Set Telegram secrets

```bash
cp .env.example .env
# Edit .env and fill in your bot token and chat ID
```

`.env`:
```
TELEGRAM_BOT_TOKEN=123456789:AABBccddeeffgghh...
TELEGRAM_CHAT_ID=-1001234567890
```

> **Get your chat ID:** Send a message to your bot, then visit:
> `https://api.telegram.org/bot<TOKEN>/getUpdates`

## Running

### Manually

```bash
cd linkedin_jobs_notification
uv run python main.py
```

### With cron (every 30 minutes)

```bash
crontab -e
```

Add:
```
*/30 * * * * cd /path/to/linkedin_jobs_notification && /path/to/uv run python main.py >> /tmp/linkedin_jobs.log 2>&1
```

Find the full path to `uv` with `which uv`.

## Running tests

```bash
cd linkedin_jobs_notification
uv run pytest tests/ -v
```

## Project structure

```
linkedin_jobs_notification/
├── main.py          # Entry point / orchestrator
├── config.py        # Config loader + Pydantic models
├── store.py         # SeenJobsStore (aiosqlite dedup)
├── notifier.py      # Telegram notification sender
├── config.yaml      # Your config (gitignored)
├── config.yaml.example
├── .env             # Your secrets (gitignored)
├── .env.example
└── tests/
    ├── test_config.py
    ├── test_store.py
    └── test_notifier.py
```

## Security notes

- `config.yaml`, `.env`, and `*_session.json` are in `.gitignore` — never commit them.
- The Telegram bot token and chat ID must always come from environment variables.
- Do not run multiple instances of this app with the same LinkedIn account simultaneously.
