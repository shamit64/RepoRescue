"""Command-line entry point for RepoRescue."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporescue import __version__


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
    is_git = (path / ".git").exists()
    print(f"Scanning {path.resolve()}")
    print(f"  git repository: {'yes' if is_git else 'no'}")
    print("  no checks registered yet")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return cmd_scan(Path(args.path))
    return 1  # unreachable: argparse enforces a subcommand
