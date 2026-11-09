"""Command-line entry point for RepoRescue."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporescue import __version__
from reporescue.checks import run_all
from reporescue.context import RepoContext
from reporescue.report import FORMATS, Report, fmt_score, render


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reporescue",
        description="Analyze the health of a local repository. Nothing leaves your machine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan a local repository")
    scan.add_argument("path", nargs="?", default=".", help="path to the repository (default: .)")
    scan.add_argument(
        "--format", "-f", choices=FORMATS, default="text",
        help="report format (default: text)",
    )
    scan.add_argument(
        "--output", "-o", metavar="FILE", type=Path,
        help="write the report to FILE instead of standard output",
    )
    scan.add_argument(
        "--fail-under", metavar="N", type=float,
        help="exit with status 1 if the overall score is below N (0-100), e.g. in CI",
    )
    return parser


def emit(text: str) -> None:
    """Print to stdout, falling back to UTF-8 bytes on consoles that can't encode the text."""
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.flush()


def cmd_scan(path: Path, fmt: str = "text", output: Path | None = None,
             fail_under: float | None = None) -> int:
    if not path.is_dir():
        print(f"error: {path} is not a directory", file=sys.stderr)
        return 2
    ctx = RepoContext(path.resolve())
    report = Report.build(ctx.root, run_all(ctx))
    content = render(report, fmt)

    if output is None:
        emit(content)
    else:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write {output}: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote {fmt} report to {output}", file=sys.stderr)

    overall = report.score.overall
    if fail_under is not None and (overall is None or overall < fail_under):
        print(
            f"Overall score {fmt_score(overall)} is below --fail-under {fail_under:g}",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return cmd_scan(Path(args.path), args.format, args.output, args.fail_under)
    return 1  # unreachable: argparse enforces a subcommand
