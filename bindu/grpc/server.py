"""gRPC server for the Bindu core — accepts SDK registrations on port 3774.

This module starts a gRPC server that implements BinduService. External
SDKs (TypeScript, Kotlin, Rust) connect to this server to register their
agents via RegisterAgent.

The server uses a ThreadPoolExecutor for concurrent request handling.
It is started either:
  - By the `bindu serve --grpc` CLI command (standalone mode)
  - By BinduApplication lifespan when grpc.enabled=True (integrated mode)

Usage:
    from bindu.grpc.server import start_grpc_server
    from bindu.grpc.registry import AgentRegistry

    registry = AgentRegistry()
    server = start_grpc_server(registry)
    server.wait_for_termination()  # blocks
"""

from __future__ import annotations

from concurrent import futures

import grpc

from bindu.grpc.generated import agent_handler_pb2_grpc
from bindu.grpc.registry import AgentRegistry
from bindu.grpc.service import BinduServiceImpl
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.grpc.server")


def start_grpc_server(
    registry: AgentRegistry | None = None,
    host: str | None = None,
    port: int | None = None,
    max_workers: int | None = None,
) -> grpc.Server:
    """Start the Bindu gRPC server for SDK agent registration.

    Creates a gRPC server that serves BinduService, allowing external SDKs
    to register agents via RegisterAgent RPC.

    Args:
        registry: Agent registry instance. Creates a new one if None.
        host: Bind host. Defaults to app_settings.grpc.host.
        port: Bind port. Defaults to app_settings.grpc.port (3774).
        max_workers: Thread pool size. Defaults to app_settings.grpc.max_workers.

    Returns:
        The started grpc.Server instance. Call wait_for_termination() to block,
        or stop() to shut down.
    """
    registry = registry or AgentRegistry()
    host = host or app_settings.grpc.host
    port = port or app_settings.grpc.port
    max_workers = max_workers or app_settings.grpc.max_workers

    # Create gRPC server with thread pool
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            (
                "grpc.max_receive_message_length",
                app_settings.grpc.max_message_length,
            ),
            (
                "grpc.max_send_message_length",
                app_settings.grpc.max_message_length,
            ),
        ],
    )

    # Register BinduService
    agent_handler_pb2_grpc.add_BinduServiceServicer_to_server(
        BinduServiceImpl(registry),
        server,
    )

    # Bind to address
    bind_address = f"{host}:{port}"
    server.add_insecure_port(bind_address)

    # Start serving
    server.start()
    logger.info(f"gRPC server started on {bind_address}")
    logger.info(
        "Waiting for SDK agent registrations... "
        "(TypeScript, Kotlin, Rust agents can now connect)"
    )

    return server
