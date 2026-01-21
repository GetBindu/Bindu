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

from .config import (
    DEFAULT_DSPY_MODEL,
    MIN_FEEDBACK_THRESHOLD,
)
from .dataset import build_golden_dataset, convert_to_dspy_examples
from .extractor import ExtractionStrategy
from .guard import ensure_system_stable
from .models import PromptCandidate
from .optimizer import optimize
from .postgres import fetch_raw_task_data
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
    current_prompt_text: str,
    strategy: ExtractionStrategy = ExtractionStrategy.LAST_TURN,
    require_feedback: bool = True,
) -> None:
    """Train and optimize agent prompts using DSPy.

    This function orchestrates the complete training pipeline:
    1. Ensures system is stable (no active experiments)
    2. Configures DSPy with the default language model
    3. Fetches raw task data with feedback from PostgreSQL
    4. Builds golden dataset using the complete pipeline:
       - Normalize feedback
       - Extract interactions (with configurable strategy)
       - Filter by feedback quality
       - Validate and clean
       - Deduplicate
    5. Converts dataset to DSPy Example format
    6. Loads the agent program
    7. Runs DSPy optimization with the provided optimizer
    8. Initializes A/B test:
       - Inserts optimized prompt as candidate (10% traffic)
       - Sets active prompt to 90% traffic
       - Zeros out all other prompts

    Args:
        optimizer: DSPy optimizer instance to use for training (SIMBA or GEPA required).
        current_prompt_text: Current prompt text to initialize and optimize.
        strategy: Extraction strategy (LAST_TURN or FULL_HISTORY)
        require_feedback: Whether to require feedback for inclusion in dataset

    Returns:
        None. The optimized prompt is inserted into the database as a candidate.

    Raises:
        RuntimeError: If an experiment is already active or STORAGE__POSTGRES_URL not set
        ConnectionError: If unable to connect to database
        ValueError: If golden dataset pipeline fails

    Example:
        >>> from dspy.teleprompt import SIMBA
        >>> from bindu.dspy.extractor import ExtractionStrategy
        >>> import asyncio
        >>> optimizer = SIMBA()
        >>> await train_async(
        ...     optimizer=optimizer,
        ...     current_prompt_text="You are a helpful assistant.",
        ...     strategy=ExtractionStrategy.FULL_HISTORY
        ... )
        # Candidate prompt now in database with 10% traffic
        
    Note:
        This is an async function. When calling from async code, use await.
        For sync contexts, use the train() wrapper function instead.
        
        DSPy training only initializes experiments. It does NOT:
        - Promote candidates to active
        - Rollback prompts
        - Adjust traffic beyond initial 90/10 split
    """
    logger.info("Starting DSPy training pipeline")

    # Step 0: Ensure system is stable (no active experiments)
    logger.info("Checking system stability")
    await ensure_system_stable()

    # Step 1: Configure DSPy with default model
    logger.info(f"Configuring DSPy with model: {DEFAULT_DSPY_MODEL}")
    lm = dspy.LM(DEFAULT_DSPY_MODEL)
    dspy.configure(lm=lm)

    # Step 2: Fetch raw task data from database (async operation)
    logger.info("Fetching raw task data from database")
    raw_tasks = await fetch_raw_task_data()

    if not raw_tasks:
        raise ValueError("No tasks found in database")

    logger.info(f"Fetched {len(raw_tasks)} raw tasks")

    # Step 3: Build golden dataset using complete pipeline
    logger.info(
        f"Building golden dataset (strategy={strategy.value}, "
        f"require_feedback={require_feedback}, "
        f"threshold={MIN_FEEDBACK_THRESHOLD})"
    )
    golden_dataset = build_golden_dataset(
        raw_tasks=raw_tasks,
        strategy=strategy,
        require_feedback=require_feedback,
        min_feedback_threshold=MIN_FEEDBACK_THRESHOLD,
    )

    logger.info(f"Golden dataset prepared with {len(golden_dataset)} examples")

    # Step 4: Convert to DSPy examples
    logger.info("Converting to DSPy examples")
    dspy_examples = convert_to_dspy_examples(golden_dataset)

    # Step 5: Load agent program
    logger.info("Initializing agent program")
    program = AgentProgram(current_prompt_text)

    # Step 6: Validate optimizer and prompt requirements
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

    # Step 8: Initialize A/B test with optimized prompt
    # DSPy training creates the candidate and sets initial traffic split.
    # It does NOT promote, rollback, or adjust traffic beyond this point.
    
    logger.info("Inserting optimized prompt as candidate with 10% traffic")
    candidate_id = await insert_prompt(
        text=instructions,
        status="candidate",
        traffic=0.10,
    )
    logger.info(f"Candidate prompt inserted (id={candidate_id})")
    
    # Get current active prompt and set it to 90% traffic
    active_prompt = await get_active_prompt()
    if active_prompt is None:
        raise RuntimeError(
            "No active prompt found. System requires an active prompt "
            "before DSPy training can initialize A/B testing."
        )
    
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
    current_prompt_text: str,
    optimizer: Any = None,
    strategy: ExtractionStrategy = ExtractionStrategy.LAST_TURN,
    require_feedback: bool = True,
) -> None:
    """Synchronous wrapper for train_async().

    This function provides a synchronous interface to the async training pipeline.
    For use in async contexts, call train_async() directly.

    Args:
        current_prompt_text: Current prompt text to initialize the agent program.
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
                current_prompt_text=current_prompt_text,
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