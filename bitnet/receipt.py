"""Canonical receipt format — deterministic, versioned, independently verifiable."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA_VERSION = "bitnet-receipt-v1"


def canonical_json(obj: dict) -> str:
    """Deterministic JSON: sorted keys, no extra whitespace, separators minimal."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_timestamp() -> str:
    """ISO 8601 UTC with explicit Z, no microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_receipt(snapshot: Any) -> dict:
    """Build a canonical receipt from a FolderSnapshot."""
    return {
        "schema": RECEIPT_SCHEMA_VERSION,
        "root": str(snapshot.root),
        "merkle_root": snapshot.merkle_root,
        "files_seen": len(snapshot.files),
        "duplicate_groups": snapshot.duplicate_groups,
        "duplicate_files": snapshot.duplicate_files,
        "total_bytes": snapshot.total_bytes,
        "scanned_at": canonical_timestamp(),
    }


def receipt_hash(receipt: dict) -> str:
    """Compute the canonical SHA-256 hash of a receipt."""
    return hashlib.sha256(canonical_json(receipt).encode("utf-8")).hexdigest()


def verify_receipt(receipt: dict) -> dict:
    """Validate receipt format and return validation report."""
    report = {"valid": True, "errors": []}

    if not isinstance(receipt, dict):
        report["valid"] = False
        report["errors"].append("Receipt must be a JSON object")
        return report

    required = {"schema", "root", "merkle_root", "files_seen", "scanned_at"}
    missing = required - set(receipt.keys())
    if missing:
        report["valid"] = False
        report["errors"].append(f"Missing fields: {sorted(missing)}")

    if receipt.get("schema") != RECEIPT_SCHEMA_VERSION:
        report["errors"].append(
            f"Unknown schema: {receipt.get('schema')} (expected {RECEIPT_SCHEMA_VERSION})"
        )

    mr = receipt.get("merkle_root", "")
    if not mr.startswith("sha256:") or len(mr) != 71:
        report["valid"] = False
        report["errors"].append("merkle_root must be sha256:<64-hex>")

    fs = receipt.get("files_seen")
    if not isinstance(fs, int) or fs < 0:
        report["valid"] = False
        report["errors"].append("files_seen must be a non-negative integer")

    report["receipt_hash"] = receipt_hash(receipt)
    return report
