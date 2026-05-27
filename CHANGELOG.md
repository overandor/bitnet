# Changelog

## [0.1.0] — 2026-05-27

### Added
- **Core primitive**: SHA-256 file hashing, Merkle tree root computation, duplicate detection
- **Canonical receipts**: Versioned (`bitnet-receipt-v1`), deterministic JSON, independently hashable
- **Portable proofs**: `export-proof` and `verify-proof` commands with per-file Merkle proofs
- **Snapshot replay**: `replay` command to rescan and detect tampering against a previous receipt
- **Git integration**: `prove-repo` scans current repo with HEAD commit association; `install-hook` adds pre-commit provenance
- **CLI**: `demo`, `watch`, `verify`, `serve`, `export-proof`, `verify-proof`, `replay`, `prove-repo`, `install-hook`, `uninstall-hook`
- **Web dashboard**: FastAPI dashboard with terminal aesthetic
- **Continuous watcher**: Async scanning loop with SQLite persistence
- **Optional Solana anchoring**: Memo-transaction notarization via `SOLANA_KEYPAIR_PATH`
- **CI/CD**: GitHub Actions workflow for testing; provenance workflow for automatic receipt generation
- **Benchmarks**: `benchmark.py` script for performance validation
- **36 passing tests** covering hashing, Merkle proofs, receipts, proofs, replay, and Git integration
