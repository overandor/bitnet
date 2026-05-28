"""Portable snapshot export and verification.

A snapshot is a self-contained directory:
    snapshot/
      receipt.json      — canonical receipt
      manifest.json     — manifest of the snapshot itself
      files.json        — per-file metadata and hashes
      merkle.json       — Merkle tree structure
      proof.json        — per-file Merkle proofs
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from bitnet.scanner import FolderSnapshot
from bitnet.receipt import make_receipt, receipt_hash, verify_receipt
from bitnet.proof import export_proof, verify_proof_bundle
from bitnet.merkle import build_merkle_tree, generate_merkle_proof, verify_merkle_proof

SNAPSHOT_SCHEMA = "bitnet-snapshot-v1"


def export_snapshot(folder: Path, output_dir: Path, max_files: int = 250) -> Path:
    """Export a folder as a portable snapshot directory."""
    snapshot = FolderSnapshot(folder, max_files).scan()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # receipt.json
    receipt = make_receipt(snapshot)
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True)
    )

    # manifest.json
    manifest = {
        "schema": SNAPSHOT_SCHEMA,
        "source_root": str(folder),
        "snapshot_created": receipt["scanned_at"],
        "receipt_hash": receipt_hash(receipt),
        "files_count": len(snapshot.files),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )

    # files.json
    files_data = [
        {
            "rel_path": f["rel_path"],
            "size_bytes": f["size_bytes"],
            "raw_hash": f["raw_hash"],
            "modified_at": f["modified_at"],
            "duplicate_of": f["duplicate_of"],
        }
        for f in snapshot.files
    ]
    (output_dir / "files.json").write_text(
        json.dumps(files_data, indent=2, sort_keys=True)
    )

    # merkle.json
    tree = build_merkle_tree([f["raw_hash"] for f in snapshot.files])
    merkle_data = {
        "root": tree["root"] if tree else None,
        "levels": tree["levels"] if tree else [],
        "leaf_count": len(snapshot.files),
    }
    (output_dir / "merkle.json").write_text(
        json.dumps(merkle_data, indent=2, sort_keys=True)
    )

    # proof.json — per-file Merkle proofs
    hashes = [f["raw_hash"] for f in snapshot.files]
    proofs = []
    for f in snapshot.files:
        proof = generate_merkle_proof(f["raw_hash"], hashes)
        proofs.append({
            "rel_path": f["rel_path"],
            "raw_hash": f["raw_hash"],
            "proof": proof,
        })
    (output_dir / "proof.json").write_text(
        json.dumps(proofs, indent=2, sort_keys=True)
    )

    return output_dir


def verify_snapshot(snapshot_dir: Path) -> Dict[str, Any]:
    """Verify a portable snapshot directory."""
    snapshot_dir = Path(snapshot_dir)
    report = {
        "valid": True,
        "errors": [],
        "checks": {},
    }

    required = ["receipt.json", "manifest.json", "files.json", "merkle.json", "proof.json"]
    for fname in required:
        fpath = snapshot_dir / fname
        if not fpath.exists():
            report["valid"] = False
            report["errors"].append(f"Missing: {fname}")

    if not report["valid"]:
        return report

    # Verify receipt format
    receipt = json.loads((snapshot_dir / "receipt.json").read_text())
    receipt_report = verify_receipt(receipt)
    report["checks"]["receipt_format"] = receipt_report["valid"]
    if not receipt_report["valid"]:
        report["valid"] = False
        report["errors"].extend(receipt_report["errors"])

    # Verify manifest matches receipt
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    report["checks"]["manifest_schema"] = manifest.get("schema") == SNAPSHOT_SCHEMA
    if manifest.get("receipt_hash") != receipt_hash(receipt):
        report["valid"] = False
        report["errors"].append("manifest receipt_hash does not match computed receipt hash")

    # Verify files.json hash consistency
    files_data = json.loads((snapshot_dir / "files.json").read_text())
    merkle_data = json.loads((snapshot_dir / "merkle.json").read_text())
    proofs = json.loads((snapshot_dir / "proof.json").read_text())

    # Rebuild Merkle root from files.json
    from bitnet.merkle import build_merkle_tree
    hashes = [f["raw_hash"] for f in files_data]
    recomputed_tree = build_merkle_tree(hashes)
    recomputed_root = recomputed_tree["root"] if recomputed_tree else None

    stored_root = merkle_data.get("root")
    receipt_root = receipt.get("merkle_root")

    report["checks"]["merkle_root_recomputed"] = recomputed_root == stored_root
    report["checks"]["merkle_root_matches_receipt"] = stored_root == receipt_root

    if recomputed_root != stored_root:
        report["valid"] = False
        report["errors"].append("Recomputed Merkle root does not match stored merkle.json")
    if stored_root != receipt_root:
        report["valid"] = False
        report["errors"].append("Merkle root in merkle.json does not match receipt")

    # Verify per-file proofs
    files_verified = 0
    files_failed = 0
    for proof_entry in proofs:
        rel_path = proof_entry["rel_path"]
        raw_hash = proof_entry["raw_hash"]
        proof = proof_entry["proof"]
        if verify_merkle_proof(stored_root, proof, raw_hash):
            files_verified += 1
        else:
            files_failed += 1

    report["checks"]["files_verified"] = files_verified
    report["checks"]["files_failed"] = files_failed
    report["checks"]["files_total"] = len(proofs)

    if files_failed > 0:
        report["valid"] = False
        report["errors"].append(f"{files_failed} file proofs failed verification")

    return report
