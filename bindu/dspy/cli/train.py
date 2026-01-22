# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""CLI entry point for DSPy prompt training and optimization.

This module provides the command-line interface for training AI agent prompts
using DSPy optimization techniques. It supports multiple optimization strategies
and extraction methods for building golden datasets from task history.
"""

from __future__ import annotations

import argparse

from dspy.teleprompt import GEPA, SIMBA

from bindu.dspy.strategies import (
    FirstNTurnsStrategy,
    FullHistoryStrategy,
    LastNTurnsStrategy,
    LastTurnStrategy,
)
from bindu.dspy.train import train
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.cli.train")


def parse_strategy(name: str) -> LastTurnStrategy | FullHistoryStrategy | LastNTurnsStrategy | FirstNTurnsStrategy:
    """Parse strategy name string into strategy instance.
    
    Args:
        name: Strategy name. Supported values:
            - "last_turn": Extract only the last conversation turn
            - "full_history": Extract complete conversation history
            - "last_n:N": Extract last N turns (e.g., "last_n:3")
            - "first_n:N": Extract first N turns (e.g., "first_n:3")
    
    Returns:
        Instantiated strategy object based on the name.
    
    Raises:
        ValueError: If strategy name is not recognized.
    """
    if name == "last_turn":
        return LastTurnStrategy()
    if name == "full_history":
        return FullHistoryStrategy()
    if name.startswith("last_n:"):
        n = int(name.split(":")[1])
        return LastNTurnsStrategy(n_turns=n)
    if name.startswith("first_n:"):
        n = int(name.split(":")[1])
        return FirstNTurnsStrategy(n_turns=n)
    raise ValueError(f"Unknown strategy: {name}")


def main() -> None:
    """Run DSPy prompt training from command line.
    
    This function parses command-line arguments and orchestrates the training
    process using the specified optimizer and extraction strategy.
    """
    parser = argparse.ArgumentParser(description="Run DSPy prompt training")

    parser.add_argument(
        "--optimizer",
        choices=["simba", "gepa"],
        required=True,
        help="Prompt optimizer to use",
    )

    parser.add_argument(
        "--strategy",
        default="last_turn",
        help=(
            "Extraction strategy. Examples:\n"
            "  last_turn\n"
            "  full_history\n"
            "  last_n:3\n"
            "  first_n:3"
        ),
    )

    parser.add_argument(
        "--require-feedback",
        action="store_true",
        help="Only use interactions with feedback",
    )

    args = parser.parse_args()

    # Metric is implicitly feedback-based inside dataset
    if args.optimizer == "simba":
        optimizer = SIMBA()
    else:
        optimizer = GEPA()

    strategy = parse_strategy(args.strategy)

    train(
        optimizer=optimizer,
        strategy=strategy,
        require_feedback=args.require_feedback,
    )


if __name__ == "__main__":
    main()