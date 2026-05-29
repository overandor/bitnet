"""Portable snapshot export and verification.

A snapshot is a self-contained directory:
    snapshot/
      receipt.json      — canonical receipt
      manifest.json     — manifest of the snapshot itself
      files.json        — per-file metadata and path-bound hashes
      merkle.json       — Merkle tree structure
      proof.json        — per-file Merkle proofs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from bitnet.scanner import FolderSnapshot, canonical_leaf_hash
from bitnet.receipt import make_receipt, receipt_hash, verify_receipt
from bitnet.merkle import build_merkle_tree, generate_merkle_proof, verify_merkle_proof

SNAPSHOT_SCHEMA = "bitnet-snapshot-v1"
LEAF_MODEL = "sha256(canonical_json(rel_path,size_bytes,raw_hash))"


def _leaf_hash(file_info: dict) -> str:
    return file_info.get("leaf_hash") or canonical_leaf_hash(
        file_info["rel_path"],
        int(file_info.get("size_bytes", 0)),
        file_info["raw_hash"],
    )


def export_snapshot(folder: Path, output_dir: Path, max_files: int = 250) -> Path:
    """Export a folder as a portable snapshot directory."""
    snapshot = FolderSnapshot(folder, max_files).scan()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    receipt = make_receipt(snapshot)
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True)
    )

    manifest = {
        "schema": SNAPSHOT_SCHEMA,
        "source_root": str(folder),
        "snapshot_created": receipt["scanned_at"],
        "receipt_hash": receipt_hash(receipt),
        "files_count": len(snapshot.files),
        "leaf_model": LEAF_MODEL,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )

    files_data = [
        {
            "rel_path": f["rel_path"],
            "size_bytes": f["size_bytes"],
            "raw_hash": f["raw_hash"],
            "leaf_hash": _leaf_hash(f),
            "modified_at": f["modified_at"],
            "duplicate_of": f["duplicate_of"],
        }
        for f in snapshot.files
    ]
    (output_dir / "files.json").write_text(
        json.dumps(files_data, indent=2, sort_keys=True)
    )

    leaf_hashes = [f["leaf_hash"] for f in files_data]
    tree = build_merkle_tree(leaf_hashes)
    merkle_data = {
        "root": tree["root"] if tree else None,
        "levels": tree["levels"] if tree else [],
        "leaf_count": len(snapshot.files),
        "leaf_model": LEAF_MODEL,
    }
    (output_dir / "merkle.json").write_text(
        json.dumps(merkle_data, indent=2, sort_keys=True)
    )

    proofs = []
    for f in files_data:
        proof = generate_merkle_proof(f["leaf_hash"], leaf_hashes)
        proofs.append({
            "rel_path": f["rel_path"],
            "raw_hash": f["raw_hash"],
            "leaf_hash": f["leaf_hash"],
            "size_bytes": f["size_bytes"],
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

    receipt = json.loads((snapshot_dir / "receipt.json").read_text())
    receipt_report = verify_receipt(receipt)
    report["checks"]["receipt_format"] = receipt_report["valid"]
    if not receipt_report["valid"]:
        report["valid"] = False
        report["errors"].extend(receipt_report["errors"])

    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    report["checks"]["manifest_schema"] = manifest.get("schema") == SNAPSHOT_SCHEMA
    if manifest.get("receipt_hash") != receipt_hash(receipt):
        report["valid"] = False
        report["errors"].append("manifest receipt_hash does not match computed receipt hash")

    files_data = json.loads((snapshot_dir / "files.json").read_text())
    merkle_data = json.loads((snapshot_dir / "merkle.json").read_text())
    proofs = json.loads((snapshot_dir / "proof.json").read_text())

    leaf_hashes = [_leaf_hash(f) for f in files_data]
    recomputed_tree = build_merkle_tree(leaf_hashes)
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

    files_verified = 0
    files_failed = 0
    for proof_entry in proofs:
        leaf_hash = proof_entry.get("leaf_hash") or canonical_leaf_hash(
            proof_entry["rel_path"],
            int(proof_entry.get("size_bytes", 0)),
            proof_entry["raw_hash"],
        )
        proof = proof_entry["proof"]
        if verify_merkle_proof(stored_root, proof, leaf_hash):
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
