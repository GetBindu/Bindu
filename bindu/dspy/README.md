# DSPy Integration

> **Self-improving AI agents through automated prompt optimization**

The DSPy integration enables Bindu agents to automatically improve their system prompts using real user feedback through a safe, gradual, and reversible process.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Components](#components)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Advanced Configuration](#advanced-configuration)
- [API Reference](#api-reference)
- [Development](#development)

---

## Overview

Traditional AI agents rely on static prompts that remain unchanged over time. The DSPy integration transforms Bindu agents into **self-improving systems** that evolve based on real-world performance:

```
Traditional Agent:  LLM + hardcoded prompt → response

DSPy-Enhanced Agent: LLM + evolving prompt + feedback data → better responses over time
```

### Core Principles

- ✅ **Safe**: Canary deployment with gradual rollout
- ✅ **Measurable**: All decisions are metrics-driven
- ✅ **Reversible**: Automatic rollback on performance degradation
- ✅ **Offline**: No online learning or live mutations
- ✅ **Production-Ready**: Battle-tested for multi-agent systems

---

## Key Features

### 🎯 Automatic Prompt Optimization

Leverages [DSPy](https://github.com/stanfordnlp/dspy)'s SIMBA optimizer to generate improved prompts from high-quality interaction data.

> **Note:** Currently only SIMBA optimizer is supported. Other optimizers (GEPA, MIPRO, etc.) are planned for future releases.

### 🚀 Canary Deployment

Traffic-based A/B testing with automatic promotion or rollback based on feedback metrics.

###  Multiple Extraction Strategies

Flexible data extraction patterns for different use cases:
- Last turn only
- Full conversation history
- First/last N turns
- Context window strategies
- Similarity-based selection

---

## Architecture

The DSPy integration consists of three main subsystems:

```
┌─────────────────────────────────────────────────────────────┐
│                     ONLINE SUBSYSTEM                        │
│                    (Every Request)                          │
├─────────────────────────────────────────────────────────────┤
│  1. Prompt Router                                           │
│     ├── Fetch active & candidate prompts                   │
│     ├── Weighted random selection (90/10 split)            │
│     └── Return selected prompt                             │
│                                                             │
│  2. Feedback Collector                                      │
│     └── Store user feedback in PostgreSQL                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    OFFLINE SUBSYSTEM                        │
│                 (Scheduled via Cron)                        │
├─────────────────────────────────────────────────────────────┤
│  1. DSPy Trainer (Slow Path - Daily)                       │
│     ├── Check system stability                             │
│     ├── Build golden dataset                               │
│     ├── Run DSPy optimizer                                 │
│     ├── Insert candidate prompt (10% traffic)              │
│     └── Initialize A/B test (90/10 split)                  │
│                                                             │
│  2. Canary Controller (Fast Path - Hourly)                 │
│     ├── Compare active vs candidate metrics                │
│     ├── Promote: Increase candidate traffic                │
│     ├── Rollback: Decrease candidate traffic               │
│     └── Stabilize: Archive loser when traffic = 0%/100%    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   PERSISTENT STORAGE                        │
│                     (PostgreSQL)                            │
├─────────────────────────────────────────────────────────────┤
│  • Tasks with prompt_id foreign keys                       │
│  • User feedback linked to tasks                           │
│  • Prompt versions and traffic allocation                  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Users Interact → Feedback Stored in DB
       ↓
(Every 24h) DSPy Generates New Candidate Prompt
       ↓
(Every 1h) Canary Compares Active vs Candidate
       ↓
Promote (better) or Rollback (worse)
       ↓
System Stabilizes (100%/0% traffic)
       ↓
Ready for Next Training Cycle
```

---

## Components

### Core Modules

#### 1. **Training Orchestrator** ([train.py](./train.py))

Main entry point for prompt optimization. Coordinates the complete pipeline:

- System stability checks
- Active prompt retrieval
- Golden dataset construction
- DSPy optimizer execution
- Candidate prompt initialization
- A/B test setup (90/10 split)

**Key Functions:**
- `train_async()`: Async training pipeline
- `train()`: Synchronous wrapper

**Supported Optimizer:** SIMBA only (GEPA and others planned for future releases)

#### 2. **Dataset Builder** ([dataset.py](./dataset.py))

Implements the golden dataset pipeline with 6 stages:

```python
Raw Tasks → Normalize Feedback → Extract Interactions 
   → Filter by Quality → Validate → Deduplicate → Golden Dataset
```

**Key Functions:**
- `fetch_raw_task_data()`: Retrieve tasks from PostgreSQL
- `normalize_feedback()`: Convert ratings/thumbs to 0.0-1.0 scale
- `extract_interactions()`: Apply extraction strategy
- `build_golden_dataset()`: Complete pipeline orchestration
- `convert_to_dspy_examples()`: Format for DSPy

#### 3. **Prompt Router** ([prompt_selector.py](./prompt_selector.py))

Weighted random selection for canary deployment:

```python
# Example: 90% active, 10% candidate
prompt = await select_prompt_with_canary()
# Returns prompt based on traffic weights
```

**Key Functions:**
- `select_prompt_with_canary()`: Traffic-weighted selection

#### 4. **Canary Controller** ([canary/controller.py](./canary/controller.py))

Manages gradual rollout based on performance metrics:

```python
# Compare metrics
winner = compare_metrics(active, candidate)

if winner == "candidate":
    await promote_step(active, candidate)  # +10% traffic
elif winner == "active":
    await rollback_step(active, candidate)  # -10% traffic
```

Metrics (`num_interactions` and `average_feedback_score`) are calculated when the canary controller runs by aggregating all tasks with a given `prompt_id` and their associated feedback from the database.

**Key Functions:**
- `run_canary_controller()`: Main control loop
- `compare_metrics()`: Determine winner based on feedback
- `promote_step()`: Increase candidate traffic by 10%
- `rollback_step()`: Decrease candidate traffic by 10%

#### 5. **Prompt Manager** ([prompts.py](./prompts.py))

Database interface for prompt CRUD operations:

- `get_active_prompt()`: Fetch current active prompt
- `get_candidate_prompt()`: Fetch current candidate prompt
- `insert_prompt()`: Create new prompt
- `update_prompt_traffic()`: Adjust traffic allocation
- `update_prompt_status()`: Change status (active/candidate/deprecated/rolled_back)
- `zero_out_all_except()`: Reset traffic for non-experiment prompts

#### 6. **Interaction Extractor** ([extractor.py](./extractor.py))

Strategy-based extraction from conversation history:

```python
from bindu.dspy.strategies import LastTurnStrategy, FullHistoryStrategy

# Clean and extract
extractor = InteractionExtractor(strategy=LastTurnStrategy())
interaction = extractor.extract(task_id, history, feedback_score, feedback_type)
```

**Key Functions:**
- `clean_messages()`: Remove empty/invalid messages
- `InteractionExtractor.extract()`: Apply strategy to history

### Extraction Strategies

All strategies inherit from `BaseExtractionStrategy` ([strategies/base.py](./strategies/base.py)) and implement:

```python
class BaseExtractionStrategy(ABC):
    @property
    def name(self) -> str:
        """Strategy identifier"""
        
    def extract(self, task_id, messages, feedback_score, feedback_type) -> Interaction | None:
        """Extract interaction from cleaned messages"""
```

#### Available Strategies

| Strategy | Module | Description | Use Case |
|----------|--------|-------------|----------|
| **LastTurnStrategy** | [last_turn.py](./strategies/last_turn.py) | Extracts only the final user-assistant exchange | Simple, focused training |
| **FullHistoryStrategy** | [full_history.py](./strategies/full_history.py) | First user input + entire conversation as output | Multi-turn understanding |
| **LastNTurnsStrategy** | [last_n_turns.py](./strategies/last_n_turns.py) | Last N conversation turns | Recent context focus |
| **FirstNTurnsStrategy** | [first_n_turns.py](./strategies/first_n_turns.py) | First N conversation turns | Onboarding patterns |
| **ContextWindowStrategy** | [context_window.py](./strategies/context_window.py) | Sliding window with system prompt | Contextual conversations |
| **SimilarityStrategy** | [similarity.py](./strategies/similarity.py) | Semantic similarity-based selection | Topic-focused training |
| **KeyTurnsStrategy** | [key_turns.py](./strategies/key_turns.py) | Extract turns with specific keywords | Feature-specific optimization |
| **SlidingWindowStrategy** | [sliding_window.py](./strategies/sliding_window.py) | Multiple overlapping windows | Comprehensive coverage |
| **SummaryContextStrategy** | [summary_context.py](./strategies/summary_context.py) | Summarized history as context | Long conversations |

### Supporting Modules

- **models.py**: Data models (`Interaction`, `PromptCandidate`)
- **signature.py**: DSPy signature definition (`AgentSignature`)
- **program.py**: DSPy program module (`AgentProgram`)
- **optimizer.py**: Optimizer wrapper with compile delegation
- **guard.py**: System stability checks (`ensure_system_stable`)

### CLI Commands

#### Training CLI ([cli/train.py](./cli/train.py))

```bash
python -m bindu.dspy.cli.train \
  --optimizer simba \
  --strategy last_turn \
  --require-feedback
```

**Arguments:**
- `--optimizer`: Optimizer to use (currently only `simba` is supported)
- `--strategy`: Extraction strategy (e.g., `last_turn`, `full_history`, `last_n:3`)
- `--require-feedback`: Only use interactions with feedback

#### Canary CLI ([cli/canary.py](./cli/canary.py))

```bash
python -m bindu.dspy.cli.canary
```

Runs one iteration of the canary controller.

---

## Getting Started

### Prerequisites

1. **PostgreSQL Database**
   - DSPy requires PostgreSQL for storing interactions, feedback, and prompt versions
   - Set `STORAGE__POSTGRES_URL` environment variable

2. **DSPy Configuration**
   - Default model configured in `app_settings.dspy.default_model`
   - Min feedback threshold: `app_settings.dspy.min_feedback_threshold`
   - Max query limit: `app_settings.dspy.max_interactions_query_limit`

### Initial Setup

#### 1. Enable PostgreSQL

Ensure your agent has PostgreSQL enabled and the connection string set:

```bash
export STORAGE__POSTGRES_URL="postgresql://user:pass@localhost:5432/bindu"
```

#### 2. Bootstrap Initial Prompt

On first run, the system prompt from your agent's `main.py` is automatically saved to the database as:
- `status = active`
- `traffic = 100%`

After this, **all prompts are served from the database**, not from code.

#### 3. Configure Cron Jobs

Set up two cron jobs for automated operation:

**DSPy Training (Daily at 2 AM):**
```cron
0 2 * * * cd /srv/my_agent && uv run python -m bindu.dspy.cli.train --optimizer simba --require-feedback
```

**Canary Controller (Hourly):**
```cron
0 * * * * cd /srv/my_agent && uv run python -m bindu.dspy.cli.canary
```

---

## Usage

### Basic Training Workflow

#### 1. **Manual Training Run**

```bash
# Using SIMBA optimizer with last turn strategy
uv run python -m bindu.dspy.cli.train \
  --optimizer simba \
  --strategy last_turn \
  --require-feedback
```

This will:
1. Check system stability (no active experiments)
2. Fetch current active prompt
3. Build golden dataset from high-quality interactions
4. Run SIMBA optimization
5. Insert optimized prompt as candidate (10% traffic)
6. Set active prompt to 90% traffic
7. Initialize A/B test

#### 2. **Manual Canary Run**

```bash
# Run one iteration of canary controller
uv run python -m bindu.dspy.cli.canary
```

This will:
1. Fetch active and candidate prompts
2. Compare average feedback scores
3. Adjust traffic (+/- 10%) based on performance
4. Stabilize system when traffic reaches 0% or 100%

### Programmatic Usage

#### Training from Python

```python
import asyncio
from dspy.teleprompt import SIMBA
from bindu.dspy import train_async
from bindu.dspy.strategies import ContextWindowStrategy

# Configure strategy
strategy = ContextWindowStrategy(n_turns=3, system_prompt="Be helpful and concise")

# Configure optimizer (only SIMBA is currently supported)
optimizer = SIMBA()

# Run training
await train_async(
    optimizer=optimizer,
    strategy=strategy,
    require_feedback=True
)
```

#### Runtime Prompt Selection

```python
from bindu.dspy.prompt_selector import select_prompt_with_canary

# During agent request handling
prompt = await select_prompt_with_canary()

if prompt:
    system_message = prompt["prompt_text"]
    prompt_id = prompt["id"]
    
    # Use prompt_id later for feedback tracking
```

#### Feedback Storage

Feedback is stored in the `task_feedback` table and linked to tasks. Each task references the prompt used via a `prompt_id` foreign key.

```python
# Feedback is stored against individual tasks
# Tasks are linked to prompts via prompt_id
```

---

## Advanced Configuration

### Custom Extraction Strategies

Create your own strategy by inheriting from `BaseExtractionStrategy`:

```python
from bindu.dspy.strategies import BaseExtractionStrategy
from bindu.dspy.models import Interaction
from typing import Any
from uuid import UUID

class CustomStrategy(BaseExtractionStrategy):
    def __init__(self, custom_param: str):
        self.custom_param = custom_param
    
    @property
    def name(self) -> str:
        return f"custom_{self.custom_param}"
    
    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        # Your extraction logic here
        user_input = "..."
        agent_output = "..."
        
        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )
```

### Optimizer Configuration

#### SIMBA Optimizer

```python
from dspy.teleprompt import SIMBA

optimizer = SIMBA(
    # SIMBA-specific configuration
)

await train_async(optimizer=optimizer, strategy=strategy)
```

> **Current Limitation:** Only the SIMBA optimizer is currently supported. SIMBA is a prompt-mutating optimizer that refines existing prompts rather than generating new ones from scratch.
>
> **Planned Support:** Other DSPy optimizers (GEPA, MIPRO, etc.) are planned for future releases.

### Canary Controller Tuning

Adjust constants in [canary/controller.py](./canary/controller.py):

```python
# Minimum interactions before comparing metrics
MIN_INTERACTIONS_THRESHOLD = 20  # Default: 20

# Traffic adjustment step size
TRAFFIC_STEP = 0.1  # Default: 10% per step
```

### Dataset Filtering

Control dataset quality in your training call:

```python
await train_async(
    optimizer=optimizer,
    strategy=strategy,
    require_feedback=True,  # Only interactions with feedback
)
```

Or via settings:

```python
# Minimum feedback score for inclusion
app_settings.dspy.min_feedback_threshold = 0.6  # Default: 0.0 (all)

# Maximum interactions to fetch
app_settings.dspy.max_interactions_query_limit = 10000  # Default: 10000
```

---

## API Reference

### Training Functions

#### `train_async()`

```python
async def train_async(
    optimizer: Any,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
) -> None
```

**Parameters:**
- `optimizer`: DSPy optimizer instance. Currently only SIMBA is supported. Required.
- `strategy`: Extraction strategy. Defaults to `LastTurnStrategy()`.
- `require_feedback`: Whether to require feedback for dataset inclusion.

**Raises:**
- `RuntimeError`: If experiment is already active or POSTGRES_URL not set
- `ValueError`: If no active prompt found or optimizer invalid (non-SIMBA)
- `ConnectionError`: If database connection fails

#### `train()`

Synchronous wrapper for `train_async()`. Do not call from async contexts.

### Dataset Functions

#### `build_golden_dataset()`

```python
async def build_golden_dataset(
    limit: int | None = None,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
    min_feedback_threshold: float = 0.0,
) -> list[Interaction]
```

**Returns:** List of high-quality `Interaction` objects ready for training.

#### `convert_to_dspy_examples()`

```python
def convert_to_dspy_examples(
    interactions: list[Interaction]
) -> list[dspy.Example]
```

Converts `Interaction` objects to DSPy `Example` format.

### Prompt Management Functions

#### `select_prompt_with_canary()`

```python
async def select_prompt_with_canary() -> dict[str, Any] | None
```

**Returns:** Selected prompt dict with keys:
- `id`: Prompt ID
- `prompt_text`: Actual prompt content
- `status`: `active` or `candidate`
- `traffic`: Current traffic allocation (0.0-1.0)
- `num_interactions`: Total tasks using this prompt
- `average_feedback_score`: Average normalized feedback across all tasks

### Canary Controller Functions

#### `run_canary_controller()`

```python
async def run_canary_controller() -> None
```

Main canary control loop. Compares metrics and adjusts traffic.

#### `compare_metrics()`

```python
def compare_metrics(
    active: dict,
    candidate: dict
) -> Literal["active", "candidate", None]
```

**Returns:**
- `"candidate"`: Candidate is winning
- `"active"`: Active is winning
- `None`: Tie or insufficient data

### Guard Functions

#### `ensure_system_stable()`

```python
async def ensure_system_stable(agent_id: str | None = None) -> None
```

**Raises:** `RuntimeError` if a candidate prompt already exists (experiment active).

---

## Development

### Project Structure

```
bindu/dspy/
├── __init__.py              # Package exports
├── train.py                 # Training orchestrator
├── dataset.py               # Golden dataset pipeline
├── extractor.py             # Interaction extraction
├── models.py                # Data models
├── signature.py             # DSPy signature
├── program.py               # DSPy program
├── optimizer.py             # Optimizer wrapper
├── prompts.py               # Prompt management
├── prompt_selector.py       # Canary selection
├── guard.py                 # Stability checks
├── canary/
│   ├── __init__.py
│   └── controller.py        # Canary controller
├── cli/
│   ├── train.py            # Training CLI
│   └── canary.py           # Canary CLI
└── strategies/
    ├── __init__.py
    ├── base.py             # Abstract base
    ├── last_turn.py        # Last turn strategy
    ├── full_history.py     # Full history strategy
    ├── last_n_turns.py     # Last N turns
    ├── first_n_turns.py    # First N turns
    ├── context_window.py   # Context window
    ├── similarity.py       # Similarity-based
    ├── key_turns.py        # Keyword-based
    ├── sliding_window.py   # Sliding window
    └── summary_context.py  # Summary-based
```

### Testing

Run tests from the project root:

```bash
# Unit tests
pytest tests/unit/test_dspy/

# Integration tests
pytest tests/integration/test_dspy/

# E2E tests
pytest tests/e2e/test_dspy/
```

### Adding New Strategies

1. Create a new file in `strategies/`
2. Inherit from `BaseExtractionStrategy`
3. Implement `name` property and `extract()` method
4. Export in `strategies/__init__.py`
5. Add to CLI parser in `cli/train.py`

Example:

```python
# strategies/my_strategy.py
from .base import BaseExtractionStrategy
from ..models import Interaction

class MyStrategy(BaseExtractionStrategy):
    @property
    def name(self) -> str:
        return "my_strategy"
    
    def extract(self, task_id, messages, feedback_score, feedback_type):
        # Implementation
        return Interaction(...)
```

### Logging

All modules use the centralized logger:

```python
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.my_module")

logger.info("Informational message")
logger.debug("Debug details")
logger.warning("Warning message")
logger.error("Error message")
```

---

## FAQ

### How often should I run training?

**Recommendation:** Once every 24 hours. Training is expensive and requires sufficient new feedback data to be effective.

### How often should I run the canary controller?

**Recommendation:** Every hour. The canary controller is lightweight and metrics-driven. Frequent checks enable faster convergence.

### What happens if training is triggered during an active experiment?

Training will **fail with an error**. The system checks for active candidates and blocks training until the experiment stabilizes.

### Can I run multiple experiments simultaneously?

No. The system enforces **at most 2 prompts with non-zero traffic** at any time (active + candidate). This simplifies comparison and ensures clean rollback.

### What if the candidate performs worse?

The canary controller will **automatically roll back** by progressively reducing candidate traffic to 0% and restoring active to 100%.

### How is feedback normalized?

- **Rating (1-5):** Divided by 5 → [0.0, 1.0]
- **Thumbs up/down:** 1.0 for up, 0.0 for down
- **Missing:** `None`

### What optimizers are supported?

Currently **only SIMBA** is supported. SIMBA is a prompt-mutating optimizer that refines existing prompts based on feedback data. Other DSPy optimizers (GEPA, MIPRO, etc.) are planned for future releases.

### Can I use DSPy without PostgreSQL?

No. DSPy **requires PostgreSQL** for storing feedback, prompts, and metrics. Without it, the system cannot function.

---

## License

This module is part of the Bindu project. See the main project LICENSE for details.

## Contributing

We ❤️ contributions! Please see the main project's [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## Support

- **Issues:** [GitHub Issues](https://github.com/getbindu/Bindu/issues/new/choose)
- **Documentation:** [Main Bindu Docs](../../README.md)

---

**Built with ❤️ by the Bindu team** 🌻
