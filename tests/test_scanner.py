"""Tests for scanner and Merkle tree operations."""

import tempfile
from pathlib import Path

from bitnet.scanner import FolderSnapshot, sha256_file, merkle_root
from bitnet.merkle import generate_merkle_proof, verify_merkle_proof


class TestSha256File:
    def test_hashes_deterministically(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello world\n")
            path = Path(f.name)
        h1 = sha256_file(path)
        h2 = sha256_file(path)
        assert h1 == h2
        assert h1.startswith("sha256:")
        path.unlink()

    def test_different_content_different_hash(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content A")
            path_a = Path(f.name)
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content B")
            path_b = Path(f.name)
        assert sha256_file(path_a) != sha256_file(path_b)
        path_a.unlink()
        path_b.unlink()


class TestMerkleRoot:
    def test_empty_list(self):
        root = merkle_root([])
        assert root.startswith("sha256:")

    def test_single_hash(self):
        root = merkle_root(["sha256:" + "ab" * 32])
        assert root.startswith("sha256:")

    def test_deterministic(self):
        hashes = [f"sha256:{i:064x}" for i in range(4)]
        r1 = merkle_root(hashes)
        r2 = merkle_root(hashes)
        assert r1 == r2

    def test_order_independent_for_given_leaf_set(self):
        r1 = merkle_root(["sha256:" + "aa" * 32, "sha256:" + "bb" * 32])
        r2 = merkle_root(["sha256:" + "bb" * 32, "sha256:" + "aa" * 32])
        assert r1 == r2


class TestFolderSnapshot:
    def test_scans_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("print(1)\n")
            (root / "b.py").write_text("print(2)\n")
            snap = FolderSnapshot(root, max_files=50).scan()
            assert len(snap.files) == 2
            assert snap.merkle_root.startswith("sha256:")
            assert snap.total_bytes > 0
            assert all("leaf_hash" in f for f in snap.files)

    def test_detects_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            content = "same content\n"
            (root / "original.txt").write_text(content)
            (root / "backup").mkdir()
            (root / "backup" / "copy.txt").write_text(content)
            snap = FolderSnapshot(root, max_files=50).scan()
            assert snap.duplicate_files == 1
            assert snap.duplicate_groups == 1

    def test_skips_ignored_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real.py").write_text("x = 1\n")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "cached.pyc").write_text("cached")
            snap = FolderSnapshot(root, max_files=50).scan()
            assert len(snap.files) == 1
            assert snap.files[0]["rel_path"] == "real.py"

    def test_path_change_changes_merkle_root_even_when_content_same(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("same bytes\n")
            before = FolderSnapshot(root, max_files=50).scan()
            (root / "b.txt").write_text((root / "a.txt").read_text())
            (root / "a.txt").unlink()
            after = FolderSnapshot(root, max_files=50).scan()
            assert before.files[0]["raw_hash"] == after.files[0]["raw_hash"]
            assert before.files[0]["leaf_hash"] != after.files[0]["leaf_hash"]
            assert before.merkle_root != after.merkle_root


class TestMerkleProof:
    def test_proof_verifies(self):
        hashes = [f"sha256:{i:064x}" for i in range(8)]
        root = merkle_root(hashes)
        target = hashes[3]
        proof = generate_merkle_proof(target, hashes)
        assert verify_merkle_proof(root, proof, target)

    def test_tampered_proof_fails(self):
        hashes = [f"sha256:{i:064x}" for i in range(8)]
        root = merkle_root(hashes)
        target = hashes[3]
        proof = generate_merkle_proof(target, hashes)
        if proof:
            proof[0]["hash"] = "sha256:" + "0" * 64
        assert not verify_merkle_proof(root, proof, target)

    def test_missing_hash_returns_empty(self):
        proof = generate_merkle_proof("sha256:missing", ["sha256:a", "sha256:b"])
        assert proof == []
