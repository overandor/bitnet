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
  "root": "demo/sample-folder",
  "merkle_root": "sha256:6c186b73c975...",
  "files_seen": 6,
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

A BitNet receipt is a deterministic JSON object whose SHA-256 hash is independently verifiable:

```json
{
  "root": "/home/user/project",
  "merkle_root": "sha256:a3f7b2...e8d1",
  "files_seen": 247,
  "duplicate_files": 3,
  "total_bytes": 1843200,
  "scanned_at": "2024-06-15T14:32:11Z"
}
```

Verify with `bitnet verify <receipt>` or any SHA-256 implementation.

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
bitnet demo                  # Zero-setup demo on synthetic folder
bitnet watch <folder>        # Scan and persist to SQLite
bitnet watch <folder> --continuous   # Start a watcher loop
bitnet verify <receipt>      # Validate receipt format
bitnet serve                 # Launch dashboard at localhost:8765
```

## Use Cases

- **Code integrity**: Prove your source tree hasn't been tampered with
- **Legal documents**: Timestamp and verify contract folders
- **AI outputs**: Track provenance of generated artifacts
- **Data pipelines**: Ensure datasets remain unchanged between stages
- **Release artifacts**: Cryptographically bind release binaries to their source

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
