# BitNet Compliance & Control Mapping

**BitNet: cryptographic evidence infrastructure for software, datasets, AI artifacts, and mission-critical folders.**

This document maps BitNet features to recognized federal security frameworks, controls, and verification methods.

---

## 1. Framework Alignment

| Framework | Relevance to BitNet |
|-----------|---------------------|
| **NIST SSDF / SP 800-218** | Secure Software Development Framework — BitNet provides tamper-evident proof of software artifacts at build time |
| **NIST RMF** | Risk Management Framework — BitNet receipts serve as audit evidence for file integrity controls |
| **NIST SP 800-53 Rev 5** | Security and Privacy Controls — BitNet maps to CM-3, CM-5, SI-7, AU-6 |
| **CISA Secure by Design** | Secure-by-design principles — BitNet is local-first, deterministic, auditable |
| **SLSA (Supply-chain Levels for Software Artifacts)** | BitNet provides artifact integrity and build provenance at Level 2+ |
| **in-toto** | Software supply-chain layout integrity — BitNet generates layout-linkable receipts |
| **SBOM (SPDX / CycloneDX)** | BitNet can verify SBOM files have not been altered since generation |
| **Sigstore / Rekor** | Transparency log compatibility — BitNet receipts can be published to Rekor |
| **OSCAL** | Open Security Controls Assessment Language — BitNet receipts can be exported as OSCAL assessment evidence |

---

## 2. Control Mapping

### CM-3 — Configuration Change Control
| BitNet Feature | Evidence Produced | Verification Method |
|----------------|-------------------|---------------------|
| `bitnet watch` + `--continuous` | SQLite receipt with Merkle root and timestamp | `bitnet replay` against previous receipt |
| `bitnet export-proof` | Portable JSON bundle with per-file Merkle proofs | `bitnet verify-proof` independently |

### CM-5 — Access Restrictions for Change
| BitNet Feature | Evidence Produced | Verification Method |
|----------------|-------------------|---------------------|
| `bitnet scan` / `bitnet watch` | File-level SHA-256 hashes | Byte-for-byte re-comparison |
| `bitnet replay` | Tamper detection report | Merkle root equality check |

### SI-7 — Software, Firmware, and Information Integrity
| BitNet Feature | Evidence Produced | Verification Method |
|----------------|-------------------|---------------------|
| `bitnet verify-proof` | Per-file Merkle proof verification | Cryptographic hash chain validation |
| `bitnet replay` | Changed/unchanged status with Merkle root diff | Independent re-scan |

### AU-6 — Audit Record Review
| BitNet Feature | Evidence Produced | Verification Method |
|----------------|-------------------|---------------------|
| Canonical receipt (`bitnet-receipt-v1`) | Deterministic JSON with schema version | SHA-256 of canonical JSON |
| `bitnet prove-repo` | Git HEAD commit + folder Merkle root | Git log + `bitnet replay` |

---

## 3. BitNet → SLSA Level Mapping

| SLSA Requirement | BitNet Capability | Status |
|------------------|-------------------|--------|
| Build scripts are version controlled | `bitnet prove-repo` scans repo + records HEAD | Supported |
| Build service generates signed provenance | Receipt includes Merkle root + timestamp | Supported |
| Provenance is authenticated and tamper-evident | Canonical receipt with SHA-256 hash | Supported |
| Provenance includes build parameters | Receipt includes `files_seen`, `total_bytes`, `root` | Supported |
| Dependencies are pinned and verified | `bitnet replay` detects any file changes | Supported |
| Build environment is well-defined | `bitnet watch --continuous` monitors for drift | Supported |

**BitNet achieves SLSA Level 2** for artifact integrity and build provenance. Level 3 requires sandboxed builds and isolated build environments, which BitNet does not provide.

---

## 4. Trust Model

| Claim | Basis | Limitation |
|-------|-------|------------|
| Receipt is tamper-evident | SHA-256 of canonical JSON | Receipt file itself can be replaced; trust requires separate storage |
| Merkle root is deterministic | Sorted SHA-256 file hashes, byte-level tree construction | Same files in same order only |
| File integrity is verifiable | Per-file Merkle proofs in portable bundles | Original files must be available for re-hash |
| Git association is authentic | Git HEAD commit hash from `git rev-parse` | Git history can be rewritten with `--force` |
| Continuous monitoring detects changes | SQLite WAL + async watcher loop | Watcher must be running; offline gaps possible |

---

## 5. Evidence Formats

### Receipt (`bitnet-receipt-v1`)
```json
{
  "schema": "bitnet-receipt-v1",
  "root": "/path/to/folder",
  "merkle_root": "sha256:...",
  "files_seen": 247,
  "duplicate_groups": 2,
  "duplicate_files": 3,
  "total_bytes": 1843200,
  "scanned_at": "2024-06-15T14:32:11Z",
  "git_commit": "abc123...",
  "git_message": "feat: release v1.2.3"
}
```

### Portable Proof Bundle (`bitnet-proof-v1`)
```json
{
  "schema": "bitnet-proof-v1",
  "receipt": { ... },
  "receipt_hash": "sha256:...",
  "files": [
    {
      "rel_path": "src/main.py",
      "raw_hash": "sha256:...",
      "size_bytes": 472,
      "merkle_proof": [{"side": "right", "hash": "sha256:..."}]
    }
  ]
}
```

---

## 6. Operational Recommendations for Federal Use

1. **Store receipts separately** from the folders they describe (WORM storage, S3 Object Lock, offline)
2. **Sign receipts** with organization signing keys (future: `bitnet sign`)
3. **Publish to Rekor** for transparency-log inclusion (future: `bitnet attest --rekor`)
4. **Integrate with CI/CD** using `bitnet watch . --output receipt.json` in GitHub Actions
5. **Use `bitnet replay` in deployment pipelines** to verify artifacts before release
6. **Maintain control mapping** in OSCAL format for ATO packages (future: `bitnet export-oscal`)

---

## 7. What BitNet Is NOT

- Not a blockchain protocol
- Not a token system
- Not a marketplace
- Not a cloud storage service
- Not a backup tool
- Not a vulnerability scanner
- Not a replacement for formal code signing (PKI)

BitNet is a **local-first cryptographic provenance primitive**. It produces evidence. It does not enforce policy.

---

*This document is versioned with the codebase. For the current mapping, see the commit tagged with this document version.*
