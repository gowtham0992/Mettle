from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_packaged_entrypoint_bootstraps_src_layout() -> None:
    script = """
import runpy
import sys
from pathlib import Path

repository = Path(sys.argv[1]).resolve()
source_root = str(repository / "src")
sys.path = [entry for entry in sys.path if str(Path(entry or ".").resolve()) != source_root]
runpy.run_path(str(repository / "agentcore_app.py"), run_name="agentcore_import_test")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(REPOSITORY_ROOT)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
