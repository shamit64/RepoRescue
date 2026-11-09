"""Health check registry. Each check is a function taking a RepoContext and returning a CheckResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from reporescue.context import RepoContext


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    check_id: str
    category: str
    title: str
    status: Status
    message: str
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Check:
    check_id: str
    category: str
    title: str
    func: Callable[[RepoContext], tuple[Status, str, list[str]] | tuple[Status, str]]

    def run(self, ctx: RepoContext) -> CheckResult:
        try:
            outcome = self.func(ctx)
        except Exception as exc:  # a broken check must not break the whole scan
            outcome = (Status.SKIP, f"check errored: {exc}")
        status, message, *rest = outcome
        details = rest[0] if rest else []
        return CheckResult(self.check_id, self.category, self.title, status, message, list(details))


REGISTRY: list[Check] = []


def check(check_id: str, category: str, title: str):
    """Decorator that registers a health check."""

    def register(func):
        REGISTRY.append(Check(check_id, category, title, func))
        return func

    return register


def all_checks() -> list[Check]:
    # Importing the modules populates REGISTRY; the order here is the report order.
    import reporescue.checks.docs  # noqa: F401
    import reporescue.checks.git  # noqa: F401
    import reporescue.checks.code  # noqa: F401
    import reporescue.checks.deps  # noqa: F401

    return list(REGISTRY)


def run_all(ctx: RepoContext) -> list[CheckResult]:
    return [c.run(ctx) for c in all_checks()]
