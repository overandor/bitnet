"""SQLite persistence — five core tables only."""

import aiosqlite
from pathlib import Path
from typing import Optional

SQLITE_PATH = Path.home() / ".bitnet" / "bitnet.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS folder_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    mode TEXT DEFAULT 'one_shot',
    files_seen INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    files_new INTEGER DEFAULT 0,
    files_modified INTEGER DEFAULT 0,
    files_unchanged INTEGER DEFAULT 0,
    duplicate_groups INTEGER DEFAULT 0,
    duplicate_files INTEGER DEFAULT 0,
    duplicate_bytes INTEGER DEFAULT 0,
    total_bytes INTEGER DEFAULT 0,
    merkle_root TEXT,
    appraised_files INTEGER DEFAULT 0,
    total_appraised_value_usd REAL DEFAULT 0,
    total_lendable_value_usd REAL DEFAULT 0,
    kpi_json TEXT,
    anchor_tx TEXT,
    explorer_url TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS folder_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES folder_runs(id),
    root_path TEXT NOT NULL,
    path TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    size_bytes INTEGER DEFAULT 0,
    modified_at TEXT,
    raw_hash TEXT NOT NULL,
    duplicate_of TEXT,
    change_status TEXT DEFAULT 'new',
    appraised_value_usd REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS folder_watchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT UNIQUE NOT NULL,
    interval_seconds INTEGER DEFAULT 300,
    max_files INTEGER DEFAULT 250,
    active INTEGER DEFAULT 1,
    anchor_enabled INTEGER DEFAULT 0,
    appraise_enabled INTEGER DEFAULT 0,
    last_run_id INTEGER,
    last_run_at TEXT,
    last_summary_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chain_anchors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES folder_runs(id),
    network TEXT DEFAULT 'solana-devnet',
    network_code TEXT DEFAULT 'SDV',
    tx_signature TEXT NOT NULL,
    tx_short TEXT,
    explorer_url TEXT,
    anchor_data_hash TEXT,
    status TEXT DEFAULT 'confirmed',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appraisals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES folder_files(id),
    appraised_value_usd REAL DEFAULT 0,
    appraisal_confidence REAL DEFAULT 0,
    category TEXT,
    complexity_score REAL DEFAULT 0,
    estimated_hours REAL DEFAULT 0,
    hourly_rate REAL DEFAULT 0,
    reasoning TEXT,
    model_used TEXT,
    evidence_json TEXT,
    receipt_hash TEXT,
    created_at TEXT NOT NULL
);
"""


async def get_db(path: Optional[Path] = None) -> aiosqlite.Connection:
    db_path = path or SQLITE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db(path: Optional[Path] = None):
    db = await get_db(path)
    await db.executescript(SCHEMA)
    await db.commit()
    await db.close()
