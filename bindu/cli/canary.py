# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""CLI entry point for DSPy canary deployment controller.

This module provides the command-line interface for running the canary controller,
which manages A/B testing and gradual rollout of optimized prompts.
"""

from __future__ import annotations

import argparse
import asyncio

from bindu.dspy.canary.controller import run_canary_controller
from bindu.utils.logging import get_logger

logger = get_logger("bindu.cli.canary")


def main() -> None:
    """Run the canary deployment controller.
    
    This function serves as the main entry point for the canary CLI.
    It orchestrates the canary deployment process for prompt optimization.
    """
    parser = argparse.ArgumentParser(
        description="Run the canary deployment controller for A/B testing prompts"
    )

    parser.add_argument(
        "--did",
        required=True,
        type=str,
        help=(
            "Decentralized Identifier (DID) for schema isolation. "
            "Required for multi-tenancy support."
        ),
    )

    args = parser.parse_args()
    
    logger.info(f"Starting canary controller for DID: {args.did}")
    asyncio.run(run_canary_controller(did=args.did))


if __name__ == "__main__":
    main()