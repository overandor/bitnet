"""Tests for CLI diff command."""

import json
import tempfile
from pathlib import Path

import pytest

from bitnet.scanner import FolderSnapshot
from bitnet.receipt import make_receipt


def test_diff_match():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n")
        snap = FolderSnapshot(root, 50).scan()
        r1 = make_receipt(snap)
        r2 = make_receipt(snap)
        # Override timestamps to be identical for clean test
        r2["scanned_at"] = r1["scanned_at"]

        p1 = Path(td) / "r1.json"
        p2 = Path(td) / "r2.json"
        p1.write_text(json.dumps(r1))
        p2.write_text(json.dumps(r2))

        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "bitnet.cli", "diff", str(p1), str(p2)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "match" in result.stdout or "UNCHANGED" in result.stdout


def test_diff_different():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n")
        snap1 = FolderSnapshot(root, 50).scan()
        r1 = make_receipt(snap1)

        (root / "b.py").write_text("y = 2\n")
        snap2 = FolderSnapshot(root, 50).scan()
        r2 = make_receipt(snap2)

        p1 = Path(td) / "r1.json"
        p2 = Path(td) / "r2.json"
        p1.write_text(json.dumps(r1))
        p2.write_text(json.dumps(r2))

        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "bitnet.cli", "diff", str(p1), str(p2)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "diff" in result.stdout or "TAMPERED" in result.stdout or "differ" in result.stdout
