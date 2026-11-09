"""Turn check results into category scores, an overall score, a letter grade and a fix list."""

from __future__ import annotations

from dataclasses import dataclass, field

from reporescue.checks import CheckResult, Status

# How much each status is worth. SKIP is not here: skipped checks are left out of the maths.
STATUS_POINTS = {Status.PASS: 1.0, Status.WARN: 0.5, Status.FAIL: 0.0}

# (minimum score, grade), checked top to bottom.
GRADE_BANDS = [(90, "A"), (75, "B"), (60, "C"), (40, "D")]

# A concrete next step for each check. A (check_id, status) key wins over a plain check_id key,
# for checks whose warn and fail mean different things.
SUGGESTIONS: dict[str | tuple[str, Status], str] = {
    ("docs.readme", Status.FAIL): "Add a README.md that says what the project does and how to run it",
    ("docs.readme", Status.WARN): "Expand the README with install steps, usage and an example",
    "docs.license": "Add a LICENSE file (choosealicense.com helps pick one)",
    "docs.gitignore": "Add a .gitignore (github.com/github/gitignore has templates per language)",
    "docs.contributing": "Add a CONTRIBUTING.md explaining how to set up, test and submit changes",
    ("git.activity", Status.WARN): "Commit recent work, or note in the README if the project is finished",
    ("git.activity", Status.FAIL): "Commit recent work, or mark the project as archived or unmaintained",
    "git.bus_factor": "Get a second person reviewing and committing so knowledge is shared",
    "git.stale_branches": "Merge or delete branches nobody has touched in 90+ days",
    "git.uncommitted": "Commit or stash the changes in the working tree",
    "code.tests": "Add a tests/ directory with at least one test for the main code path",
    "code.todos": "Turn the TODO/FIXME markers into tracked issues, or resolve them",
    "code.large_files": "Move large files to Git LFS or a release asset instead of the repository",
    "code.secrets": "Remove the secrets, rotate them now, and load them from the environment instead",
    "deps.lockfile": "Commit the lockfile your package manager generates next to the manifest",
    "deps.pinned": "Pin Python requirements to exact versions (==), e.g. with pip-compile",
}

DEFAULT_SUGGESTION = "Review this check's details and address the issue it reports"


def suggestion_for(result: CheckResult) -> str:
    return SUGGESTIONS.get(
        (result.check_id, result.status), SUGGESTIONS.get(result.check_id, DEFAULT_SUGGESTION)
    )


def grade_for(score: float | None) -> str:
    if score is None:
        return "N/A"
    for minimum, grade in GRADE_BANDS:
        if score >= minimum:
            return grade
    return "F"


@dataclass
class CategoryScore:
    name: str
    score: float | None  # None when every check in the category was skipped
    counts: dict[str, int]


@dataclass
class Fix:
    check_id: str
    category: str
    title: str
    status: Status
    message: str
    suggestion: str


@dataclass
class Score:
    overall: float | None
    grade: str
    categories: list[CategoryScore] = field(default_factory=list)
    top_fixes: list[Fix] = field(default_factory=list)


def score_results(results: list[CheckResult]) -> Score:
    # Keep categories in the order the results arrive, which is the report order.
    grouped: dict[str, list[CheckResult]] = {}
    for r in results:
        grouped.setdefault(r.category, []).append(r)

    categories = []
    for name, items in grouped.items():
        scored = [STATUS_POINTS[r.status] for r in items if r.status in STATUS_POINTS]
        value = round(100 * sum(scored) / len(scored), 1) if scored else None
        counts = {s.value: sum(r.status is s for r in items) for s in Status}
        categories.append(CategoryScore(name, value, counts))

    scored_categories = [c.score for c in categories if c.score is not None]
    overall = (
        round(sum(scored_categories) / len(scored_categories), 1) if scored_categories else None
    )

    fixes = [
        Fix(r.check_id, r.category, r.title, r.status, r.message, suggestion_for(r))
        for status in (Status.FAIL, Status.WARN)
        for r in results
        if r.status is status
    ]
    return Score(overall, grade_for(overall), categories, fixes)
