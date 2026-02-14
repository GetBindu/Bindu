"""Server startup and shutdown utilities.

This module provides utilities for starting uvicorn servers with proper
signal handling and graceful shutdown.
"""

import signal
import sys
from typing import Any

import uvicorn

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.server_runner")


def setup_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown.

    Registers handlers for SIGINT (Ctrl+C) and SIGTERM (Docker/systemd stop).
    """

    def handle_shutdown(signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name
        logger.info(f"\n🛑 Received {signal_name}, initiating graceful shutdown...")
        logger.info("Cleaning up resources (storage, scheduler, tasks)...")
        # uvicorn will handle the actual cleanup via lifespan context
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_shutdown)  # Docker/systemd stop

    logger.debug("Signal handlers registered for graceful shutdown")


def run_server(app: Any, host: str, port: int, display_info: bool = True) -> None:
    """Run uvicorn server with graceful shutdown handling.

    Args:
        app: ASGI application to serve
        host: Host address to bind to
        port: Port number to bind to
        display_info: Whether to display startup info messages
    """
    # Setup signal handlers
    setup_signal_handlers()

    if display_info:
        logger.info(f"Starting uvicorn server at {host}:{port}...")
        logger.info("Press Ctrl+C to stop the server gracefully")

    ssl_kwargs = {}

    # Configure mTLS if enabled
    from bindu.settings import app_settings

    if app_settings.security.mtls_enabled:
        import ssl
        from pathlib import Path

        cert_dir = Path(app_settings.security.cert_dir)
        cert_path = cert_dir / "agent.crt"
        key_path = cert_dir / "agent.key"
        ca_path = cert_dir / "ca.crt"

        if not (cert_path.exists() and key_path.exists() and ca_path.exists()):
            logger.error(f"mTLS enabled but certificates not found in {cert_dir}")
            sys.exit(1)

        logger.info("🔒 mTLS enabled: enforcing mutual authentication")

        # Create SSL context for strict mTLS
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_verify_locations(cafile=str(ca_path))
        ssl_context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

        ssl_kwargs = {
            "ssl_certfile": str(cert_path),
            "ssl_keyfile": str(key_path),
            "ssl_ca_certs": str(ca_path),
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_version": ssl.PROTOCOL_TLS_SERVER,
        }

    try:
        uvicorn.run(app, host=host, port=port, **ssl_kwargs)
    except KeyboardInterrupt:
        # This shouldn't be reached due to signal handler, but just in case
        logger.info("\n🛑 Server interrupted, shutting down...")
    finally:
        # Note: Cleanup happens in BinduApplication's lifespan context manager
        logger.info("✅ Server stopped cleanly")
