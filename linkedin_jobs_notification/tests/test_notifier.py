"""Unit tests for notifier.py — no real Telegram calls."""
import pytest
import httpx
import respx

from linkedin_scraper.models.job import Job
from config import TelegramConfig
from notifier import _format_job_message, _escape, send_job_notification


TELEGRAM_CONFIG = TelegramConfig(bot_token="bot123:TOKEN", chat_id="-100999")

SAMPLE_JOB = Job(
    linkedin_url="https://www.linkedin.com/jobs/view/123456",
    job_title="QA Engineer",
    company="Acme Corp",
    location="Remote, Worldwide",
    posted_date="2 days ago",
    applicant_count="42 applicants",
)


# ---------------------------------------------------------------------------
# _escape
# ---------------------------------------------------------------------------

def test_escape_plain_text():
    assert _escape("Hello World") == "Hello World"


def test_escape_special_chars():
    result = _escape("C++ & .NET (v2.0)")
    # Dots and parens must be escaped in MarkdownV2
    assert "\\." in result
    assert "\\(" in result
    assert "\\)" in result


# ---------------------------------------------------------------------------
# _format_job_message
# ---------------------------------------------------------------------------

def test_format_job_message_contains_title():
    msg = _format_job_message(SAMPLE_JOB, "My Profile")
    assert "QA Engineer" in msg


def test_format_job_message_contains_company():
    msg = _format_job_message(SAMPLE_JOB, "My Profile")
    assert "Acme Corp" in msg


def test_format_job_message_contains_linkedin_url():
    msg = _format_job_message(SAMPLE_JOB, "My Profile")
    assert SAMPLE_JOB.linkedin_url in msg


def test_format_job_message_contains_profile_name():
    msg = _format_job_message(SAMPLE_JOB, "QA Remote")
    assert "QA Remote" in msg


def test_format_job_message_minimal_job():
    """Job with only a URL must not raise."""
    job = Job(linkedin_url="https://www.linkedin.com/jobs/view/999")
    msg = _format_job_message(job, "Profile")
    assert "linkedin.com/jobs/view/999" in msg


# ---------------------------------------------------------------------------
# send_job_notification — mocked HTTP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_send_job_notification_calls_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_CONFIG.bot_token}/sendMessage"
    route = respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))

    async with httpx.AsyncClient() as client:
        await send_job_notification(TELEGRAM_CONFIG, SAMPLE_JOB, "QA Profile", client=client)

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_send_job_notification_raises_on_http_error():
    url = f"https://api.telegram.org/bot{TELEGRAM_CONFIG.bot_token}/sendMessage"
    respx.post(url).mock(return_value=httpx.Response(400, json={"ok": False}))

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await send_job_notification(TELEGRAM_CONFIG, SAMPLE_JOB, "QA Profile", client=client)
