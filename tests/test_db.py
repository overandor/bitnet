"""Tests for database persistence."""

import tempfile
from pathlib import Path

import pytest
import aiosqlite

from bitnet.db import init_db, get_db


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        await init_db(db_path)
        db = await get_db(db_path)
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='folder_runs'"
        )
        row = await cursor.fetchone()
        assert row is not None
        await db.close()


@pytest.mark.asyncio
async def test_folder_run_insert():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        await init_db(db_path)
        db = await get_db(db_path)
        cursor = await db.execute(
            "INSERT INTO folder_runs (root_path, status, started_at) VALUES (?, 'complete', ?)",
            ("/tmp/test", "2024-01-01T00:00:00"),
        )
        await db.commit()
        assert cursor.lastrowid == 1
        await db.close()
