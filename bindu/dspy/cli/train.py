# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose     |
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


def feedback_metric(example, prediction_dict, trace=None):
    """Compute training metric using feedback scores.

    This metric prioritizes explicit feedback scores when available,
    and falls back to exact match comparison otherwise.

    IMPORTANT: This function signature matches DSPy SIMBA's requirement:
    metric: Callable[[dspy.Example, dict[str, Any]], float]

    Args:
        example: DSPy Example with input, output, and optional feedback
        prediction_dict: Dictionary containing prediction outputs (has 'output' key)
        trace: Optional trace for optimization (unused)

    Returns:
        Float score between 0.0 and 1.0
    """
    # Validate prediction has output
    if not prediction_dict or 'output' not in prediction_dict:
        return 0.0

    actual_output = prediction_dict.get('output', '')
    if not actual_output:
        return 0.0

    # Use explicit feedback score if available
    if hasattr(example, 'feedback') and example.feedback:
        feedback_score = example.feedback.get('score')
        if feedback_score is not None:
            return float(feedback_score)

    # Fallback to exact match
    expected = example.output if hasattr(example, 'output') else ""
    return 1.0 if expected.strip() == actual_output.strip() else 0.0


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

    parser.add_argument(
        "--did",
        type=str,
        default=None,
        help="DID (Decentralized Identifier) for schema isolation. Example: did:bindu:author:agent:id",
    )

    # SIMBA optimizer parameters
    parser.add_argument(
        "--bsize",
        type=int,
        default=32,
        help="Mini-batch size for SIMBA optimizer (default: 32)",
    )

    parser.add_argument(
        "--num-candidates",
        type=int,
        default=6,
        help="Number of candidate programs to produce per iteration (default: 6)",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=8,
        help="Number of optimization steps to run (default: 8)",
    )

    parser.add_argument(
        "--max-demos",
        type=int,
        default=4,
        help="Maximum number of demonstrations per predictor (default: 4)",
    )

    parser.add_argument(
        "--num-threads",
        type=int,
        default=None,
        help="Number of threads for parallel execution (default: None = auto)",
    )

    args = parser.parse_args()

    # Create optimizer with feedback metric and parameters
    if args.optimizer == "simba":
        optimizer = SIMBA(
            metric=feedback_metric,
            bsize=args.bsize,
            num_candidates=args.num_candidates,
            max_steps=args.max_steps,
            max_demos=args.max_demos,
            num_threads=args.num_threads,
        )
    else:
        # GEPA also accepts similar parameters
        optimizer = GEPA(
            metric=feedback_metric,
            bsize=args.bsize,
            num_candidates=args.num_candidates,
            max_steps=args.max_steps,
            max_demos=args.max_demos,
            num_threads=args.num_threads,
        )

    strategy = parse_strategy(args.strategy)

    train(
        optimizer=optimizer,
        strategy=strategy,
        require_feedback=args.require_feedback,
        did=args.did,
    )


if __name__ == "__main__":
    main()