"""Checks based on git history. All skip when the target is not a git repository."""

import time
from collections import Counter

from reporescue.checks import Status, check

DAY = 86_400
STALE_BRANCH_DAYS = 90


@check("git.activity", "git", "Recent activity")
def activity(ctx):
    if not ctx.is_git:
        return Status.SKIP, "Not a git repository."
    ts = ctx.git("log", "-1", "--format=%ct")
    if not ts:
        return Status.WARN, "Repository has no commits."
    days = int((time.time() - int(ts)) // DAY)
    if days > 365:
        return Status.FAIL, f"Last commit was {days} days ago."
    if days > 90:
        return Status.WARN, f"Last commit was {days} days ago."
    return Status.PASS, f"Last commit was {days} day(s) ago."


@check("git.bus_factor", "git", "Bus factor")
def bus_factor(ctx):
    if not ctx.is_git:
        return Status.SKIP, "Not a git repository."
    log = ctx.git("log", "--since=12.months", "--format=%aE")
    authors = Counter(line.lower() for line in (log or "").splitlines() if line)
    total = sum(authors.values())
    if total == 0:
        return Status.SKIP, "No commits in the last 12 months."
    top_email, top = authors.most_common(1)[0]
    share = top / total
    details = [f"{email}: {n} commits" for email, n in authors.most_common(5)]
    if len(authors) == 1:
        return Status.WARN, "One person made every commit in the last 12 months.", details
    if share > 0.8:
        return Status.WARN, f"One author made {share:.0%} of commits in the last 12 months.", details
    return Status.PASS, f"{len(authors)} authors in the last 12 months.", details


@check("git.stale_branches", "git", "Stale branches")
def stale_branches(ctx):
    if not ctx.is_git:
        return Status.SKIP, "Not a git repository."
    out = ctx.git("for-each-ref", "--format=%(refname:short) %(committerdate:unix)", "refs/heads")
    cutoff = time.time() - STALE_BRANCH_DAYS * DAY
    stale = []
    for line in (out or "").splitlines():
        name, _, ts = line.rpartition(" ")
        if ts.isdigit() and int(ts) < cutoff:
            stale.append(name)
    if stale:
        return (
            Status.WARN,
            f"{len(stale)} local branch(es) untouched for over {STALE_BRANCH_DAYS} days.",
            stale,
        )
    return Status.PASS, "No stale local branches."


@check("git.uncommitted", "git", "Uncommitted changes")
def uncommitted(ctx):
    if not ctx.is_git:
        return Status.SKIP, "Not a git repository."
    out = ctx.git("status", "--porcelain")
    if out is None:
        return Status.SKIP, "Could not read git status."
    changed = [line for line in out.splitlines() if line]
    if changed:
        return Status.WARN, f"{len(changed)} uncommitted change(s) in the working tree.", changed[:20]
    return Status.PASS, "Working tree is clean."
