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


def build_merkle_tree(hashes: List[str]) -> Dict[str, Any]:
    """Build full Merkle tree and return root + all levels.

    Matches scanner.merkle_root construction exactly.
    """
    if not hashes:
        empty = hashlib.sha256(b"").hexdigest()
        return {"root": f"sha256:{empty}", "levels": [[empty]], "leaf_count": 0}

    layer = [bytes.fromhex(h.replace("sha256:", "")) for h in sorted(hashes)]
    levels = [layer[:]]  # store bytes at each level
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(hashlib.sha256(left + right).digest())
        layer = nxt
        levels.append(layer[:])

    root = f"sha256:{layer[0].hex()}"
    # convert levels to hex strings for serialization
    hex_levels = [[n.hex() for n in lvl] for lvl in levels]
    return {"root": root, "levels": hex_levels, "leaf_count": len(hashes)}


def verify_merkle_proof(merkle_root: str, proof: List[Dict[str, str]], target_hash: str) -> bool:
    """Verify a Merkle proof against an expected root."""
    current_hash = target_hash.replace("sha256:", "")
    for step in proof:
        sibling = step["hash"].replace("sha256:", "")
        if step.get("position") == "left" or step.get("side") == "left":
            current_hash = hashlib.sha256(
                bytes.fromhex(sibling) + bytes.fromhex(current_hash)
            ).hexdigest()
        else:
            current_hash = hashlib.sha256(
                bytes.fromhex(current_hash) + bytes.fromhex(sibling)
            ).hexdigest()
    expected = merkle_root.replace("sha256:", "")
    return current_hash == expected
