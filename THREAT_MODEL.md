# BitNet Threat Model

**Version:** 0.1.0  
**Scope:** BitNet local-first cryptographic provenance runtime

---

## 1. What BitNet Protects Against

| Threat | Protection | Limitation |
|--------|------------|------------|
| **Silent file modification** | Merkle root changes on any file alteration | Only detects changes at scan time; offline gaps possible |
| **Receipt forgery** | Canonical deterministic JSON with SHA-256 hash | Receipt file itself can be replaced; separate storage required |
| **Undetected tampering between scans** | Continuous watcher re-scans on interval | Watcher must be running; gap = blind spot |
| **Replay of old receipts** | Timestamps + Merkle root comparison | Clock can be manipulated locally |
| **Partial file corruption** | Per-file Merkle proofs in portable bundles | Original file must be available for re-hash |
| **Agent action denial** | Hash chain with previous_action_hash linkage | Chain file can be deleted entirely |
| **Supply-chain injection** | Folder scan at build time detects added files | Cannot detect malicious but valid files |
| **Bit-flip in transit** | SHA-256 per-file + Merkle root | Only for data under BitNet's scope |

## 2. What BitNet Does NOT Protect Against

| Threat | Why Not | What To Use Instead |
|--------|---------|---------------------|
| **Malicious file contents** | BitNet hashes, does not inspect | AV, static analysis, code review |
| **In-memory attacks** | BitNet scans filesystem, not RAM | EDR, kernel monitoring |
| **Network exfiltration** | No network monitoring | IDS, DLP, firewall logs |
| **Social engineering** | Technical primitive, not human control | Training, MFA, access controls |
| **Compromised signing keys** | BitNet does not manage PKI (yet) | HSM, key ceremony, Sigstore |
| **Quantum preimage attacks** | SHA-256 is not quantum-resistant | CRYSTALS-Dilithium, future hash migration |
| **Encrypted-but-tampered files** | Hash matches even if ciphertext is wrong | Authenticated encryption (AES-GCM) |
| **Deletion of the chain file** | Local file can be wiped | WORM storage, remote backup, Rekor publishing |
| **Symlink / path traversal** | BitNet follows filesystem semantics | Canonical path resolution, chroot |

## 3. Trust Boundaries

```
┌─────────────────────────────────────────┐
│  User Machine (BitNet runs here)        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Folder  │  │ SQLite  │  │ Chain   │ │
│  │ Files   │  │ Receipts│  │ JSONL   │ │
│  └────┬────┘  └────┬────┘  └────┬────┘ │
│       │            │            │       │
│       └────────────┴────────────┘       │
│                     │                   │
│              ┌──────▼──────┐            │
│              │ SHA-256     │            │
│              │ Merkle Root │            │
│              └──────┬──────┘            │
│                     │                   │
│       Optional: Solana memo tx          │
└─────────────────────────────────────────┘
                    │
              ┌─────▼─────┐
              │  Solana   │
              │  Devnet   │
              └───────────┘
```

- **Trusted:** BitNet process, filesystem, local SQLite, local chain file
- **Untrusted:** Network, remote storage, anyone with root on the machine
- **Optional trust anchor:** Solana devnet (external, append-only)

## 4. Attack Scenarios

### Scenario A: Attacker modifies a file between scans
- **Detection:** Next scan → Merkle root mismatch → `TAMPERED` status
- **Miss condition:** Watcher offline during modification and before next manual scan

### Scenario B: Attacker replaces receipt.json with an old one
- **Detection:** `bitnet replay` recomputes Merkle root and compares
- **Miss condition:** If the attacker also restores the old folder state, replay passes

### Scenario C: Attacker deletes the agent chain file
- **Detection:** Chain file absence is obvious; backups/WORM storage prevent this
- **Miss condition:** No backup + no Rekor publishing

### Scenario D: Attacker injects a file that passes policy
- **Detection:** File appears in scan; Merkle root changes (detected as change, not necessarily malicious)
- **Miss condition:** BitNet cannot distinguish benign from malicious additions

## 5. Assurance Level

BitNet provides **detection**, not prevention. It is a **forensic primitive**, not a security control.

For federal systems:
- Use BitNet as **evidence generation** (NIST AU-6, SI-7)
- Pair with **prevention controls** (CM-3, CM-5) for change management
- Publish receipts to **Rekor** for external tamper evidence
- Store receipts on **WORM media** for legal admissibility

## 6. Open Questions

1. Should BitNet support authenticated encryption for receipt files?
2. Should chain entries be signed with Ed25519 before anchoring?
3. What is the migration path when SHA-256 is no longer sufficient?
4. Should BitNet support remote attestation (TPM/TEE integration)?

*Track progress on these questions in GitHub issues.*
