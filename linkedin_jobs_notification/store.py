"""Persistent store for seen job IDs, backed by SQLite via aiosqlite."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    job_id       TEXT PRIMARY KEY,
    found_at     TEXT NOT NULL,
    profile_name TEXT NOT NULL
)
"""


class SeenJobsStore:
    """Async context manager wrapping an aiosqlite connection.

    Usage::

        async with SeenJobsStore("seen_jobs.db") as store:
            if await store.is_new(job_id):
                await store.mark_seen(job_id, profile_name="QA Engineer")
    """

    def __init__(self, db_path: str | Path = "seen_jobs.db") -> None:
        self._db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "SeenJobsStore":
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.execute(_CREATE_TABLE)
        await self._conn.commit()
        logger.debug("SeenJobsStore opened at '%s'.", self._db_path)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.debug("SeenJobsStore closed.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def is_new(self, job_id: str) -> bool:
        """Return True if *job_id* has not been seen before."""
        self._require_open()
        async with self._conn.execute(  # type: ignore[union-attr]
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            return await cursor.fetchone() is None

    async def mark_seen(self, job_id: str, profile_name: str) -> None:
        """Record *job_id* as seen.  No-op if already recorded (INSERT OR IGNORE)."""
        self._require_open()
        found_at = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(  # type: ignore[union-attr]
            "INSERT OR IGNORE INTO seen_jobs (job_id, found_at, profile_name) VALUES (?, ?, ?)",
            (job_id, found_at, profile_name),
        )
        await self._conn.commit()
        logger.debug("Marked job '%s' as seen (profile: %s).", job_id, profile_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_open(self) -> None:
        if self._conn is None:
            raise RuntimeError("SeenJobsStore is not open. Use it as an async context manager.")
