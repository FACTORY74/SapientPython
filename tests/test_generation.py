import subprocess
import sys


def test_committed_protobuf_code_is_reproducible() -> None:
    subprocess.run(
        [sys.executable, "scripts/generate_protos.py", "--check"],
        check=True,
    )
