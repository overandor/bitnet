"""Continuous folder watchers — re-scan on interval and detect changes."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bitnet.db import get_db
from bitnet.scanner import FolderSnapshot

SCAN_STATE: dict[int, asyncio.Task] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def previous_hashes(db, root_path: str) -> dict[str, str]:
    """Load previous hashes for change detection."""
    row = await (
        await db.execute(
            "SELECT id FROM folder_runs WHERE root_path=? AND status='complete' ORDER BY finished_at DESC LIMIT 1",
            (root_path,),
        )
    ).fetchone()
    if not row:
        return {}
    cursor = await db.execute("SELECT rel_path, raw_hash FROM folder_files WHERE run_id=?", (row["id"],))
    return {r["rel_path"]: r["raw_hash"] for r in await cursor.fetchall()}


async def record_run(
    db,
    root_path: str,
    snapshot: FolderSnapshot,
    mode: str = "one_shot",
) -> int:
    """Record a folder run to the database. Returns run_id."""
    cursor = await db.execute(
        "INSERT INTO folder_runs (root_path, status, mode, started_at) VALUES (?, 'running', ?, ?)",
        (str(root_path), mode, now_iso()),
    )
    run_id = cursor.lastrowid
    await db.commit()

    prev = await previous_hashes(db, str(root_path))
    new_count = modified_count = unchanged_count = 0

    for f in snapshot.files:
        prev_hash = prev.get(f["rel_path"])
        if prev_hash is None:
            change_status = "new"
            new_count += 1
        elif prev_hash != f["raw_hash"]:
            change_status = "modified"
            modified_count += 1
        else:
            change_status = "unchanged"
            unchanged_count += 1

        await db.execute(
            """INSERT INTO folder_files (
                run_id, root_path, path, rel_path, size_bytes, modified_at,
                raw_hash, duplicate_of, change_status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, str(root_path), f["path"], f["rel_path"], f["size_bytes"],
                f["modified_at"], f["raw_hash"], f["duplicate_of"], change_status, now_iso(),
            ),
        )

    await db.execute(
        """UPDATE folder_runs SET
            status='complete', files_seen=?, files_changed=?, files_new=?,
            files_modified=?, files_unchanged=?, duplicate_groups=?, duplicate_files=?,
            total_bytes=?, merkle_root=?, finished_at=?
        WHERE id=?""",
        (
            len(snapshot.files), new_count + modified_count, new_count,
            modified_count, unchanged_count, snapshot.duplicate_groups,
            snapshot.duplicate_files, snapshot.total_bytes,
            snapshot.merkle_root, now_iso(), run_id,
        ),
    )
    await db.commit()
    return run_id


async def upsert_watcher(
    root_path: str,
    interval_seconds: int = 300,
    max_files: int = 250,
    anchor: bool = False,
    appraise: bool = False,
) -> dict:
    """Create or update a folder watcher."""
    root = str(Path(root_path).expanduser().resolve())
    now = now_iso()
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO folder_watchers (
                root_path, interval_seconds, max_files, active, anchor_enabled,
                appraise_enabled, created_at, updated_at
            ) VALUES (?,?,?,1,?,?,?,?)
            ON CONFLICT(root_path) DO UPDATE SET
                interval_seconds=excluded.interval_seconds,
                max_files=excluded.max_files,
                active=1,
                anchor_enabled=excluded.anchor_enabled,
                appraise_enabled=excluded.appraise_enabled,
                updated_at=excluded.updated_at""",
            (root, interval_seconds, max_files, int(anchor), int(appraise), now, now),
        )
        await db.commit()
        row = await (await db.execute("SELECT * FROM folder_watchers WHERE root_path=?", (root,))).fetchone()
        watcher = dict(row)
    finally:
        await db.close()

    wid = watcher["id"]
    if wid not in SCAN_STATE or SCAN_STATE[wid].done():
        SCAN_STATE[wid] = asyncio.create_task(_watch_loop(watcher))
    return watcher


async def _watch_loop(watcher: dict):
    """Background loop for a watcher."""
    while True:
        db = await get_db()
        try:
            row = await (await db.execute("SELECT * FROM folder_watchers WHERE id=?", (watcher["id"],))).fetchone()
            if not row or not row["active"]:
                return
            watcher = dict(row)
        finally:
            await db.close()

        try:
            snapshot = FolderSnapshot(watcher["root_path"], watcher["max_files"]).scan()
            db = await get_db()
            try:
                run_id = await record_run(db, watcher["root_path"], snapshot, mode="continuous")
                await db.execute(
                    """UPDATE folder_watchers SET last_run_id=?, last_run_at=?, updated_at=? WHERE id=?""",
                    (run_id, now_iso(), now_iso(), watcher["id"]),
                )
                await db.commit()
            finally:
                await db.close()
        except Exception as exc:
            db = await get_db()
            try:
                await db.execute(
                    "UPDATE folder_watchers SET last_summary_json=?, updated_at=? WHERE id=?",
                    (json.dumps({"error": str(exc)}), now_iso(), watcher["id"]),
                )
                await db.commit()
            finally:
                await db.close()

        await asyncio.sleep(max(15, int(watcher["interval_seconds"] or 300)))


async def stop_watcher(watcher_id: int) -> dict:
    """Stop a running watcher."""
    db = await get_db()
    try:
        await db.execute("UPDATE folder_watchers SET active=0, updated_at=? WHERE id=?", (now_iso(), watcher_id))
        await db.commit()
        row = await (await db.execute("SELECT * FROM folder_watchers WHERE id=?", (watcher_id,))).fetchone()
    finally:
        await db.close()
    task = SCAN_STATE.pop(watcher_id, None)
    if task:
        task.cancel()
    return dict(row) if row else {"id": watcher_id, "active": 0}
