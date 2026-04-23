"""Bindu gRPC Adapter — Language-agnostic agent support.

This package enables agents written in any language (TypeScript, Kotlin, Rust, etc.)
to register with the Bindu core and be executed as microservices.

Architecture:
    The gRPC adapter has two sides:

    1. BinduService (core side, port 3774):
       - Receives RegisterAgent calls from language SDKs
       - Runs the full bindufy logic (DID, auth, x402, manifest, HTTP server)
       - Manages agent lifecycle (heartbeat, unregister)

    2. GrpcAgentClient (core → SDK):
       - Callable that replaces manifest.run for remote agents
       - Calls HandleMessages on the SDK's AgentHandler service
       - Returns results in the same format as Python handlers

    The key invariant: GrpcAgentClient is a drop-in replacement for manifest.run.
    ManifestWorker, ResultProcessor, and ResponseDetector require zero changes.

Usage:
    # Start core with gRPC enabled
    bindufy(config, handler, grpc=True)

    # Or via environment variable
    GRPC__ENABLED=true python my_agent.py
"""

from bindu.grpc.client import GrpcAgentClient
from bindu.grpc.registry import AgentRegistry
from bindu.grpc.server import start_grpc_server

__all__ = [
    "GrpcAgentClient",
    "AgentRegistry",
    "start_grpc_server",
]
