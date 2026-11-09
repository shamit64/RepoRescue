"""Render a scan as text, JSON, Markdown or a self-contained HTML page."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from reporescue import __version__
from reporescue.checks import CheckResult, Status
from reporescue.scoring import Score, score_results

# Bump when the JSON layout changes in a way that could break consumers.
SCHEMA_VERSION = 1

FORMATS = ("text", "json", "markdown", "html")

LABELS = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}


@dataclass
class Report:
    root: Path
    scanned_at: datetime
    results: list[CheckResult]
    score: Score

    @classmethod
    def build(cls, root: Path, results: list[CheckResult], scanned_at: datetime | None = None):
        when = scanned_at or datetime.now(timezone.utc)
        return cls(root, when.replace(microsecond=0), results, score_results(results))

    @property
    def scanned_at_iso(self) -> str:
        return self.scanned_at.isoformat().replace("+00:00", "Z")

    def by_category(self) -> dict[str, list[CheckResult]]:
        grouped: dict[str, list[CheckResult]] = {}
        for r in self.results:
            grouped.setdefault(r.category, []).append(r)
        return grouped

    def counts(self) -> dict[Status, int]:
        return {s: sum(r.status is s for r in self.results) for s in Status}


def fmt_score(value: float | None) -> str:
    return "n/a" if value is None else f"{value:g}"


def summary_line(report: Report) -> str:
    c = report.counts()
    return (
        f"{c[Status.PASS]} passed, {c[Status.WARN]} warnings, "
        f"{c[Status.FAIL]} failed, {c[Status.SKIP]} skipped"
    )


# --- text -------------------------------------------------------------------------------------


def render_text(report: Report) -> str:
    scores = {c.name: c.score for c in report.score.categories}
    lines = [f"Scanning {report.root}"]
    for category, items in report.by_category().items():
        value = scores.get(category)
        label = "not scored" if value is None else f"{fmt_score(value)}/100"
        lines.append(f"\n[{category}]  {label}")
        for r in items:
            lines.append(f"  {LABELS[r.status]}  {r.title}: {r.message}")
            if r.status in (Status.WARN, Status.FAIL):
                lines.extend(f"          - {d}" for d in r.details[:5])
    lines.append(f"\n{summary_line(report)}")
    lines.append(f"Overall score: {fmt_score(report.score.overall)}/100  (grade {report.score.grade})")
    if report.score.top_fixes:
        lines.append("\nTop fixes:")
        for i, fix in enumerate(report.score.top_fixes, 1):
            lines.append(f"  {i:>2}. [{LABELS[fix.status]}] {fix.title}: {fix.suggestion}")
    return "\n".join(lines) + "\n"


# --- JSON -------------------------------------------------------------------------------------


def to_dict(report: Report) -> dict:
    return {
        "version": SCHEMA_VERSION,
        "tool_version": __version__,
        "root": str(report.root),
        "scanned_at": report.scanned_at_iso,
        "overall": {"score": report.score.overall, "grade": report.score.grade},
        "categories": [
            {"name": c.name, "score": c.score, "counts": c.counts} for c in report.score.categories
        ],
        "results": [
            {
                "check_id": r.check_id,
                "category": r.category,
                "title": r.title,
                "status": r.status.value,
                "message": r.message,
                "details": list(r.details),
            }
            for r in report.results
        ],
        "top_fixes": [
            {
                "check_id": f.check_id,
                "category": f.category,
                "title": f.title,
                "status": f.status.value,
                "message": f.message,
                "suggestion": f.suggestion,
            }
            for f in report.score.top_fixes
        ],
    }


def render_json(report: Report) -> str:
    return json.dumps(to_dict(report), indent=2) + "\n"


# --- Markdown ---------------------------------------------------------------------------------


def md_cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: Report) -> str:
    s = report.score
    out = [
        "# RepoRescue report",
        "",
        f"- **Repository:** `{report.root}`",
        f"- **Scanned at:** {report.scanned_at_iso}",
        f"- **Overall score:** {fmt_score(s.overall)}/100 (grade **{s.grade}**)",
        f"- **Checks:** {summary_line(report)}",
        "",
        "## Category scores",
        "",
        "| Category | Score | Pass | Warn | Fail | Skip |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for c in s.categories:
        n = c.counts
        out.append(
            f"| {c.name} | {fmt_score(c.score)} | {n['pass']} | {n['warn']} | {n['fail']} | {n['skip']} |"
        )

    out += ["", "## Top fixes", ""]
    if s.top_fixes:
        for i, f in enumerate(s.top_fixes, 1):
            out.append(f"{i}. **{LABELS[f.status]}** {f.title}: {f.suggestion}")
    else:
        out.append("Nothing to fix. Every check passed or was skipped.")

    out += ["", "## Results"]
    for category, items in report.by_category().items():
        out += ["", f"### {category}", "", "| Status | Check | Result |", "|---|---|---|"]
        for r in items:
            out.append(f"| {LABELS[r.status]} | {md_cell(r.title)} | {md_cell(r.message)} |")
        flagged = [r for r in items if r.details and r.status in (Status.WARN, Status.FAIL)]
        for r in flagged:
            out += ["", f"<details><summary>{html.escape(r.title)} details</summary>", ""]
            out += [f"- `{d}`" for d in r.details]
            out += ["", "</details>"]
    return "\n".join(out) + "\n"


# --- HTML -------------------------------------------------------------------------------------

HTML_CSS = """
:root {
  --bg: #f7f7f5; --card: #ffffff; --text: #1d1d1b; --muted: #6b6b66; --line: #e3e2dd;
  --pass: #1f7a4d; --warn: #a15c00; --fail: #b3261e; --skip: #6b6b66; --bar: #e9e8e3;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161615; --card: #1f1f1d; --text: #ecebe6; --muted: #a3a29c; --line: #34332f;
    --pass: #5cc48d; --warn: #e3a64a; --fail: #f07b72; --skip: #a3a29c; --bar: #2c2b28;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 32px 0 12px; }
.meta { color: var(--muted); font-size: 13px; word-break: break-all; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
.hero { display: flex; gap: 20px; align-items: center; margin-top: 20px; flex-wrap: wrap; }
.grade { font-size: 44px; font-weight: 700; width: 84px; height: 84px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; border: 2px solid currentColor; }
.g-A, .g-B { color: var(--pass); } .g-C, .g-D { color: var(--warn); } .g-F { color: var(--fail); }
.g-NA { color: var(--skip); }
.score { font-size: 28px; font-weight: 600; }
.cats { display: grid; gap: 10px; }
.cat { display: grid; grid-template-columns: 90px 1fr 56px; gap: 12px; align-items: center; }
.bar { height: 10px; background: var(--bar); border-radius: 5px; overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--pass); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
ol.fixes { margin: 0; padding-left: 22px; }
ol.fixes li { margin: 6px 0; }
.tag { display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .04em;
  padding: 1px 6px; border-radius: 4px; border: 1px solid currentColor; }
.s-pass { color: var(--pass); } .s-warn { color: var(--warn); }
.s-fail { color: var(--fail); } .s-skip { color: var(--skip); }
table { width: 100%; border-collapse: collapse; }
td { padding: 8px 6px; border-top: 1px solid var(--line); vertical-align: top; }
td:first-child { width: 60px; }
td.title { width: 32%; font-weight: 500; }
details { margin-top: 4px; color: var(--muted); font-size: 13px; }
details code { word-break: break-all; }
footer { margin-top: 40px; color: var(--muted); font-size: 12px; }
"""


def _tag(status: Status) -> str:
    return f'<span class="tag s-{status.value}">{LABELS[status]}</span>'


def render_html(report: Report) -> str:
    e = html.escape
    s = report.score
    grade_class = "g-NA" if s.grade == "N/A" else f"g-{s.grade}"

    cats = []
    for c in s.categories:
        width = 0 if c.score is None else c.score
        cats.append(
            f'<div class="cat"><span>{e(c.name)}</span>'
            f'<div class="bar"><span style="width:{width:g}%"></span></div>'
            f'<span class="num">{fmt_score(c.score)}</span></div>'
        )

    if s.top_fixes:
        fixes = "".join(
            f"<li>{_tag(f.status)} <strong>{e(f.title)}</strong>: {e(f.suggestion)}</li>"
            for f in s.top_fixes
        )
        fixes_html = f'<ol class="fixes">{fixes}</ol>'
    else:
        fixes_html = "<p>Nothing to fix. Every check passed or was skipped.</p>"

    sections = []
    for category, items in report.by_category().items():
        rows = []
        for r in items:
            extra = ""
            if r.details and r.status in (Status.WARN, Status.FAIL):
                lis = "".join(f"<li><code>{e(d)}</code></li>" for d in r.details)
                extra = f"<details><summary>{len(r.details)} detail(s)</summary><ul>{lis}</ul></details>"
            rows.append(
                f'<tr><td>{_tag(r.status)}</td><td class="title">{e(r.title)}</td>'
                f"<td>{e(r.message)}{extra}</td></tr>"
            )
        sections.append(
            f'<h2>{e(category)}</h2><div class="card"><table>{"".join(rows)}</table></div>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RepoRescue report</title>
<style>{HTML_CSS}</style>
</head>
<body>
<main>
<h1>RepoRescue report</h1>
<div class="meta">{e(str(report.root))} &middot; scanned {e(report.scanned_at_iso)}</div>
<div class="hero">
  <div class="grade {grade_class}">{e(s.grade)}</div>
  <div>
    <div class="score">{fmt_score(s.overall)}<span class="meta"> / 100</span></div>
    <div class="meta">{e(summary_line(report))}</div>
  </div>
</div>
<h2>Category scores</h2>
<div class="card cats">{"".join(cats)}</div>
<h2>Top fixes</h2>
<div class="card">{fixes_html}</div>
{"".join(sections)}
<footer>Generated by RepoRescue {e(__version__)}. This report was produced locally and contains no external resources.</footer>
</main>
</body>
</html>
"""


RENDERERS = {
    "text": render_text,
    "json": render_json,
    "markdown": render_markdown,
    "html": render_html,
}


def render(report: Report, fmt: str) -> str:
    return RENDERERS[fmt](report)
