#!/bin/bash
# Generate protobuf stubs for all supported languages.
#
# Usage:
#   bash scripts/generate_protos.sh [language]
#
# Languages: python (default), typescript, all
#
# Prerequisites:
#   Python:     pip install grpcio-tools protobuf
#   TypeScript: npm install -g grpc_tools_node_protoc_ts @grpc/grpc-js

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/proto"
PROTO_FILE="$PROTO_DIR/agent_handler.proto"

LANGUAGE="${1:-python}"

if [ ! -f "$PROTO_FILE" ]; then
    echo "Error: Proto file not found at $PROTO_FILE"
    exit 1
fi

generate_python() {
    echo "Generating Python stubs..."
    local OUT_DIR="$PROJECT_ROOT/bindu/grpc/generated"
    mkdir -p "$OUT_DIR"

    uv run python -m grpc_tools.protoc \
        -I"$PROTO_DIR" \
        --python_out="$OUT_DIR" \
        --grpc_python_out="$OUT_DIR" \
        --pyi_out="$OUT_DIR" \
        "$PROTO_FILE"

    # Fix imports in generated grpc file (grpcio-tools generates absolute imports)
    local GRPC_FILE="$OUT_DIR/agent_handler_pb2_grpc.py"
    if [ -f "$GRPC_FILE" ]; then
        sed -i.bak 's/^import agent_handler_pb2/from bindu.grpc.generated import agent_handler_pb2/' "$GRPC_FILE"
        rm -f "$GRPC_FILE.bak"
    fi

    echo "Python stubs generated in $OUT_DIR"
}

generate_typescript() {
    echo "Generating TypeScript stubs..."
    local OUT_DIR="$PROJECT_ROOT/sdks/typescript/src/generated"
    mkdir -p "$OUT_DIR"

    # Using @grpc/proto-loader compatible generation
    npx grpc_tools_node_protoc \
        --ts_out=grpc_js:"$OUT_DIR" \
        --grpc_out=grpc_js:"$OUT_DIR" \
        -I"$PROTO_DIR" \
        "$PROTO_FILE" 2>/dev/null || {
        echo "Warning: TypeScript generation requires grpc_tools_node_protoc_ts"
        echo "Install with: npm install -g grpc_tools_node_protoc_ts"
    }

    echo "TypeScript stubs generated in $OUT_DIR"
}

case "$LANGUAGE" in
    python)
        generate_python
        ;;
    typescript|ts)
        generate_typescript
        ;;
    all)
        generate_python
        generate_typescript
        ;;
    *)
        echo "Unknown language: $LANGUAGE"
        echo "Supported: python, typescript, all"
        exit 1
        ;;
esac

echo "Done."
