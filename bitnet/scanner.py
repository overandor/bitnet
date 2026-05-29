"""Filesystem scanner — hash files, detect changes, build path-bound Merkle trees."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache",
    "node_modules", ".venv", "venv", "target", "dist", "build",
    ".idea", ".vscode", ".tox", ".egg-info",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """Return sha256:hexdigest for a single file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def canonical_leaf_hash(rel_path: str, size_bytes: int, raw_hash: str) -> str:
    """Hash the file identity, not only the file bytes.

    Earlier BitNet roots were built only from content hashes. That detected byte
    tampering, but it did not bind the root to the folder layout. This leaf hash
    commits to the relative path, file size, and content hash so renames/path
    swaps change the Merkle root.
    """
    payload = {
        "rel_path": str(rel_path).replace("\\", "/"),
        "size_bytes": int(size_bytes),
        "raw_hash": raw_hash,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def merkle_root(hashes: list[str]) -> str:
    """Compute Merkle root from a list of leaf hashes (deterministic, sorted)."""
    if not hashes:
        return "sha256:" + hashlib.sha256(b"").hexdigest()
    layer = [bytes.fromhex(h.replace("sha256:", "")) for h in sorted(hashes)]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(hashlib.sha256(left + right).digest())
        layer = nxt
    return f"sha256:{layer[0].hex()}"


def iter_files(root: Path, max_files: int) -> Iterator[Path]:
    """Yield file paths under root, skipping common build/cache dirs."""
    seen = 0
    for path in sorted(root.rglob("*")):
        if seen >= max_files:
            break
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        try:
            if path.is_symlink():
                continue
            path.stat()
        except OSError:
            continue
        seen += 1
        yield path


class FolderSnapshot:
    """A point-in-time snapshot of a folder."""

    def __init__(self, root: Path, max_files: int = 250):
        self.root = Path(root).expanduser().resolve()
        self.max_files = max_files
        self.files: list[dict] = []
        self.merkle_root: str = ""
        self.duplicate_files = 0
        self.duplicate_groups = 0
        self.total_bytes = 0

    def scan(self) -> "FolderSnapshot":
        if not self.root.exists() or not self.root.is_dir():
            raise ValueError(f"Not a directory: {self.root}")

        hash_to_first: dict[str, str] = {}
        hash_counts: Counter[str] = Counter()
        ext_counts: Counter[str] = Counter()
        size_by_ext: Counter[str] = Counter()

        for path in iter_files(self.root, self.max_files):
            stat = path.stat()
            rel = str(path.relative_to(self.root)).replace("\\", "/")
            raw_hash = sha256_file(path)
            leaf_hash = canonical_leaf_hash(rel, stat.st_size, raw_hash)
            duplicate_of = hash_to_first.get(raw_hash)
            hash_to_first.setdefault(raw_hash, rel)
            hash_counts[raw_hash] += 1

            ext = path.suffix.lower() or "[none]"
            ext_counts[ext] += 1
            size_by_ext[ext] += stat.st_size
            self.total_bytes += stat.st_size

            self.files.append({
                "path": str(path),
                "rel_path": rel,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "raw_hash": raw_hash,
                "leaf_hash": leaf_hash,
                "duplicate_of": duplicate_of,
            })

        self.duplicate_groups = sum(1 for c in hash_counts.values() if c > 1)
        self.duplicate_files = sum(c - 1 for c in hash_counts.values() if c > 1)
        self.merkle_root = merkle_root([f["leaf_hash"] for f in self.files])
        return self

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "merkle_root": self.merkle_root,
            "files_seen": len(self.files),
            "duplicate_groups": self.duplicate_groups,
            "duplicate_files": self.duplicate_files,
            "total_bytes": self.total_bytes,
            "scanned_at": now_iso(),
            "files": self.files,
        }
