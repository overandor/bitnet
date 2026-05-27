"""Git integration — prove repo state, install hooks."""

from __future__ import annotations

import subprocess
from pathlib import Path


GIT_HOOK_TEMPLATE = '''#!/bin/sh
# BitNet pre-commit hook — generate cryptographic receipt
python -m bitnet.cli prove-repo --quiet || true
'''


def get_git_root(path: Path | None = None) -> Path | None:
    """Find the nearest .git directory."""
    start = path or Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def get_head_commit() -> str | None:
    """Return current HEAD commit hash, or None if not in a repo."""
    root = get_git_root()
    if not root:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_head_message() -> str | None:
    """Return current HEAD commit message subject."""
    root = get_git_root()
    if not root:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def install_hook(repo_path: Path | None = None) -> Path | None:
    """Install the BitNet pre-commit hook."""
    root = repo_path or get_git_root()
    if not root:
        return None
    hook_path = root / ".git" / "hooks" / "pre-commit"
    existing = hook_path.read_text() if hook_path.exists() else ""
    if "bitnet" in existing:
        return hook_path  # already installed
    with hook_path.open("a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(GIT_HOOK_TEMPLATE)
    hook_path.chmod(0o755)
    return hook_path


def uninstall_hook(repo_path: Path | None = None) -> bool:
    """Remove the BitNet pre-commit hook lines."""
    root = repo_path or get_git_root()
    if not root:
        return False
    hook_path = root / ".git" / "hooks" / "pre-commit"
    if not hook_path.exists():
        return False
    content = hook_path.read_text()
    lines = [ln for ln in content.splitlines() if "bitnet" not in ln]
    hook_path.write_text("\n".join(lines) + "\n")
    return True
