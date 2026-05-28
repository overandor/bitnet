"""Tests for portable snapshot export and verification."""

import json
import tempfile
from pathlib import Path

from bitnet.snapshot import export_snapshot, verify_snapshot


def test_export_snapshot_creates_all_files():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')\n")
        (root / "src" / "utils.py").write_text("def add(a, b): return a + b\n")

        out = Path(td) / "snapshot"
        export_snapshot(root, out, max_files=50)

        assert (out / "receipt.json").exists()
        assert (out / "manifest.json").exists()
        assert (out / "files.json").exists()
        assert (out / "merkle.json").exists()
        assert (out / "proof.json").exists()

        receipt = json.loads((out / "receipt.json").read_text())
        assert receipt["schema"] == "bitnet-receipt-v1"
        assert receipt["files_seen"] == 2

        manifest = json.loads((out / "manifest.json").read_text())
        assert manifest["schema"] == "bitnet-snapshot-v1"
        assert manifest["files_count"] == 2


def test_verify_snapshot_valid():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        (root / "a.py").write_text("x = 1\n")
        (root / "b.py").write_text("y = 2\n")

        out = Path(td) / "snapshot"
        export_snapshot(root, out, max_files=50)
        report = verify_snapshot(out)

        assert report["valid"] is True
        assert report["checks"]["receipt_format"] is True
        assert report["checks"]["manifest_schema"] is True
        assert report["checks"]["merkle_root_recomputed"] is True
        assert report["checks"]["merkle_root_matches_receipt"] is True
        assert report["checks"]["files_verified"] == 2
        assert report["checks"]["files_failed"] == 0


def test_verify_snapshot_tampered_receipt():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        (root / "a.py").write_text("x = 1\n")

        out = Path(td) / "snapshot"
        export_snapshot(root, out, max_files=50)

        receipt = json.loads((out / "receipt.json").read_text())
        receipt["files_seen"] = 999
        (out / "receipt.json").write_text(json.dumps(receipt))

        report = verify_snapshot(out)
        assert report["valid"] is False
        # manifest hash mismatch + merkle mismatch
        assert any("receipt_hash" in e for e in report["errors"])


def test_verify_snapshot_missing_files():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "snapshot"
        out.mkdir()
        (out / "receipt.json").write_text("{}")
        (out / "manifest.json").write_text("{}")

        report = verify_snapshot(out)
        assert report["valid"] is False
        assert any("Missing" in e for e in report["errors"])


def test_verify_snapshot_empty_folder():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "empty"
        root.mkdir()
        out = Path(td) / "snapshot"
        export_snapshot(root, out, max_files=50)
        report = verify_snapshot(out)
        # Empty folder has no files, so no proofs to verify
        assert report["valid"] is True
