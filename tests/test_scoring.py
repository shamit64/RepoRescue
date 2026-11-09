import pytest

from reporescue.checks import CheckResult, Status, all_checks
from reporescue.scoring import (
    DEFAULT_SUGGESTION,
    SUGGESTIONS,
    grade_for,
    score_results,
    suggestion_for,
)


def res(check_id, status, category=None):
    category = category or check_id.split(".")[0]
    return CheckResult(check_id, category, check_id.title(), status, f"{check_id} message")


def test_category_and_overall_scores():
    results = [
        res("docs.a", Status.PASS),
        res("docs.b", Status.WARN),
        res("docs.c", Status.FAIL),
        res("docs.d", Status.SKIP),  # excluded: docs = (1 + 0.5 + 0) / 3
        res("git.a", Status.PASS),
        res("git.b", Status.PASS),  # git = 100
    ]
    score = score_results(results)
    cats = {c.name: c for c in score.categories}
    assert cats["docs"].score == 50.0
    assert cats["git"].score == 100.0
    assert cats["docs"].counts == {"pass": 1, "warn": 1, "fail": 1, "skip": 1}
    assert score.overall == 75.0
    assert score.grade == "B"


def test_all_skip_category_has_no_score_and_is_left_out():
    results = [res("docs.a", Status.FAIL), res("deps.a", Status.SKIP), res("deps.b", Status.SKIP)]
    score = score_results(results)
    cats = {c.name: c for c in score.categories}
    assert cats["deps"].score is None
    assert score.overall == 0.0  # mean of docs alone; deps is not counted as zero
    assert score.grade == "F"


def test_skipped_category_does_not_lower_overall():
    results = [res("docs.a", Status.PASS), res("deps.a", Status.SKIP)]
    assert score_results(results).overall == 100.0


def test_nothing_scored():
    score = score_results([res("docs.a", Status.SKIP)])
    assert score.overall is None
    assert score.grade == "N/A"
    assert score_results([]).overall is None


def test_scores_are_rounded():
    results = [res("docs.a", Status.PASS), res("docs.b", Status.PASS), res("docs.c", Status.WARN)]
    assert score_results(results).overall == 83.3


def test_category_order_follows_results():
    results = [res("git.a", Status.PASS), res("docs.a", Status.PASS), res("code.a", Status.PASS)]
    assert [c.name for c in score_results(results).categories] == ["git", "docs", "code"]


@pytest.mark.parametrize("value, grade", [
    (100, "A"), (90, "A"), (89.9, "B"), (75, "B"), (74.9, "C"), (60, "C"),
    (59.9, "D"), (40, "D"), (39.9, "F"), (0, "F"), (None, "N/A"),
])
def test_grade_bands(value, grade):
    assert grade_for(value) == grade


def test_top_fixes_fail_before_warn_in_report_order():
    results = [
        res("docs.readme", Status.WARN),
        res("docs.license", Status.FAIL),
        res("git.activity", Status.PASS),
        res("code.todos", Status.WARN),
        res("code.tests", Status.FAIL),
        res("deps.lockfile", Status.SKIP),
    ]
    fixes = score_results(results).top_fixes
    assert [f.check_id for f in fixes] == ["docs.license", "code.tests", "docs.readme", "code.todos"]
    assert fixes[0].suggestion.startswith("Add a LICENSE file")


def test_status_specific_suggestions():
    assert "Expand" in suggestion_for(res("docs.readme", Status.WARN))
    assert "Add a README" in suggestion_for(res("docs.readme", Status.FAIL))
    assert suggestion_for(res("x.unknown", Status.FAIL)) == DEFAULT_SUGGESTION


def test_every_registered_check_has_a_suggestion():
    keyed = {k if isinstance(k, str) else k[0] for k in SUGGESTIONS}
    missing = [c.check_id for c in all_checks() if c.check_id not in keyed]
    assert missing == []
