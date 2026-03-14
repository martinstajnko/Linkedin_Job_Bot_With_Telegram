"""Configuration loader for linkedin_jobs_notification.

Loads config.yaml and resolves ${ENV_VAR} placeholders from the environment
(or a .env file via python-dotenv).
"""
import logging
import os
import re
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Load .env once at import time (safe to call multiple times — no-op if already loaded)
load_dotenv()

_ENV_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} placeholders with values from the environment."""
    def _replace(match: re.Match) -> str:
        var = match.group(1)
        resolved = os.environ.get(var)
        if resolved is None:
            raise ValueError(f"Environment variable '{var}' referenced in config is not set.")
        return resolved

    return _ENV_PLACEHOLDER.sub(_replace, value)


def _resolve_all(obj: object) -> object:
    """Recursively resolve env-var placeholders in all string values."""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _resolve_all(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_all(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SearchProfile(BaseModel):
    """A single LinkedIn job search profile."""

    name: str
    keywords: str
    location: str = "Worldwide"
    remote: bool = False
    posted_within_hours: Optional[int] = None
    limit: int = Field(default=25, ge=1, le=100)

    @field_validator("posted_within_hours")
    @classmethod
    def validate_hours(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("posted_within_hours must be a positive integer.")
        return v


class LinkedInConfig(BaseModel):
    session_file: str = "linkedin_session.json"


class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str


class AppConfig(BaseModel):
    linkedin: LinkedInConfig
    telegram: TelegramConfig
    searches: list[SearchProfile]

    @field_validator("searches")
    @classmethod
    def at_least_one_search(cls, v: list[SearchProfile]) -> list[SearchProfile]:
        if not v:
            raise ValueError("At least one search profile must be defined.")
        return v


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str | Path = "config.yaml") -> AppConfig:
    """Load and validate the application config from a YAML file.

    Args:
        path: Path to config.yaml (absolute or relative to cwd).

    Returns:
        Validated AppConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If a required env var placeholder is unset or validation fails.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path.resolve()}")

    with config_path.open() as f:
        raw = yaml.safe_load(f)

    resolved = _resolve_all(raw)
    config = AppConfig.model_validate(resolved)
    logger.info(f"Loaded config from '{config_path}': {len(config.searches)} search profile(s).")
    return config
