"""gRPC server implementation for Bindu."""

from __future__ import annotations

import asyncio
from typing import Optional

import grpc
from grpc import aio

from bindu.server.applications import BinduApplication
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.server")


class GrpcServer:
    """gRPC server for Bindu agents.

    This server provides gRPC endpoints alongside the existing JSON-RPC server,
    enabling dual protocol support for agent communication.

    Example:
        ```python
        from bindu.server.grpc import GrpcServer
        from bindu.server.applications import BinduApplication

        app = BinduApplication(...)
        grpc_server = GrpcServer(app, port=50051)
        await grpc_server.start()
        ```
    """

    def __init__(
        self,
        app: BinduApplication,
        port: int = 50051,
        host: str = "[::]",
        max_workers: int = 10,
    ):
        """Initialize gRPC server.

        Args:
            app: Bindu application instance
            port: Port to listen on (default: 50051)
            host: Host to bind to (default: "[::]" for IPv6)
            max_workers: Maximum number of worker threads
        """
        self.app = app
        self.port = port
        self.host = host
        self.max_workers = max_workers
        self._server: Optional[aio.Server] = None

    async def start(self) -> None:
        """Start the gRPC server."""
        if self._server is not None:
            logger.warning("gRPC server is already running")
            return

        # Create gRPC server
        self._server = aio.server()
        
        # Add servicer (requires generated protobuf code)
        try:
            from .servicer import A2AServicer
            from bindu.grpc import a2a_pb2_grpc
            
            servicer = A2AServicer(self.app.task_manager)
            a2a_pb2_grpc.add_A2AServiceServicer_to_server(servicer, self._server)
            logger.info("A2AServicer registered successfully")
        except ImportError as e:
            logger.warning(
                f"Could not register servicer - protobuf code not generated: {e}. "
                "Run: python scripts/generate_proto.py"
            )
            # Server will start but won't handle requests until protobuf code is generated

        # Add insecure port (for now - TLS support can be added later)
        listen_addr = f"{self.host}:{self.port}"
        self._server.add_insecure_port(listen_addr)

        # Start server
        await self._server.start()
        logger.info(f"gRPC server started on {listen_addr}")

        # Keep server running
        await self._server.wait_for_termination()

    async def stop(self, grace_period: float = 5.0) -> None:
        """Stop the gRPC server.

        Args:
            grace_period: Time to wait for ongoing requests to complete
        """
        if self._server is None:
            return

        logger.info("Stopping gRPC server...")
        await self._server.stop(grace_period)
        self._server = None
        logger.info("gRPC server stopped")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

