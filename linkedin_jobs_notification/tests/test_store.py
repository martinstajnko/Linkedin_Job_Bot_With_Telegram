"""Unit tests for store.py (SeenJobsStore)."""
import pytest
import pytest_asyncio

from store import SeenJobsStore


@pytest.mark.asyncio
async def test_is_new_returns_true_for_unknown_job(tmp_path):
    db = tmp_path / "test.db"
    async with SeenJobsStore(db) as store:
        assert await store.is_new("job_abc") is True


@pytest.mark.asyncio
async def test_mark_seen_then_is_new_returns_false(tmp_path):
    db = tmp_path / "test.db"
    async with SeenJobsStore(db) as store:
        await store.mark_seen("job_abc", "QA Engineer")
        assert await store.is_new("job_abc") is False


@pytest.mark.asyncio
async def test_mark_seen_idempotent(tmp_path):
    db = tmp_path / "test.db"
    async with SeenJobsStore(db) as store:
        await store.mark_seen("job_abc", "QA Engineer")
        # Second call must not raise (INSERT OR IGNORE)
        await store.mark_seen("job_abc", "Other Profile")
        assert await store.is_new("job_abc") is False


@pytest.mark.asyncio
async def test_multiple_jobs_independent(tmp_path):
    db = tmp_path / "test.db"
    async with SeenJobsStore(db) as store:
        await store.mark_seen("job_1", "Profile A")
        assert await store.is_new("job_1") is False
        assert await store.is_new("job_2") is True


@pytest.mark.asyncio
async def test_persistence_across_sessions(tmp_path):
    db = tmp_path / "test.db"
    async with SeenJobsStore(db) as store:
        await store.mark_seen("job_persist", "QA")

    # Re-open a new instance against the same file
    async with SeenJobsStore(db) as store2:
        assert await store2.is_new("job_persist") is False


def test_require_open_raises_on_closed_store():
    store = SeenJobsStore(":memory:")
    with pytest.raises(RuntimeError, match="not open"):
        store._require_open()
