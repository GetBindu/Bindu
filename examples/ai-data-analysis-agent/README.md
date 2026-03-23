# AI Data Analysis Agent

An autonomous, agentic AI data analyst built for the Bindu framework. This agent can ingest raw CSV datasets, compute statistical summaries, identify missing values, and autonomously generate and save visual charts (bar, line, scatter) based on natural language prompts.

## Features

- **Automated Dataset Profiling:** Quickly reads CSV structures, data types, and null values.
- **Statistical Summarization:** Computes core metrics (mean, median, standard deviation) using Pandas.
- **Autonomous Visualization:** Uses a thread-safe Matplotlib/Seaborn backend (`Agg`) to securely generate and save `.png` charts without blocking background worker execution.
- **Self-Documenting:** Automatically saves its final synthesized Markdown report alongside the generated charts in an `outputs/` directory.

## Prerequisites

- Python 3.12+
- `uv` package manager (recommended)
- An OpenRouter API key

## Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Add your OpenRouter API key to the `.env` file.

## Usage
You can trigger the agent via the Bindu REST API or run it directly using the framework:
  ```bash
  uv run python examples/ai-data-analysis-agent/ai_data_analysis_agent.py
  ```
### Example Prompt

"Please analyze the dataset located at /path/to/sample_sales.csv. Give me a brief summary of the data, and then generate a bar chart showing Sales by Product."

## Architecture Notes
- **Thread Safety:** The visualization tool explicitly sets matplotlib.use('Agg') to prevent GUI thread panics when executed by Bindu's background task workers.
- **Autonomous Artifacts:** Instead of relying on client-side JSON parsing, the agent is configured to inherently save its own Markdown reports to the local file system.
