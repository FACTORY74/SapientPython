import subprocess
import sys
import tarfile
import zipfile
import shutil
from pathlib import Path


def test_wheel_and_source_distribution_contents(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    checkout = tmp_path / "checkout"
    shutil.copytree(
        source_root,
        checkout,
        ignore=shutil.ignore_patterns(
            ".venv",
            ".pytest_cache",
            "tmp",
            "output",
            "*.egg-info",
            "__pycache__",
            "*.pyc",
            "*.pdf",
            "SAPIENT networked autonomous sensing - GOV.UK_files",
        ),
    )
    artifacts = tmp_path / "artifacts"
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(artifacts)],
        check=True,
        cwd=checkout,
    )
    wheel = next(artifacts.glob("*.whl"))
    source = next(artifacts.glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
    assert "sapient/__init__.py" in wheel_names
    assert "sapient_msg/bsi_flex_335_v2_0/sapient_message.proto" in wheel_names
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in wheel_names)
    assert not any(name.startswith("tests/") for name in wheel_names)

    with tarfile.open(source, "r:gz") as archive:
        source_names = {name.split("/", 1)[-1] for name in archive.getnames()}
    assert "architecture.md" in source_names
    assert "requirements.txt" in source_names
    assert "tests/test_outer_messages.py" in source_names
    assert "scripts/generate_protos.py" in source_names
