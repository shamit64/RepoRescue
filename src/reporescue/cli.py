"""Command-line entry point for RepoRescue."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporescue import __version__
from reporescue.checks import Status, run_all
from reporescue.context import RepoContext

ICONS = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reporescue",
        description="Analyze the health of a local repository. Nothing leaves your machine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan a local repository")
    scan.add_argument("path", nargs="?", default=".", help="path to the repository (default: .)")
    return parser


def cmd_scan(path: Path) -> int:
    if not path.is_dir():
        print(f"error: {path} is not a directory", file=sys.stderr)
        return 2
    ctx = RepoContext(path.resolve())
    print(f"Scanning {ctx.root}")
    results = run_all(ctx)
    category = None
    for r in results:
        if r.category != category:
            category = r.category
            print(f"\n[{category}]")
        print(f"  {ICONS[r.status]}  {r.title}: {r.message}")
        if r.status in (Status.WARN, Status.FAIL):
            for d in r.details[:5]:
                print(f"          - {d}")
    counts = {s: sum(r.status is s for r in results) for s in Status}
    print(
        f"\n{counts[Status.PASS]} passed, {counts[Status.WARN]} warnings, "
        f"{counts[Status.FAIL]} failed, {counts[Status.SKIP]} skipped"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return cmd_scan(Path(args.path))
    return 1  # unreachable: argparse enforces a subcommand
