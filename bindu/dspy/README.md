# DSPy Integration for Bindu

This module provides offline prompt optimization for Bindu agents using [DSPy](https://github.com/stanfordnlp/dspy). It reads historical interaction data from PostgreSQL, builds high-quality training datasets, and uses DSPy optimizers to generate improved prompts.

## Overview

```
                              ┌─────────────────┐
                              │ Golden Dataset  │
                              │    Pipeline     │
                              └────────┬────────┘
                                       │
                                       ▼
                     ┌─────────────────────────────┐
                     │  Step 0: Fetch from DB      │
                     │  (fetch_raw_task_data)      │
                     └────────┬────────────────────┘
                              │
                              ▼
                     ┌─────────────────────────────┐
                     │  Step 1: Extract            │
                     │  (Extraction Strategies)    │
                     └────────┬────────────────────┘
                              │
                              ▼
                     ┌─────────────────────────────┐
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  DSPy Optimizer │
                              │  (any optimizer)│
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  Prompt         │
                              │  Candidates     │
                              └─────────────────┘
```

## Quick Start

### Prerequisites

1. Set the PostgreSQL connection URL:
```bash
export STORAGE__POSTGRES_URL="postgresql://user:pass@host:5432/bindu"
```

2. Set your LLM API key (for DSPy optimization):
```bash
export OPENAI_API_KEY="sk-..."
```

### Basic Usage

```python
from bindu.dspy import train

# Run training with defaults (LastTurnStrategy + BootstrapFewShot)
candidates = train()

# Get the best prompt
best_prompt = candidates[0]
print(f"Score: {best_prompt.score:.2%}")
print(f"Prompt: {best_prompt.text}")
```

### Async Usage

```python
import asyncio
from bindu.dspy.train import train_async

async def main():
    candidates = await train_async()
    return candidates

candidates = asyncio.run(main())
```

## Extraction Strategies

Strategies determine how conversation history is transformed into training examples. They are **pure Python** (no DSPy dependency) and can be used independently.

### Available Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `LastTurnStrategy` | Last user-assistant pair only | Simple Q&A agents |
| `FullHistoryStrategy` | Entire conversation | Context-heavy agents |
| `LastNTurnsStrategy` | Last N turns | Recent context matters |
| `FirstNTurnsStrategy` | First N turns | Initial context matters |
| `ContextWindowStrategy` | Last N turns with concatenated context | Multi-turn context |
| `SlidingWindowStrategy` | Multiple examples via sliding window | Data augmentation |
| `SummaryContextStrategy` | Summarizes older turns | Long conversations |
| `KeyTurnsStrategy` | Semantically relevant turns | Topic-focused agents |

### Using Strategies

```python
from bindu.dspy import train
from bindu.dspy.strategies import (
    LastTurnStrategy,
    ContextWindowStrategy,
    KeyTurnsStrategy,
    SlidingWindowStrategy,
    get_strategy,
)

# Simple strategies - no config needed
candidates = train(strategy=LastTurnStrategy())

# Strategies with parameters
candidates = train(
    strategy=ContextWindowStrategy(
        n_turns=5,
        system_prompt="You are a helpful assistant."
    )
)

# Key turns with similarity method
candidates = train(
    strategy=KeyTurnsStrategy(
        n_turns=4,
        similarity_method="weighted",  # "jaccard", "weighted", "overlap"
        include_final=True,
    )
)

# Sliding window for data augmentation
candidates = train(
    strategy=SlidingWindowStrategy(
        window_size=3,
        stride=1,
        start_offset=0,
    )
)

# Factory pattern
strategy = get_strategy("context_window", n_turns=3)
candidates = train(strategy=strategy)
```

## DSPy Optimizers

The `train()` function accepts any DSPy optimizer. If none is provided, it defaults to `BootstrapFewShot`.

### Using Different Optimizers

```python
import dspy
from bindu.dspy import train

# Default: BootstrapFewShot
candidates = train()

# BootstrapFewShot with custom settings
optimizer = dspy.BootstrapFewShot(
    max_bootstrapped_demos=10,
    max_labeled_demos=5,
)
candidates = train(optimizer=optimizer)

# MIPRO optimizer
optimizer = dspy.MIPRO(
    num_candidates=10,
    init_temperature=1.0,
)
candidates = train(optimizer=optimizer)

# BootstrapFewShotWithRandomSearch
optimizer = dspy.BootstrapFewShotWithRandomSearch(
    max_bootstrapped_demos=8,
    num_candidate_programs=10,
)
candidates = train(optimizer=optimizer)
```

### Custom Metrics

```python
import dspy
from bindu.dspy import train

def custom_metric(example, prediction, trace=None):
    """Custom metric for optimization."""
    # Your evaluation logic
    return prediction.output and len(prediction.output) > 10

optimizer = dspy.BootstrapFewShot(
    metric=custom_metric,
    max_bootstrapped_demos=8,
)
candidates = train(optimizer=optimizer)
```

## Configuration

Configuration is managed in `bindu/dspy/config.py`:

```python
# Model settings
DEFAULT_DSPY_MODEL = "openai/gpt-3.5-turbo"

# Dataset thresholds
MIN_FEEDBACK_THRESHOLD = 0.8  # Minimum feedback score [0.0, 1.0]
MIN_EXAMPLES = 10             # Minimum dataset size
MAX_EXAMPLES = 10000          # Maximum dataset size
MIN_INPUT_LENGTH = 10         # Minimum user input length
MIN_OUTPUT_LENGTH = 10        # Minimum agent output length

# Optimization settings
NUM_PROMPT_CANDIDATES = 3     # Number of candidates to return
MAX_BOOTSTRAPPED_DEMOS = 8    # Default few-shot demos

# Database
MAX_INTERACTIONS_QUERY_LIMIT = 10000
```

### Using a Different LLM

```python
import dspy
from bindu.dspy.train import train_async
import asyncio

async def train_with_custom_model():
    # Configure DSPy before training
    lm = dspy.LM("anthropic/claude-3-opus-20240229")
    dspy.configure(lm=lm)

    # Or use Google
    # lm = dspy.LM("google/gemini-1.5-flash", api_key=api_key)

    return await train_async()

candidates = asyncio.run(train_with_custom_model())
```

## Pipeline Details

### Golden Dataset Pipeline

The pipeline transforms raw database records into training examples:

```
Raw Tasks (PostgreSQL)
    │
    ▼
┌───────────────────────────────────────────┐
│ 1. Normalize Feedback                      │
│    - rating (1-5) → 0.0-1.0               │
│    - thumbs_up (bool) → 0.0 or 1.0        │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│ 2. Extract Interactions                    │
│    - Apply extraction strategy            │
│    - Parse turns from history             │
│    - Attach feedback scores               │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│ 3. Filter by Feedback Quality              │
│    - require_feedback=True → drop no-fb   │
│    - Keep only score >= threshold         │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│ 4. Validate & Clean                        │
│    - Check min input/output length        │
│    - Normalize whitespace                 │
│    - Remove identical input/output        │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│ 5. Deduplicate                             │
│    - Remove exact (input, output) dupes   │
└───────────────────────────────────────────┘
    │
    ▼
Golden Dataset (list[dict])
```

### Database Connection

The module uses PostgresStorage for database access. Data fetching is now integrated
into the golden dataset pipeline:

```python
# Build golden dataset (fetches data internally)
from bindu.dspy.dataset import build_golden_dataset

# Build dataset with automatic data fetching
golden_dataset = await build_golden_dataset(
    limit=1000,  # Optional: max tasks to fetch
    strategy=LastTurnStrategy(),
    require_feedback=True,
)
```

If you need to fetch raw data separately for analysis:

```python
# Fetch training data from the database
from bindu.dspy.dataset import fetch_raw_task_data

# Fetch data (PostgresStorage handles connection management)
raw_tasks = await fetch_raw_task_data(limit=1000)
```

Connection management is handled internally by PostgresStorage, with automatic
cleanup after each fetch operation.
- `POOL_SIZE = 1` - Single connection for sequential queries
- `MAX_OVERFLOW = 1` - One extra if needed
- `POOL_RECYCLE = 1800` - Recycle after 30 minutes
- `POOL_TIMEOUT = 30` - Wait up to 30s for connection

## Output Format

`train()` returns a list of `PromptCandidate` objects:

```python
@dataclass(frozen=True)
class PromptCandidate:
    text: str              # The optimized prompt text
    score: float           # Quality score (0.0 - 1.0)
    metadata: dict         # Additional info (optimizer type, etc.)
```

Example output:
```python
candidates = train()

for candidate in candidates:
    print(f"Score: {candidate.score:.2%}")
    print(f"Type: {candidate.metadata.get('type')}")
    print(f"Prompt:\n{candidate.text}\n")
```

## Complete Example

```python
import dspy
from bindu.dspy import train
from bindu.dspy.strategies import ContextWindowStrategy

# 1. Configure extraction strategy
strategy = ContextWindowStrategy(
    n_turns=5,
    system_prompt="You are a helpful AI assistant for customer support."
)

# 2. Configure optimizer
optimizer = dspy.BootstrapFewShot(
    max_bootstrapped_demos=10,
    max_labeled_demos=5,
)

# 3. Run training
candidates = train(
    optimizer=optimizer,
    strategy=strategy,
    require_feedback=True,  # Only use interactions with positive feedback
)

# 4. Use the best prompt
best = candidates[0]
print(f"Best prompt (score: {best.score:.2%}):")
print(best.text)

# 5. Apply to your agent
# agent.system_prompt = best.text
```

## Module Structure

```
bindu/dspy/
├── __init__.py          # Public API (train)
├── train.py             # Training orchestration
├── optimizer.py         # DSPy optimizer wrapper
├── dataset.py           # Golden dataset pipeline
├── extractor.py         # Interaction extractor
├── postgres.py          # Database access layer
├── program.py           # DSPy program definition
├── signature.py         # DSPy signature
├── models.py            # Data models (Interaction, PromptCandidate)
├── config.py            # Configuration constants
└── strategies/          # Extraction strategies
    ├── __init__.py      # Strategy exports + factory
    ├── base.py          # BaseExtractionStrategy
    ├── last_turn.py
    ├── full_history.py
    ├── last_n_turns.py
    ├── first_n_turns.py
    ├── context_window.py
    ├── sliding_window.py
    ├── summary_context.py
    ├── key_turns.py
    └── similarity.py    # Similarity functions for KeyTurnsStrategy
```

## Troubleshooting

### "STORAGE__POSTGRES_URL environment variable not set"
Set the database connection URL:
```bash
export STORAGE__POSTGRES_URL="postgresql://user:pass@localhost:5432/bindu"
```

### "Dataset too small: X examples (minimum required: 10)"
Your database doesn't have enough high-quality interactions. Options:
- Lower `MIN_FEEDBACK_THRESHOLD` in config
- Set `require_feedback=False` to include interactions without feedback
- Collect more interaction data

### "No tasks found in database"
The `tasks` table is empty. Ensure your Bindu server has been running and processing requests.

### Connection timeout errors
Check that:
- PostgreSQL is running and accessible
- The connection URL is correct
- Network/firewall allows the connection
