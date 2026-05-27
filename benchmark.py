#!/usr/bin/env python3
"""Benchmark BitNet scan performance."""

import tempfile
import time
from pathlib import Path

from bitnet.scanner import FolderSnapshot


def create_test_folder(n_files: int, root: Path) -> None:
    """Create n synthetic files in root."""
    for i in range(n_files):
        subdir = root / f"dir_{i % 10}"
        subdir.mkdir(exist_ok=True)
        (subdir / f"file_{i}.py").write_text(f"# file {i}\n" + "x = 1\n" * 20)


def benchmark(n_files: int) -> dict:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        create_test_folder(n_files, root)

        start = time.perf_counter()
        snap = FolderSnapshot(root, max_files=n_files + 100).scan()
        elapsed = time.perf_counter() - start

        return {
            "files": len(snap.files),
            "elapsed_ms": round(elapsed * 1000, 2),
            "ms_per_file": round(elapsed * 1000 / max(len(snap.files), 1), 3),
            "merkle_root": snap.merkle_root[:20] + "...",
        }


if __name__ == "__main__":
    for n in [100, 500, 1000, 5000]:
        result = benchmark(n)
        print(f"{result['files']:>5} files | {result['elapsed_ms']:>7.2f} ms | {result['ms_per_file']:>6.3f} ms/file | root {result['merkle_root']}")
