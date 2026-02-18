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
using DSPy optimization techniques. It supports multiple optimization strategies,
evaluation metrics, and extraction methods for building golden datasets from
task history.
"""

from __future__ import annotations

import argparse

from dspy.teleprompt import SIMBA

from bindu.dspy.metrics import get_metric
from bindu.dspy.strategies import (
    FirstNTurnsStrategy,
    FullHistoryStrategy,
    LastNTurnsStrategy,
    LastTurnStrategy,
)
from bindu.dspy.train import train
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.cli.train")


def parse_strategy(
    name: str,
) -> LastTurnStrategy | FullHistoryStrategy | LastNTurnsStrategy | FirstNTurnsStrategy:
    """Parse strategy name string into strategy instance.

    Args:
        name: Strategy name. Supported values:
            - "last_turn": Extract only the last conversation turn
            - "full_history": Extract complete conversation history
            - "last_n:N": Extract last N turns (e.g., "last_n:3")
            - "first_n:N": Extract first N turns (e.g., "first_n:3")

    Returns:
        Instantiated strategy object.

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

    Parses CLI arguments, constructs the appropriate optimizer and metric,
    and invokes the training pipeline.
    """
    parser = argparse.ArgumentParser(
        description="Run DSPy prompt training"
    )

    parser.add_argument(
        "--optimizer",
        choices=["simba"],
        default="simba",
        help="Prompt optimizer to use (only 'simba' is supported)",
    )

    parser.add_argument(
        "--metric",
        choices=["embedding", "llm_judge"],
        default="embedding",
        help=(
            "Evaluation metric used during optimization.\n"
            "  embedding   - Cosine similarity in embedding space\n"
            "  llm_judge   - LLM-as-judge scoring"
        ),
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
        "--did",
        type=str,
        default=None,
        help=(
            "DID (Decentralized Identifier) for schema isolation.\n"
            "Example: did:bindu:author:agent:id"
        ),
    )

    parser.add_argument(
        "--min-feedback-threshold",
        type=float,
        default=None,
        help=(
            "Minimum feedback quality threshold for filtering interactions when "
            "building the golden dataset. Interactions with feedback scores below "
            "this threshold will be excluded. If not set, no filtering will be applied."
        ),
    )

    # Optimizer parameters
    parser.add_argument(
        "--bsize",
        type=int,
        default=32,
        help="Mini-batch size (default: 32)",
    )

    parser.add_argument(
        "--num-candidates",
        type=int,
        default=6,
        help="Number of candidate programs per iteration (default: 6)",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=8,
        help="Number of optimization steps (default: 8)",
    )

    parser.add_argument(
        "--max-demos",
        type=int,
        default=4,
        help="Maximum demonstrations per predictor (default: 4)",
    )

    parser.add_argument(
        "--num-threads",
        type=int,
        default=None,
        help="Number of threads for parallel execution (default: auto)",
    )

    args = parser.parse_args()

    logger.info(
        "Initializing DSPy training | "
        f"optimizer={args.optimizer}, "
        f"metric={args.metric}, "
        f"strategy={args.strategy}, "
        f"DID={args.did or 'public'}"
    )

    # Resolve metric
    metric_fn = get_metric(args.metric)

    # Construct optimizer
    if args.optimizer == "simba":
        optimizer = SIMBA(
            metric=metric_fn,
            bsize=args.bsize,
            num_candidates=args.num_candidates,
            max_steps=args.max_steps,
            max_demos=args.max_demos,
            num_threads=args.num_threads,
        )
    else:
        raise ValueError(f"Unsupported optimizer: {args.optimizer}")

    strategy = parse_strategy(args.strategy)

    train(
        optimizer=optimizer,
        strategy=strategy,
        did=args.did,
        min_feedback_threshold=args.min_feedback_threshold,
    )


if __name__ == "__main__":
    main()