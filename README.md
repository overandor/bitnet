# BitNet

> **Self-proving folders.**

Local-first tamper-evident provenance for software supply chains.

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
Folder → SHA-256 → Merkle Root → Canonical Receipt
```

Re-scan a folder. If the Merkle root matches, nothing changed. If it differs, something tampered.

BitNet maps to NIST SSDF, NIST RMF, NIST 800-53 (CM-3, CM-5, SI-7, AU-6), CISA Secure by Design, and SLSA Level 2. See [`COMPLIANCE.md`](COMPLIANCE.md) for the full control mapping.

## CLI

```bash
bitnet demo                       # Zero-setup demo
bitnet scan <folder>              # Scan without persistence
bitnet watch <folder>             # Scan and persist to SQLite audit log
bitnet receipt <folder> <out>     # Generate canonical receipt
bitnet verify <receipt>           # Validate receipt format
bitnet diff <a> <b>               # Compare two receipts
bitnet export-proof <folder> <out>   # Portable proof bundle
bitnet verify-proof <bundle>      # Verify proof bundle
bitnet replay <folder> <receipt>  # Rescan and detect tampering
bitnet prove-repo                 # Scan git repo, include HEAD
bitnet install-hook               # Add pre-commit hook
bitnet serve                      # Launch dashboard
```

## Use Cases

- **Software supply chain**: Prove build artifacts were not silently modified
- **AI artifact provenance**: Track generated code, models, datasets
- **Dataset integrity**: Ensure training data remains unchanged between stages
- **Release verification**: Cryptographically bind release binaries to source
- **Incident response**: Preserve evidence of folder state at a point in time
- **Contractor audit**: Generate ATO-ready evidence for NIST controls

## Trust

- All hashing is local. No telemetry. No data leaves your machine.
- Receipts are deterministic and independently verifiable.
- 38 passing tests. Reproducible builds.
- MIT licensed.

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

With optional Solana notarization:

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
