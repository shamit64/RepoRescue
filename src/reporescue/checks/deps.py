"""Dependency manifest checks. Offline: they read files only."""

import re

from reporescue.checks import Status, check

# manifest -> lockfiles that pin it
MANIFESTS = {
    "package.json": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock"],
    "Pipfile": ["Pipfile.lock"],
    "Cargo.toml": ["Cargo.lock"],
    "Gemfile": ["Gemfile.lock"],
    "go.mod": ["go.sum"],
    "composer.json": ["composer.lock"],
}
PINNED_RE = re.compile(r"==|===|@ |\.whl$|\.tar\.gz$")


@check("deps.lockfile", "deps", "Lockfiles")
def lockfile(ctx):
    found = [m for m in MANIFESTS if (ctx.root / m).is_file()]
    if not found:
        return Status.SKIP, "No dependency manifest with a standard lockfile."
    missing = [m for m in found if not any((ctx.root / lock).is_file() for lock in MANIFESTS[m])]
    if missing:
        return Status.WARN, "Manifest(s) without a lockfile: " + ", ".join(missing)
    return Status.PASS, "Every manifest has a lockfile: " + ", ".join(found)


@check("deps.pinned", "deps", "Pinned Python requirements")
def pinned_requirements(ctx):
    req_files = [f for f in ctx.files if re.fullmatch(r"requirements.*\.txt", f.name)]
    if not req_files:
        return Status.SKIP, "No requirements*.txt files."
    unpinned = []
    for f in req_files:
        for lineno, raw in enumerate((ctx.read_text(f) or "").splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            if not PINNED_RE.search(line):
                unpinned.append(f"{f}:{lineno}: {line}")
    if unpinned:
        return Status.WARN, f"{len(unpinned)} unpinned requirement(s).", unpinned[:20]
    return Status.PASS, "All requirements are pinned."
