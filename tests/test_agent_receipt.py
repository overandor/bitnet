"""Tests for Proof-of-Agent-Action receipt chain."""

import json
import tempfile
from pathlib import Path

from bitnet.agent_receipt import (
    AgentChain,
    make_agent_receipt,
    agent_receipt_hash,
    verify_agent_receipt,
    is_material_action,
    MATERIAL_ACTIONS,
    NON_MATERIAL_ACTIONS,
)


def test_make_agent_receipt():
    r = make_agent_receipt(
        action_type="commit",
        agent_id="test-agent",
        workspace_hash="sha256:abc123",
        tool_used="git",
        files_touched=["src/main.py"],
    )
    assert r["schema"] == "bitnet-agent-action-v1"
    assert r["action_type"] == "commit"
    assert r["agent_id"] == "test-agent"
    assert r["workspace_hash"] == "sha256:abc123"
    assert r["tool_used"] == "git"
    assert r["files_touched"] == ["src/main.py"]
    assert r["action_id"].startswith("act_")
    assert "timestamp" in r


def test_verify_agent_receipt_valid():
    r = make_agent_receipt(action_type="scan", agent_id="a1")
    report = verify_agent_receipt(r)
    assert report["valid"] is True
    assert not report["errors"]
    assert "receipt_hash" in report


def test_verify_agent_receipt_missing_fields():
    r = make_agent_receipt(action_type="scan", agent_id="a1")
    del r["workspace_hash"]
    report = verify_agent_receipt(r)
    assert report["valid"] is False
    assert any("Missing fields" in e for e in report["errors"])


def test_agent_receipt_hash_determinism():
    r = make_agent_receipt(action_type="test_run", agent_id="a1")
    h1 = agent_receipt_hash(r)
    h2 = agent_receipt_hash(r)
    assert h1 == h2
    assert len(h1) == 64


def test_agent_receipt_hash_chain():
    r = make_agent_receipt(action_type="scan", agent_id="a1")
    h_no_prev = agent_receipt_hash(r)
    h_with_prev = agent_receipt_hash(r, "sha256:prev123")
    assert h_no_prev != h_with_prev


def test_is_material_action():
    assert is_material_action("commit") is True
    assert is_material_action("file_edit") is True
    assert is_material_action("token_generated") is False
    assert is_material_action("heartbeat") is False
    assert is_material_action("unknown_custom") is False


def test_agent_chain_append_and_verify():
    with tempfile.TemporaryDirectory() as td:
        chain_path = Path(td) / "chain.jsonl"
        chain = AgentChain(chain_path)

        e1 = chain.append(action_type="scan", agent_id="agent-1")
        assert "receipt" in e1
        assert "chain_hash" in e1
        assert e1["chain_hash"] != ""

        e2 = chain.append(action_type="commit", agent_id="agent-1")
        assert e2["receipt"]["previous_action_hash"] == e1["chain_hash"]

        report = chain.verify_chain()
        assert report["valid"] is True
        assert report["length"] == 2
        assert not report["errors"]


def test_agent_chain_tamper_detection():
    with tempfile.TemporaryDirectory() as td:
        chain_path = Path(td) / "chain.jsonl"
        chain = AgentChain(chain_path)
        chain.append(action_type="scan", agent_id="a1")
        chain.append(action_type="commit", agent_id="a1")

        # Tamper with the file
        lines = chain_path.read_text().strip().splitlines()
        entry = json.loads(lines[0])
        entry["receipt"]["action_type"] = "tampered"
        lines[0] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        chain_path.write_text("\n".join(lines) + "\n")

        report = chain.verify_chain()
        assert report["valid"] is False
        assert len(report["errors"]) > 0
        assert "chain hash mismatch" in report["errors"][0]


def test_agent_chain_entries():
    with tempfile.TemporaryDirectory() as td:
        chain_path = Path(td) / "chain.jsonl"
        chain = AgentChain(chain_path)
        chain.append(action_type="scan", agent_id="a1")
        entries = chain.entries()
        assert len(entries) == 1
        assert entries[0]["receipt"]["action_type"] == "scan"


def test_agent_chain_empty():
    with tempfile.TemporaryDirectory() as td:
        chain_path = Path(td) / "chain.jsonl"
        chain = AgentChain(chain_path)
        report = chain.verify_chain()
        assert report["valid"] is True
        assert report["length"] == 0
