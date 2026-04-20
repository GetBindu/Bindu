"""Server startup and shutdown utilities.

This module provides utilities for starting uvicorn servers with proper
signal handling and graceful shutdown.
"""

import signal
import sys
import threading
from typing import Any

import uvicorn

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.server_runner")


def setup_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown.

    Registers handlers for SIGINT (Ctrl+C) and SIGTERM (Docker/systemd stop).
    Skips registration if not running in the main thread (e.g., when uvicorn
    is started in a background thread by the gRPC registration flow).
    """
    if threading.current_thread() is not threading.main_thread():
        logger.debug("Skipping signal handler registration (not in main thread)")
        return

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

    Supports being called from both the main thread (normal bindufy flow)
    and from a background thread (gRPC registration flow via _bindufy_core
    with run_server_in_background=True).

    Args:
        app: ASGI application to serve
        host: Host address to bind to
        port: Port number to bind to
        display_info: Whether to display startup info messages
    """
    # Setup signal handlers (skips automatically if not in main thread)
    setup_signal_handlers()

    if display_info:
        logger.info(f"Starting uvicorn server at {host}:{port}...")
        logger.info("Press Ctrl+C to stop the server gracefully")

    try:
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        # This shouldn't be reached due to signal handler, but just in case
        logger.info("\n🛑 Server interrupted, shutting down...")
    finally:
        # Note: Cleanup happens in BinduApplication's lifespan context manager
        logger.info("✅ Server stopped cleanly")
