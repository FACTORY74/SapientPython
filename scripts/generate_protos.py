"""Regenerate or verify the committed BSI Flex 335 v2.0 protobuf modules."""

import argparse
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTATION = ROOT / "Documentation" / "SAPIENT-Proto-Files"
PACKAGED = ROOT / "src" / "sapient_msg"


def schema_sources() -> list[tuple[Path, Path]]:
    pairs = [(DOCUMENTATION / "proto_options.proto", PACKAGED / "proto_options.proto")]
    source_version = DOCUMENTATION / "bsi_flex_335_v2_0"
    packaged_version = PACKAGED / "bsi_flex_335_v2_0"
    pairs.extend((source, packaged_version / source.name) for source in sorted(source_version.glob("*.proto")))
    return pairs


def copy_schemas(destination_root: Path) -> None:
    for source, packaged in schema_sources():
        relative = packaged.relative_to(PACKAGED.parent)
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def compile_schemas(destination_root: Path) -> None:
    proto_root = destination_root
    proto_files = [destination_root / packaged.relative_to(PACKAGED.parent) for _, packaged in schema_sources()]
    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        "-I",
        str(proto_root),
        f"--python_out={destination_root}",
        *(str(path) for path in proto_files),
    ]
    subprocess.run(command, check=True)


def check() -> int:
    mismatches = [str(packaged) for source, packaged in schema_sources() if not packaged.exists() or not filecmp.cmp(source, packaged, shallow=False)]
    with tempfile.TemporaryDirectory(prefix="sapient-proto-") as directory:
        generated_root = Path(directory)
        copy_schemas(generated_root)
        compile_schemas(generated_root)
        for _, packaged_schema in schema_sources():
            generated = generated_root / packaged_schema.relative_to(PACKAGED.parent)
            generated_python = generated.with_name(f"{generated.stem}_pb2.py")
            committed_python = packaged_schema.with_name(f"{packaged_schema.stem}_pb2.py")
            if not committed_python.exists() or not filecmp.cmp(generated_python, committed_python, shallow=False):
                mismatches.append(str(committed_python))
    if mismatches:
        print("Generated protobuf files are stale:", file=sys.stderr)
        print("\n".join(sorted(set(mismatches))), file=sys.stderr)
        return 1
    print(f"Verified {len(schema_sources())} schemas and generated modules")
    return 0


def generate() -> int:
    copy_schemas(ROOT / "src")
    compile_schemas(ROOT / "src")
    print("Regenerated packaged schemas and Python protobuf modules")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify without modifying files")
    arguments = parser.parse_args()
    return check() if arguments.check else generate()


if __name__ == "__main__":
    raise SystemExit(main())
