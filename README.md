# RepoRescue

Local-first repository health analyzer. RepoRescue reads a repository on your machine and reports on its health. It never uploads your code anywhere.

## Status

Early development. The CLI runs, but health checks are not implemented yet.

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
