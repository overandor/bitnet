"""Tests for canonical receipt hashing and verification."""

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from bitnet.scanner import FolderSnapshot
from bitnet.receipt import (
    canonical_json,
    canonical_timestamp,
    make_receipt,
    receipt_hash,
    verify_receipt,
    RECEIPT_SCHEMA_VERSION,
)


def test_canonical_json_deterministic():
    d = {"b": 2, "a": 1}
    s1 = canonical_json(d)
    s2 = canonical_json(d)
    assert s1 == s2
    assert s1 == '{"a":1,"b":2}'


def test_canonical_timestamp_format():
    ts = canonical_timestamp()
    assert ts.endswith("Z")
    assert "+" not in ts
    assert len(ts) == 20  # YYYY-MM-DDTHH:MM:SSZ


def test_make_receipt_has_schema():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "x.txt").write_text("hello")
        snap = FolderSnapshot(root, 50).scan()
        receipt = make_receipt(snap)
        assert receipt["schema"] == RECEIPT_SCHEMA_VERSION
        assert receipt["root"] == str(root.resolve())
        assert receipt["merkle_root"].startswith("sha256:")
        assert receipt["files_seen"] == 1
        assert receipt["scanned_at"].endswith("Z")


def test_receipt_hash_determinism():
    receipt = {
        "schema": RECEIPT_SCHEMA_VERSION,
        "root": "/tmp/test",
        "merkle_root": "sha256:" + "ab" * 32,
        "files_seen": 42,
        "duplicate_groups": 0,
        "duplicate_files": 0,
        "total_bytes": 1024,
        "scanned_at": "2024-06-15T14:32:11Z",
    }
    h1 = receipt_hash(receipt)
    h2 = receipt_hash(receipt)
    assert h1 == h2
    assert len(h1) == 64


def test_receipt_hash_tamper_detection():
    receipt = {
        "schema": RECEIPT_SCHEMA_VERSION,
        "root": "/tmp/test",
        "merkle_root": "sha256:" + "ab" * 32,
        "files_seen": 42,
        "duplicate_groups": 0,
        "duplicate_files": 0,
        "total_bytes": 1024,
        "scanned_at": "2024-06-15T14:32:11Z",
    }
    original = receipt_hash(receipt)
    receipt["files_seen"] = 99
    tampered = receipt_hash(receipt)
    assert original != tampered


def test_verify_receipt_valid():
    receipt = {
        "schema": RECEIPT_SCHEMA_VERSION,
        "root": "/tmp/test",
        "merkle_root": "sha256:" + "ab" * 32,
        "files_seen": 42,
        "duplicate_groups": 0,
        "duplicate_files": 0,
        "total_bytes": 1024,
        "scanned_at": "2024-06-15T14:32:11Z",
    }
    report = verify_receipt(receipt)
    assert report["valid"] is True
    assert report["errors"] == []
    assert "receipt_hash" in report


def test_verify_receipt_missing_fields():
    receipt = {"schema": RECEIPT_SCHEMA_VERSION, "root": "/tmp/test"}
    report = verify_receipt(receipt)
    assert report["valid"] is False
    assert any("Missing fields" in e for e in report["errors"])


def test_verify_receipt_invalid_merkle_root():
    receipt = {
        "schema": RECEIPT_SCHEMA_VERSION,
        "root": "/tmp/test",
        "merkle_root": "bad",
        "files_seen": 42,
        "scanned_at": "2024-06-15T14:32:11Z",
    }
    report = verify_receipt(receipt)
    assert report["valid"] is False
    assert any("merkle_root" in e for e in report["errors"])


def test_verify_receipt_bad_schema():
    receipt = {
        "schema": "unknown-v99",
        "root": "/tmp/test",
        "merkle_root": "sha256:" + "ab" * 32,
        "files_seen": 42,
        "scanned_at": "2024-06-15T14:32:11Z",
    }
    report = verify_receipt(receipt)
    assert any("Unknown schema" in e for e in report["errors"])


def test_snapshot_to_dict_structure():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "x.txt").write_text("hello")
        snap = FolderSnapshot(root, 50).scan()
        d = snap.to_dict()
        assert "root" in d
        assert "merkle_root" in d
        assert "files_seen" in d
        assert "files" in d
        assert d["files_seen"] == 1
