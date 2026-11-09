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


def test_module_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "reporescue", "--version"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert __version__ in result.stdout
