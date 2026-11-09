# Changelog

All notable changes to RepoRescue are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - Unreleased

First release.

### Added

- MIT license.
- `reporescue scan [path]` command, also available as `python -m reporescue`.
- 14 offline health checks in four categories:
  - **docs**: README, license, `.gitignore`, contributing guide.
  - **git**: recent activity, bus factor, stale branches, uncommitted changes.
  - **code**: tests present, TODO/FIXME markers, large files, committed secrets.
  - **deps**: lockfiles, pinned Python requirements.
- Scoring: 0 to 100 per category, an overall score, a letter grade (A to F), and a prioritised list of top fixes with a concrete suggestion for each.
- Report formats: text, JSON (versioned schema), Markdown, and a self-contained HTML file.
- `--format`, `--output` and `--fail-under` options for use in CI.

### Fixed (found in trial scans of public repositories)

- The bus-factor check is skipped in shallow clones such as the default `actions/checkout`. Before this, a shallow clone always looked like a single-author project.
- The checked-out branch is no longer reported as a stale branch. Recent activity already covers it.
- npm projects that turn off lockfiles on purpose (`package-lock=false` in `.npmrc`) no longer get a lockfile warning.
- File lines under uncommitted changes keep their git status columns. ` M file` used to lose its leading space.
