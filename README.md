# BitNet

> **Self-proving folders.**

BitNet turns any folder into a cryptographically verifiable object.

It continuously hashes files, builds Merkle trees, detects duplicates, and generates receipts you can independently verify — then watches forever.

![Demo](https://user-images.githubusercontent.com/bitnet/demo.gif)

## One Command

```bash
pip install bitnet
bitnet watch ~/important-folder
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
Folder → SHA-256 → Deduplicate → Merkle Root → SQLite Receipt → Optional Solana Anchor → Watch Forever
```

**One sentence:** Folders that continuously generate cryptographic proofs of their own integrity.

Re-scan a folder. If the Merkle root matches, nothing changed. If it differs, something tampered.

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
┌─────────────┐     ┌──────────┐     ┌──────────┐     ┌────────────┐
│   Folder    │────▶│  SHA-256 │────▶│  Merkle  │────▶│  SQLite    │
│   Files     │     │  Hashes  │     │   Root   │     │  Receipt   │
└─────────────┘     └──────────┘     └────┬─────┘     └────────────┘
                                          │
                                    ┌─────▼─────┐
                                    │  Optional │
                                    │  Solana   │
                                    │  Anchor   │
                                    └───────────┘
```

- **Local-first**: All hashing runs on your machine. No data leaves unless you explicitly anchor.
- **Deterministic**: Same files, same order → same Merkle root, every time.
- **Continuous**: Watchers re-scan on interval and detect changes automatically.
- **Streaming**: O(1) memory per file. Scans 1,000 files in < 2 seconds on M1 MacBook.

## CLI

```bash
bitnet demo                       # Zero-setup demo on synthetic folder
bitnet watch <folder>             # Scan and persist to SQLite
bitnet watch <folder> --continuous   # Start a watcher loop
bitnet verify <receipt>           # Validate receipt format
bitnet export-proof <folder> <out>   # Portable proof bundle with Merkle proofs
bitnet verify-proof <bundle>      # Independently verify a proof bundle
bitnet replay <folder> <receipt>  # Rescan and compare against previous receipt
bitnet prove-repo                 # Scan current git repo, include HEAD commit
bitnet install-hook               # Add pre-commit provenance hook
bitnet serve                      # Launch dashboard at localhost:8765
```

## Use Cases

- **Code integrity**: Prove your source tree hasn't been tampered with
- **Legal documents**: Timestamp and verify contract folders
- **AI outputs**: Track provenance of generated artifacts
- **Data pipelines**: Ensure datasets remain unchanged between stages
- **Release artifacts**: Cryptographically bind release binaries to their source

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
bitnet watch ~/project --output receipt.json
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
    bitnet watch . --output receipt.json
- name: Upload receipt
  uses: actions/upload-artifact@v4
  with:
    name: provenance-receipt
    path: receipt.json
```

## Optional: Solana Anchoring

Set `SOLANA_KEYPAIR_PATH` to a valid keypair JSON file. BitNet writes Merkle roots as **memo transactions** on Solana devnet. Purely notarization — no tokens, no contracts, no DeFi mechanics.

```bash
export SOLANA_KEYPAIR_PATH=/path/to/keypair.json
pip install bitnet[solana]
bitnet watch ~/important-folder --anchor
```

## Trust

- All hashing is local
- All LLM inference is local (Ollama, optional)
- No telemetry
- No data leaves your machine unless you explicitly enable Solana anchoring
- Receipts are deterministic and independently verifiable

## Install

```bash
pip install bitnet
```

With Solana:

```bash
pip install bitnet[solana]
```

## Development

```bash
git clone https://github.com/bitnet/bitnet.git
cd bitnet
pip install -e ".[dev]"
pytest
```

## License

MIT
