"""gRPC server implementation for Bindu."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Optional, cast

import grpc
from grpc import aio as grpc_aio  # type: ignore[attr-defined]

from bindu.server.applications import BinduApplication
from bindu.settings import app_settings
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
        await grpc_server.wait_for_termination()
        ```
    """

    def __init__(
        self,
        app: BinduApplication,
        port: int = 50051,
        host: str = "[::]",
        max_workers: int = 10,
        tls_enabled: bool = False,
        tls_cert_path: str | None = None,
        tls_key_path: str | None = None,
    ):
        """Initialize gRPC server.

        Args:
            app: Bindu application instance
            port: Port to listen on (default: 50051)
            host: Host to bind to (default: "[::]" for IPv6)
            max_workers: Maximum number of concurrent RPCs to allow
            tls_enabled: Enable TLS for gRPC server
            tls_cert_path: Path to PEM-encoded TLS certificate chain
            tls_key_path: Path to PEM-encoded TLS private key
        """
        self.app = app
        self.port = port
        self.host = host
        self.max_workers = max_workers
        self.tls_enabled = tls_enabled
        self.tls_cert_path = tls_cert_path
        self.tls_key_path = tls_key_path
        self._server: Optional[grpc_aio.Server] = None

    async def start(self) -> None:
        """Start the gRPC server without blocking."""
        if self._server is not None:
            logger.warning("gRPC server is already running")
            return

        listen_addr = f"{self.host}:{self.port}"
        server_credentials: grpc.ServerCredentials | None = None
        if self.tls_enabled:
            if not self.tls_cert_path or not self.tls_key_path:
                raise ValueError(
                    "gRPC TLS is enabled but certificate/key paths are not set"
                )
            cert_bytes = Path(self.tls_cert_path).read_bytes()
            key_bytes = Path(self.tls_key_path).read_bytes()
            server_credentials = grpc.ssl_server_credentials([(key_bytes, cert_bytes)])

        interceptors: list[grpc_aio.ServerInterceptor] = []
        if app_settings.auth.enabled:
            from .auth import GrpcAuthInterceptor

            interceptors.append(
                GrpcAuthInterceptor(app_settings.auth, hydra_config=app_settings.hydra)
            )
            logger.info("gRPC auth interceptor enabled")

        # Create gRPC server
        self._server = grpc_aio.server(
            interceptors=interceptors or None,
            maximum_concurrent_rpcs=self.max_workers,
        )

        # Add servicer (requires generated protobuf code)
        try:
            from .servicer import A2AServicer

            a2a_pb2_grpc = cast(Any, importlib.import_module("bindu.grpc.a2a_pb2_grpc"))
            servicer = A2AServicer(self.app.task_manager)
            a2a_pb2_grpc.add_A2AServiceServicer_to_server(servicer, self._server)
            logger.info("A2AServicer registered successfully")
        except ImportError as e:
            logger.warning(
                f"Could not register servicer - protobuf code not generated: {e}. "
                "Run: python scripts/generate_proto.py"
            )
            # Server will start but won't handle requests until protobuf code is generated

        if self.tls_enabled:
            if server_credentials is None:
                raise RuntimeError(
                    "gRPC TLS is enabled but server credentials were not created"
                )
            self._server.add_secure_port(listen_addr, server_credentials)
        else:
            self._server.add_insecure_port(listen_addr)

        # Start server
        await self._server.start()
        logger.info(f"gRPC server started on {listen_addr}")

    async def wait_for_termination(self) -> None:
        """Block until the gRPC server terminates."""
        if self._server is None:
            logger.warning("gRPC server is not running")
            return
        await self._server.wait_for_termination()

    async def serve(self) -> None:
        """Start the gRPC server and wait for termination."""
        await self.start()
        await self.wait_for_termination()

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
