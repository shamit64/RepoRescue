# RepoRescue

Local-first repository health analyzer. RepoRescue reads a repository on your machine and reports on its health. It never uploads your code anywhere.

## Status

Early development. `reporescue scan` runs the checks below and prints the results. Scoring and JSON/HTML reports are coming next.

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

## Run the tests

```bash
pytest
```
