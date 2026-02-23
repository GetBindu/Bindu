# Structured Real-Time Research Report Agent with Citation Enforcement

## Overview

The **Structured Real-Time Research Report Agent** is an AI-powered research assistant designed to generate well-structured, source-backed reports using real-time web search.

The agent enforces citation inclusion, extracts publication dates and sources, and presents information in a clear analytical format suitable for financial, policy, and technical research contexts.

This project demonstrates:

* Tool-augmented AI (web search integration)
* Structured report generation
* Source and date extraction
* Citation-aware output formatting
* Interactive clarification for format and audience
* Production-ready agent deployment via Bindu

## Key Features

### 1. Mandatory Web Search

The agent uses live web search to retrieve recent, verifiable information.
It does not rely solely on prior knowledge.

### 2. Citation Enforcement

Each factual claim includes:

* Source name
* Article title (when available)
* Publication date
* URL (listed in the Sources section)

If verification is not possible, the agent explicitly flags the information.

### 3. Structured Output Format

All reports follow a consistent professional structure:

* Title
* Introduction
* Key Findings
* Thematic Sections (if applicable)
* Analysis
* Conclusion
* Sources

### 4. Clarification Before Assumption

If a query is ambiguous (e.g., unspecified quarter, audience, or format), the agent requests clarification instead of making assumptions.

### 5. Formal Research Tone

Outputs are written in a neutral, professional tone suitable for:

* Financial reports
* Policy analysis
* Industry briefings
* Academic summaries
* Investor research

## Architecture

The agent is built using:

* **Bindu Agent Framework**
* **OpenRouter-compatible models**
* **DuckDuckGo web search tool**
* **Python 3.12+**
* **Environment-based API key configuration**

### Core Components

* `Agent` — Handles instruction-following and structured output
* `DuckDuckGoTools()` — Provides real-time web search capability
* OpenRouter model integration — Enables model flexibility
* Handler function — Connects the agent to Bindu deployment

## Installation

### Prerequisites

* Python 3.12 or higher
* UV package manager
* OpenRouter API key (free or paid)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Create Virtual Environment

```bash
uv venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
uv pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

## Running the Agent

From the project root:

```bash
uv run examples/research-report/research_report_agent.py
```

The agent will start locally and be accessible via the Bindu interface.

## Model Configuration

Example configuration using OpenRouter:

```python
model = OpenAIChat(
    id="nvidia/nemotron-3-nano-30b-a3b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.2,
)
```

You may switch to any supported OpenRouter model by changing the `id` field.

For production reliability, a paid endpoint is recommended to avoid rate limits and truncation.

## Agent Instructions (Core Logic)

The agent is configured with structured citation-aware instructions including:

* Mandatory use of web search
* Inclusion of dates and source names
* Structured formatting
* Explicit flagging of unverified claims
* Professional analytical tone
* Clarification prompts when necessary

## Example Prompts

The agent supports research queries such as:

* "Provide a detailed report on India's Union Budget 2026 announcements related to AI and semiconductors."
* "Write a structured financial report on Infosys FY2025 earnings with proper citations."
* "Summarize recent funding developments in AI startups with source-backed analysis."

## Output Format Example

```
# Title

## Introduction
Context and overview.

## Key Findings
- Finding 1 (Source: Publication, Date)
- Finding 2 (Source: Publication, Date)

## Analysis
Interpretation supported by cited sources.

## Conclusion
Summary of findings.

## Sources
1. Publication Name – Article Title – Date
   URL: https://example.com
```

## Design Principles

1. Accuracy over speed
2. Source-backed reporting
3. Structured professional formatting
4. Explicit uncertainty handling
5. Interactive clarification when needed

## Limitations

* Free-tier models may:

  * Truncate long responses
  * Hit rate limits
  * Return provider errors during peak usage
* Web search results depend on publicly available content
* Real-time updates depend on search availability

For high-volume or production use, a paid model endpoint is recommended.

## Contribution

This agent is designed as a structured, citation-aware research tool for open-source collaboration.

Improvements are welcome, particularly in:
* Enhanced citation formatting
* Source validation improvements
* Improved fallback logic
* Multi-source cross-verification
* Output standardization enhancements

## License

Refer to the repository’s `LICENSE` file for details.
