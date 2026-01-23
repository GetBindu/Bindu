# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Training orchestration for DSPy prompt optimization.

This module provides the main training pipeline that coordinates all steps
of the prompt optimization process, from data collection to candidate generation.
"""


from __future__ import annotations

import asyncio
from typing import Any

import dspy

from bindu.utils.logging import get_logger

from bindu.settings import app_settings
from .dataset import build_golden_dataset, convert_to_dspy_examples
from .strategies import BaseExtractionStrategy, LastTurnStrategy
from .guard import ensure_system_stable
from .models import PromptCandidate
from .optimizer import optimize
from .program import AgentProgram
from .prompts import (
    get_active_prompt,
    insert_prompt,
    update_prompt_traffic,
    zero_out_all_except,
)

from dspy.teleprompt import SIMBA, GEPA

logger = get_logger("bindu.dspy.train")

async def train_async(
    optimizer: Any,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
) -> None:
    """Train and optimize agent prompts using DSPy.

    This function orchestrates the complete training pipeline:
    1. Ensures system is stable (no active experiments)
    2. Fetches current active prompt from database
    3. Configures DSPy with the default language model
    4. Builds golden dataset using the complete pipeline:
       - Fetch raw task data with feedback from PostgreSQL
       - Normalize feedback
       - Extract interactions (with configurable strategy)
       - Filter by feedback quality
       - Validate and clean
       - Deduplicate
    5. Converts dataset to DSPy Example format
    6. Loads the agent program with active prompt
    7. Runs DSPy optimization with the provided optimizer
    8. Initializes A/B test:
       - Inserts optimized prompt as candidate (10% traffic)
       - Sets active prompt to 90% traffic
       - Zeros out all other prompts

    Args:
        optimizer: DSPy optimizer instance to use for training.
            If None, uses BootstrapFewShot with default settings.
        strategy: Extraction strategy to use. Defaults to LastTurnStrategy.
            Use strategy classes from bindu.dspy.strategies:
            - LastTurnStrategy()
            - FullHistoryStrategy()
            - LastNTurnsStrategy(n_turns=3)
            - FirstNTurnsStrategy(n_turns=3)
            - ContextWindowStrategy(n_turns=3, system_prompt="...")
        require_feedback: Whether to require feedback for inclusion in dataset
    Returns:
        None. The optimized prompt is inserted into the database as a candidate.

    Raises:
        RuntimeError: If an experiment is already active or STORAGE__POSTGRES_URL not set
        ConnectionError: If unable to connect to database
        ValueError: If golden dataset pipeline fails or no active prompt found

    Example:
        >>> from dspy.teleprompt import MIPRO
        >>> from bindu.dspy.strategies import ContextWindowStrategy
        >>> import asyncio
        >>> strategy = ContextWindowStrategy(n_turns=3, system_prompt="Be helpful")
        >>> optimizer = MIPRO(num_candidates=10, metric=my_metric)
        >>> candidates = asyncio.run(train_async(
        ...     optimizer=optimizer,
        ...     strategy=strategy
        ... ))
        >>> best_prompt = candidates[0]

    Note:
        This is an async function. When calling from async code, use await.
        For sync contexts, use the train() wrapper function instead.
        
        DSPy training only initializes experiments. It does NOT:
        - Promote candidates to active
        - Rollback prompts
        - Adjust traffic beyond initial 90/10 split
    """
    strategy = strategy or LastTurnStrategy()
    logger.info(f"Starting DSPy training pipeline with {strategy.name} strategy")

    # Step 0: Ensure system is stable (no active experiments)
    logger.info("Checking system stability")
    await ensure_system_stable()

    # Step 1: Fetch current active prompt from database
    logger.info("Fetching active prompt from database")
    active_prompt = await get_active_prompt()
    if active_prompt is None:
        raise ValueError(
            "No active prompt found in database. System requires an active prompt "
            "before DSPy training can begin."
        )
    
    current_prompt_text = active_prompt["prompt_text"]
    logger.info(f"Using active prompt (id={active_prompt['id']}) as base for optimization")

    # Step 2: Configure DSPy with default model
    logger.info(f"Configuring DSPy with model: {app_settings.dspy.default_model}")
    lm = dspy.LM(app_settings.dspy.default_model)
    dspy.configure(lm=lm)

    # Step 3: Build golden dataset using complete pipeline (fetches data internally)
    logger.info(
        f"Building golden dataset (strategy={strategy.name}, "
        f"require_feedback={require_feedback}, "
        f"threshold={app_settings.dspy.min_feedback_threshold})"
    )
    golden_dataset = await build_golden_dataset(
        limit=None,  # Use default from settings
        strategy=strategy,
        require_feedback=require_feedback,
        min_feedback_threshold=app_settings.dspy.min_feedback_threshold,
    )

    logger.info(f"Golden dataset prepared with {len(golden_dataset)} examples")

    # Step 5: Convert to DSPy examples
    logger.info("Converting to DSPy examples")
    dspy_examples = convert_to_dspy_examples(golden_dataset)

    # Step 6: Load agent program
    logger.info("Initializing agent program")
    program = AgentProgram(current_prompt_text)

    # Step 7: Validate optimizer and prompt requirements
    # v1 only supports prompt-mutating optimizers (SIMBA / GEPA).
    # These optimizers require an existing prompt to refine.
    if optimizer is None:
        raise ValueError(
            "v1 requires an explicit prompt-optimizing optimizer "
            "(SIMBA or GEPA)."
        )

    if not isinstance(optimizer, (SIMBA, GEPA)):
        raise ValueError(
            f"Optimizer {type(optimizer).__name__} does not support "
            "prompt extraction in v1."
        )

    if not current_prompt_text.strip():
        raise ValueError(
            "current_prompt_text must be provided for prompt optimization."
        )

    # Step 7: Run prompt optimization
    # The optimizer mutates the program's instructions based on the dataset.
    logger.info(
        f"Running prompt optimization using {type(optimizer).__name__}"
    )
    optimized_program = optimize(
        program=program,
        dataset=dspy_examples,
        optimizer=optimizer,
    )

    logger.info(
        "Extracting optimized instructions from predictor"
    )
    instructions = optimized_program.instructions
    
    if not instructions or not instructions.strip():
        raise RuntimeError("Optimizer did not produce valid instructions")

    # Step 9: Initialize A/B test with optimized prompt
    # DSPy training creates the candidate and sets initial traffic split.
    # It does NOT promote, rollback, or adjust traffic beyond this point.
    
    logger.info("Inserting optimized prompt as candidate with 10% traffic")
    candidate_id = await insert_prompt(
        text=instructions,
        status="candidate",
        traffic=0.10,
    )
    logger.info(f"Candidate prompt inserted (id={candidate_id})")
    
    # Set active prompt to 90% traffic (already fetched in Step 1)
    active_id = active_prompt["id"]
    logger.info(f"Setting active prompt (id={active_id}) to 90% traffic")
    await update_prompt_traffic(active_id, 0.90)
    
    # Zero out traffic for all other prompts
    logger.info("Zeroing out traffic for all other prompts")
    await zero_out_all_except([active_id, candidate_id])
    
    logger.info(
        f"A/B test initialized: active (id={active_id}) at 90%, "
        f"candidate (id={candidate_id}) at 10%"
    )

def train(
    optimizer: Any = None,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
) -> None:
    """Synchronous wrapper for train_async().

    This function provides a synchronous interface to the async training pipeline.
    For use in async contexts, call train_async() directly.

    Args:
        optimizer: DSPy optimizer instance (default: None)
        strategy: Extraction strategy (LAST_TURN or FULL_HISTORY)
        require_feedback: Whether to require feedback for inclusion in dataset

    Returns:
        None. The optimized prompt is inserted into the database as a candidate.

    Raises:
        RuntimeError: If called from within an async event loop. Use train_async() instead.
    """
    try:
        asyncio.run(
            train_async(
                optimizer=optimizer,
                strategy=strategy,
                require_feedback=require_feedback,
            )
        )
    except RuntimeError as e:
        if "event loop" in str(e):
            raise RuntimeError(
                "train() cannot be called from an async context. "
                "Use 'await train_async()' instead."
            ) from e
        raise