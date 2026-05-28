# BitNet v0.1.0 Release Checklist

## Pre-Release

- [x] All tests pass (53/53)
- [x] README trimmed to < 500 words, no speculative language
- [x] COMPLIANCE.md maps to NIST/CISA/SLSA controls
- [x] THREAT_MODEL.md states protection claims and limitations
- [x] CHANGELOG.md created
- [x] No financial language (no USD, lendable, collateral, treasury, appraisal)
- [x] GitHub Action `verify-repo` created under `.github/actions/verify-repo/`
- [x] CI workflow tests on Python 3.10, 3.11, 3.12
- [x] CLI commands verified: demo, scan, watch, receipt, verify, diff, export-proof, verify-proof, replay, prove-repo, install-hook, snapshot, verify-snapshot, agent-action, agent-chain-verify, agent-policy, serve
- [x] `bitnet verify` rescans folder and compares Merkle roots
- [x] Portable snapshot export/verify works end-to-end
- [x] Agent action receipt chain works with hash chain tamper detection
- [x] Optional Solana anchoring stores only `BITNET_ACTION:<hash>` on-chain
- [x] Dashboard defaults to localhost (`127.0.0.1`)
- [x] `.gitignore` excludes pycache, build artifacts, receipts

## Release Steps

1. [ ] Create GitHub Release at `https://github.com/overandor/bitnet/releases/new`
2. [ ] Tag: `v0.1.0`
3. [ ] Title: `BitNet v0.1.0 — Self-Proving Folders`
4. [ ] Paste release notes from `RELEASE_NOTES.md`
5. [ ] Publish release
6. [ ] Verify CI passes on tagged commit
7. [ ] Verify `pip install bitnet` works from PyPI (when published)

## Post-Release

- [ ] Record release hash in agent action chain
- [ ] Publish demo GIF to README placeholder
- [ ] Announce on relevant channels (if any)
- [ ] Monitor first issues for 48 hours

## Primitives in this release

| Primitive | Status |
|-----------|--------|
| SHA-256 file hashing | Stable |
| Merkle tree root | Stable |
| Canonical receipt (`bitnet-receipt-v1`) | Stable |
| Portable proof bundle (`bitnet-proof-v1`) | Stable |
| Portable snapshot (`bitnet-snapshot-v1`) | Stable |
| Snapshot replay / tamper detection | Stable |
| Git integration (prove-repo, install-hook) | Stable |
| Agent action receipt chain | Stable |
| Policy-based action filtering | Stable |
| SQLite persistence | Stable |
| FastAPI dashboard | Stable |
| Solana memo anchoring (optional) | Stable |
| GitHub Action `verify-repo` | Stable |

## Deferred to v0.2.0+

- Sigstore Rekor integration (`attest`)
- Ed25519 signing (`sign`)
- SBOM generation (`sbom`)
- OSCAL export (`export-oscal`)
- TPM/TEE remote attestation
- Benchmark suite with real numbers
- Demo GIF / visual proof
