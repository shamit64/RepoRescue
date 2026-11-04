"""Checks over the project's files."""

import re

from reporescue.checks import Status, check

LARGE_FILE_BYTES = 5 * 1024 * 1024
TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "__tests__"}
TEST_FILE_RE = re.compile(r"(^test_.*|.*_test\.\w+$|.*\.(test|spec)\.\w+$)")

SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Hard-coded credential": re.compile(
        r"""(?i)\b(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*["'][^"'\s]{12,}["']"""
    ),
}
SECRET_FILE_NAMES = {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}


@check("code.tests", "code", "Tests present")
def tests_present(ctx):
    test_files = [
        f for f in ctx.files
        if any(part.lower() in TEST_DIR_NAMES for part in f.parts[:-1]) or TEST_FILE_RE.match(f.name)
    ]
    if not test_files:
        return Status.FAIL, "No test files found."
    return Status.PASS, f"{len(test_files)} test file(s) found."


@check("code.todos", "code", "TODO / FIXME markers")
def todos(ctx):
    hits = []
    for f in ctx.files:
        text = ctx.read_text(f)
        if not text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if TODO_RE.search(line):
                hits.append(f"{f}:{lineno}")
    if len(hits) > 50:
        return Status.WARN, f"{len(hits)} TODO/FIXME markers.", hits[:20]
    return Status.PASS, f"{len(hits)} TODO/FIXME marker(s).", hits[:20]


@check("code.large_files", "code", "Large files")
def large_files(ctx):
    big = []
    for f in ctx.files:
        try:
            size = (ctx.root / f).stat().st_size
        except OSError:
            continue
        if size > LARGE_FILE_BYTES:
            big.append(f"{f} ({size / 1024 / 1024:.1f} MB)")
    if big:
        return Status.WARN, f"{len(big)} file(s) over {LARGE_FILE_BYTES // 1024 // 1024} MB.", big
    return Status.PASS, "No oversized files."


@check("code.secrets", "code", "Committed secrets")
def secrets(ctx):
    hits = []
    for f in ctx.files:
        if f.name.lower() in SECRET_FILE_NAMES:
            hits.append(f"{f}: sensitive file name")
            continue
        text = ctx.read_text(f)
        if not text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    hits.append(f"{f}:{lineno}: {label}")
                    break
    if hits:
        return Status.FAIL, f"{len(hits)} possible secret(s) in the repository.", hits[:20]
    return Status.PASS, "No likely secrets found."
