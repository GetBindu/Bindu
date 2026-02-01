#!/usr/bin/env python3
"""Generate Python code from Protocol Buffer definitions.

This script generates the Python gRPC code from .proto files.

Usage:
    python scripts/generate_proto.py
"""

import subprocess
import sys
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
PROTO_DIR = PROJECT_ROOT / "proto"
OUTPUT_DIR = PROJECT_ROOT / "bindu" / "grpc"


def _patch_grpc_module(grpc_file: Path) -> None:
    text = grpc_file.read_text()
    updated = text

    base_module = grpc_file.name.replace("_pb2_grpc.py", "_pb2")
    alias_module = base_module.replace("_", "__")
    import_line = f"import {base_module} as {alias_module}"
    relative_import_line = f"from . import {base_module} as {alias_module}"
    if import_line in updated:
        updated = updated.replace(import_line, relative_import_line)

    if (
        relative_import_line in updated
        and "type: ignore[possibly-unbound-import]" not in updated
    ):
        updated = updated.replace(
            relative_import_line,
            f"{relative_import_line}  # type: ignore[possibly-unbound-import]",
        )

    if "from typing import Any as _Any" not in updated:
        updated = updated.replace(
            "import warnings\n\n",
            "import warnings\nfrom typing import Any as _Any\n\n",
        )

    experimental_line = 'experimental: _Any = getattr(grpc, "experimental", grpc)'
    if experimental_line not in updated:
        import_line_with_ignore = (
            f"{relative_import_line}  # type: ignore[possibly-unbound-import]"
        )
        target_line = (
            import_line_with_ignore
            if import_line_with_ignore in updated
            else relative_import_line
        )
        if target_line in updated:
            updated = updated.replace(
                f"{target_line}\n",
                f"{target_line}\n\n{experimental_line}\n",
            )

    updated = updated.replace("grpc.experimental.", "experimental.")

    if updated != text:
        grpc_file.write_text(updated)


def _patch_pyi_module(pyi_file: Path) -> None:
    text = pyi_file.read_text()
    updated = text

    if "from typing import Any as _Any" not in updated:
        updated = updated.replace(
            "from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union",
            "from typing import Any as _Any, ClassVar as _ClassVar, Optional as _Optional, Union as _Union",
        )

    updated = updated.replace("_struct_pb2.Struct", "_Any")
    updated = updated.replace(
        "class ServingStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):",
        "class ServingStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):  # type: ignore[conflicting-metaclass]",
    )

    if updated != text:
        pyi_file.write_text(updated)


def generate_proto_code():
    """Generate Python code from .proto files."""
    if not PROTO_DIR.exists():
        print(f"❌ Proto directory not found: {PROTO_DIR}")
        return False

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "__init__.py").touch()

    proto_files = list(PROTO_DIR.glob("*.proto"))
    if not proto_files:
        print(f"❌ No .proto files found in {PROTO_DIR}")
        return False

    print(f"📦 Found {len(proto_files)} proto file(s)")

    for proto_file in proto_files:
        print(f"🔨 Generating code from {proto_file.name}...")

        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grpc_tools.protoc",
                    f"-I{PROTO_DIR}",
                    f"--python_out={OUTPUT_DIR}",
                    f"--pyi_out={OUTPUT_DIR}",
                    f"--grpc_python_out={OUTPUT_DIR}",
                    str(proto_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"✅ Generated code from {proto_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating code from {proto_file.name}:")
            print(e.stderr)
            return False
        except FileNotFoundError:
            print(
                "❌ grpc_tools.protoc not found. Install with: pip install grpcio-tools"
            )
            return False

    for grpc_file in OUTPUT_DIR.glob("*_pb2_grpc.py"):
        _patch_grpc_module(grpc_file)

    for pyi_file in OUTPUT_DIR.glob("*_pb2.pyi"):
        _patch_pyi_module(pyi_file)

    print(f"\n✅ All proto files processed. Output in: {OUTPUT_DIR}")
    return True


if __name__ == "__main__":
    success = generate_proto_code()
    sys.exit(0 if success else 1)
