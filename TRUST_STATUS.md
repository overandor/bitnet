# BitNet Trust Status

This file separates implemented behavior from planned capability. It is intended to prevent overclaiming.

## Implemented

| Capability | Status | Notes |
|---|---:|---|
| Local file hashing | REAL | Files are SHA-256 hashed locally. |
| Path-bound Merkle leaves | REAL | Leaves now commit to `rel_path`, `size_bytes`, and `raw_hash`. |
| Folder Merkle root | REAL | Built from canonical leaf hashes. |
| Receipt generation | REAL | Canonical JSON receipt with schema, root, Merkle root, file count, byte count, duplicate count, timestamp. |
| Receipt replay against live folder | REAL | Re-scans the folder and compares Merkle roots. |
| Portable proof bundle | REAL | Exports per-file Merkle proofs using path-bound leaf hashes. |
| Portable snapshot directory | REAL | Exports receipt, manifest, files, Merkle tree, and proofs. |
| SQLite run persistence | REAL | Stores folder runs, file rows, watchers, anchors, and audit log. |
| Local dashboard | REAL | Defaults to localhost. |
| Agent action hash chain | REAL | Stores local JSONL hash chain for material actions. |

## Partial / Environment-dependent

| Capability | Status | Notes |
|---|---:|---|
| Solana devnet anchoring | PARTIAL | Optional. Requires compatible Solana Python dependencies and `SOLANA_KEYPAIR_PATH`. On-chain memo stores only a shortened root/hash payload. |
| Pre-commit hook | PARTIAL | Hook invokes `prove-repo`; strict receipt staging/policy mode is still future work. |
| Web API access control | PARTIAL | Safe by default on localhost. Public deployment requires `BITNET_API_KEY` and a future root allowlist. |

## Planned, not yet production claims

| Capability | Status | Notes |
|---|---:|---|
| Ed25519 receipt signing | PLANNED | CLI command exists as a placeholder. |
| Sigstore/Rekor attestation | PLANNED | CLI command exists as a placeholder. |
| SBOM generation | PLANNED | CLI command exists as a placeholder. |
| OSCAL export | PLANNED | CLI command exists as a placeholder. |
| Formal SLSA certification | NOT CLAIMED | BitNet can produce evidence useful for SLSA-style workflows, but it is not certified. |
| Formal NIST compliance | NOT CLAIMED | BitNet can support control evidence, but does not itself grant compliance or ATO. |

## Threat Model Summary

BitNet detects silent content or path/layout drift when a prior receipt/proof/snapshot is available. It does not prevent tampering, replace code signing, prove author identity, prove legal ownership, or secure a publicly exposed dashboard by itself.
