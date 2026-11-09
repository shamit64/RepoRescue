import json
from datetime import datetime, timezone
from html.parser import HTMLParser

import pytest

from reporescue.checks import CheckResult, Status
from reporescue.report import FORMATS, SCHEMA_VERSION, Report, render


@pytest.fixture
def report(tmp_path):
    results = [
        CheckResult("docs.readme", "docs", "README", Status.PASS, "README.md has 120 words."),
        CheckResult("docs.license", "docs", "License", Status.FAIL, "No LICENSE file."),
        CheckResult("code.todos", "code", "TODO | FIXME", Status.WARN, "2 markers <b>.",
                    ["a.py:1", "b.py:<script>"]),
        CheckResult("deps.lockfile", "deps", "Lockfiles", Status.SKIP, "No manifests."),
    ]
    when = datetime(2026, 11, 9, 12, 30, 15, 999, tzinfo=timezone.utc)
    # A path with a space; on Windows this also has backslashes and a drive letter.
    return Report.build(tmp_path / "my repo", results, scanned_at=when)


def test_text(report):
    out = render(report, "text")
    assert "[docs]  50/100" in out
    assert "[deps]  not scored" in out
    assert "FAIL  License: No LICENSE file." in out
    assert "          - a.py:1" in out
    assert "1 passed, 1 warnings, 1 failed, 1 skipped" in out
    assert "Overall score: 50/100  (grade D)" in out
    assert "Top fixes:" in out
    assert "1. [FAIL] License: Add a LICENSE file" in out


def test_json_schema(report):
    data = json.loads(render(report, "json"))
    assert set(data) >= {
        "version", "root", "scanned_at", "overall", "categories", "results", "top_fixes",
    }
    assert data["version"] == SCHEMA_VERSION
    assert data["root"] == str(report.root)  # Windows backslashes survive the round trip
    assert data["scanned_at"] == "2026-11-09T12:30:15Z"
    assert data["overall"] == {"score": 50.0, "grade": "D"}
    assert [c["name"] for c in data["categories"]] == ["docs", "code", "deps"]
    assert data["categories"][2]["score"] is None
    assert data["results"][2] == {
        "check_id": "code.todos", "category": "code", "title": "TODO | FIXME", "status": "warn",
        "message": "2 markers <b>.", "details": ["a.py:1", "b.py:<script>"],
    }
    assert [f["check_id"] for f in data["top_fixes"]] == ["docs.license", "code.todos"]
    assert set(data["top_fixes"][0]) == {
        "check_id", "category", "title", "status", "message", "suggestion",
    }


def test_markdown(report):
    out = render(report, "markdown")
    lines = out.splitlines()
    for heading in ("# RepoRescue report", "## Category scores", "## Top fixes", "## Results",
                    "### docs", "### code", "### deps"):
        assert heading in lines
    assert "| docs | 50 | 1 | 0 | 1 | 0 |" in lines
    assert "TODO \\| FIXME" in out  # pipes escaped so the table stays intact
    assert "1. **FAIL** License: Add a LICENSE file" in out


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.urls += [v for k, v in attrs if k in ("src", "href") and v]


def test_html_is_self_contained_and_escaped(report):
    out = render(report, "html")
    assert out.startswith("<!doctype html>")
    parser = _Collector()
    parser.feed(out)
    assert "style" in parser.tags
    assert "script" not in parser.tags and "link" not in parser.tags
    assert parser.urls == []
    assert "http://" not in out and "https://" not in out
    assert "&lt;script&gt;" in out and "<script>" not in out
    assert 'class="grade g-D">D<' in out
    assert "Add a LICENSE file" in out


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_handles_a_clean_report(tmp_path, fmt):
    results = [CheckResult("docs.readme", "docs", "README", Status.PASS, "ok")]
    out = render(Report.build(tmp_path, results), fmt)
    assert "100" in out
