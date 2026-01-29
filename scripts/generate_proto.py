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
            print("❌ grpc_tools.protoc not found. Install with: pip install grpcio-tools")
            return False

    print(f"\n✅ All proto files processed. Output in: {OUTPUT_DIR}")
    return True


if __name__ == "__main__":
    success = generate_proto_code()
    sys.exit(0 if success else 1)

