"""Bindu CLI — command-line interface for the Bindu framework.

Provides the ``bindu`` command with subcommands:

  - ``bindu serve --grpc``       : start the Bindu core for SDK registration
  - ``bindu serve --script PATH`` : execute a user agent script (the script
    calls ``bindufy()`` itself). Used by ``BoxdRuntimeProvider`` inside the VM.
"""

import argparse
import os
import signal
import sys

from bindu.utils.logging import get_logger

logger = get_logger("bindu.cli")


def _handle_serve(args: argparse.Namespace) -> None:
    """Handle the ``bindu serve`` command.

    Modes:
      ``--script <path>``: execute a user agent script.
      ``--grpc``:          start the gRPC core for SDK registration.
    """
    if args.script:
        _run_user_script(args.script)
        return

    if not args.grpc:
        print("Error: --grpc or --script required for `bindu serve`")
        print("Usage:")
        print("  bindu serve --grpc [--grpc-port 3774]")
        print("  bindu serve --script <path>")
        sys.exit(1)

    # Import here to avoid loading heavy dependencies on --help
    from bindu.grpc.registry import AgentRegistry
    from bindu.grpc.server import start_grpc_server

    grpc_port = args.grpc_port
    registry = AgentRegistry()

    logger.info(f"Starting Bindu core with gRPC on port {grpc_port}")

    server = start_grpc_server(registry=registry, port=grpc_port)

    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    server.wait_for_termination()


def _run_user_script(path: str) -> None:
    """Execute the user's agent script in ``__main__`` context."""
    import runpy

    script_path = os.path.abspath(path)
    sys.path.insert(0, os.path.dirname(script_path))
    runpy.run_path(script_path, run_name="__main__")


def main() -> None:
    """Run the Bindu CLI."""
    parser = argparse.ArgumentParser(prog="bindu", description="Bindu Framework CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    serve_parser = subparsers.add_parser(
        "serve", help="Start the Bindu core or execute a user agent script"
    )
    serve_parser.add_argument(
        "--grpc",
        action="store_true",
        help="Enable gRPC server for SDK registration",
    )
    serve_parser.add_argument(
        "--grpc-port",
        type=int,
        default=3774,
        help="gRPC server port (default: 3774)",
    )
    serve_parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Path to a user agent script that calls bindufy()",
    )

    args = parser.parse_args()

    if args.command == "serve":
        _handle_serve(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
