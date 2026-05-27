"""Tests for Git integration."""

import tempfile
from pathlib import Path

from bitnet.git import (
    get_git_root,
    get_head_commit,
    get_head_message,
    install_hook,
    uninstall_hook,
    GIT_HOOK_TEMPLATE,
)


def test_get_git_root_finds_repo():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        found = get_git_root(root)
        assert found == root


def test_get_git_root_none_outside():
    with tempfile.TemporaryDirectory() as td:
        found = get_git_root(Path(td))
        assert found is None


def test_install_and_uninstall_hook():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git" / "hooks").mkdir(parents=True)
        hook_path = install_hook(root)
        assert hook_path is not None
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "bitnet" in content

        # Idempotent
        hook_path2 = install_hook(root)
        assert hook_path2 == hook_path
        assert hook_path.read_text().count("bitnet") == 1

        assert uninstall_hook(root) is True
        content_after = hook_path.read_text()
        assert "bitnet" not in content_after

        assert uninstall_hook(root) is True  # hook exists, just no bitnet lines
