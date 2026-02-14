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


def run_server(
    app: Any,
    host: str,
    port: int,
    display_info: bool = True,
    ssl_keyfile: str | None = None,
    ssl_certfile: str | None = None,
    ssl_ca_certs: str | None = None,
    ssl_cert_reqs: int = 0,
) -> None:
    """Run uvicorn server with graceful shutdown handling.

    Args:
        app: ASGI application to serve
        host: Host address to bind to
        port: Port number to bind to
        display_info: Whether to display startup info messages
        ssl_keyfile: Path to SSL key file
        ssl_certfile: Path to SSL certificate file
        ssl_ca_certs: Path to CA certificate file
        ssl_cert_reqs: SSL certificate requirements (default: 0 - ssl.CERT_NONE)
    """
    # Setup signal handlers
    setup_signal_handlers()

    if display_info:
        logger.info(f"Starting uvicorn server at {host}:{port}...")
        logger.info("Press Ctrl+C to stop the server gracefully")

    try:
        if ssl_keyfile and ssl_certfile:
            logger.info(f"🔒 Starting server with SSL/TLS enabled (mTLS: {'enabled' if ssl_cert_reqs else 'disabled'})")
            uvicorn.run(
                app,
                host=host,
                port=port,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
                ssl_ca_certs=ssl_ca_certs,
                ssl_cert_reqs=ssl_cert_reqs,
            )
        else:
            uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        # This shouldn't be reached due to signal handler, but just in case
        logger.info("\n🛑 Server interrupted, shutting down...")
    finally:
        # Note: Cleanup happens in BinduApplication's lifespan context manager
        logger.info("✅ Server stopped cleanly")
