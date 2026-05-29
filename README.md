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
Folder → SHA-256 files → path-bound Merkle leaves → Merkle Root → Canonical Receipt
```

Re-scan a folder. If the Merkle root matches, nothing changed. If it differs, content or path/layout state changed.

BitNet can produce evidence useful for NIST SSDF/RMF/800-53, CISA Secure by Design, and SLSA-style workflows, but it does **not** itself grant compliance, certification, ATO, or formal SLSA level. See [`COMPLIANCE.md`](COMPLIANCE.md) and [`TRUST_STATUS.md`](TRUST_STATUS.md).

## CLI

```bash
bitnet demo                       # Zero-setup demo
bitnet scan <folder>              # Scan without persistence
bitnet watch <folder>             # Scan and persist to SQLite audit log
bitnet receipt <folder> <out>     # Generate canonical receipt
bitnet verify <receipt>           # Rescan folder and compare Merkle roots
bitnet diff <a> <b>               # Compare two receipts
bitnet export-proof <folder> <out>   # Portable proof bundle
bitnet verify-proof <bundle>      # Verify proof bundle
bitnet replay <folder> <receipt>  # Rescan and detect tampering
bitnet prove-repo                 # Scan git repo, include HEAD
bitnet install-hook               # Add pre-commit hook
bitnet snapshot <folder> <out>    # Export portable snapshot directory
bitnet verify-snapshot <dir>      # Verify snapshot integrity
bitnet agent-action <type>        # Log material agent action
bitnet agent-chain-verify         # Verify agent action hash chain
bitnet agent-policy               # Show material action policy
bitnet serve                      # Launch dashboard
```

Some advanced commands such as signing, SBOM export, OSCAL export, and Rekor attestation are present as planned CLI placeholders until implemented. See [`TRUST_STATUS.md`](TRUST_STATUS.md).

## Use Cases

- **Software supply chain**: Prove build artifacts were not silently modified
- **AI artifact provenance**: Track generated code, models, datasets
- **Dataset integrity**: Ensure training data remains unchanged between stages
- **Release verification**: Cryptographically bind release binaries to source
- **Incident response**: Preserve evidence of folder state at a point in time
- **Contractor audit evidence**: Generate local evidence that can support formal control assessments

## Trust

- All hashing is local. No telemetry. No data leaves your machine.
- Receipts are deterministic and independently verifiable.
- Folder roots are path-bound: relative path + size + file hash.
- MIT licensed.

See [`THREAT_MODEL.md`](THREAT_MODEL.md) for what BitNet protects against and what it does not.

## What BitNet Is NOT

- Not a blockchain protocol
- Not a token system
- Not a marketplace
- Not a cloud storage service
- Not a backup tool
- Not a vulnerability scanner
- Not a replacement for formal code signing (PKI)
- Not a compliance certification by itself

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
