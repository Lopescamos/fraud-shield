from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_imports_contract_ok() -> None:
    """Runs ``lint-imports`` as a subprocess so ``include_external_packages``
    sees the real project imports."""
    service_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command; lint_imports_command()",
        ],
        cwd=service_root,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, output
    assert "0 broken" in output, output
