# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Dataset preparation for DSPy training.

This module implements the complete golden dataset pipeline:
0. Fetch raw task data from PostgreSQL
1. Normalize feedback from raw task data
2. Extract interactions using configurable strategies
3. Filter by feedback quality
4. Validate and clean interactions
5. Deduplicate examples
6. Prepare final golden dataset

The pipeline transforms raw PostgreSQL task data into high-quality
training examples for DSPy prompt optimization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import dspy

from bindu.utils.logging import get_logger

from bindu.settings import app_settings
from bindu.server.storage.postgres_storage import PostgresStorage
from .extractor import InteractionExtractor
from .models import Interaction
from .strategies import BaseExtractionStrategy, LastTurnStrategy

logger = get_logger("bindu.dspy.dataset")


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RawTaskData:
    """Raw task data fetched from the database.

    This represents the raw data before interaction extraction.

    Attributes:
        id: Task UUID
        history: List of message dictionaries from the conversation
        created_at: Timestamp when the task was created
        feedback_data: Optional feedback dictionary (ratings, thumbs up/down)
    """

    id: UUID
    history: list[dict[str, Any]]
    created_at: Any
    feedback_data: dict[str, Any] | None = None


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RawTaskData:
    """Raw task data fetched from the database.

    This represents the raw data before interaction extraction.

    Attributes:
        id: Task UUID
        history: List of message dictionaries from the conversation
        created_at: Timestamp when the task was created
        feedback_data: Optional feedback dictionary (ratings, thumbs up/down)
    """

    id: UUID
    history: list[dict[str, Any]]
    created_at: Any
    feedback_data: dict[str, Any] | None = None


# =============================================================================
# Data Access Functions
# =============================================================================


async def fetch_raw_task_data(
    limit: int | None = None,
    did: str | None = None,
) -> list[RawTaskData]:
    """Fetch raw task data with feedback from PostgreSQL.

    This function reads task data from the database along with associated
    feedback using a LEFT JOIN. It returns raw data that needs to be
    processed by the extraction and filtering pipeline.

    The function uses PostgresStorage for all database operations, ensuring
    consistent connection management and error handling across the application.

    Args:
        limit: Maximum number of tasks to fetch (default: from settings)
        did: Decentralized Identifier for schema isolation (required for multi-tenancy)

    Returns:
        List of RawTaskData objects containing task history and feedback

    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL environment variable is not set
        ConnectionError: If unable to connect to database or query fails
    """
    if limit is None:
        limit = app_settings.dspy.max_interactions_query_limit

    logger.info(f"Fetching up to {limit} tasks from database (DID: {did or 'public'})")

    # Create storage instance with DID for schema isolation
    storage = PostgresStorage(did=did)

    try:
        await storage.connect()

        # Fetch tasks with feedback using the specialized method
        rows = await storage.fetch_tasks_with_feedback(limit=limit)

        # Convert to RawTaskData objects
        raw_tasks = [
            RawTaskData(
                id=row["id"],
                history=row["history"],
                created_at=row["created_at"],
                feedback_data=row["feedback_data"],
            )
            for row in rows
        ]

        logger.info(f"Fetched {len(raw_tasks)} raw tasks from database")
        return raw_tasks

    except Exception as e:
        logger.error(f"Failed to fetch raw task data from database: {e}")
        raise ConnectionError(f"Failed to fetch raw task data: {e}") from e

    finally:
        # Always clean up the connection
        await storage.disconnect()


def normalize_feedback(feedback_data: dict[str, Any] | None) -> tuple[float | None, str | None]:
    """Normalize feedback data to a single numeric score [0.0, 1.0].

    Accepts multiple feedback formats:
    - { rating: 1-5 } → normalized to 0.0-1.0
    - { thumbs_up: true/false } → 1.0 or 0.0
    - Missing/invalid → None

    Args:
        feedback_data: Raw feedback data from database

    Returns:
        Tuple of (normalized_score, feedback_type) or (None, None)
    """
    if not feedback_data:
        return None, None

    # Try rating format (1-5 scale)
    rating = feedback_data.get("rating")
    if rating is not None:
        try:
            rating_val = float(rating)
            if 1 <= rating_val <= 5:
                normalized = rating_val / 5.0
                return normalized, "rating"
        except (ValueError, TypeError):
            pass

    # Try thumbs_up format
    thumbs_up = feedback_data.get("thumbs_up")
    if thumbs_up is not None:
        if isinstance(thumbs_up, bool):
            return 1.0 if thumbs_up else 0.0, "thumbs_up"
        # Handle string "true"/"false"
        if isinstance(thumbs_up, str):
            thumbs_up_lower = thumbs_up.lower()
            if thumbs_up_lower in ("true", "1", "yes"):
                return 1.0, "thumbs_up"
            elif thumbs_up_lower in ("false", "0", "no"):
                return 0.0, "thumbs_up"

    return None, None


def extract_interactions(
    raw_tasks: list[RawTaskData],
    strategy: BaseExtractionStrategy | None = None,
) -> list[Interaction]:
    """Extract interactions from raw task data.

    For each task:
    1. Normalize feedback
    2. Extract interactions using specified strategy (may produce multiple per task)
    3. Collect all valid interactions

    Args:
        raw_tasks: Raw task data from database
        strategy: Extraction strategy to use. Defaults to LastTurnStrategy.

    Returns:
        List of extracted interactions
    """
    strategy = strategy or LastTurnStrategy()
    extractor = InteractionExtractor(strategy)
    interactions: list[Interaction] = []

    for task in raw_tasks:
        # Normalize feedback
        feedback_score, feedback_type = normalize_feedback(task.feedback_data)

        # Extract interactions (may return multiple for strategies like SlidingWindowStrategy)
        extracted = extractor.extract_all(
            task_id=task.id,
            history=task.history,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )

        interactions.extend(extracted)

    logger.info(
        f"Extracted {len(interactions)} interactions from {len(raw_tasks)} tasks "
        f"using {strategy.name} strategy"
    )
    return interactions

def validate_and_clean_interactions(
    interactions: list[Interaction],
) -> list[Interaction]:
    """Validate and clean interactions.

    Validation rules:
    - Minimum length for input and output
    - Output must not be identical to input
    - Remove excessive whitespace
    - Normalize Unicode

    Args:
        interactions: List of interactions to validate

    Returns:
        List of valid, cleaned interactions
    """
    validated: list[Interaction] = []

    for interaction in interactions:
        # Clean whitespace
        user_input = " ".join(interaction.user_input.split())
        agent_output = " ".join(interaction.agent_output.split())

        # Check minimum lengths
        if len(user_input) < app_settings.dspy.min_input_length:
            continue
        if len(agent_output) < app_settings.dspy.min_output_length:
            continue

        # Check not identical
        if user_input == agent_output:
            continue

        # Create cleaned interaction
        validated.append(
            Interaction(
                id=interaction.id,
                user_input=user_input,
                agent_output=agent_output,
                feedback_score=interaction.feedback_score,
                feedback_type=interaction.feedback_type,
            )
        )

    logger.info(
        f"Validated {len(validated)} interactions from {len(interactions)} total "
        f"(min_input={app_settings.dspy.min_input_length}, min_output={app_settings.dspy.min_output_length})"
    )
    return validated


def deduplicate_interactions(interactions: list[Interaction]) -> list[Interaction]:
    """Remove duplicate interactions based on (user_input, agent_output).

    Args:
        interactions: List of interactions to deduplicate

    Returns:
        List of unique interactions
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Interaction] = []

    for interaction in interactions:
        key = (interaction.user_input, interaction.agent_output)
        if key not in seen:
            seen.add(key)
            unique.append(interaction)

    if len(unique) < len(interactions):
        logger.info(f"Removed {len(interactions) - len(unique)} duplicate interactions")

    return unique


def prepare_golden_dataset(
    interactions: list[Interaction],
) -> list[dict[str, Any]]:
    """Prepare golden dataset in DSPy-ready format.

    Converts cleaned interactions into simple input-output pairs.

    Args:
        interactions: Validated, deduplicated interactions

    Returns:
        Golden dataset ready for DSPy training
    """
    dataset: list[dict[str, Any]] = []

    for interaction in interactions:
        dataset.append(
            {
                "input": interaction.user_input,
                "output": interaction.agent_output,
                "feedback": {
                    "score": interaction.feedback_score,
                    "type": interaction.feedback_type,
                },
            }
        )

    logger.info(f"Prepared golden dataset with {len(dataset)} examples")
    return dataset


def validate_dataset_size(dataset: list[dict[str, Any]]) -> None:
    """Validate that dataset size is within acceptable bounds.

    Args:
        dataset: Golden dataset to validate

    Raises:
        ValueError: If dataset is too small or too large
    """
    size = len(dataset)

    if size < app_settings.dspy.min_examples:
        raise ValueError(
            f"Dataset too small: {size} examples (minimum required: {app_settings.dspy.min_examples})"
        )

    if size > app_settings.dspy.max_examples:
        logger.warning(
            f"Dataset size ({size}) exceeds maximum ({app_settings.dspy.max_examples}). "
            f"Consider sampling or adjusting query limit."
        )

    logger.info(f"Dataset size validation passed: {size} examples")


async def build_golden_dataset(
    limit: int | None = None,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
    min_feedback_threshold: float = None,
    did: str | None = None,
) -> list[dict[str, Any]]:
    """Build complete golden dataset from raw task data.

    This is the main pipeline function that orchestrates all steps:
    0. Fetch raw task data from database
    1. Extract interactions from raw tasks
    2. Filter by feedback quality
    3. Validate and clean
    4. Deduplicate
    5. Prepare golden dataset
    6. Validate size

    Args:
        limit: Maximum number of tasks to fetch from database (default: from settings)
        strategy: Extraction strategy to use. Defaults to LastTurnStrategy.
        require_feedback: Whether to require feedback for inclusion
        min_feedback_threshold: Minimum feedback score threshold
        did: Decentralized Identifier for schema isolation (required for multi-tenancy)

    Returns:
        Golden dataset ready for DSPy training

    Raises:
        ValueError: If dataset is too small or pipeline fails
        ConnectionError: If unable to fetch data from database
    """
    if min_feedback_threshold is None:
        min_feedback_threshold = app_settings.dspy.min_feedback_threshold
    
    strategy = strategy or LastTurnStrategy()
    logger.info(f"Starting golden dataset pipeline with {strategy.name} strategy")

    # Step 0: Fetch raw task data from database
    logger.info("Fetching raw task data from database")
    raw_tasks = await fetch_raw_task_data(limit=limit, did=did)
    
    if not raw_tasks:
        raise ValueError("No tasks found in database")
    
    logger.info(f"Fetched {len(raw_tasks)} raw tasks")

    # Step 1: Extract interactions
    interactions = extract_interactions(raw_tasks, strategy=strategy)
    if not interactions:
        raise ValueError("No interactions extracted from raw tasks")

    # # Step 2: Filter by feedback quality
    # interactions = filter_by_feedback_quality(
    #     interactions,
    #     require_feedback=require_feedback,
    #     min_threshold=min_feedback_threshold,
    # )
    # if not interactions:
    #     raise ValueError("No interactions passed feedback quality filter")

    # Step 3: Validate and clean
    interactions = validate_and_clean_interactions(interactions)
    if not interactions:
        raise ValueError("No interactions passed validation")

    # Step 4: Deduplicate
    interactions = deduplicate_interactions(interactions)
    if not interactions:
        raise ValueError("No interactions after deduplication")

    # Step 5: Prepare golden dataset
    dataset = prepare_golden_dataset(interactions)

    # Step 6: Validate size
    validate_dataset_size(dataset)

    logger.info("Golden dataset pipeline completed successfully")
    return dataset


def convert_to_dspy_examples(
    dataset: list[dict[str, Any]],
) -> list[dspy.Example]:
    """Convert golden dataset into DSPy Example format.

    Transforms the golden dataset into dspy.Example objects that can be
    used directly for prompt optimization.

    Args:
        dataset: Golden dataset with input-output pairs

    Returns:
        List of dspy.Example objects ready for training
    """
    examples: list[dspy.Example] = []

    for item in dataset:
        example = dspy.Example(
            input=item["input"],
            output=item["output"],
            feedback=item.get("feedback"),
        ).with_inputs("input")
        examples.append(example)

    logger.info(f"Converted {len(examples)} examples to DSPy format")
    return examples