# RepoRescue

**A local-first health check for your repositories.**

RepoRescue looks at a repository on your machine and tells you how healthy it is. It checks documentation, git hygiene, tests, committed secrets and dependency pinning, gives each area a score, and lists the most useful fixes first. You can read the results in your terminal or save them as JSON, Markdown or a single-file HTML report.

## Local-first promise

- **Your code never leaves your machine.** RepoRescue makes no network requests. It reads files and runs read-only `git` commands, and that's all.
- **No account, API key or telemetry.**
- **No runtime dependencies.** It uses only the Python standard library.
- **Reports are self-contained.** The HTML report has no scripts, fonts or external assets, so it opens offline and is safe to attach to a ticket.

## Install

RepoRescue needs Python 3.10 or newer, plus `git` on your PATH for the git checks.

```bash
pip install git+https://github.com/shamit64/RepoRescue
```

Check that it works:

```bash
reporescue --version
```

## Usage

```bash
reporescue scan                      # scan the current directory
reporescue scan path/to/repo         # scan another directory
```

| Option | What it does |
|---|---|
| `--format`, `-f` | `text` (default), `json`, `markdown` or `html` |
| `--output FILE`, `-o FILE` | Write the report to `FILE` instead of standard output. Missing parent folders are created. |
| `--fail-under N` | Exit with status 1 if the overall score is below `N` (0 to 100) |

Exit codes: `0` success, `1` score below `--fail-under`, `2` bad path or unwritable output file.

### Text (default)

```text
$ reporescue scan .
Scanning /home/me/RepoRescue

[docs]  62.5/100
  PASS  README: README.md present (812 words).
  FAIL  License: No LICENSE file. Others cannot legally reuse the code.
  PASS  .gitignore: .gitignore present.
  WARN  Contributing guide: No CONTRIBUTING guide.

[git]  100/100
  PASS  Recent activity: Last commit was 0 day(s) ago.
  PASS  Bus factor: 2 authors in the last 12 months.
  PASS  Stale branches: No stale local branches.
  PASS  Uncommitted changes: Working tree is clean.

[code]  100/100
  PASS  Tests present: 4 test file(s) found.
  PASS  TODO / FIXME markers: 11 TODO/FIXME marker(s).
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

### JSON

```bash
reporescue scan . --format json --output report.json
```

The JSON output has a stable layout. `version` is the schema version and changes only when the layout does.

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

### Markdown

```bash
reporescue scan . -f markdown -o HEALTH.md
```

This gives you a summary, a table of category scores, the top fixes and a results table for each category. It's handy for pull request comments or a wiki page.

### HTML

```bash
reporescue scan . -f html -o reporescue-report.html
```

This writes one file with inline CSS and light and dark themes. Open it in any browser.

## Use it in CI

`--fail-under` makes the scan fail a build when health drops below a threshold. In GitHub Actions:

```yaml
name: Repo health

on: [push, pull_request]

jobs:
  reporescue:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # full history, so the bus-factor check can run
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install git+https://github.com/shamit64/RepoRescue
      - run: reporescue scan . --format markdown --output reporescue.md --fail-under 75
      - run: cat reporescue.md >> "$GITHUB_STEP_SUMMARY"
        if: always()
```

The scan still writes the report when the score is too low, so the job summary shows why the build failed. Without `fetch-depth: 0` the checkout is shallow. In that case the bus-factor check is skipped rather than guessed.

## Checks

All checks run offline against your local copy. In a git repository, only tracked files are scanned.

| Category | Check | What it looks for |
|---|---|---|
| docs | README | A README at the root, and that it isn't nearly empty |
| docs | License | A LICENSE, LICENCE or COPYING file |
| docs | .gitignore | A root `.gitignore` |
| docs | Contributing guide | CONTRIBUTING in the root, `.github/` or `docs/` |
| git | Recent activity | Days since the last commit |
| git | Bus factor | Whether one author made most commits in the last 12 months (skipped in shallow clones) |
| git | Stale branches | Local branches, other than the checked-out one, untouched for 90+ days |
| git | Uncommitted changes | A dirty working tree |
| code | Tests present | Test directories or test-named files |
| code | TODO / FIXME markers | How many are left in the code |
| code | Large files | Files over 5 MB |
| code | Committed secrets | AWS keys, private keys, GitHub/Slack tokens, hard-coded passwords, `.env` files |
| deps | Lockfiles | A lockfile next to package.json, Pipfile, Cargo.toml, Gemfile, go.mod or composer.json (`package-lock=false` in `.npmrc` counts as a deliberate choice) |
| deps | Pinned Python requirements | Unpinned lines in `requirements*.txt` |

Every check that warns or fails comes with a suggested fix.

## Scoring

Each check scores 1 for pass, 0.5 for warn and 0 for fail. Skipped checks are left out. A category's score is its average times 100. A category where every check was skipped gets no score and doesn't affect the total. The overall score is the average of the scored categories.

| Grade | Overall score |
|---|---|
| A | 90 or more |
| B | 75 to 89.9 |
| C | 60 to 74.9 |
| D | 40 to 59.9 |
| F | below 40 |

Top fixes list every failing check first, then every warning, in report order.

## Contributing

Issues and pull requests are welcome at [github.com/shamit64/RepoRescue](https://github.com/shamit64/RepoRescue).

```bash
git clone https://github.com/shamit64/RepoRescue
cd RepoRescue
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

- A check is a function decorated with `@check(...)` in `src/reporescue/checks/`. It returns a status, a message and optional details. Add a suggestion for it in `src/reporescue/scoring.py`. A test fails if one is missing.
- Keep RepoRescue offline and dependency-free: no network calls, and standard library only at runtime.
- Add tests for new behaviour. CI runs the suite on Python 3.10 to 3.13.

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

No license has been chosen yet. Until one is added, the default copyright rules apply.
