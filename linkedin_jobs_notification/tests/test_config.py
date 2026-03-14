"""Unit tests for config.py — no I/O with LinkedIn or Telegram."""
import os
import textwrap

import pytest
import yaml

from config import AppConfig, SearchProfile, TelegramConfig, LinkedInConfig, load_config


# ---------------------------------------------------------------------------
# SearchProfile model
# ---------------------------------------------------------------------------

def test_search_profile_defaults():
    p = SearchProfile(name="QA", keywords="QA Engineer")
    assert p.location == "Worldwide"
    assert p.remote is False
    assert p.limit == 25
    assert p.posted_within_hours is None


def test_search_profile_full():
    p = SearchProfile(
        name="Remote AI QA",
        keywords="AI QA Engineer",
        location="Europe",
        remote=True,
        posted_within_hours=24,
        limit=50,
    )
    assert p.remote is True
    assert p.posted_within_hours == 24


def test_search_profile_limit_bounds():
    with pytest.raises(Exception):
        SearchProfile(name="X", keywords="X", limit=0)
    with pytest.raises(Exception):
        SearchProfile(name="X", keywords="X", limit=101)


def test_search_profile_posted_within_hours_zero_raises():
    with pytest.raises(Exception):
        SearchProfile(name="X", keywords="X", posted_within_hours=0)


def test_search_profile_posted_within_hours_negative_raises():
    with pytest.raises(Exception):
        SearchProfile(name="X", keywords="X", posted_within_hours=-5)


# ---------------------------------------------------------------------------
# load_config — using tmp_path + monkeypatch instead of real files/env
# ---------------------------------------------------------------------------

def _write_config(tmp_path, content: str) -> str:
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(content))
    return str(p)


VALID_CONFIG = """\
    linkedin:
      session_file: my_session.json
    telegram:
      bot_token: "${TEST_BOT_TOKEN}"
      chat_id: "${TEST_CHAT_ID}"
    searches:
      - name: QA Engineer Remote
        keywords: QA Engineer
        location: Worldwide
        remote: true
        posted_within_hours: 24
        limit: 25
      - name: AI QA Engineer
        keywords: AI QA Engineer
        location: Europe
        remote: false
        limit: 10
"""


def test_load_config_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_BOT_TOKEN", "bot123")
    monkeypatch.setenv("TEST_CHAT_ID", "456")
    path = _write_config(tmp_path, VALID_CONFIG)
    config = load_config(path)

    assert isinstance(config, AppConfig)
    assert config.linkedin.session_file == "my_session.json"
    assert config.telegram.bot_token == "bot123"
    assert config.telegram.chat_id == "456"
    assert len(config.searches) == 2

    first = config.searches[0]
    assert first.name == "QA Engineer Remote"
    assert first.remote is True
    assert first.posted_within_hours == 24
    assert first.limit == 25

    second = config.searches[1]
    assert second.remote is False
    assert second.location == "Europe"


def test_load_config_missing_env_var_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TEST_CHAT_ID", raising=False)
    path = _write_config(tmp_path, VALID_CONFIG)
    with pytest.raises(ValueError, match="TEST_BOT_TOKEN"):
        load_config(path)


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_load_config_empty_searches_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_BOT_TOKEN", "x")
    monkeypatch.setenv("TEST_CHAT_ID", "y")
    path = _write_config(
        tmp_path,
        """\
        linkedin:
          session_file: s.json
        telegram:
          bot_token: "${TEST_BOT_TOKEN}"
          chat_id: "${TEST_CHAT_ID}"
        searches: []
        """,
    )
    with pytest.raises(Exception, match="[Aa]t least one"):
        load_config(path)
