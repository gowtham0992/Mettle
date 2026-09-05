from pathlib import Path
import subprocess
from zipfile import ZipFile


def test_runtime_package_removes_design_sources_and_nested_archives(tmp_path):
    script = Path("scripts/prune_agentcore_zip.sh").resolve()
    (tmp_path / "agentcore").mkdir()
    artifact = tmp_path / "agentcore/test.zip"
    with ZipFile(artifact, "w") as archive:
        for name in ["agentcore_app.py", "src/mettle/workflow.py", "untitled.pen", "Mettle Structural Redesign.zip", "UI mockups for form.zip"]:
            archive.writestr(name, "test fixture")
    subprocess.run(["bash", str(script), "agentcore/test.zip"], cwd=tmp_path, check=True, capture_output=True)
    with ZipFile(artifact) as archive:
        assert set(archive.namelist()) == {"agentcore_app.py", "src/mettle/workflow.py"}
