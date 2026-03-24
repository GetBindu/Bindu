"""Bindu CLI — command-line interface for the Bindu framework.

Provides the `bindu` command with subcommands:
  - bindu serve --grpc  : Start the Bindu core with gRPC server for SDK registration

The CLI is primarily an internal interface used by language SDKs (TypeScript,
Kotlin, Rust) to spawn the Python core as a child process. End users typically
use bindufy() directly in their Python scripts.
"""

import argparse
import signal
import sys

from bindu.utils.logging import get_logger

logger = get_logger("bindu.cli")


def _handle_serve(args: argparse.Namespace) -> None:
    """Handle the `bindu serve` command.

    Starts the gRPC server on the specified port and waits for SDK agents
    to register via RegisterAgent. When an agent registers, the core runs
    the full bindufy logic and starts an HTTP server for that agent.

    Args:
        args: Parsed CLI arguments (port, grpc_port, grpc flag).
    """
    if not args.grpc:
        print("Error: --grpc flag is required for `bindu serve`")
        print("Usage: bindu serve --grpc [--grpc-port 3774]")
        sys.exit(1)

    # Import here to avoid loading heavy dependencies on --help
    from bindu.grpc.registry import AgentRegistry
    from bindu.grpc.server import start_grpc_server

    grpc_port = args.grpc_port
    registry = AgentRegistry()

    logger.info(f"Starting Bindu core with gRPC on port {grpc_port}")

    server = start_grpc_server(registry=registry, port=grpc_port)

    # Handle graceful shutdown
    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Block until terminated
    server.wait_for_termination()


def main() -> None:
    """Run the Bindu CLI."""
    parser = argparse.ArgumentParser(
        prog="bindu",
        description="Bindu Framework CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # bindu serve
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the Bindu core server",
    )
    serve_parser.add_argument(
        "--grpc",
        action="store_true",
        help="Enable gRPC server for language SDK registration",
    )
    serve_parser.add_argument(
        "--grpc-port",
        type=int,
        default=3774,
        help="gRPC server port (default: 3774)",
    )

    args = parser.parse_args()

    if args.command == "serve":
        _handle_serve(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
