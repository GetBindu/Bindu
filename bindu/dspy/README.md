# DSPy Integration for Bindu

Bindu's DSPy integration provides automated prompt optimization and continuous improvement for AI agents through machine learning. The system collects real user interactions and feedback, then uses DSPy's optimization algorithms to automatically refine agent prompts over time.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Three Ways to Use DSPy](#three-ways-to-use-dspy)
  - [1. Enable DSPy for Online Prompt Selection](#1-enable-dspy-for-online-prompt-selection)
  - [2. Train New Prompts (Offline)](#2-train-new-prompts-offline)
  - [3. Canary Deployment (Offline)](#3-canary-deployment-offline)
- [Configuration Reference](#configuration-reference)
- [Extraction Strategies](#extraction-strategies)
- [CLI Reference](#cli-reference)
- [Advanced Topics](#advanced-topics)

---

## Overview

The DSPy integration addresses a core challenge in AI agent development: **prompt engineering is iterative and time-consuming**. Instead of manually tweaking prompts based on trial and error, DSPy enables data-driven optimization:

1. **Collect** user feedback on agent responses
2. **Build** golden datasets from high-quality interactions
3. **Optimize** prompts using machine learning (DSPy optimizers)
4. **Test** new prompts gradually via A/B testing (canary deployment)
5. **Promote** or rollback based on real-world performance

This creates a feedback loop where your agent continuously improves based on actual user interactions.

### Key Features

- **Automatic prompt optimization** using DSPy's SIMBA and GEPA optimizers
- **Canary deployment** with gradual traffic shifting (A/B testing)
- **Multi-strategy data extraction** (last turn, full history, context windows, etc.)
- **DID-based multi-tenancy** for isolated prompt management per agent
- **PostgreSQL-backed** prompt versioning and metrics tracking

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
│     ├── Weighted random selection (80/20 split)            │
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
│     ├── Insert candidate prompt (20% traffic)              │
│     └── Initialize A/B test (80/20 split)                  │
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

1. **User Request** → Prompt Router selects prompt (weighted random) → Agent responds
2. **User Feedback** → Stored in PostgreSQL with task link
3. **Daily Training** → Build dataset from feedback → Optimize → Create candidate
4. **Hourly Canary** → Compare metrics → Adjust traffic → Promote/rollback

---

## Three Ways to Use DSPy

There are three distinct ways to interact with Bindu's DSPy system, each serving a different purpose:

### 1. Enable DSPy for Online Prompt Selection

**Purpose:** Use DSPy-optimized prompts during live agent execution with automatic A/B testing.

**When to use:** After you've trained and deployed candidate prompts, enable this to have your agent automatically use optimized prompts from the database instead of static config files.

#### Configuration

Add to your agent config JSON:

```json
{
  "author": "you@example.com",
  "name": "My Agent",
  "description": "An agent with DSPy optimization",
  "version": "1.0.0",
  "enable_dspy": true,
  ...
}
```

#### Required Environment Variables

```bash
# PostgreSQL connection for prompt storage
STORAGE_TYPE=postgres
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bindu
```

#### How It Works

When `enable_dspy: true` is set:

1. Agent startup checks for the `enable_dspy` flag in your manifest
2. On each user request, the system calls `select_prompt_with_canary()`
3. The prompt selector fetches `active` and `candidate` prompts from PostgreSQL
4. Weighted random selection based on traffic allocation (e.g., 90% active, 10% candidate)
5. Selected prompt replaces the system message in the agent's context

**Logs:**
```
🔧 DSPy Optimization: ✅ ENABLED - System prompts will be loaded from database with canary deployment
```

#### What It Does NOT Do

- Does **not** train new prompts (use CLI `train` command)
- Does **not** adjust traffic allocation (use CLI `canary` command)
- Simply reads from database and selects prompts based on current traffic settings

---

### 2. Train New Prompts (Offline)

**Purpose:** Generate optimized prompt candidates using DSPy machine learning algorithms.

**When to use:** Periodically (e.g., daily) when you've accumulated enough user feedback and want to create improved prompts.

#### Configuration

Training is controlled entirely via environment variables and CLI arguments.

##### Required Environment Variables

```bash
# PostgreSQL connection (required)
STORAGE_TYPE=postgres
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bindu

# OpenRouter API Key (required for DSPy training)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# DSPy Configuration
DSPY__DEFAULT_MODEL=openrouter/openai/gpt-4o-mini
DSPY__MIN_FEEDBACK_THRESHOLD=0.8

# Dataset Constraints
DSPY__MIN_EXAMPLES=2
DSPY__MAX_EXAMPLES=10000
DSPY__MIN_INPUT_LENGTH=10
DSPY__MIN_OUTPUT_LENGTH=10

# Initial A/B Test Traffic Split (after training)
DSPY__INITIAL_CANDIDATE_TRAFFIC=0.4  # 40% to new candidate
DSPY__INITIAL_ACTIVE_TRAFFIC=0.6     # 60% to current active

# Note: DID is required and must be passed via --did CLI flag
```

##### Optional Environment Variables

```bash
# Advanced dataset settings
DSPY__MAX_FULL_HISTORY_LENGTH=10000
DSPY__DEFAULT_N_TURNS=3
DSPY__DEFAULT_WINDOW_SIZE=2
DSPY__DEFAULT_STRIDE=1

# Optimization parameters
DSPY__NUM_PROMPT_CANDIDATES=3
DSPY__MAX_BOOTSTRAPPED_DEMOS=8
DSPY__MAX_INTERACTIONS_QUERY_LIMIT=10000
```

#### CLI Command

```bash
python -m bindu.dspy.cli.train \
  --optimizer simba \
  --strategy last_turn \
  --require-feedback \
  --did "did:bindu:author:sales-agent:0a174d468f2c40268f03159ca9b4eac2" \
  --bsize 32 \
  --num-candidates 6 \
  --max-steps 8 \
  --max-demos 4 \
  --num-threads 4
```

#### CLI Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--optimizer` | Yes | Optimizer to use: `simba` or `gepa` | - |
| `--did` | **Yes** | DID for schema isolation | - |
| `--strategy` | No | Extraction strategy (see [Extraction Strategies](#extraction-strategies)) | `last_turn` |
| `--require-feedback` | No | Only use interactions with user feedback | `false` |
| `--bsize` | No | Mini-batch size for optimizer | `32` |
| `--num-candidates` | No | Candidate programs per iteration | `6` |
| `--max-steps` | No | Optimization steps to run | `8` |
| `--max-demos` | No | Max demonstrations per predictor | `4` |
| `--num-threads` | No | Threads for parallel execution | `auto` |

#### What Happens During Training

1. **System Stability Check**: Ensures no active A/B test is running (no candidate prompt exists)
2. **Fetch Active Prompt**: Retrieves current production prompt from database
3. **Configure DSPy**: Sets up DSPy with the model from `DSPY__DEFAULT_MODEL`
4. **Build Golden Dataset**:
   - Fetch tasks with feedback from PostgreSQL
   - Normalize feedback scores to [0.0, 1.0]
   - Extract interactions using chosen strategy
   - Filter by `DSPY__MIN_FEEDBACK_THRESHOLD`
   - Validate (min length, non-empty content)
   - Deduplicate
5. **Convert to DSPy Format**: Transform to `dspy.Example` objects
6. **Optimize**: Run SIMBA/GEPA optimizer on dataset
7. **Initialize A/B Test**:
   - Insert optimized prompt as `candidate` with traffic from `DSPY__INITIAL_CANDIDATE_TRAFFIC`
   - Update active prompt traffic to `DSPY__INITIAL_ACTIVE_TRAFFIC`
   - Zero out all other prompts

#### Output

```
INFO Starting DSPy training pipeline with last_turn strategy (DID: public)
INFO Checking system stability
INFO System stable check passed: no active candidate prompt
INFO Fetching active prompt from database
INFO Using active prompt (id=1) as base for optimization
INFO Configuring DSPy with model: openrouter/openai/gpt-4o-mini
INFO Building golden dataset (strategy=last_turn, require_feedback=True, threshold=0.8)
INFO Golden dataset prepared with 150 examples
INFO Converting to DSPy examples
INFO Initializing agent program
INFO Running prompt optimization using SIMBA
INFO Extracting optimized instructions from predictor
INFO Inserting optimized prompt as candidate with 40% traffic
INFO Candidate prompt inserted (id=2)
INFO Setting active prompt (id=1) to 60% traffic
INFO Zeroing out traffic for all other prompts
INFO A/B test initialized: active (id=1) at 60%, candidate (id=2) at 40%
```

---

### 3. Canary Deployment (Offline)

**Purpose:** Gradually shift traffic between active and candidate prompts based on performance metrics.

**When to use:** Run periodically (e.g., hourly via cron) after training to monitor A/B test results and automatically promote/rollback candidates.

#### Configuration

Canary deployment is controlled via environment variables and CLI arguments.

##### Required Environment Variables

```bash
# PostgreSQL connection (required)
STORAGE_TYPE=postgres
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bindu

# Canary Deployment Settings
DSPY__MIN_CANARY_INTERACTIONS_THRESHOLD=2  # Min interactions before comparison
DSPY__CANARY_TRAFFIC_STEP=0.2               # Traffic adjustment per run (20%)

# Note: DID is required and must be passed via --did CLI flag
```

#### CLI Command

```bash
python -m bindu.dspy.cli.canary \
  --did "did:bindu:author:sales-agent:0a174d468f2c40268f03159ca9b4eac2"
```

#### CLI Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--did` | **Yes** | DID for schema isolation | - |

#### How Canary Works

The canary controller compares average feedback scores between `active` and `candidate` prompts:

1. **Fetch Prompts**: Get both `active` and `candidate` from database with metrics:
   - `num_interactions`: Total interactions using this prompt
   - `average_feedback_score`: Mean normalized feedback score [0.0, 1.0]
   - `traffic`: Current traffic allocation [0.0, 1.0]

2. **Check Threshold**: If candidate has fewer than `DSPY__MIN_CANARY_INTERACTIONS_THRESHOLD` interactions, treat as tie (no action)

3. **Compare Metrics**:
   - **Candidate Wins** (higher avg score): Promote by `DSPY__CANARY_TRAFFIC_STEP`
   - **Active Wins** (higher avg score): Rollback by `DSPY__CANARY_TRAFFIC_STEP`
   - **Tie** (equal scores or missing data): No change

4. **Stabilization**: When traffic reaches 0% or 100%:
   - **Candidate at 100%**: Promote to `active`, deprecate old active
   - **Candidate at 0%**: Mark as `rolled_back`

#### Example Scenarios

**Scenario 1: Candidate is Winning**
```
Active: avg_score=0.82, traffic=0.6
Candidate: avg_score=0.91, traffic=0.4, interactions=5

Action: Promote
Result: Active traffic=0.4, Candidate traffic=0.6
```

**Scenario 2: Active is Winning**
```
Active: avg_score=0.89, traffic=0.4
Candidate: avg_score=0.75, traffic=0.6, interactions=8

Action: Rollback
Result: Active traffic=0.6, Candidate traffic=0.4
```

**Scenario 3: Not Enough Data**
```
Active: avg_score=0.85, traffic=0.6
Candidate: avg_score=0.88, traffic=0.4, interactions=1

Action: No change (below threshold of 2 interactions)
```

**Scenario 4: Full Promotion**
```
Active: avg_score=0.80, traffic=0.0
Candidate: avg_score=0.95, traffic=1.0, interactions=100

Action: Stabilize
Result: Candidate becomes new active, old active marked as deprecated
```

#### Output Logs

```
INFO Starting canary controller (DID: public)
INFO Candidate is winning (score=0.910 vs active=0.820)
INFO Promoting candidate: traffic 0.4 -> 0.6, active 0.6 -> 0.4
INFO Canary controller storage connection closed
```

---

## Configuration Reference

### Environment Variables

All DSPy settings use the `DSPY__` prefix:

#### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DSPY__DEFAULT_MODEL` | string | `openrouter/openai/gpt-4o-mini` | Model for DSPy optimization (use `openrouter/` prefix) |
| `DSPY__MIN_FEEDBACK_THRESHOLD` | float | `0.8` | Min normalized feedback score [0.0-1.0] for training inclusion |

#### Dataset Filtering

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DSPY__MIN_EXAMPLES` | int | `2` | Minimum examples required in golden dataset |
| `DSPY__MAX_EXAMPLES` | int | `10000` | Maximum examples allowed in golden dataset |
| `DSPY__MIN_INPUT_LENGTH` | int | `10` | Minimum character length for user input |
| `DSPY__MIN_OUTPUT_LENGTH` | int | `10` | Minimum character length for agent output |
| `DSPY__MAX_FULL_HISTORY_LENGTH` | int | `10000` | Max characters for full history extraction |

#### Strategy Defaults

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DSPY__DEFAULT_N_TURNS` | int | `3` | Default turns for `last_n` and `first_n` strategies |
| `DSPY__DEFAULT_WINDOW_SIZE` | int | `2` | Default window size for sliding window |
| `DSPY__DEFAULT_STRIDE` | int | `1` | Default stride for sliding window (1 = overlapping) |

#### Optimization Parameters

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DSPY__NUM_PROMPT_CANDIDATES` | int | `3` | Number of optimized prompt candidates to generate |
| `DSPY__MAX_BOOTSTRAPPED_DEMOS` | int | `8` | Max bootstrapped demonstrations for few-shot learning |
| `DSPY__MAX_INTERACTIONS_QUERY_LIMIT` | int | `10000` | Max interactions to fetch from database per query |

#### Canary Deployment

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DSPY__MIN_CANARY_INTERACTIONS_THRESHOLD` | int | `2` | Min interactions before comparing candidate metrics |
| `DSPY__CANARY_TRAFFIC_STEP` | float | `0.2` | Traffic adjustment per canary run (0.2 = 20%) |
| `DSPY__INITIAL_CANDIDATE_TRAFFIC` | float | `0.4` | Initial traffic for new candidate after training (40%) |
| `DSPY__INITIAL_ACTIVE_TRAFFIC` | float | `0.6` | Initial traffic for active when candidate created (60%) |

### Agent Config (JSON)

Add to your agent's configuration file:

```json
{
  "enable_dspy": true
}
```

This is the **only** agent-specific setting needed. All other DSPy configuration is environment-based.

---

## Extraction Strategies

Extraction strategies determine how conversation history is transformed into training examples. Different strategies suit different use cases.

### Available Strategies

#### 1. `last_turn` (Default)

Extracts only the final user-assistant exchange.

**Use when:** Your agent is stateless or each interaction is independent.

```bash
--strategy last_turn
```

**Example:**
```
Input:  "What is 2+2?"
Output: "4"
```

---

#### 2. `full_history`

Extracts the complete conversation history.

**Use when:** Context from entire conversation is critical for optimization.

```bash
--strategy full_history
```

**Example:**
```
Input:  "User: Hi\nAssistant: Hello!\nUser: What is 2+2?"
Output: "User said hi, I greeted them, then they asked about 2+2. The answer is 4."
```

**Constraint:** Total history must be under `DSPY__MAX_FULL_HISTORY_LENGTH` characters.

---

#### 3. `last_n:N`

Extracts the last N conversation turns.

**Use when:** Recent context matters, but full history is too noisy.

```bash
--strategy last_n:3  # Last 3 turns
```

**Example (last_n:2):**
```
Input:  "User: What is the capital of France?\nAssistant: Paris.\nUser: What is its population?"
Output: "Approximately 2.2 million people live in Paris."
```

---

#### 4. `first_n:N`

Extracts the first N conversation turns.

**Use when:** Initial interactions set important context or instructions.

```bash
--strategy first_n:3  # First 3 turns
```

---

#### 5. `context_window`

*Advanced strategy - requires code-level configuration (not available via CLI)*

Extracts N turns with optional system prompt injection.

**Use when:** You need fine control over context window and system messages.

---

#### 6. `sliding_window`

*Advanced strategy - requires code-level configuration*

Creates multiple overlapping training examples from a single conversation.

**Use when:** You want to maximize training data from long conversations.

---

## CLI Reference

### Training CLI

```bash
python -m bindu.dspy.cli.train [OPTIONS]
```

#### Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--optimizer` | choice | **Yes** | - | Optimizer: `simba` or `gepa` |
| `--did` | string | **Yes** | `null` | DID for multi-tenant isolation |
| `--strategy` | string | No | `last_turn` | Extraction strategy (see above) |
| `--require-feedback` | flag | No | `false` | Only use interactions with feedback |
| `--bsize` | int | No | `32` | Mini-batch size for SIMBA/GEPA |
| `--num-candidates` | int | No | `6` | Candidate programs per iteration |
| `--max-steps` | int | No | `8` | Optimization steps to run |
| `--max-demos` | int | No | `4` | Max demonstrations per predictor |
| `--num-threads` | int | No | `auto` | Parallel execution threads |

---

### Canary CLI

```bash
python -m bindu.dspy.cli.canary [OPTIONS]
```

#### Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--did` | string | **Yes** | - | DID for multi-tenant isolation |

---

## Advanced Topics

### Multi-Tenancy with DIDs

Bindu supports multi-tenant prompt management using Decentralized Identifiers (DIDs). Each agent can have isolated prompts, feedback, and A/B tests.

**DID Format:**
```
did:bindu:author:agent:id
```

**Example:**
```
did:bindu:john:sales-agent:production
```

**How to Use:**

1. **Set DID in CLI (required):**
   ```bash
   --did "did:bindu:john:sales-agent:production"
   ```

2. **Schema Isolation:** Each DID gets its own PostgreSQL schema, ensuring complete data isolation

---

### Scheduling with Cron

Recommended cron setup:

```bash
# Train daily at 2 AM (DID is required)
0 2 * * * cd /path/to/bindu && python -m bindu.dspy.cli.train --optimizer simba --did "did:bindu:author:agent:v1" --require-feedback

# Run canary hourly (DID is required)
0 * * * * cd /path/to/bindu && python -m bindu.dspy.cli.canary --did "did:bindu:author:agent:v1"
```

For multi-agent setups:

```bash
# Agent 1
0 2 * * * python -m bindu.dspy.cli.train --optimizer simba --did "did:bindu:acme:agent1:v1" --require-feedback
0 * * * * python -m bindu.dspy.cli.canary --did "did:bindu:acme:agent1:v1"

# Agent 2
15 2 * * * python -m bindu.dspy.cli.train --optimizer gepa --did "did:bindu:acme:agent2:v1" --require-feedback
15 * * * * python -m bindu.dspy.cli.canary --did "did:bindu:acme:agent2:v1"
```

---

### Understanding Optimizers

#### SIMBA (Similarity-Based Meta-Prompting with Adaptation)

**Best for:** General-purpose prompt optimization with balanced exploration/exploitation.

**Characteristics:**
- Uses similarity-based selection of demonstrations
- Adapts prompts based on feedback scores
- Good for diverse datasets

**When to use:**
- You have varied user interactions
- You want robust prompts that generalize well
- Default choice for most cases

---

#### GEPA (Guided Exploration with Probabilistic Adaptation)

**Best for:** More aggressive prompt optimization with probabilistic exploration.

**Characteristics:**
- Guided exploration of prompt space
- Probabilistic adaptation based on metrics
- Can find more creative prompt variations

**When to use:**
- You want to explore prompt variations more aggressively
- You have well-defined success metrics (feedback scores)
- You're willing to experiment beyond conservative changes

---

### Metrics and Feedback

The system uses normalized feedback scores [0.0, 1.0]:

| Feedback Type | Raw Value | Normalized |
|---------------|-----------|------------|
| 5-star rating | 1-5 | 0.0-1.0 |
| Thumbs up/down | true/false | 1.0/0.0 |
| Custom score | any | normalized to [0.0, 1.0] |

**Golden Dataset Inclusion:**

Only interactions with `normalized_score >= DSPY__MIN_FEEDBACK_THRESHOLD` are included in training.

**Canary Comparison:**

Average feedback score determines winner:
- `avg(candidate) > avg(active)` → Promote
- `avg(active) > avg(candidate)` → Rollback
- Equal or insufficient data → No change

---

### Prompt States

| State | Description | Traffic | Next State |
|-------|-------------|---------|------------|
| `active` | Current production prompt | Usually high (60-100%) | Can become `deprecated` |
| `candidate` | New prompt being tested | Starts low (40%), can increase | Can become `active` or `rolled_back` |
| `deprecated` | Old active after candidate promotion | 0% | Terminal state |
| `rolled_back` | Failed candidate | 0% | Terminal state |

**State Transitions:**

```
Training → candidate (40%) + active (60%)
         ↓
Canary runs (hourly)
         ↓
Candidate wins → active (100%) + deprecated (0%)
OR
Candidate loses → rolled_back (0%) + active (100%)
```

---

### Troubleshooting

#### "No active prompt found"

**Cause:** Database has no `active` status prompt.

**Solution:**
```sql
-- Insert an initial active prompt manually
INSERT INTO prompts (prompt_text, status, traffic, created_at)
VALUES ('You are a helpful AI assistant.', 'active', 1.0, NOW());
```

---

#### "Experiment still active"

**Cause:** A `candidate` prompt already exists when trying to train.

**Solution:** Wait for canary to stabilize (promote or rollback), or manually resolve:

```sql
-- Check current state
SELECT id, status, traffic FROM prompts WHERE status IN ('active', 'candidate');

-- Option 1: Force rollback
UPDATE prompts SET status='rolled_back', traffic=0.0 WHERE status='candidate';
UPDATE prompts SET traffic=1.0 WHERE status='active';

-- Option 2: Force promotion
UPDATE prompts SET status='active', traffic=1.0 WHERE status='candidate';
UPDATE prompts SET status='deprecated', traffic=0.0 WHERE status='active' AND id != <candidate_id>;
```

---

#### "Golden dataset empty"

**Cause:** No interactions meet `DSPY__MIN_FEEDBACK_THRESHOLD`.

**Solutions:**
1. Lower threshold: `DSPY__MIN_FEEDBACK_THRESHOLD=0.5`
2. Disable feedback requirement: `--require-feedback` (omit flag)
3. Collect more user feedback before training

---

### Module Structure

```
bindu/dspy/
├── __init__.py              # Public API (train)
├── models.py                # Data models (Interaction, PromptCandidate)
├── dataset.py               # Golden dataset pipeline
├── extractor.py             # Interaction extraction orchestrator
├── guard.py                 # Training safety checks
├── optimizer.py             # DSPy optimizer wrapper
├── program.py               # DSPy program definition
├── prompts.py               # Prompt CRUD operations
├── prompt_selector.py       # Canary-based prompt selection
├── signature.py             # DSPy signature definitions
├── train.py                 # Main training orchestrator
│
├── strategies/              # Extraction strategy implementations
│   ├── __init__.py
│   ├── base.py             # Abstract base class
│   ├── last_turn.py        # Last turn extraction
│   ├── full_history.py     # Full conversation extraction
│   ├── last_n_turns.py     # Last N turns
│   ├── first_n_turns.py    # First N turns
│   ├── context_window.py   # Context window with system prompt
│   ├── sliding_window.py   # Sliding window (multiple examples)
│   └── ...
│
├── canary/                  # Canary deployment subsystem
│   ├── __init__.py
│   └── controller.py       # Canary logic (promote/rollback)
│
└── cli/                     # Command-line interfaces
    ├── train.py            # Training CLI entry point
    └── canary.py           # Canary CLI entry point
```

---

## Quick Start Guide

### Step 1: Enable DSPy in Your Agent

Edit your agent config:

```json
{
  "name": "My Agent",
  "enable_dspy": true,
  ...
}
```

Set environment variables:

```bash
export STORAGE_TYPE=postgres
export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bindu
export OPENROUTER_API_KEY=your_openrouter_api_key_here
export DSPY__DEFAULT_MODEL=openrouter/openai/gpt-4o-mini
```

### Step 2: Insert Initial Active Prompt

```sql
INSERT INTO prompts (prompt_text, status, traffic, created_at)
VALUES ('You are a helpful AI assistant.', 'active', 1.0, NOW());
```

### Step 3: Collect User Feedback

Start your agent and have users interact with it. Collect feedback via your feedback mechanism.

### Step 4: Train Optimized Prompts

```bash
python -m bindu.dspy.cli.train \
  --optimizer simba \
  --strategy last_turn \
  --require-feedback \
  --did "did:bindu:author:sales-agent:0a174d468f2c40268f03159ca9b4eac2" \
  --bsize 32 \
  --num-candidates 6 \
  --max-steps 8 \
  --max-demos 4 \
  --num-threads 4
```

### Step 5: Run Canary (Automated)

Set up hourly cron:

```bash
0 * * * * python -m bindu.dspy.cli.canary --did "did:bindu:author:sales-agent:0a174d468f2c40268f03159ca9b4eac2"
```

### Step 6: Monitor

Watch logs for promotion/rollback events, check database for prompt states:

```sql
SELECT id, status, traffic, average_feedback_score, num_interactions
FROM prompts
ORDER BY created_at DESC;
```

---

## Additional Resources

- [DSPy Documentation](https://docs.getbindu.com/bindu/learn/dspy/overview)
- [Bindu Main README](../../README.md)
- [Task Feedback Documentation](../../README.md#task-feedback-and-dspy)

---

## Support

Issues and questions: [GitHub Issues](https://github.com/getbindu/Bindu/issues/new/choose)
