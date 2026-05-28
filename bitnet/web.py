"""FastAPI web dashboard — view folder runs and Merkle roots."""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from bitnet.db import get_db, init_db
from bitnet.scanner import FolderSnapshot
from bitnet.watcher import upsert_watcher, stop_watcher, record_run
from bitnet.anchor import anchor_service

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

API_KEY = os.getenv("BITNET_API_KEY", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="BitNet",
    version="0.1.0",
    description="Self-proving folders — cryptographic provenance dashboard.",
    lifespan=lifespan,
)


async def _audit_log(action: str, detail: dict, client_ip: str = ""):
    """Persist audit record for every state-changing API call."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO audit_log (action, detail, client_ip, created_at)
               VALUES (?, ?, ?, ?)""",
            (action, json.dumps(detail, sort_keys=True), client_ip, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()
    finally:
        await db.close()


async def _require_api_key(request: Request):
    """Require BITNET_API_KEY if set; always allow localhost."""
    if not API_KEY:
        return True
    client = request.client
    if client and client.host in ("127.0.0.1", "::1", "localhost"):
        return True
    header = request.headers.get("x-api-key", "")
    query = request.query_params.get("api_key", "")
    if header == API_KEY or query == API_KEY:
        return True
    return False


@app.get("/", response_class=HTMLResponse)
async def home():
    db = await get_db()
    try:
        runs_cursor = await db.execute(
            "SELECT * FROM folder_runs WHERE status='complete' ORDER BY finished_at DESC LIMIT 12")
        runs = [dict(r) for r in await runs_cursor.fetchall()]

        watch_cursor = await db.execute(
            "SELECT * FROM folder_watchers ORDER BY updated_at DESC LIMIT 12")
        watchers = [dict(w) for w in await watch_cursor.fetchall()]
    finally:
        await db.close()

    run_rows = ""
    for run in runs:
        run_rows += f"""
        <tr>
          <td><div class="name">{run['root_path']}</div><div class="mono hash">{run.get('merkle_root') or 'no root'}</div></td>
          <td><span class="pill">{run['status']}</span></td>
          <td>{run['files_seen']}</td>
          <td>{run['files_changed']}</td>
          <td>{run['duplicate_files']}</td>
          <td class="mono">{run['anchor_tx'] or '-'}</td>
        </tr>
        """

    watcher_rows = ""
    for w in watchers:
        status = "running" if w.get("active") else "stopped"
        watcher_rows += f"""
        <tr>
          <td><div class="name">{w['root_path']}</div></td>
          <td><span class="pill {'ok' if w['active'] else 'warn'}">{status}</span></td>
          <td>{w.get('last_run_at') or 'never'}</td>
        </tr>
        """

    solana_status = "on" if anchor_service.available else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BitNet — Self-Proving Folders</title>
  <style>
    :root {{
      --bg:#0a0a0a; --panel:#141414; --border:#2a2a2a;
      --text:#e8e8e8; --muted:#888; --accent:#00d4aa;
      --accent-dim:#008f6b; --warn:#f0a040; --red:#e06040;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"SF Pro",system-ui,sans-serif; line-height:1.45; }}
    .shell {{ max-width:1100px; margin:0 auto; padding:24px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }}
    h1 {{ font-size:26px; margin:0; font-weight:800; }}
    h1 span {{ color:var(--accent); }}
    .tagline {{ color:var(--muted); font-size:14px; margin-top:4px; }}
    .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:18px; margin-bottom:16px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px; }}
    .stat {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; }}
    .stat .value {{ font-size:28px; font-weight:800; color:var(--accent); }}
    .stat .label {{ color:var(--muted); font-size:12px; text-transform:uppercase; margin-top:4px; }}
    .services {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:16px; }}
    .service {{ display:flex; justify-content:space-between; align-items:center; background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:12px; }}
    .dot {{ width:10px; height:10px; border-radius:50%; background:var(--red); }}
    .dot.on {{ background:var(--accent); box-shadow:0 0 0 3px rgba(0,212,170,.15), 0 0 14px rgba(0,212,170,.35); }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th {{ text-align:left; color:var(--muted); font-size:11px; text-transform:uppercase; padding:10px; border-bottom:1px solid var(--border); }}
    td {{ padding:10px; border-bottom:1px solid var(--border); }}
    .name {{ font-weight:700; }}
    .mono {{ font-family:"SF Mono",Menlo,monospace; font-size:11px; color:var(--muted); }}
    .hash {{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .pill {{ display:inline-flex; align-items:center; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:700; text-transform:uppercase; background:#1a2a22; color:var(--accent); }}
    .pill.ok {{ background:#1a2a22; color:var(--accent); }}
    .pill.warn {{ background:#2a2218; color:var(--warn); }}
    @media (max-width:800px) {{ .services,.grid {{ grid-template-columns:1fr; }} table {{ min-width:700px; }} .table-wrap {{ overflow-x:auto; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <div class="topbar">
      <div>
        <h1>BitNet <span>Self-Proving Folders</span></h1>
        <div class="tagline">Drop a folder. Hash every file. Build a Merkle tree. Watch forever.</div>
      </div>
    </div>

    <div class="services">
      <div class="service"><div><strong>Solana Devnet</strong><div class="mono">{anchor_service.wallet_address[:16]}... {await anchor_service.get_balance() if anchor_service.available else ""}</div></div><span class="dot {solana_status}"></span></div>
      <div class="service"><div><strong>SQLite WAL</strong><div class="mono">local persistence</div></div><span class="dot on"></span></div>
    </div>

    <div class="grid">
      <div class="stat"><div class="value">{len(runs)}</div><div class="label">Folder Runs</div></div>
      <div class="stat"><div class="value">{sum(r['files_seen'] for r in runs)}</div><div class="label">Files Hashed</div></div>
      <div class="stat"><div class="value">{len([w for w in watchers if w.get('active')])}</div><div class="label">Active Watchers</div></div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">Folder Runs</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Folder</th><th>Status</th><th>Files</th><th>Changed</th><th>Dupes</th><th>Anchor</th></tr></thead>
          <tbody>{run_rows or '<tr><td colspan="6" class="mono">No runs yet. Run: bitnet watch /path/to/folder</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">Continuous Watchers</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Folder</th><th>Status</th><th>Last Run</th></tr></thead>
          <tbody>{watcher_rows or '<tr><td colspan="3" class="mono">No active watchers.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  </main>
</body>
</html>"""


@app.post("/api/watch")
async def api_watch(request: Request, root_path: str, interval: int = 300, max_files: int = 250):
    if not await _require_api_key(request):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    client_ip = request.client.host if request.client else ""
    await _audit_log("watch", {"root_path": root_path, "interval": interval, "max_files": max_files}, client_ip)
    watcher = await upsert_watcher(root_path, interval, max_files)
    return {"status": "watching", "watcher_id": watcher["id"]}


@app.post("/api/scan")
async def api_scan(request: Request, root_path: str, max_files: int = 250):
    if not await _require_api_key(request):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    client_ip = request.client.host if request.client else ""
    await _audit_log("scan", {"root_path": root_path, "max_files": max_files}, client_ip)
    snapshot = FolderSnapshot(root_path, max_files).scan()
    db = await get_db()
    try:
        run_id = await record_run(db, root_path, snapshot)
    finally:
        await db.close()
    return {"status": "complete", "run_id": run_id, "merkle_root": snapshot.merkle_root, "files_seen": len(snapshot.files)}


@app.get("/api/runs")
async def api_runs(limit: int = 20):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM folder_runs ORDER BY finished_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "version": "0.1.0"}


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    uvicorn.run("bitnet.web:app", host=host, port=port, reload=False)
