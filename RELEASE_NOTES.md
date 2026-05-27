# BitNet v0.1.0

**Self-proving folders.**

Local-first tamper-evident provenance for software supply chains.

## What's In This Release

- **Core primitive**: SHA-256 file hashing, Merkle tree root computation, duplicate detection
- **Canonical receipts**: Versioned (`bitnet-receipt-v1`), deterministic JSON, independently hashable
- **Portable proofs**: `export-proof` and `verify-proof` commands with per-file Merkle proofs
- **Snapshot replay**: `replay` command to rescan and detect tampering against a previous receipt
- **Git integration**: `prove-repo` scans current repo with HEAD commit association; `install-hook` adds pre-commit provenance
- **Web dashboard**: FastAPI dashboard at `localhost:8765`
- **Continuous watcher**: Async scanning loop with SQLite persistence
- **Optional Solana notarization**: Memo-transaction anchoring via `SOLANA_KEYPAIR_PATH`
- **CI/CD**: GitHub Actions workflow for testing; provenance workflow for automatic receipt generation
- **GitHub Action**: `bitnet/verify-repo` composite action for supply-chain verification
- **38 passing tests**

## Quick Start

```bash
pip install bitnet
bitnet demo
```

## Verification

```bash
git clone https://github.com/overandor/bitnet.git
cd bitnet
pip install -e ".[dev]"
pytest
```

## Compliance

BitNet maps to NIST SSDF, NIST RMF, NIST 800-53 (CM-3, CM-5, SI-7, AU-6), CISA Secure by Design, and SLSA Level 2. See [COMPLIANCE.md](COMPLIANCE.md).

## License

MIT
