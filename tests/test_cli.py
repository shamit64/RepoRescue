import json
import subprocess
import sys

import pytest

from reporescue import __version__
from reporescue.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_scan_directory(tmp_path, capsys):
    assert main(["scan", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "[docs]" in out
    assert "FAIL  README" in out
    assert "passed," in out


def test_scan_missing_path(tmp_path, capsys):
    assert main(["scan", str(tmp_path / "nope")]) == 2
    assert "not a directory" in capsys.readouterr().err


def test_scan_text_includes_scores(tmp_path, capsys):
    assert main(["scan", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Overall score:" in out
    assert "Top fixes:" in out


@pytest.mark.parametrize("fmt", ["json", "markdown", "html"])
def test_scan_formats_to_stdout(tmp_path, capsys, fmt):
    assert main(["scan", str(tmp_path), "--format", fmt]) == 0
    out = capsys.readouterr().out
    if fmt == "json":
        assert json.loads(out)["root"] == str(tmp_path.resolve())
    elif fmt == "markdown":
        assert out.startswith("# RepoRescue report")
    else:
        assert out.startswith("<!doctype html>")


def test_scan_output_writes_file(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "out dir" / "report.json"  # space in the name, parent not created yet
    assert main(["scan", str(repo), "-f", "json", "--output", str(target)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Wrote json report to" in captured.err
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["root"] == str(repo.resolve())


def test_fail_under(tmp_path, capsys):
    # An empty directory fails several checks, so it scores below 100.
    assert main(["scan", str(tmp_path), "--fail-under", "0"]) == 0
    assert main(["scan", str(tmp_path), "--fail-under", "100"]) == 1
    assert "below --fail-under 100" in capsys.readouterr().err


def test_fail_under_boundary(tmp_path):
    from reporescue.checks import run_all
    from reporescue.context import RepoContext
    from reporescue.scoring import score_results

    overall = score_results(run_all(RepoContext(tmp_path.resolve()))).overall
    assert main(["scan", str(tmp_path), "--fail-under", str(overall)]) == 0
    assert main(["scan", str(tmp_path), "--fail-under", str(overall + 0.1)]) == 1


def test_bad_path_still_exits_2_with_fail_under(tmp_path):
    assert main(["scan", str(tmp_path / "nope"), "--fail-under", "50"]) == 2


def test_bad_format_is_rejected(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["scan", str(tmp_path), "--format", "xml"])
    assert exc.value.code == 2


def test_module_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "reporescue", "--version"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert __version__ in result.stdout
