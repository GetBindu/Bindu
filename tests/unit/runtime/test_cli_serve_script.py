"""Test ``bindu serve --script <path>``."""
import subprocess
import sys
from pathlib import Path


def test_serve_script_executes_user_module(tmp_path: Path):
    """`bindu serve --script foo.py` should execute foo.py in __main__ context."""
    script = tmp_path / "foo.py"
    script.write_text(
        "import sys\n"
        "print('SCRIPT_RAN', file=sys.stderr)\n"
        "sys.exit(0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-m", "bindu.cli", "serve", "--script", str(script)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "SCRIPT_RAN" in result.stderr


def test_serve_without_grpc_or_script_errors():
    """`bindu serve` (no args) should print an error and exit non-zero."""
    result = subprocess.run(
        [sys.executable, "-m", "bindu.cli", "serve"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0
    assert "--grpc" in result.stdout or "--script" in result.stdout
