"""Telegram notification sender for new LinkedIn job postings."""
import logging
from typing import Optional

import httpx
from linkedin_scraper.models.job import Job

from config import TelegramConfig

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Maximum message length enforced by Telegram (4096 chars for regular messages)
_MAX_MESSAGE_LENGTH = 4096


def _format_job_message(job: Job, profile_name: str) -> str:
    """Render a job posting as a Telegram Markdown v2-safe plain-text message."""
    lines = [
        f"*New job alert* — {_escape(profile_name)}",
        "",
    ]

    if job.job_title:
        lines.append(f"*{_escape(job.job_title)}*")
    if job.company:
        lines.append(f"Company: {_escape(job.company)}")
    if job.location:
        lines.append(f"Location: {_escape(job.location)}")
    if job.posted_date:
        lines.append(f"Posted: {_escape(job.posted_date)}")
    if job.applicant_count:
        lines.append(f"Applicants: {_escape(job.applicant_count)}")

    lines.extend(["", f"[View on LinkedIn]({job.linkedin_url})"])
    return "\n".join(lines)


def _escape(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters in plain text segments."""
    # Characters that must be escaped in MarkdownV2 outside links/code
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{ch}" if ch in special else ch for ch in text)


async def send_job_notification(
    config: TelegramConfig,
    job: Job,
    profile_name: str,
    client: Optional[httpx.AsyncClient] = None,
) -> None:
    """Send a Telegram notification for a new job posting.

    Args:
        config: Telegram bot token and chat_id.
        job: The job to notify about.
        profile_name: Display name of the search profile that found it.
        client: Optional pre-existing httpx.AsyncClient (useful for testing).

    Raises:
        httpx.HTTPStatusError: If Telegram returns a non-2xx response.
        httpx.RequestError: On network errors.
    """
    message = _format_job_message(job, profile_name)
    if len(message) > _MAX_MESSAGE_LENGTH:
        message = message[: _MAX_MESSAGE_LENGTH - 3] + "\\.\\.\\."

    url = _TELEGRAM_API.format(token=config.bot_token)
    payload = {
        "chat_id": config.chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }

    async def _post(c: httpx.AsyncClient) -> None:
        response = await c.post(url, json=payload)
        response.raise_for_status()
        logger.info(
            "Telegram notification sent for job '%s' (profile: %s).",
            job.job_title or job.linkedin_url,
            profile_name,
        )

    if client is not None:
        await _post(client)
    else:
        async with httpx.AsyncClient(timeout=10) as c:
            await _post(c)
