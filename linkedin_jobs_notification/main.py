"""Entry point for the LinkedIn jobs cron notification app.

Invoked by cron every N minutes.  For each search profile in config.yaml it:
  1. Scrapes LinkedIn job search results (Playwright, read-only, async)
  2. Filters out already-seen job IDs (SQLite via SeenJobsStore)
  3. Sends a Telegram notification for each new job
  4. Persists the new job IDs so they are not re-notified next cycle
"""
import asyncio
import logging
import sys
from pathlib import Path

from linkedin_scraper import BrowserManager
from linkedin_scraper.scrapers.job_search import JobSearchScraper
from linkedin_scraper.scrapers.job import JobScraper

from config import AppConfig, SearchProfile, load_config
from store import SeenJobsStore
from notifier import send_job_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _run_profile(
    profile: SearchProfile,
    browser_manager: BrowserManager,
    store: SeenJobsStore,
    config: AppConfig,
) -> int:
    """Run a single search profile and notify about new jobs.

    Returns:
        Number of new jobs notified.
    """
    logger.info("Running profile '%s' (keywords=%r, remote=%s)", profile.name, profile.keywords, profile.remote)
    new_count = 0

    search_scraper = JobSearchScraper(browser_manager.page)
    job_urls = await search_scraper.search(
        keywords=profile.keywords,
        location=profile.location,
        limit=profile.limit,
        remote=profile.remote,
        posted_within_hours=profile.posted_within_hours,
    )
    logger.info("Profile '%s': found %d job URL(s).", profile.name, len(job_urls))

    for url in job_urls:
        # Normalise URL — strip query params to use as stable ID
        job_id = url.split("?")[0].rstrip("/")

        if not await store.is_new(job_id):
            logger.debug("Already seen: %s", job_id)
            continue

        # Scrape job details
        try:
            job_scraper = JobScraper(browser_manager.page)
            job = await job_scraper.scrape(url)
        except Exception:
            logger.exception("Failed to scrape job details for %s — skipping.", url)
            continue

        # Send Telegram notification
        try:
            await send_job_notification(config.telegram, job, profile.name)
        except Exception:
            logger.exception("Failed to send Telegram notification for %s — will still mark seen.", url)

        await store.mark_seen(job_id, profile.name)
        new_count += 1

    return new_count


async def run(config_path: str | Path = "config.yaml") -> None:
    """Main async entry point."""
    config = load_config(config_path)

    async with SeenJobsStore(config.linkedin.session_file.replace(".json", "_seen.db")) as store:
        async with BrowserManager() as browser:
            await browser.load_session(config.linkedin.session_file)

            # Run all profiles sequentially to respect LinkedIn rate limits
            # (a single browser/account must not send concurrent requests)
            total_new = 0
            for profile in config.searches:
                try:
                    count = await _run_profile(profile, browser, store, config)
                    total_new += count
                except Exception:
                    logger.exception("Error running profile '%s' — continuing.", profile.name)

    logger.info("Done. %d new job(s) notified across %d profile(s).", total_new, len(config.searches))


if __name__ == "__main__":
    asyncio.run(run())

