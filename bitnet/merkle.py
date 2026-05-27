"""Merkle tree operations — proofs and verification."""

import hashlib
from typing import List, Dict, Any


def _hex_to_bytes(h: str) -> bytes:
    return bytes.fromhex(h.replace("sha256:", ""))


def _hash_pair(left: str, right: str) -> str:
    """Hash two hex strings the same way merkle_root() does with bytes."""
    combined = _hex_to_bytes(left) + _hex_to_bytes(right)
    return hashlib.sha256(combined).hexdigest()


def generate_merkle_proof(file_hash: str, file_hashes: List[str]) -> List[Dict[str, str]]:
    """Generate a Merkle proof for a specific file hash within a list of hashes."""
    if not file_hashes or file_hash not in file_hashes:
        return []

    sorted_hashes = sorted(file_hashes)
    proof = []
    current_level = sorted_hashes[:]
    target_hash = file_hash

    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        for i in range(0, len(current_level), 2):
            if current_level[i] == target_hash:
                proof.append({"hash": current_level[i + 1], "position": "right"})
                target_hash = _hash_pair(current_level[i], current_level[i + 1])
                break
            elif current_level[i + 1] == target_hash:
                proof.append({"hash": current_level[i], "position": "left"})
                target_hash = _hash_pair(current_level[i], current_level[i + 1])
                break

        new_level = []
        for i in range(0, len(current_level), 2):
            new_level.append(_hash_pair(current_level[i], current_level[i + 1]))
        current_level = new_level

    return proof


def verify_merkle_proof(merkle_root: str, proof: List[Dict[str, str]], target_hash: str) -> bool:
    """Verify a Merkle proof against an expected root."""
    current_hash = target_hash.replace("sha256:", "")
    for step in proof:
        sibling = step["hash"].replace("sha256:", "")
        if step["position"] == "left":
            current_hash = hashlib.sha256(
                bytes.fromhex(sibling) + bytes.fromhex(current_hash)
            ).hexdigest()
        else:
            current_hash = hashlib.sha256(
                bytes.fromhex(current_hash) + bytes.fromhex(sibling)
            ).hexdigest()
    expected = merkle_root.replace("sha256:", "")
    return current_hash == expected
