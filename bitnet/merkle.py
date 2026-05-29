"""Merkle tree operations — proofs and verification.

All proof functions operate on canonical leaf hashes, not raw file-content hashes.
For folder proofs, the leaf should commit to rel_path + size_bytes + raw_hash.
"""

import hashlib
from typing import List, Dict, Any


def _hex_to_bytes(h: str) -> bytes:
    return bytes.fromhex(h.replace("sha256:", ""))


def _hash_pair(left: str, right: str) -> str:
    """Hash two sha256 hex strings the same way scanner.merkle_root() does."""
    combined = _hex_to_bytes(left) + _hex_to_bytes(right)
    return hashlib.sha256(combined).hexdigest()


def generate_merkle_proof(leaf_hash: str, leaf_hashes: List[str]) -> List[Dict[str, str]]:
    """Generate a Merkle proof for a specific canonical leaf hash."""
    if not leaf_hashes or leaf_hash not in leaf_hashes:
        return []

    sorted_hashes = sorted(leaf_hashes)
    proof = []
    current_level = sorted_hashes[:]
    target_hash = leaf_hash

    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        matched = False
        for i in range(0, len(current_level), 2):
            if current_level[i] == target_hash:
                proof.append({"hash": current_level[i + 1], "position": "right"})
                target_hash = _hash_pair(current_level[i], current_level[i + 1])
                matched = True
                break
            if current_level[i + 1] == target_hash:
                proof.append({"hash": current_level[i], "position": "left"})
                target_hash = _hash_pair(current_level[i], current_level[i + 1])
                matched = True
                break

        if not matched:
            return []

        new_level = []
        for i in range(0, len(current_level), 2):
            new_level.append(_hash_pair(current_level[i], current_level[i + 1]))
        current_level = new_level

    return proof


def build_merkle_tree(hashes: List[str]) -> Dict[str, Any]:
    """Build full Merkle tree and return root + all levels."""
    if not hashes:
        empty = hashlib.sha256(b"").hexdigest()
        return {"root": f"sha256:{empty}", "levels": [[empty]], "leaf_count": 0}

    layer = [bytes.fromhex(h.replace("sha256:", "")) for h in sorted(hashes)]
    levels = [layer[:]]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(hashlib.sha256(left + right).digest())
        layer = nxt
        levels.append(layer[:])

    root = f"sha256:{layer[0].hex()}"
    hex_levels = [[n.hex() for n in lvl] for lvl in levels]
    return {"root": root, "levels": hex_levels, "leaf_count": len(hashes)}


def verify_merkle_proof(merkle_root: str, proof: List[Dict[str, str]], target_hash: str) -> bool:
    """Verify a Merkle proof against an expected root using a canonical leaf hash."""
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
