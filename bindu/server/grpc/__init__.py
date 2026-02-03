"""gRPC server implementation for Bindu.

This module provides gRPC support for Bindu agents, enabling dual protocol
communication (JSON-RPC over HTTP and gRPC).

See issue #67 for the full design: https://github.com/GetBindu/Bindu/issues/67
"""

from .server import GrpcServer
from .servicer import A2AServicer

__all__ = ["GrpcServer", "A2AServicer"]
