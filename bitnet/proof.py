"""Portable proof bundles — export and verify independently of the original machine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bitnet.merkle import generate_merkle_proof, verify_merkle_proof
from bitnet.receipt import canonical_json, make_receipt, receipt_hash, RECEIPT_SCHEMA_VERSION
from bitnet.scanner import FolderSnapshot

PROOF_SCHEMA_VERSION = "bitnet-proof-v1"


def export_proof(
    snapshot: Any,
    output_path: Path,
    include_file_proofs: bool = True,
) -> Path:
    """Export a portable proof bundle for a snapshot."""
    receipt = make_receipt(snapshot)
    bundle = {
        "schema": PROOF_SCHEMA_VERSION,
        "receipt": receipt,
        "receipt_hash": receipt_hash(receipt),
        "files": [],
    }

    if include_file_proofs and snapshot.files:
        hashes = [f["raw_hash"] for f in snapshot.files]
        for file_info in snapshot.files:
            proof = generate_merkle_proof(file_info["raw_hash"], hashes)
            bundle["files"].append({
                "rel_path": file_info["rel_path"],
                "raw_hash": file_info["raw_hash"],
                "size_bytes": file_info["size_bytes"],
                "merkle_proof": proof,
            })

    output_path = Path(output_path)
    output_path.write_text(canonical_json(bundle), encoding="utf-8")
    return output_path


def verify_proof_bundle(bundle_path: Path) -> dict:
    """Verify a portable proof bundle. Returns a report dict."""
    report = {
        "valid": False,
        "errors": [],
        "receipt_valid": False,
        "merkle_root_match": False,
        "files_verified": 0,
        "files_total": 0,
    }

    try:
        data = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    except Exception as exc:
        report["errors"].append(f"Cannot read bundle: {exc}")
        return report

    if data.get("schema") != PROOF_SCHEMA_VERSION:
        report["errors"].append(
            f"Unknown proof schema: {data.get('schema')} (expected {PROOF_SCHEMA_VERSION})"
        )

    receipt = data.get("receipt", {})
    expected_hash = data.get("receipt_hash", "")
    actual_hash = receipt_hash(receipt)
    if expected_hash != actual_hash:
        report["errors"].append("Receipt hash mismatch — receipt may have been tampered")
    else:
        report["receipt_valid"] = True

    merkle_root = receipt.get("merkle_root", "")
    files = data.get("files", [])
    report["files_total"] = len(files)

    for f in files:
        proof = f.get("merkle_proof", [])
        if verify_merkle_proof(merkle_root, proof, f["raw_hash"]):
            report["files_verified"] += 1
        else:
            report["errors"].append(f"Merkle proof failed for {f['rel_path']}")

    if report["files_total"] > 0 and report["files_verified"] == report["files_total"]:
        report["merkle_root_match"] = True

    if not report["errors"]:
        report["valid"] = True

    return report


def replay_snapshot(folder_path: Path, previous_receipt: dict, max_files: int = 250) -> dict:
    """Rescan a folder and compare against a previous receipt."""
    report = {
        "status": "unknown",
        "previous_merkle_root": previous_receipt.get("merkle_root"),
        "current_merkle_root": "",
        "files_seen": 0,
        "previous_files_seen": previous_receipt.get("files_seen", 0),
        "match": False,
        "errors": [],
    }

    try:
        snapshot = FolderSnapshot(folder_path, max_files).scan()
    except Exception as exc:
        report["status"] = "error"
        report["errors"].append(f"Scan failed: {exc}")
        return report

    report["current_merkle_root"] = snapshot.merkle_root
    report["files_seen"] = len(snapshot.files)

    if snapshot.merkle_root == previous_receipt.get("merkle_root"):
        report["status"] = "unchanged"
        report["match"] = True
    else:
        report["status"] = "tampered"
        report["match"] = False

    return report
