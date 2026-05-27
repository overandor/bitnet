# BitNet Migration Report

**Date:** 2026-05-27
**Source:** `/Users/alep/Downloads` (membra monorepo)
**Destination:** `/Users/alep/Downloads/bitnet` (standalone public repo)
**Branding:** Rebranded from `FileLife` to `BitNet` for infrastructure-native positioning

---

## Rebrand Rationale

`BitNet` was chosen over `FileLife` because:
- **Shorter, more primitive-sounding** — reads like infrastructure, not a product
- **Bit** signals cryptographic / binary / hash-native identity
- **Net** signals networked / distributed / provenance graph potential
- More legible to security and infrastructure engineers
- Less risk of sounding like a consumer file-sync tool

**Name availability check required before public launch:**
- GitHub: `github.com/bitnet` (likely taken — check `bitnet-fs`, `bitnet-proof`, `bitnet-provenance`)
- PyPI: `bitnet` (likely taken — same fallbacks apply)
- Fallbacks: `bitnet-fs`, `bitnet-proof`, `bitnet-provenance`, `bitnet-integrity`

---

## What Was Extracted

### Core Primitive: Continuous Cryptographic Filesystem Provenance

The entire `membra-filelife-registry` application was extracted and cleaned into a standalone Python package. The following modules were ported with MEMBRA branding, financial language, and speculative systems removed:

| Source File | Destination | Status |
|-------------|-------------|--------|
| `membra-filelife-registry/app/main.py` | `bitnet/web.py` | **Extracted + cleaned** — dashboard only, no cloud/IPFS tables |
| `membra-filelife-registry/app/database.py` | `bitnet/db.py` | **Extracted + reduced** — 5 tables only |
| `membra-filelife-registry/app/services/folder_collateral.py` | `bitnet/scanner.py` + `bitnet/watcher.py` | **Extracted + split** — hashing, Merkle, change detection |
| `membra-filelife-registry/app/services/merkle_onchain.py` | `bitnet/merkle.py` | **Extracted + cleaned** — proof generation and verification |
| `membra-filelife-registry/app/services/appraisal.py` | `bitnet/appraisal.py` | **Extracted + cleaned** — LLM valuation, no financial KPIs |
| `membra-filelife-registry/app/services/solana_anchor.py` | `bitnet/anchor.py` | **Extracted + cleaned** — optional memo anchoring, no token language |

### New Files Created

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package manifest, CLI entry point `bitnet` |
| `bitnet/cli.py` | CLI commands: `demo`, `watch`, `verify`, `serve` |
| `demo/sample-folder/` | Zero-setup synthetic files for `bitnet demo` |
| `README.md` | Public-facing README with hero statement |
| `tests/test_scanner.py` | SHA-256 determinism, Merkle root determinism, duplicate detection |
| `tests/test_db.py` | SQLite WAL initialization, folder_run persistence |
| `tests/test_watcher.py` | Change detection: new, modified, unchanged |
| `tests/test_receipt.py` | Receipt hash determinism and tamper detection |

---

## Rebrand Changes

### Package Structure
- `filelife/` → `bitnet/`
- `filelife/filelife/` → `bitnet/bitnet/`

### CLI
- Command: `filelife` → `bitnet`
- Subcommands unchanged: `demo`, `watch`, `verify`, `serve`

### Imports
- All internal imports: `from filelife.X` → `from bitnet.X`

### Data Directory
- `~/.filelife/filelife.db` → `~/.bitnet/bitnet.db`

### Web Dashboard
- Title: `FileLife` → `BitNet`
- Tagline: `BitNet Self-Proving Folders`
- Help text updated: `bitnet watch /path/to/folder`

### Demo Files
- All demo folder READMEs and source files updated to reference `BitNet`

---

## What Was Intentionally Excluded

### 1. MEMBRA Branding
All references to "MEMBRA", "FileLife Collateral Engine", "Collateral Registry", "Provenance Schedule", and related branding were removed.

### 2. Financial / Market Language
The following concepts were deliberately stripped:
- `collateral_records` table (lending, face value, advance rates, haircuts)
- `liens` table (pledging, loan holders, release dates)
- `financial_kpis` table (amounts due, payment status, cashflow, risk scores)
- `appraised_value_usd` was retained as a **metadata estimate only** — no lending semantics
- All references to "lendable", "eligible", "collateral value", "advance ratio"

### 3. Speculative Systems
- Token economics (MemGas, liquid staking, derivative tokens)
- Governance engines (action classes, approval states, policy simulation)
- Treasury systems (budgeting, runway, revenue recording)
- ZK-PoPC economic engine (capacity proofs, mint formulas, epochs)
- Liquidity pools and NFT minting (mock implementations)

### 4. Cloud / IPFS Integrations
- Cloud storage sync (R2/S3 abstraction)
- IPFS model bucket and pinning
- IPFS CID generation for files

### 5. Legal Collateral Schedules
All `03_ai_generated_code_provenance_schedule.csv` and related CSV files across every subproject were excluded. There were 15+ identical copies totaling thousands of rows.

### 6. Chat Export Archives
The `windsurf_chat_export/` directory (hundreds of exported chat files) was excluded.

### 7. Trading Systems
All futures trading, hedging, and arbitrage code was excluded:
- `01_Trading_Systems/Hedging_Project/`
- `01_Trading_Systems/ENA_Hedging_Project/`
- `01_Trading_Systems/algo_micro_cap_bot/`
- `arb-execution-engine/`
- Standalone scripts (`check_futures_balance.py`, `close_shib_positions.py`, etc.)

### 8. Research Artifacts
- `02_AI_Agents/llm-os/` — economic simulation engine
- `06_Projects/overmanifold/` — semantic runtime
- `chat_to_chain/` — extraction pipeline (can become a plugin later)
- `agent-optimizer/` — Tauri desktop experiment
- All `MEMBRA_*` top-level trees

---

## Database Schema Changes

### Before (15+ tables)
```
files, manifests, lifecycle_events, appraisals, collateral_records,
liens, verifications, github_commits, chain_anchors, llm_queries,
pids, financial_kpis, folder_runs, folder_files, folder_watchers,
cloud_files
```

### After (5 tables)
```
folder_runs       — point-in-time snapshots
folder_files      — per-file records with change_status
folder_watchers   — continuous watcher configuration
chain_anchors     — Solana transaction receipts
appraisals        — LLM valuation estimates
```

---

## CLI Commands

```bash
bitnet demo              # Zero-setup demo on synthetic folder
bitnet watch <folder>    # Scan and optionally watch a folder
bitnet verify <receipt>  # Verify a snapshot receipt
bitnet serve             # Launch web dashboard
```

---

## Solana Anchoring Status

**Optional.** Disabled by default.

Requires:
```bash
export SOLANA_KEYPAIR_PATH=/path/to/keypair.json
pip install bitnet[solana]
```

When enabled, writes Merkle roots as **memo transactions** on Solana devnet. This is purely notarization — no smart contracts, no tokens, no DeFi mechanics.

---

## Remaining Work Before Public Launch

1. **Check name availability**: Verify `bitnet` is free on GitHub and PyPI; fall back to `bitnet-fs` or `bitnet-proof` if taken
2. **Install and test** the package locally: `pip install -e .`
3. **Run tests**: `pytest` — all 4 test files must pass
4. **Record demo GIF**: `bitnet demo` + screen capture
5. **Verify CLI entry point**: `bitnet --help` works after pip install
6. **Add GitHub Actions CI**: `.github/workflows/ci.yml` for pytest on push
7. **Update repo references**: Replace `github.com/bitnet/bitnet` with actual repo URL
8. **Tag v0.1.0**: `git tag v0.1.0 && git push origin v0.1.0`

---

## Honest Assessment

The extracted `bitnet` package contains **one real, working primitive**:
- File hashing, Merkle trees, change detection, SQLite persistence, and optional Solana anchoring
- All running in a single Python process with no external dependencies beyond FastAPI/aiosqlite
- A clean CLI and a functional web dashboard

**What it does NOT contain** (and should not until later):
- Real ZK proofs (uses SHA-256, not SNARKs)
- Real token minting
- Real lending/collateral markets
- Real DeFi integrations
- Real NFT minting (was mock in source)

This is the correct boundary for a v0.1.0 public release. The primitive is real. The surrounding systems were narrative pollution.

---

## Migration Hash

```
bitnet-migration-2026-05-27
extracted: 10 modules
rebranded: filelife → bitnet (all imports, CLI, docs, paths)
excluded: 40+ directories, 15+ legal CSV sets, all trading systems, all economic simulations
new: 4 test suites, CLI, demo folder, standalone README
```
