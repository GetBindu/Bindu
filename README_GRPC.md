# gRPC Support for Bindu (Issue #67)

This document tracks the implementation of gRPC support for Bindu agents.

## Status: 🚧 In Progress

This is a work-in-progress feature. See [Issue #67](https://github.com/GetBindu/Bindu/issues/67) for the full design document.

## Current Progress

### ✅ Completed
- [x] Protocol Buffer definitions (`.proto` files)
- [x] Basic gRPC server structure
- [x] Placeholder servicer implementation

### 🚧 In Progress
- [ ] Generate Python code from `.proto` files
- [ ] Implement protobuf ↔ Pydantic conversion utilities
- [ ] Implement A2AServicer methods
- [ ] Add gRPC server to BinduApplication
- [ ] Add tests
- [ ] Add documentation and examples

### 📋 TODO
- [ ] TLS/SSL support
- [ ] Streaming support
- [ ] Performance benchmarking
- [ ] Client libraries
- [ ] Migration guide

## Getting Started

### Prerequisites

Install gRPC tools:

```bash
pip install grpcio grpcio-tools
```

### Generate Python Code from Proto Files

```bash
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./bindu/grpc \
    --grpc_python_out=./bindu/grpc \
    ./proto/a2a.proto
```

### Running the gRPC Server

```python
from bindu.server.grpc import GrpcServer
from bindu.server.applications import BinduApplication

app = BinduApplication(...)
grpc_server = GrpcServer(app, port=50051)

# Start server
await grpc_server.start()
```

## Contributing

We welcome contributions! Areas that need help:

1. **Protocol Converters**: Implement protobuf ↔ Pydantic conversion
2. **Servicer Implementation**: Complete the A2AServicer methods
3. **Testing**: Add unit and integration tests
4. **Documentation**: Improve docs and add examples
5. **Performance**: Optimize gRPC streaming

See [CONTRIBUTING.md](.github/contributing.md) for guidelines.

## References

- [Issue #67](https://github.com/GetBindu/Bindu/issues/67) - Full design document
- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protocol Buffers Guide](https://protobuf.dev/getting-started/pythontutorial/)

