"""Shared, read-only view of the repository that checks inspect."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

# Directories that are never part of the project's own source.
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", "dist", "build", "target", ".idea", ".vscode",
}


@dataclass
class RepoContext:
    root: Path
    _git_cache: dict = field(default_factory=dict, repr=False)

    @cached_property
    def is_git(self) -> bool:
        return self.git("rev-parse", "--is-inside-work-tree") == "true"

    @cached_property
    def is_shallow(self) -> bool:
        """True for a shallow clone (e.g. actions/checkout's default), where history is cut off."""
        return self.is_git and self.git("rev-parse", "--is-shallow-repository") == "true"

    @cached_property
    def current_branch(self) -> str | None:
        if not self.is_git:
            return None
        return self.git("branch", "--show-current") or None  # empty on a detached HEAD

    def git(self, *args: str) -> str | None:
        """Run a read-only git command in the repo. Returns stdout, or None on failure."""
        if args in self._git_cache:
            return self._git_cache[args]
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), *args],
                capture_output=True, text=True, timeout=60,
            )
            # rstrip only: leading spaces are meaningful (e.g. " M file" in git status).
            out = result.stdout.rstrip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            out = None
        self._git_cache[args] = out
        return out

    @cached_property
    def files(self) -> list[Path]:
        """Project files relative to the root: tracked files in a git repo, else a filtered walk."""
        if self.is_git:
            listing = self.git("ls-files", "-z")
            if listing is not None:
                return sorted(
                    Path(p) for p in listing.split("\0")
                    if p and (self.root / p).is_file()
                )
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                found.append((Path(dirpath) / name).relative_to(self.root))
        return sorted(found)

    def top_level(self, *names: str) -> Path | None:
        """Return the first top-level file whose name matches any of names (case-insensitive)."""
        wanted = {n.lower() for n in names}
        for entry in sorted(self.root.iterdir()):
            if entry.is_file() and (entry.name.lower() in wanted or entry.stem.lower() in wanted):
                return entry
        return None

    def read_text(self, rel: Path, limit: int = 1_000_000) -> str | None:
        """Read a text file, or None if it is binary, too large, or unreadable."""
        path = self.root / rel
        try:
            if path.stat().st_size > limit:
                return None
            data = path.read_bytes()
        except OSError:
            return None
        if b"\0" in data[:8192]:
            return None
        return data.decode("utf-8", errors="replace")
