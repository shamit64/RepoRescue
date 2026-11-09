# RepoRescue

Local-first repository health analyzer. RepoRescue reads a repository on your machine and reports on its health. It never uploads your code anywhere.

## Status

Early development. `reporescue scan` runs the checks below, scores the repository and writes a report as text, JSON, Markdown or HTML.

## Checks

All checks run offline against your local copy. In a git repository, only tracked files are scanned.

| Category | Check | What it looks for |
|---|---|---|
| docs | README | A README at the root, and that it isn't nearly empty |
| docs | License | A LICENSE, LICENCE or COPYING file |
| docs | .gitignore | A root `.gitignore` |
| docs | Contributing guide | CONTRIBUTING in the root, `.github/` or `docs/` |
| git | Recent activity | Days since the last commit |
| git | Bus factor | Whether one author made most commits in the last 12 months |
| git | Stale branches | Local branches untouched for 90+ days |
| git | Uncommitted changes | A dirty working tree |
| code | Tests present | Test directories or test-named files |
| code | TODO / FIXME markers | How many are left in the code |
| code | Large files | Files over 5 MB |
| code | Committed secrets | AWS keys, private keys, GitHub/Slack tokens, hard-coded passwords, `.env` files |
| deps | Lockfiles | A lockfile next to package.json, Pipfile, Cargo.toml, Gemfile, go.mod or composer.json |
| deps | Pinned Python requirements | Unpinned lines in `requirements*.txt` |

## Install (development)

```bash
pip install -e ".[dev]"
```

## Usage

```bash
reporescue scan path/to/repo
reporescue --version
```

### Options

| Option | What it does |
|---|---|
| `--format`, `-f` | `text` (default), `json`, `markdown` or `html` |
| `--output FILE`, `-o FILE` | Write the report to `FILE` instead of standard output. Missing parent folders are created. |
| `--fail-under N` | Exit with status 1 if the overall score is below `N` (0-100). Useful in CI. |

Exit codes: `0` success, `1` score below `--fail-under`, `2` bad path or unwritable output file.

```bash
reporescue scan . --format html --output reporescue-report.html
reporescue scan . -f json -o report.json
reporescue scan . --fail-under 75
```

The HTML report is a single file with inline CSS and no scripts, fonts or other external assets, so it opens offline.

### Example output

```text
$ reporescue scan .
Scanning /home/me/RepoRescue

[docs]  62.5/100
  PASS  README: README.md present (291 words).
  FAIL  License: No LICENSE file. Others cannot legally reuse the code.
  PASS  .gitignore: .gitignore present.
  WARN  Contributing guide: No CONTRIBUTING guide.

[git]  100/100
  PASS  Recent activity: Last commit was 4 day(s) ago.
  PASS  Bus factor: 2 authors in the last 12 months.
  PASS  Stale branches: No stale local branches.
  PASS  Uncommitted changes: Working tree is clean.

[code]  100/100
  PASS  Tests present: 4 test file(s) found.
  PASS  TODO / FIXME markers: 6 TODO/FIXME marker(s).
  PASS  Large files: No oversized files.
  PASS  Committed secrets: No likely secrets found.

[deps]  not scored
  SKIP  Lockfiles: No dependency manifest with a standard lockfile.
  SKIP  Pinned Python requirements: No requirements*.txt files.

10 passed, 1 warnings, 1 failed, 2 skipped
Overall score: 87.5/100  (grade B)

Top fixes:
   1. [FAIL] License: Add a LICENSE file (choosealicense.com helps pick one)
   2. [WARN] Contributing guide: Add a CONTRIBUTING.md explaining how to set up, test and submit changes
```

## Scoring

Each check scores 1 for pass, 0.5 for warn and 0 for fail. Skipped checks are left out. A category's score is its average times 100. A category where every check was skipped gets no score. The overall score is the average of the scored categories.

| Grade | Overall score |
|---|---|
| A | 90 or more |
| B | 75 to 89.9 |
| C | 60 to 74.9 |
| D | 40 to 59.9 |
| F | below 40 |

Top fixes list every failing check first, then every warning, each with a concrete suggestion.

### JSON schema

`--format json` produces a stable object. `version` is the schema version and changes only when the layout does.

```json
{
  "version": 1,
  "tool_version": "0.1.0",
  "root": "/home/me/RepoRescue",
  "scanned_at": "2026-11-09T14:16:44Z",
  "overall": {"score": 87.5, "grade": "B"},
  "categories": [{"name": "docs", "score": 62.5, "counts": {"pass": 2, "warn": 1, "fail": 1, "skip": 0}}],
  "results": [{"check_id": "docs.license", "category": "docs", "title": "License", "status": "fail", "message": "...", "details": []}],
  "top_fixes": [{"check_id": "docs.license", "category": "docs", "title": "License", "status": "fail", "message": "...", "suggestion": "..."}]
}
```

`score` is `null` for a category with no scored checks, and for `overall` when nothing was scored.

## Run the tests

```bash
pytest
```
