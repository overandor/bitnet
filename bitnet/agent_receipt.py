"""Proof-of-Agent-Action: cryptographic receipt chain for material agent actions.

Every material action produces a signed local receipt and an optional
blockchain timestamp. On-chain stores only the hash. Receipts contain
the actual data and are kept local.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from bitnet.receipt import canonical_json, canonical_timestamp

AGENT_ACTION_SCHEMA = "bitnet-agent-action-v1"

# Material actions that should be anchored under normal policy.
MATERIAL_ACTIONS: Set[str] = {
    "file_edit",
    "commit",
    "test_run",
    "secret_scan",
    "sbom_generation",
    "receipt_creation",
    "deployment",
    "github_push",
    "github_pr",
    "verification_failure",
    "scan",
    "verify",
    "watch",
    "replay",
    "export_proof",
    "import",
    "provision",
    "deprovision",
    "policy_change",
}

# Actions that are never anchored — too noisy, too low-value.
NON_MATERIAL_ACTIONS: Set[str] = {
    "token_generated",
    "log_line",
    "retry",
    "ui_click",
    "heartbeat",
    "ping",
    "tooltip",
    "autocomplete",
    "suggestion",
    "idle",
}


def _make_action_id() -> str:
    """Generate a short, unique action identifier."""
    return f"act_{uuid.uuid4().hex[:16]}"


def make_agent_receipt(
    action_type: str,
    agent_id: str,
    workspace_hash: str = "",
    input_hash: str = "",
    output_hash: str = "",
    tool_used: str = "",
    files_touched: Optional[List[str]] = None,
    previous_action_hash: str = "",
    merkle_root: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an Agent Action Receipt.

    Args:
        action_type: One of MATERIAL_ACTIONS or a custom string.
        agent_id: Identifier for the agent producing the action.
        workspace_hash: SHA-256 hash of the workspace state (optional).
        input_hash: SHA-256 hash of inputs (optional).
        output_hash: SHA-256 hash of outputs (optional).
        tool_used: Tool or sub-system that performed the action.
        files_touched: List of relative paths affected (optional).
        previous_action_hash: SHA-256 of the previous action in the chain.
        merkle_root: Merkle root if a folder snapshot was involved.
        metadata: Arbitrary extra fields (not validated, but canonicalized).
    """
    receipt: Dict[str, Any] = {
        "schema": AGENT_ACTION_SCHEMA,
        "action_id": _make_action_id(),
        "agent_id": agent_id,
        "action_type": action_type,
        "timestamp": canonical_timestamp(),
        "workspace_hash": workspace_hash,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "tool_used": tool_used,
        "files_touched": files_touched or [],
        "previous_action_hash": previous_action_hash,
        "merkle_root": merkle_root,
    }
    if metadata:
        receipt["metadata"] = metadata
    return receipt


def agent_receipt_hash(receipt: Dict[str, Any], previous_chain_hash: str = "") -> str:
    """Compute the canonical hash of an agent action receipt.

    If previous_chain_hash is provided, the result is:
        sha256(canonical_json(receipt) + previous_chain_hash)

    This forms a hash chain where each action commits to its predecessor,
    making silent rewrites detectable.
    """
    payload = canonical_json(receipt)
    if previous_chain_hash:
        payload = payload + previous_chain_hash
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_agent_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an agent action receipt format."""
    report = {"valid": True, "errors": []}

    if not isinstance(receipt, dict):
        report["valid"] = False
        report["errors"].append("Receipt must be a JSON object")
        return report

    required = {
        "schema",
        "action_id",
        "agent_id",
        "action_type",
        "timestamp",
        "workspace_hash",
        "input_hash",
        "output_hash",
        "tool_used",
        "files_touched",
        "previous_action_hash",
        "merkle_root",
    }
    missing = required - set(receipt.keys())
    if missing:
        report["valid"] = False
        report["errors"].append(f"Missing fields: {sorted(missing)}")

    if receipt.get("schema") != AGENT_ACTION_SCHEMA:
        report["errors"].append(
            f"Unknown schema: {receipt.get('schema')} (expected {AGENT_ACTION_SCHEMA})"
        )

    at = receipt.get("action_type", "")
    if not at or not isinstance(at, str):
        report["valid"] = False
        report["errors"].append("action_type must be a non-empty string")

    ft = receipt.get("files_touched")
    if not isinstance(ft, list):
        report["valid"] = False
        report["errors"].append("files_touched must be a list")

    report["receipt_hash"] = agent_receipt_hash(receipt)
    return report


def is_material_action(action_type: str, policy: Optional[Set[str]] = None) -> bool:
    """Return True if the action type should be anchored under the policy.

    Args:
        action_type: The action type string to check.
        policy: Override set of material actions. Defaults to MATERIAL_ACTIONS.
    """
    if action_type in NON_MATERIAL_ACTIONS:
        return False
    if policy is None:
        policy = MATERIAL_ACTIONS
    return action_type in policy


class AgentChain:
    """Hash chain of agent actions with persistence."""

    def __init__(self, chain_path: Optional[Path] = None):
        self.chain_path = chain_path or (Path.home() / ".bitnet" / "agent_chain.jsonl")
        self.chain_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Read the last entry to recover the chain head."""
        if not self.chain_path.exists():
            return ""
        lines = self.chain_path.read_text().strip().splitlines()
        if not lines:
            return ""
        try:
            last = json.loads(lines[-1])
            return last.get("chain_hash", "")
        except Exception:
            return ""

    @property
    def last_hash(self) -> str:
        return self._last_hash

    def append(
        self,
        action_type: str,
        agent_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a receipt, compute its chain hash, and append to the log."""
        receipt = make_agent_receipt(
            action_type=action_type,
            agent_id=agent_id,
            previous_action_hash=self._last_hash,
            **kwargs,
        )
        chain_hash = agent_receipt_hash(receipt, self._last_hash)
        entry = {
            "receipt": receipt,
            "chain_hash": chain_hash,
            "anchored": False,
        }
        with self.chain_path.open("a") as f:
            f.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
        self._last_hash = chain_hash
        return entry

    def verify_chain(self) -> Dict[str, Any]:
        """Verify the integrity of the entire chain."""
        if not self.chain_path.exists():
            return {"valid": True, "length": 0, "errors": []}

        errors = []
        prev_hash = ""
        count = 0

        with self.chain_path.open("r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: invalid JSON — {e}")
                    continue

                receipt = entry.get("receipt", {})
                stored_chain = entry.get("chain_hash", "")
                expected = agent_receipt_hash(receipt, prev_hash)
                if stored_chain != expected:
                    errors.append(
                        f"Line {line_num}: chain hash mismatch (stored={stored_chain[:16]}..., expected={expected[:16]}...)"
                    )

                prev_hash = stored_chain
                count += 1

        return {
            "valid": len(errors) == 0,
            "length": count,
            "errors": errors,
        }

    def entries(self) -> List[Dict[str, Any]]:
        """Yield all entries in the chain."""
        if not self.chain_path.exists():
            return []
        results = []
        with self.chain_path.open("r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return results
