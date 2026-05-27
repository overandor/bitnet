# BitNet

> **Self-proving folders.**

BitNet is cryptographic evidence infrastructure for software, datasets, AI artifacts, and mission-critical folders.

It continuously hashes files, builds Merkle trees, detects duplicates, and generates receipts you can independently verify — then watches forever.

![Demo](https://user-images.githubusercontent.com/bitnet/demo.gif)

## One Command

```bash
pip install bitnet
bitnet scan ~/release-artifacts
```

## Demo (No Setup)

```bash
bitnet demo
```

```
BitNet — Self-Proving Folders

┌──────────────────────────────────────────────┐
│ Folder        demo/sample-folder             │
│ Files Scanned 6                              │
│ Merkle Root   sha256:6c186b73c975...         │
│ Proof valid   True                           │
│ Proof depth   3 sibling hashes               │
└──────────────────────────────────────────────┘

Receipt:
{
  "schema": "bitnet-receipt-v1",
  "root": "demo/sample-folder",
  "merkle_root": "sha256:6c186b73c975...",
  "files_seen": 6,
  "duplicate_groups": 0,
  "duplicate_files": 0,
  "total_bytes": 1293,
  "scanned_at": "2026-05-27T20:17:41Z"
}
```

## What It Does

```
Folder → SHA-256 → Deduplicate → Merkle Root → Canonical Receipt → SQLite Audit Log → Watch Forever
```

**One sentence:** Local-first tamper-evident provenance for software supply chains.

Re-scan a folder. If the Merkle root matches, nothing changed. If it differs, something tampered.

## Federal & Compliance Positioning

BitNet maps to recognized security frameworks:

| Framework | BitNet Alignment |
|-----------|------------------|
| **NIST SSDF / SP 800-218** | Tamper-evident proof of software artifacts at build time |
| **NIST RMF** | Audit evidence for file integrity controls |
| **NIST SP 800-53 Rev 5** | CM-3, CM-5, SI-7, AU-6 |
| **CISA Secure by Design** | Local-first, deterministic, auditable |
| **SLSA** | Artifact integrity and build provenance (Level 2) |
| **in-toto** | Layout-linkable receipts |
| **SBOM** | Verify SPDX/CycloneDX files have not been altered |

See [`COMPLIANCE.md`](COMPLIANCE.md) for the full control mapping.

## Proof Artifact

A BitNet receipt is a canonical, versioned JSON object whose SHA-256 hash is independently verifiable:

```json
{
  "schema": "bitnet-receipt-v1",
  "root": "/home/user/project",
  "merkle_root": "sha256:a3f7b2...e8d1",
  "files_seen": 247,
  "duplicate_groups": 2,
  "duplicate_files": 3,
  "total_bytes": 1843200,
  "scanned_at": "2024-06-15T14:32:11Z"
}
```

Verify with `bitnet verify <receipt>` or any SHA-256 implementation. Receipts use deterministic JSON (sorted keys, minimal separators) so the hash is reproducible across platforms.

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌──────────┐     ┌─────────────────┐
│   Folder    │────▶│  SHA-256 │────▶│  Merkle  │────▶│  Canonical      │
│   Files     │     │  Hashes  │     │   Root   │     │  Receipt        │
└─────────────┘     └──────────┘     └────┬─────┘     └─────────────────┘
                                          │
                                    ┌─────▼─────┐
                                    │  SQLite   │
                                    │  Audit    │
                                    │  Log      │
                                    └───────────┘
```

- **Local-first**: All hashing runs on your machine. No telemetry. No external dependencies.
- **Deterministic**: Same files, same order → same Merkle root, every time.
- **Continuous**: Watchers re-scan on interval and detect changes automatically.
- **Streaming**: O(1) memory per file. Scans 1,000 files in < 50ms on modern hardware.
- **Testable**: 36 passing tests. Reproducible builds.

## CLI

```bash
bitnet demo                       # Zero-setup demo on synthetic folder
bitnet scan <folder>              # Scan without persistence
bitnet watch <folder>             # Scan and persist to SQLite audit log
bitnet watch <folder> --continuous   # Start a watcher loop
bitnet receipt <folder> <out>       # Generate canonical receipt file
bitnet verify <receipt>           # Validate receipt format and canonical hash
bitnet diff <receipt-a> <receipt-b> # Compare two receipts
bitnet export-proof <folder> <out>   # Portable proof bundle with Merkle proofs
bitnet verify-proof <bundle>      # Independently verify a proof bundle
bitnet replay <folder> <receipt>  # Rescan and detect tampering
bitnet prove-repo                 # Scan git repo, include HEAD commit
bitnet install-hook               # Add pre-commit provenance hook
bitnet serve                      # Launch dashboard at localhost:8765
```

Planned commands (track progress in GitHub issues):

```bash
bitnet sign <receipt> --key <key>       # Ed25519 sign a receipt
bitnet attest <receipt> --rekor         # Sign + publish to Sigstore Rekor
bitnet sbom <folder> <out>              # SPDX/CycloneDX provenance
bitnet export-oscal <receipt> <out>     # NIST OSCAL assessment evidence
```

## Use Cases

- **Software supply chain**: Prove build artifacts were not silently modified
- **AI artifact provenance**: Track generated code, models, datasets
- **Dataset integrity**: Ensure training data remains unchanged between stages
- **Release verification**: Cryptographically bind release binaries to source
- **Incident response**: Preserve evidence of folder state at a point in time
- **Contractor audit**: Generate ATO-ready evidence for NIST controls

## Portable Proof Bundles

Export a folder as a self-contained proof anyone can verify:

```bash
bitnet export-proof ~/project project-proof.json
bitnet verify-proof project-proof.json
```

Bundles include per-file Merkle proofs, so every file's inclusion in the root is independently checkable.

## Snapshot Replay

Prove a folder hasn't changed since a previous receipt:

```bash
bitnet receipt ~/project receipt.json
# later...
bitnet replay ~/project receipt.json
# → Status: UNCHANGED
```

If any file changes, the replay reports `TAMPERED` with the differing Merkle roots.

## Git Integration

Prove the state of a Git repository and include the current HEAD commit:

```bash
bitnet prove-repo --output repo-receipt.json
```

Install a pre-commit hook to automatically generate receipts before each commit:

```bash
bitnet install-hook
```

## GitHub Actions Provenance

Attach a BitNet receipt to every push:

```yaml
- name: Generate provenance receipt
  run: |
    pip install bitnet
    bitnet scan . --output receipt.json
- name: Upload receipt
  uses: actions/upload-artifact@v4
  with:
    name: provenance-receipt
    path: receipt.json
```

## Trust

- All hashing is local
- No telemetry
- No data leaves your machine
- Receipts are deterministic and independently verifiable
- 36 passing tests with reproducible results
- MIT licensed

## What BitNet Is NOT

- Not a blockchain protocol
- Not a token system
- Not a marketplace
- Not a cloud storage service
- Not a backup tool
- Not a vulnerability scanner
- Not a replacement for formal code signing (PKI)

BitNet is a **local-first cryptographic provenance primitive**. It produces evidence. It does not enforce policy.

## Install

```bash
pip install bitnet
```

With Solana notarization (optional):

```bash
pip install bitnet[solana]
```

## Development

```bash
git clone https://github.com/overandor/bitnet.git
cd bitnet
pip install -e ".[dev]"
pytest
```

## License

MIT
