"""Tests for portable proof bundles and snapshot replay."""

import json
import tempfile
from pathlib import Path

import pytest

from bitnet.scanner import FolderSnapshot
from bitnet.proof import export_proof, verify_proof_bundle, replay_snapshot
from bitnet.receipt import make_receipt


class TestExportProof:
    def test_exports_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            snap = FolderSnapshot(root, 50).scan()
            out = Path(td) / "proof.json"
            export_proof(snap, out)
            assert out.exists()
            data = json.loads(out.read_text())
            assert data["schema"] == "bitnet-proof-v1"
            assert "receipt" in data
            assert "receipt_hash" in data
            assert len(data["files"]) == 1
            assert "merkle_proof" in data["files"][0]

    def test_bundle_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            (root / "b.py").write_text("y = 2\n")
            snap = FolderSnapshot(root, 50).scan()
            out = Path(td) / "proof.json"
            export_proof(snap, out)
            report = verify_proof_bundle(out)
            assert report["valid"] is True
            assert report["receipt_valid"] is True
            assert report["merkle_root_match"] is True
            assert report["files_verified"] == report["files_total"]

    def test_tampered_bundle_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            snap = FolderSnapshot(root, 50).scan()
            out = Path(td) / "proof.json"
            export_proof(snap, out)
            # Tamper receipt hash
            data = json.loads(out.read_text())
            data["receipt_hash"] = "0" * 64
            out.write_text(json.dumps(data))
            report = verify_proof_bundle(out)
            assert report["valid"] is False
            assert report["receipt_valid"] is False

    def test_missing_file_in_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            (root / "b.py").write_text("y = 2\n")
            snap = FolderSnapshot(root, 50).scan()
            out = Path(td) / "proof.json"
            export_proof(snap, out)
            # Corrupt a file proof
            data = json.loads(out.read_text())
            data["files"][0]["merkle_proof"][0]["hash"] = "sha256:" + "0" * 64
            out.write_text(json.dumps(data))
            report = verify_proof_bundle(out)
            assert report["valid"] is False
            assert report["files_verified"] == 1  # one file still verifies


class TestReplaySnapshot:
    def test_unchanged_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            snap = FolderSnapshot(root, 50).scan()
            receipt = make_receipt(snap)
            report = replay_snapshot(root, receipt)
            assert report["status"] == "unchanged"
            assert report["match"] is True
            assert report["current_merkle_root"] == receipt["merkle_root"]

    def test_tampered_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            snap = FolderSnapshot(root, 50).scan()
            receipt = make_receipt(snap)
            # Tamper
            (root / "a.py").write_text("x = 2\n")
            report = replay_snapshot(root, receipt)
            assert report["status"] == "tampered"
            assert report["match"] is False

    def test_new_file_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n")
            snap = FolderSnapshot(root, 50).scan()
            receipt = make_receipt(snap)
            # Add file
            (root / "b.py").write_text("y = 2\n")
            report = replay_snapshot(root, receipt)
            assert report["status"] == "tampered"
            assert report["match"] is False
            assert report["files_seen"] == 2
            assert report["previous_files_seen"] == 1
