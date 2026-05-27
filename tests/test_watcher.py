"""Tests for watcher change detection."""

import tempfile
from pathlib import Path

import pytest

from bitnet.db import init_db, get_db
from bitnet.scanner import FolderSnapshot
from bitnet.watcher import record_run, previous_hashes


@pytest.mark.asyncio
async def test_previous_hashes_empty():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        await init_db(db_path)
        db = await get_db(db_path)
        prev = await previous_hashes(db, "/nonexistent")
        assert prev == {}
        await db.close()


@pytest.mark.asyncio
async def test_record_and_detect_changes():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        await init_db(db_path)

        # First scan
        root = Path(td) / "project"
        root.mkdir()
        (root / "a.py").write_text("v1\n")
        (root / "b.py").write_text("v1\n")

        db = await get_db(db_path)
        snap1 = FolderSnapshot(root, 50).scan()
        run1 = await record_run(db, str(root), snap1)
        await db.close()

        # Modify one file
        (root / "a.py").write_text("v2\n")

        db = await get_db(db_path)
        snap2 = FolderSnapshot(root, 50).scan()
        run2 = await record_run(db, str(root), snap2)
        await db.close()

        db = await get_db(db_path)
        cursor = await db.execute(
            "SELECT change_status FROM folder_files WHERE run_id=? AND rel_path='a.py'", (run2,)
        )
        row = await cursor.fetchone()
        assert row["change_status"] == "modified"

        cursor = await db.execute(
            "SELECT change_status FROM folder_files WHERE run_id=? AND rel_path='b.py'", (run2,)
        )
        row = await cursor.fetchone()
        assert row["change_status"] == "unchanged"
        await db.close()
