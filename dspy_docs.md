# DSPy Integration in Bindu

Bindu integrates **DSPy** to allow agents to *improve their system prompts automatically* using real user feedback — safely, gradually, and reversibly.

This document explains:

1. How to **enable DSPy** in a Bindu agent
2. How the **runtime prompt routing** works
3. How **offline DSPy training** works
4. How **canary promotion & rollback** work
5. What infrastructure (Postgres, cron) is required
6. The mental model behind the system

---

## Why DSPy in Bindu?

Traditional agents are **static**:

```
LLM + hardcoded prompt → response
```

With DSPy enabled, Bindu agents become **self-improving systems**:

```
LLM + evolving prompt + feedback data → better responses over time
```

Key principles:

* No online learning
* No unsafe hot-swapping
* No irreversible changes
* Every change is measurable and rollback-safe

---

## High-Level Architecture

When DSPy is enabled, a Bindu agent consists of:

```
Agent Runtime
├── LLM
├── Prompt Router (active vs candidate)
├── Feedback Collector
└── Metrics Updater

Offline Controllers
├── DSPy Trainer (slow, infrequent)
└── Canary Controller (fast, frequent)

Persistent Storage
└── PostgreSQL
```

---

## Enabling DSPy in a Bindu Agent

### 1. Enable PostgreSQL

DSPy **requires Postgres**.

Postgres stores:

* All agent interactions
* User feedback
* Prompt versions
* Traffic split state
* Performance metrics

Once Postgres is enabled:

* Feedback is automatically stored
* Prompt metrics are continuously updated

> **Important:**
> If DSPy is enabled, Postgres is mandatory.
> Without Postgres, DSPy cannot run.

---

### 2. Initial Prompt Bootstrapping

When the agent starts for the **first time**:

* The system prompt is taken from `main.py`
* This prompt is saved into the database as:

  * `status = active`
  * `traffic = 100%`

From this point onward:

* **The hardcoded prompt is no longer used**
* All future requests fetch prompts from the database

---

## Runtime Prompt Routing (Online Path)

This happens **on every agent request**.

### Fetch Prompts

For each request, the agent:

1. Fetches the **active prompt**
2. Fetches the **candidate prompt** (if exists)
3. Reads their traffic percentages

Example:

```
active:    90%
candidate: 10%
```

---

### Route Traffic

A random draw determines which prompt is used:

* If the request falls in 90% → active prompt
* If the request falls in 10% → candidate prompt

This is **true canary routing**, not a toggle.

---

### Store Feedback & Metrics

After the response:

* User feedback is stored
* Prompt metrics are updated continuously:

For each prompt:

* `num_interactions`
* `average_feedback`

This happens **per interaction**, not in batch.

---

## Prompt Storage Model

Each prompt is stored as a row in `agent_prompts`:

Key fields:

* `prompt_text`
* `status` (`active`, `candidate`, `archived`)
* `traffic_percentage`
* `num_interactions`
* `average_feedback`
* timestamps

At any time:

* At most **2 prompts have non-zero traffic**
* This simplifies comparison and rollback

---

## Offline DSPy Training (Slow Path)

DSPy training **never runs during live traffic routing**.

### Supported Optimizers

> **Current limitation**
>
> At the moment, Bindu only supports the **SIMBA** optimizer for DSPy-based
> prompt optimization.
>
> Other DSPy optimizers (e.g. GEPA, MIPRO) are **not supported yet**, but are
> planned for future releases.

---

### How It’s Triggered

DSPy training is run **offline** via a CLI command.

The user is expected to trigger this using either:

* Manual execution, or
* A cron job (recommended)

---

### Manual Training Run

From the agent project root:

```
uv run python -m bindu.dspy.cli.train \
  --optimizer simba \
  --strategy full_history \
  --require-feedback
```

This command:

* Ensures the system is stable
* Fetches the active prompt
* Builds the golden dataset
* Runs DSPy (SIMBA)
* Inserts a new candidate prompt (10% traffic)
* Initializes a canary experiment (90/10 split)

---

### Cron-Based Training (Recommended)

Example: **run once every 24 hours**

```
0 2 * * * cd /srv/my_agent && uv run python -m bindu.dspy.cli.train --optimizer simba --require-feedback
```

> Training will **automatically skip** if:
>
> * A canary experiment is already running
> * The system is not stable

---

### What “Stable” Means

The system is stable if:

* Exactly **one prompt has 100% traffic**
* No canary experiment is running

If traffic is split (e.g. 90/10):

* Training is skipped
* The system waits for promotion or rollback

---

### What Training Does

When training runs:

1. Fetch golden dataset (good + bad interactions)
2. Fetch current active prompt
3. Run DSPy optimizer (SIMBA)
4. Generate a **new candidate prompt**
5. Store it in the database as:

   * `status = candidate`
   * `traffic = 10%`
6. Reduce active prompt traffic to `90%`

At this point:

* A canary experiment begins
* No further training will occur until stability is restored

---

## Canary Controller (Fast Path)

The canary controller is a **separate offline job**.

---

### Manual Canary Run

From the agent project root:

```
uv run python -m bindu.dspy.cli.canary
```

This performs **one evaluation step** and may:

* Promote the candidate
* Roll back the candidate
* Or leave traffic unchanged

---

### Cron-Based Canary Controller (Recommended)

Example: **run every hour**

```
0 * * * * cd /srv/my_agent && uv run python -m bindu.dspy.cli.canary
```

This job is:

* Lightweight
* Metric-driven
* Safe to run frequently

---

### What Canary Controller Does

On each run:

1. Fetch active and candidate prompts
2. Compare metrics (e.g. `average_feedback`)
3. Decide one of three actions:

#### 1️⃣ Promote Candidate

* Candidate performs better
* Increase candidate traffic
* Eventually:

  * candidate → 100%
  * active → 0%
* Old active is archived
* System becomes stable

#### 2️⃣ Roll Back Candidate

* Candidate performs worse
* Reduce candidate traffic
* Eventually:

  * candidate → 0%
  * active → 100%
* Candidate is archived
* System becomes stable

#### 3️⃣ Do Nothing

* Not enough data yet
* Keep current traffic split

---

## Promotion & Rollback Are Independent of Training

This is critical.

* **Training creates candidates**
* **Canary decides their fate**

Training:

* Rare (e.g. daily)
* Expensive
* Uses DSPy

Canary:

* Frequent (e.g. hourly)
* Cheap
* Uses metrics only

They never run at the same time.

---

## Cron Jobs Required

To use DSPy, users must configure **two cron jobs**.

### 1. DSPy Training (Slow)

Example:

```
0 2 * * *
```

Runs:

```
python -m bindu.dspy.cli.train --optimizer simba --require-feedback
```

Purpose:

* Generate new candidate prompts

---

### 2. Canary Controller (Fast)

Example:

```
0 * * * *
```

Runs:

```
python -m bindu.dspy.cli.canary
```

Purpose:

* Promote or roll back candidates safely

---

## Mental Model Summary

```
Users interact → feedback stored
↓
Metrics updated continuously
↓
(Every 24h) DSPy proposes a new prompt
↓
(Every 1h) Canary compares prompts
↓
Promote or rollback
↓
System stabilizes
↓
Next training allowed
```

---

## What the User Needs to Do

That’s it. Only **two responsibilities**:

1. Enable Postgres
2. Set cron jobs for:

   * DSPy training
   * Canary controller

Everything else is automatic.

---

## Why This Design Works

* ✅ Safe (canary + rollback)
* ✅ Measurable (metrics-driven)
* ✅ Reversible (no hard switches)
* ✅ Offline learning (no live mutations)
* ✅ Scales to many agents
* ✅ Compatible with any agent framework
