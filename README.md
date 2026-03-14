# One-time setup (per person)

## 1. Create VENV & Install deps
```bash
cd linkedin_jobs_notification
uv venv
uv sync --extra dev
uv run playwright install chromium
```
NOTE: The only time you'd set up a venv in linkedin_scraper is if you want to run its own tests or sample scripts independently.

## 2. Generate session — run from linkedin_jobs_notification/ so it saves in the right place
```bash
uv run python ../linkedin_scraper/samples/create_session.py
#    → browser opens, log in manually → linkedin_session.json saved HERE ✓
```

## 3. Config
```bash
cp config.yaml.example config.yaml       # edit your search profiles
cp .env.example .env                     # fill in TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
```

## Every run:
```bash
cd linkedin_jobs_notification
uv run python main.py
```
Following will run the main script, which will check for new jobs and send Telegram notifications if there are any.

## Optional: run on a schedule (e.g. every 6h) 
```bash
# open crontab
crontab -e
# add line (adjust path + timing as needed)
0 */6 * * * cd /path/to/linkedin_jobs_notification && uv run python main
```

### How to setup TELEGRAM CHAT BOT:
1. Find `BotFather` in Telegram and start a chat.
2. Send `/newbot` and follow instructions to create a new bot. You'll get a `TELEGRAM_BOT_TOKEN`.
3. To get `TELEGRAM_CHAT_ID`, start a chat with your bot and send any message. Then, visit `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates` in your browser (replace `<TELEGRAM_BOT_TOKEN>` with your actual token). Look for the `chat` object in the JSON response to find your `id`, which is your `TELEGRAM_CHAT_ID`.