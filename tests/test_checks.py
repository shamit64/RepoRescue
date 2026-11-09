import os
import subprocess
import time
from pathlib import Path

import pytest

from reporescue.checks import Status, all_checks, run_all
from reporescue.context import RepoContext


def results_by_id(root: Path):
    return {r.check_id: r for r in run_all(RepoContext(root))}


def git(root: Path, *args: str, env=None):
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        env={**os.environ, **(env or {})},
    )


def make_repo(root: Path, files: dict[str, str], author="a@example.com", when=None):
    git(root, "init", "-q", "-b", "main")
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(root, "add", "-A")
    env = {
        "GIT_AUTHOR_NAME": "A", "GIT_AUTHOR_EMAIL": author,
        "GIT_COMMITTER_NAME": "A", "GIT_COMMITTER_EMAIL": author,
    }
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{int(when)} +0000"
    git(root, "commit", "-q", "-m", "init", env=env)


def test_check_ids_are_unique():
    ids = [c.check_id for c in all_checks()]
    assert len(ids) == len(set(ids))


def test_empty_directory(tmp_path):
    r = results_by_id(tmp_path)
    assert r["docs.readme"].status is Status.FAIL
    assert r["docs.license"].status is Status.FAIL
    assert r["code.tests"].status is Status.FAIL
    assert r["git.activity"].status is Status.SKIP
    assert r["deps.lockfile"].status is Status.SKIP


def test_healthy_repo(tmp_path):
    make_repo(tmp_path, {
        "README.md": "word " * 60,
        "LICENSE": "MIT",
        ".gitignore": "*.pyc\n",
        "CONTRIBUTING.md": "be nice",
        "tests/test_x.py": "def test(): pass\n",
        "requirements.txt": "requests==2.32.3\n# comment\n-e .\n",
    })
    r = results_by_id(tmp_path)
    for check_id in ("docs.readme", "docs.license", "docs.gitignore", "docs.contributing",
                     "code.tests", "code.secrets", "git.activity", "git.uncommitted",
                     "deps.pinned"):
        assert r[check_id].status is Status.PASS, (check_id, r[check_id].message)
    assert r["git.bus_factor"].status is Status.WARN  # single author


def test_short_readme_warns(tmp_path):
    (tmp_path / "README.md").write_text("tiny")
    assert results_by_id(tmp_path)["docs.readme"].status is Status.WARN


def test_secrets_detected(tmp_path):
    fake_key = "AKIA" + "ABCDEFGHIJKLMNOP"
    (tmp_path / "config.py").write_text(f'AWS = "{fake_key}"\n')
    (tmp_path / ".env").write_text("X=1\n")
    r = results_by_id(tmp_path)["code.secrets"]
    assert r.status is Status.FAIL
    assert any("config.py:1" in d for d in r.details)
    assert any(".env" in d for d in r.details)


def test_binary_files_are_ignored(tmp_path):
    (tmp_path / "blob.bin").write_bytes(b"\0AKIAABCDEFGHIJKLMNOP")
    assert results_by_id(tmp_path)["code.secrets"].status is Status.PASS


def test_todo_count(tmp_path):
    (tmp_path / "a.py").write_text("# TODO one\n# FIXME two\nx = 1\n")
    r = results_by_id(tmp_path)["code.todos"]
    assert r.status is Status.PASS
    assert r.details == ["a.py:1", "a.py:2"]


def test_skip_dirs_not_walked(tmp_path):
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "test_x.js").write_text("")
    assert results_by_id(tmp_path)["code.tests"].status is Status.FAIL


def test_unpinned_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\nflask>=2\nclick==8.1.7\n")
    r = results_by_id(tmp_path)["deps.pinned"]
    assert r.status is Status.WARN
    assert len(r.details) == 2


def test_missing_lockfile(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert results_by_id(tmp_path)["deps.lockfile"].status is Status.WARN
    (tmp_path / "package-lock.json").write_text("{}")
    assert results_by_id(tmp_path)["deps.lockfile"].status is Status.PASS


def test_old_repo_and_stale_branch(tmp_path):
    make_repo(tmp_path, {"README.md": "x"}, when=time.time() - 400 * 86_400)
    git(tmp_path, "branch", "old-feature")
    r = results_by_id(tmp_path)
    assert r["git.activity"].status is Status.FAIL
    assert r["git.stale_branches"].status is Status.WARN
    # The checked-out branch is judged by git.activity, so only the other branch is listed.
    assert r["git.stale_branches"].details == ["old-feature"]


def test_current_branch_alone_is_not_stale(tmp_path):
    make_repo(tmp_path, {"README.md": "x"}, when=time.time() - 400 * 86_400)
    assert results_by_id(tmp_path)["git.stale_branches"].status is Status.PASS


def test_shallow_clone_skips_bus_factor(tmp_path):
    source, clone = tmp_path / "source", tmp_path / "clone"
    source.mkdir()
    make_repo(source, {"README.md": "x"})
    (source / "b.txt").write_text("b")
    git(source, "add", "-A")
    git(source, "commit", "-q", "-m", "second", env={
        "GIT_AUTHOR_NAME": "B", "GIT_AUTHOR_EMAIL": "b@example.com",
        "GIT_COMMITTER_NAME": "B", "GIT_COMMITTER_EMAIL": "b@example.com",
    })
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", source.resolve().as_uri(), str(clone)],
        check=True, capture_output=True,
    )
    r = results_by_id(clone)
    assert r["git.bus_factor"].status is Status.SKIP
    assert "Shallow clone" in r["git.bus_factor"].message
    assert r["git.activity"].status is Status.PASS  # the tip commit is still there


def test_uncommitted_details_keep_status_columns(tmp_path):
    make_repo(tmp_path, {"README.md": "x"})
    (tmp_path / "README.md").write_text("changed")
    r = results_by_id(tmp_path)["git.uncommitted"]
    assert r.details == [" M README.md"]


def test_npmrc_can_opt_out_of_lockfile(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / ".npmrc").write_text("ignore-scripts=true\npackage-lock = false\n")
    r = results_by_id(tmp_path)["deps.lockfile"]
    assert r.status is Status.PASS
    assert "intentionally disabled" in r.message
    (tmp_path / ".npmrc").write_text("package-lock=true\n")
    assert results_by_id(tmp_path)["deps.lockfile"].status is Status.WARN


def test_uncommitted_changes(tmp_path):
    make_repo(tmp_path, {"README.md": "x"})
    (tmp_path / "new.txt").write_text("y")
    assert results_by_id(tmp_path)["git.uncommitted"].status is Status.WARN


def test_broken_check_is_skipped(monkeypatch, tmp_path):
    from reporescue import checks

    def boom(ctx):
        raise RuntimeError("nope")

    monkeypatch.setattr(checks, "REGISTRY", [checks.Check("x.boom", "x", "Boom", boom)])
    monkeypatch.setattr(checks, "all_checks", lambda: list(checks.REGISTRY))
    [result] = checks.run_all(RepoContext(tmp_path))
    assert result.status is Status.SKIP
    assert "nope" in result.message
