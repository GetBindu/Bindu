<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>The identity, communication & payments layer for AI agents</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.de.md">🇩🇪 Deutsch</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.fr.md">🇫🇷 Français</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Nederlands</a> •
  <a href="README.ta.md">🇮🇳 தமிழ்</a>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img src="https://hits.sh/github.com/Saptha-me/Bindu.svg" alt="Hits"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/dm/bindu" alt="PyPI Downloads"></a>
  <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
  <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
  <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://docs.getbindu.com"><img src="https://img.shields.io/badge/Documentation-📕-blue" alt="Documentation"></a>
  <a href="https://github.com/getbindu/Bindu/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
  <a href="https://github.com/getbindu/Bindu/stargazers"><img src="https://img.shields.io/github/stars/getbindu/Bindu" alt="GitHub stars"></a>
  <a href="https://github.com/getbindu/Bindu/network/members"><img src="https://img.shields.io/github/forks/getbindu/Bindu" alt="GitHub forks"></a>
  <a href="https://github.com/getbindu/Bindu/watchers"><img src="https://img.shields.io/github/watchers/getbindu/Bindu" alt="GitHub watchers"></a>
  <a href="https://github.com/getbindu/Bindu/issues"><img src="https://img.shields.io/github/issues/getbindu/Bindu" alt="GitHub issues"></a>
  <a href="https://github.com/getbindu/Bindu/pulls"><img src="https://img.shields.io/github/issues-pr/getbindu/Bindu" alt="GitHub pull requests"></a>
  <a href="https://github.com/getbindu/Bindu/commits/main"><img src="https://img.shields.io/github/commit-activity/m/getbindu/Bindu" alt="Commit activity"></a>
  <a href="https://github.com/getbindu/Bindu/commits/main"><img src="https://img.shields.io/github/last-commit/getbindu/Bindu" alt="Last commit"></a>
  <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
  <a href="https://github.com/getbindu/Bindu"><img src="https://img.shields.io/github/repo-size/getbindu/Bindu" alt="Repo size"></a>
  <a href="https://github.com/getbindu/Bindu/releases"><img src="https://img.shields.io/github/v/release/getbindu/Bindu" alt="Latest release"></a>
</p>

---

**Bindu** (read: _binduu_) is an operating layer for AI agents that provides identity, communication, and payment capabilities. It delivers a production-ready service with a convenient API to connect, authenticate, and orchestrate agents across distributed systems using open protocols: **A2A**, **AP2**, and **X402**.

Built with a distributed architecture (Task Manager, scheduler, storage), Bindu makes it fast to develop and easy to integrate with any AI framework. Transform any agent framework into a fully interoperable service for communication, collaboration, and commerce in the Internet of Agents.

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">Register your agent</a> • 🌻 <a href="https://docs.getbindu.com">Documentation</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord Community</a></strong>
</p>


---

<br/>

## 🎥 Watch Bindu in Action

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>


## 📋 Prerequisites

Before installing Bindu, ensure you have:

- **Python 3.12 or higher** - [Download here](https://www.python.org/downloads/)
- **UV package manager** - [Installation guide](https://github.com/astral-sh/uv)

### Verify Your Setup

```bash
# Check Python version
python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 Installation
<details>
<summary><b>Windows users note (Git & GitHub Desktop)</b></summary>

On some Windows systems, git may not be recognized in Command Prompt even after installation due to PATH configuration issues.

If you face this issue, you can use *GitHub Desktop* as an alternative:

1. Install GitHub Desktop from https://desktop.github.com/
2. Sign in with your GitHub account
3. Clone the repository using the repository URL:
   https://github.com/getbindu/Bindu.git

GitHub Desktop allows you to clone, manage branches, commit changes, and open pull requests without using the command line.

</details>

```bash
# Install Bindu
uv add bindu

# For development (if contributing to Bindu)
# Create and activate virtual environment
uv venv --python 3.12.9
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

uv sync --dev
```

<details>
<summary><b>Common Installation Issues</b> (click to expand)</summary>

<br/>

| Issue | Solution |
|-------|----------|
| `uv: command not found` | Restart your terminal after installing UV. On Windows, use PowerShell |
| `Python version not supported` | Install Python 3.12+ from [python.org](https://www.python.org/downloads/) |
| Virtual environment not activating (Windows) | Use PowerShell and run `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Download [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activate venv and run `uv sync --dev` |

</details>

---

<br/>

## 🚀 Quick Start

### Option 1: Using Cookiecutter (Recommended)

**Time to first agent: ~2 minutes ⏱️**

```bash
# Install cookiecutter
uv add cookiecutter

# Create your Bindu agent
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 Create Production Ready Agent in Minutes

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

That's it! Your local agent becomes a live, secure, discoverable service. [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Pro Tip:** Agents created with cookiecutter include GitHub Actions that automatically register your agent in the [Bindu Directory](https://bindus.directory) when you push to your repository. No manual registration needed!

### Option 2: Manual Setup

Create your agent script `my_agent.py`:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy it
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

Your agent is now live at `http://localhost:3773` and ready to communicate with other agents.

---

### Option 3: Minimal Echo Agent (Testing)

<details>
<summary><b>View minimal example</b> (click to expand)</summary>

Smallest possible working agent:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**Run and test:**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Test the agent with curl</b> (click to expand)</summary>

<br/>

Input:
```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--data '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Quote"
                }
            ],
            "kind": "message",
            "messageId": "550e8400-e29b-41d4-a716-446655440038",
            "contextId": "550e8400-e29b-41d4-a716-446655440038",
            "taskId": "550e8400-e29b-41d4-a716-446655440300"
        },
        "configuration": {
            "acceptedOutputModes": [
                "application/json"
            ]
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
}'
```

Output:
```bash
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440024",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440301",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "submitted",
            "timestamp": "2025-12-16T17:10:32.116980+00:00"
        },
        "history": [
            {
                "message_id": "550e8400-e29b-41d4-a716-446655440038",
                "context_id": "550e8400-e29b-41d4-a716-446655440038",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "kind": "message",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "role": "user"
            }
        ]
    }
}
```

Check the status of the task
```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440301"
    },
    "id": "550e8400-e29b-41d4-a716-446655440025"
}'
```

Output:
```bash
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440025",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440301",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "completed",
            "timestamp": "2025-12-16T17:10:32.122360+00:00"
        },
        "history": [
            {
                "message_id": "550e8400-e29b-41d4-a716-446655440038",
                "context_id": "550e8400-e29b-41d4-a716-446655440038",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "kind": "message",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "role": "user"
            },
            {
                "role": "assistant",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "kind": "message",
                "message_id": "2f2c1a8e-68fa-4bb7-91c2-eac223e6650b",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "context_id": "550e8400-e29b-41d4-a716-446655440038"
            }
        ],
        "artifacts": [
            {
                "artifact_id": "22ac0080-804e-4ff6-b01c-77e6b5aea7e8",
                "name": "result",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote",
                        "metadata": {
                            "did.message.signature": "5opJuKrBDW4woezujm88FzTqRDWAB62qD3wxKz96Bt2izfuzsneo3zY7yqHnV77cq3BDKepdcro2puiGTVAB52qf"  # pragma: allowlist secret
                        }
                    }
                ]
            }
        ]
    }
}
```

</details>

---

<br/>

## [Postgres Storage](https://docs.getbindu.com/bindu/learn/storage/overview)

Bindu uses PostgreSQL as its persistent storage backend for production deployments. The storage layer is built with SQLAlchemy's async engine and uses imperative mapping with protocol TypedDicts.

Its Optional  - InMemoryStorage is used by default.

### 📊 Storage Structure

The storage layer uses three main tables:

1. **tasks_table**: Stores all tasks with JSONB history and artifacts
2. **contexts_table**: Maintains context metadata and message history
3. **task_feedback_table**: Optional feedback storage for tasks

### ⚙️ Configuration

<details>
<summary><b>View configuration example</b> (click to expand)</summary>

Configure PostgreSQL connection via environment variables:

```bash
STORAGE_TYPE=postgres
DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/bindu
```

Then use the simplified config:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}
```

</details>

 **💡 Task-First Pattern**: The storage supports Bindu's task-first approach where tasks can be continued by appending messages to non-terminal tasks, enabling incremental refinements and multi-turn conversations.

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu uses Redis as its distributed task scheduler for coordinating work across multiple workers and processes. The scheduler uses Redis lists with blocking operations for efficient task distribution.

Its Optional - InMemoryScheduler is used by default.

### ⚙️ Configuration

<details>
<summary><b>View configuration example</b> (click to expand)</summary>

Configure Redis connection via environment variables:

```bash
SCHEDULER_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```

Then use the simplified config:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}
```

</details>

All operations are queued in Redis and processed by available workers using a blocking pop mechanism, ensuring efficient distribution without polling overhead.

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> Automatic retry logic with exponential backoff for resilient Bindu agents

Bindu includes a built-in Tenacity-based retry mechanism to handle transient failures gracefully across workers, storage, schedulers, and API calls. This ensures your agents remain resilient in production environments.


### ⚙️ Default Settings

If not configured, Bindu uses these defaults:

| Operation Type | Max Attempts | Min Wait | Max Wait |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Real-time error tracking and performance monitoring for Bindu agents

Sentry is a real-time error tracking and performance monitoring platform that helps you identify, diagnose, and fix issues in production. Bindu includes built-in Sentry integration to provide comprehensive observability for your AI agents.

### ⚙️ Configuration

<details>
<summary><b>View configuration example</b> (click to expand)</summary>

Configure Sentry directly in your `bindufy()` config:

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    # Storage, scheduler, sentry, and telemetry are now configured via environment variables
}

def handler(messages):
    # Your agent logic
    pass

bindufy(config, handler)
```

**Environment Variables:**

```bash
# Sentry Error Tracking (Optional)
SENTRY_ENABLED=true
SENTRY_DSN=https://<key>@<org-id>.ingest.sentry.io/<project-id>

# See examples/.env.example for complete configuration
``

</details>

### 🚀 Getting Started

1. **Create Sentry Account**: Sign up at [sentry.io](https://sentry.io)
2. **Get Your DSN**: Copy from project settings
3. **Configure Bindu**: Add `sentry` config (see above)
4. **Run Your Agent**: Sentry initializes automatically

> 📚 See the [full Sentry documentation](https://docs.getbindu.com/bindu/learn/sentry/overview) for complete details.

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> Rich capability advertisement for intelligent agent orchestration

The Bindu Skills System provides rich agent capability advertisement for intelligent orchestration and agent discovery. Inspired by Claude's skills architecture, it enables agents to provide detailed documentation about their capabilities for orchestrators to make informed routing decisions.

### 💡 What are Skills?

Skills in Bindu serve as **rich advertisement metadata** that help orchestrators:

* 🔍 **Discover** the right agent for a task
* 📖 **Understand** detailed capabilities and limitations
* ✅ **Validate** requirements before execution
* 📊 **Estimate** performance and resource needs
* 🔗 **Chain** multiple agents intelligently

> **Note**: Skills are not executable code—they're structured metadata that describe what your agent can do.

### 📋 Complete Skill Structure

<details>
<summary><b>View complete skill.yaml structure</b> (click to expand)</summary>

A skill.yaml file contains all metadata needed for intelligent orchestration:

```yaml
# Basic Metadata
id: pdf-processing-v1
name: pdf-processing
version: 1.0.0
author: raahul@getbindu.com

# Description
description: |
  Extract text, fill forms, and extract tables from PDF documents.
  Handles both standard text-based PDFs and scanned documents with OCR.

# Tags and Modes
tags:
  - pdf
  - documents
  - extraction

input_modes:
  - application/pdf

output_modes:
  - text/plain
  - application/json
  - application/pdf

# Example Queries
examples:
  - "Extract text from this PDF document"
  - "Fill out this PDF form with the provided data"
  - "Extract tables from this invoice PDF"

# Detailed Capabilities
capabilities_detail:
  text_extraction:
    supported: true
    types:
      - standard
      - scanned_with_ocr
    languages:
      - eng
      - spa
    limitations: "OCR requires pytesseract and tesseract-ocr"
    preserves_formatting: true

  form_filling:
    supported: true
    field_types:
      - text
      - checkbox
      - dropdown
    validation: true

  table_extraction:
    supported: true
    table_types:
      - simple
      - complex_multi_column
    output_formats:
      - json
      - csv

# Requirements
requirements:
  packages:
    - pypdf>=3.0.0
    - pdfplumber>=0.9.0
    - pytesseract>=0.3.10
  system:
    - tesseract-ocr
  min_memory_mb: 512

# Performance Metrics
performance:
  avg_processing_time_ms: 2000
  avg_time_per_page_ms: 200
  max_file_size_mb: 50
  max_pages: 500
  concurrent_requests: 5
  memory_per_request_mb: 500
  timeout_per_page_seconds: 30

# Rich Documentation
documentation:
  overview: |
    This agent specializes in PDF document processing with support for text extraction,
    form filling, and table extraction. Handles both standard text-based PDFs and
    scanned documents (with OCR).

  use_cases:
    when_to_use:
      - User uploads a PDF and asks to extract text
      - User needs to fill out PDF forms programmatically
      - User wants to extract tables from reports/invoices
    when_not_to_use:
      - PDF editing or modification
      - PDF creation from scratch
      - Image extraction from PDFs

  input_structure: |
    {
      "file": "base64_encoded_pdf_or_url",
      "operation": "extract_text|fill_form|extract_tables",
      "options": {
        "ocr": true,
        "language": "eng"
      }
    }

  output_format: |
    {
      "success": true,
      "pages": [{"page_number": 1, "text": "...", "confidence": 0.98}],
      "metadata": {"total_pages": 10, "processing_time_ms": 1500}
    }

  error_handling:
    - "Encrypted PDFs: Returns error requesting password"
    - "Corrupted files: Returns validation error with details"
    - "Timeout: 30s per page, returns partial results"

  examples:
    - title: "Extract Text from PDF"
      input:
        file: "https://example.com/document.pdf"
        operation: "extract_text"
      output:
        success: true
        pages:
          - page_number: 1
            text: "Extracted text..."
            confidence: 0.99

  best_practices:
    for_developers:
      - "Check file size before processing (max 50MB)"
      - "Use OCR only when necessary (3-5x slower)"
      - "Handle errors gracefully with user-friendly messages"
    for_orchestrators:
      - "Route based on operation type (extract/fill/parse)"
      - "Consider file size for performance estimation"
      - "Chain with text-analysis for content understanding"

# Assessment fields for skill negotiation
assessment:
  keywords:
    - pdf
    - extract
    - document
    - form
    - table

  specializations:
    - domain: invoice_processing
      confidence_boost: 0.3
    - domain: form_filling
      confidence_boost: 0.3

  anti_patterns:
    - "pdf editing"
    - "pdf creation"
    - "merge pdf"

  complexity_indicators:
    simple:
      - "single page"
      - "extract text"
    medium:
      - "multiple pages"
      - "fill form"
    complex:
      - "scanned document"
      - "ocr"
      - "batch processing"
```

</details>

### 🔌 API Endpoints

**List All Skills**:
```bash
GET /agent/skills
```

**Get Skill Details**:
```bash
GET /agent/skills/{skill_id}
```

**Get Skill Documentation**:
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 See the [Skills Documentation](https://github.com/getbindu/Bindu/tree/main/examples/skills) for complete examples.

---

<br/>

## Negotiation

> Capability-based agent selection for intelligent orchestration

Bindu's negotiation system enables orchestrators to query multiple agents and intelligently select the best one for a task based on skills, performance, load, and cost.

### 🔄 How It Works

1. **Orchestrator broadcasts** assessment request to multiple agents
2. **Agents self-assess** capability using skill matching and load analysis
3. **Orchestrator ranks** responses using multi-factor scoring
4. **Best agent selected** and task executed

### 🔌 Assessment Endpoint

<details>
<summary><b>View API details</b> (click to expand)</summary>

```bash
POST /agent/negotiation
```

**Request:**
```json
{
  "task_summary": "Extract tables from PDF invoices",
  "task_details": "Process invoice PDFs and extract structured data",
  "input_mime_types": ["application/pdf"],
  "output_mime_types": ["application/json"],
  "max_latency_ms": 5000,
  "max_cost_amount": "0.001",
  "min_score": 0.7,
  "weights": {
    "skill_match": 0.6,
    "io_compatibility": 0.2,
    "performance": 0.1,
    "load": 0.05,
    "cost": 0.05
  }
}
```

**Response:**
```json
{
  "accepted": true,
  "score": 0.89,
  "confidence": 0.95,
  "skill_matches": [
    {
      "skill_id": "pdf-processing-v1",
      "skill_name": "pdf-processing",
      "score": 0.92,
      "reasons": [
        "semantic similarity: 0.95",
        "tags: pdf, tables, extraction",
        "capabilities: text_extraction, table_extraction"
      ]
    }
  ],
  "matched_tags": ["pdf", "tables", "extraction"],
  "matched_capabilities": ["text_extraction", "table_extraction"],
  "latency_estimate_ms": 2000,
  "queue_depth": 2,
  "subscores": {
    "skill_match": 0.92,
    "io_compatibility": 1.0,
    "performance": 0.85,
    "load": 0.90,
    "cost": 1.0
  }
}
```

</details>

### 📊 Scoring Algorithm

Agents calculate a confidence score based on multiple factors:

```python
score = (
    skill_match * 0.6 +        # Primary: skill matching
    io_compatibility * 0.2 +   # Input/output format support
    performance * 0.1 +        # Speed and reliability
    load * 0.05 +              # Current availability
    cost * 0.05                # Pricing
)
```

### 🎯 Skill Assessment

<details>
<summary><b>View assessment metadata example</b> (click to expand)</summary>

Skills include assessment metadata for intelligent matching:

```yaml
assessment:
  keywords:
    - pdf
    - extract
    - table
    - invoice

  specializations:
    - domain: invoice_processing
      confidence_boost: 0.3
    - domain: table_extraction
      confidence_boost: 0.2

  anti_patterns:
    - "pdf editing"
    - "pdf creation"

  complexity_indicators:
    simple:
      - "single page"
      - "extract text"
    complex:
      - "scanned document"
      - "batch processing"
```

</details>

### 💡 Example: Multi-Agent Selection

```bash
# Query 10 translation agents
for agent in translation-agents:
  curl http://$agent:3773/agent/negotiation \
    -d '{"task_summary": "Translate technical manual to Spanish"}'

# Responses ranked by orchestrator
# Agent 1: score=0.98 (technical specialist, queue=2)
# Agent 2: score=0.82 (general translator, queue=0)
# Agent 3: score=0.65 (no technical specialization)
```

### ⚙️ Configuration

<details>
<summary><b>View configuration example</b> (click to expand)</summary>

Enable negotiation in your agent config:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    "negotiation": {
        "embedding_api_key": os.getenv("OPENROUTER_API_KEY"),  # Load from environment
    },
}
```

</details>

> 📚 See the [Negotiation Documentation](https://docs.getbindu.com/bindu/negotiation/overview) for complete details.

---

<br/>

## Task Feedback and DSPy

Bindu collects user feedback on task executions to enable continuous improvement through DSPy optimization. By storing feedback with ratings and metadata, you can build golden datasets from real interactions and use DSPy to automatically optimize your agent's prompts and behavior.

### Submitting Feedback

Provide feedback on any task using the `tasks/feedback` method:

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <your-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "Great job! The response was very helpful and accurate.",
        "rating": 5,
        "metadata": {
            "category": "quality",
            "source": "user",
            "helpful": true
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
}'
```

Feedback is stored in the `task_feedback` table and can be used to:
- Filter high-quality task interactions for training data
- Identify patterns in successful vs. unsuccessful completions
- Optimize agent instructions and few-shot examples with DSPy
- We are working on the DsPY - will release soon.

---

<br/>

## gRPC
Bindu can run a gRPC server alongside the JSON-RPC HTTP server.

**To Enable gRPC**
1. Generate protobufs (including .pyi stubs)
`python scripts/generate_proto.py`

2. Enable gRPC
```bash
export BINDU_GRPC_ENABLED=true
export BINDU_GRPC_HOST=0.0.0.0
export BINDU_GRPC_PORT=50051
```

3. Run your agent
```python
from bindu.penguin.bindufy import bindufy

def handler(messages: str) -> str:
    return "Hello from gRPC!"

config = {
    "author": "you@example.com",
    "name": "grpc-demo",
    "description": "grpc demo agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
}

bindufy(config, handler, run_server=True)
```

4. Call gRPC
```python
import grpc
from uuid import uuid4
from bindu.grpc import a2a_pb2, a2a_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = a2a_pb2_grpc.A2AServiceStub(channel)
request = a2a_pb2.MessageSendRequest(
    message=a2a_pb2.Message(
        message_id=str(uuid4()),
        context_id=str(uuid4()),
        task_id=str(uuid4()),
        parts=[a2a_pb2.Part(text=a2a_pb2.TextPart(text="hello"))],
        role="user",
        kind="message",
    )
)
print(stub.SendMessage(request))
```

NOTE: If you see `struct.proto not loaded`, add `from google.protobuf import struct_pb2` before importing bindu.grpc

## OpenTelemetry

Bindu integrates with **OpenTelemetry (OTEL)** to provide observability and tracing for your agents. Track agent execution, monitor performance, and debug issues using industry-standard observability platforms like **Arize** and **Langfuse**.

### Supported Platforms

- **[Arize](https://arize.com/)** - AI observability platform for monitoring and debugging ML models
- **[Langfuse](https://langfuse.com/)** - Open-source LLM engineering platform with tracing and analytics

### Configuration

Enable OpenTelemetry tracing via environment variables:

```bash
# Enable telemetry
TELEMETRY_ENABLED=true

# OTEL endpoint (Langfuse example)
OLTP_ENDPOINT=https://cloud.langfuse.com/api/public/otel/v1/traces

# Service name for your agent
OLTP_SERVICE_NAME=research-agent

# Authentication headers (Langfuse uses Basic Auth with API keys)
OLTP_HEADERS={"Authorization":"Basic <base64-encoded-public-key:secret-key>"}

# Optional: Enable verbose logging
OLTP_VERBOSE_LOGGING=true
```

### Features

- **Automatic Instrumentation**: Traces are automatically generated for agent execution, skill invocations, and LLM calls
- **Distributed Tracing**: Track requests across multiple services and workers
- **Performance Monitoring**: Measure latency, token usage, and resource consumption
- **Error Tracking**: Capture exceptions and failures with full context
- **Custom Attributes**: Add metadata to traces for filtering and analysis

### Platform-Specific Setup

**Langfuse:**
1. Create an account at [cloud.langfuse.com](https://cloud.langfuse.com)
2. Generate API keys (public and secret)
3. Base64 encode `public-key:secret-key` for the Authorization header
4. Configure environment variables:
   ```bash
   TELEMETRY_ENABLED=true
   OLTP_ENDPOINT=https://cloud.langfuse.com/api/public/otel/v1/traces
   OLTP_SERVICE_NAME=your-agent-name
   OLTP_HEADERS={"Authorization":"Basic <base64-encoded-public-key:secret-key>"}
   OLTP_VERBOSE_LOGGING=true  # Optional
   ```

**Arize:**
1. Create an account at [arize.com](https://arize.com)
2. Get your Space ID and API key from the Arize dashboard
3. Configure environment variables:
   ```bash
   TELEMETRY_ENABLED=true
   OLTP_ENDPOINT=https://otlp.arize.com/v1
   OLTP_SERVICE_NAME=your-agent-name
   OLTP_HEADERS={"space_id":"<your-space-id>","api_key":"<your-api-key>"}
   OLTP_VERBOSE_LOGGING=true  # Optional
   ```



---

<br/>

## 📬 Push Notifications

Bindu supports **real-time webhook notifications** for long-running tasks, following the [A2A Protocol specification](https://a2a-protocol.org/latest/specification/). This enables clients to receive push notifications about task state changes and artifact generation without polling.

### Quick Start

1. **Start webhook receiver:** `python examples/webhook_client_example.py`
2. **Configure agent** in `examples/echo_agent_with_webhooks.py`:
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **Run agent:** `python examples/echo_agent_with_webhooks.py`
4. **Send tasks** - webhook notifications arrive automatically

<details>
<summary><b>View webhook receiver implementation</b> (click to expand)</summary>

```python
from fastapi import FastAPI, Request, Header, HTTPException

@app.post("/webhooks/task-updates")
async def handle_task_update(request: Request, authorization: str = Header(None)):
    if authorization != "Bearer secret_abc123":
        raise HTTPException(status_code=401)

    event = await request.json()

    if event["kind"] == "status-update":
        print(f"Task {event['task_id']} state: {event['status']['state']}")
    elif event["kind"] == "artifact-update":
        print(f"Artifact generated: {event['artifact']['name']}")

    return {"status": "received"}
```

</details>

<details>
<summary><b>View notification event types</b> (click to expand)</summary>

<br/>

**Status Update Event** - Sent when task state changes:
```json
{
  "kind": "status-update",
  "task_id": "123e4567-...",
  "status": {"state": "working"},
  "final": false
}
```

**Artifact Update Event** - Sent when artifacts are generated:
```json
{
  "kind": "artifact-update",
  "task_id": "123e4567-...",
  "artifact": {
    "artifact_id": "456e7890-...",
    "name": "results.json",
    "parts": [...]
  }
}
```

</details>

### ⚙️ Configuration

<details>
<summary><b>View configuration example</b> (click to expand)</summary>

**Using `bindufy`:**

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "you@example.com",
    "name": "my_agent",
    "description": "Agent with push notifications",
    "deployment": {"url": "http://localhost:3773"},
    "capabilities": {"push_notifications": True},
    # Global webhook configuration is now set via environment variables:
    # GLOBAL_WEBHOOK_URL and GLOBAL_WEBHOOK_TOKEN
}

bindufy(config, handler)
```

**Per-Task Webhook Override:**

```python
"configuration": {
    "long_running": True,  # Persist webhook in database
    "push_notification_config": {
        "id": str(uuid4()),
        "url": "https://custom-endpoint.com/webhooks",
        "token": "custom_token_123"
    }
}
```

**Long-Running Tasks:**

For tasks that run longer than typical request timeouts (minutes, hours, or days), set `long_running=True` to persist webhook configurations across server restarts. The webhook config will be stored in the database (`webhook_configs` table).

</details>

📖 **[Complete Documentation](docs/long-running-task-notifications.md)** - Detailed guide with architecture, security, examples, and troubleshooting.

📖 **[gRPC Transport Guide](docs/GRPC.md)** - Setup, dual-protocol usage, client example, auth/TLS, RPC method coverage, and troubleshooting.

---

<br/>

## 🎨 Chat UI

Bindu includes a beautiful chat interface at `http://localhost:3773/docs`

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

The [**Bindu Directory**](https://bindus.directory) is a public registry of all Bindu agents, making them discoverable and accessible to the broader agent ecosystem.

### ✨ Automatic Registration with Cookiecutter

When you create an agent using the cookiecutter template, it includes a pre-configured GitHub Action that automatically registers your agent in the directory:

1. **Create your agent** using cookiecutter
2. **Push to GitHub** - The GitHub Action triggers automatically
3. **Your agent appears** in the [Bindu Directory](https://bindus.directory)

> **🔑 Note**: You need to collect the BINDU_PAT_TOKEN from bindus.directory and use it to register your agent.

### 📝 Manual Registration

We are working on a manual registration process.

---

<br/>

## 🌌 The Vision

```
a peek into the night sky
}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}
{{            +             +                  +   @          {{
}}   |                *           o     +                .    }}
{{  -O-    o               .               .          +       {{
}}   |                    _,.-----.,_         o    |          }}
{{           +    *    .-'.         .'-.          -O-         {{
}}      *            .'.-'   .---.   `'.'.         |     *    }}
{{ .                /_.-'   /     \   .'-.\.                   {{
}}         ' -=*<  |-._.-  |   @   |   '-._|  >*=-    .     + }}
{{ -- )--           \`-.    \     /    .-'/                   }}
}}       *     +     `.'.    '---'    .'.'    +       o       }}
{{                  .  '-._         _.-'  .                   }}
}}         |               `~~~~~~~`       - --===D       @   }}
{{   o    -O-      *   .                  *        +          {{
}}         |                      +         .            +    }}
{{ jgs          .     @      o                        *       {{
}}       o                          *          o           .  }}
{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
```

_Each symbol is an agent — a spark of intelligence. The tiny dot is Bindu, the origin point in the Internet of Agents._

### NightSky Connection [In Progress]

NightSky enables swarms of agents. Each Bindu is a dot annotating agents with the shared language of A2A, AP2, and X402. Agents can be hosted anywhere—laptops, clouds, or clusters—yet speak the same protocol, trust each other by design, and work together as a single, distributed mind.

> **💭 A Goal Without a Plan Is Just a Wish.**

---


<br/>

## 🛠️ Supported Agent Frameworks

Bindu is **framework-agnostic** and tested with:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Want integration with your favorite framework? [Let us know on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Testing

Bindu maintains **70%+ test coverage**:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## Troubleshooting
<details>
<summary>Common Issues</summary>

<br/>

| Issue | Solution |
|-------|----------|
| `Python 3.12 not found` | Install Python 3.12+ and set in PATH, or use `pyenv` |
| `bindu: command not found` | Activate virtual environment: `source .venv/bin/activate` |
| `Port 3773 already in use` | Change port in config: `"url": "http://localhost:4000"` |
| Pre-commit fails | Run `pre-commit run --all-files` |
| Tests fail | Install dev dependencies: `uv sync --dev` |
| `Permission denied` (macOS) | Run `xattr -cr .` to clear extended attributes |

**Reset environment:**
```bash
rm -rf .venv
uv venv --python 3.12.9
uv sync --dev
```

**Windows PowerShell:**
```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

</details>

<br/>

## 🤝 Contributing

We welcome contributions! Join us on [Discord](https://discord.gg/3w5zuYUuwt). Pick the channel that best matches your contribution.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Contributing Guidelines](.github/contributing.md)

---

<br/>

## 📜 License

Bindu is open-source under the [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos—your contributions make Bindu better.

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) for discussions and support
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) if you find it useful!

---

<br/>

## 👥 Active Moderators

Our dedicated moderators help maintain a welcoming and productive community:

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/raahulrahl">
        <img src="https://avatars.githubusercontent.com/u/157174139?v=4" width="100px;" alt="Raahul Dutta"/>
        <br />
        <sub><b>Raahul Dutta</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/Paraschamoli">
        <img src="https://avatars.githubusercontent.com/u/157124537?v=4" width="100px;" alt="Paras Chamoli"/>
        <br />
        <sub><b>Paras Chamoli</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/Gaurika-Sethi">
        <img src="https://avatars.githubusercontent.com/u/178935569?v=4" width="100px;" alt="Gaurika Sethi"/>
        <br />
        <sub><b>Gaurika Sethi</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/lsvishaal">
        <img src="https://avatars.githubusercontent.com/u/62366204?v=4" width="100px;" alt="Vishaal LS"/>
        <br />
        <sub><b>Vishaal LS</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/Avngrstark62">
        <img src="https://avatars.githubusercontent.com/u/133889196?v=4" width="100px;" alt="Abhijeet Singh Thakur"/>
        <br />
        <sub><b>Abhijeet Singh Thakur</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/RajezMariner">
        <img src="https://avatars.githubusercontent.com/u/30373242?v=4s" width="100px;" alt="Rajesh Somasundaram"/>
        <br />
        <sub><b>Rajesh Somasundaram</b></sub>
      </a>
      <br />
    </td>
  </tr>
</table>

> Want to become a moderator? Reach out on [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## �� Acknowledgements

Grateful to these projects:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ Roadmap

- [ ] GRPC transport support
- [x] Sentry error tracking
- [x] Ag-UI integration
- [x] Retry mechanism
- [ ] Increase test coverage to 80% - In progress
- [x] Redis scheduler implementation
- [x] Postgres database for memory storage
- [x] Negotiation support
- [ ] AP2 end-to-end support
- [ ] DSPy integration - In progress
- [ ] MLTS support
- [ ] X402 support with other facilitators

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🎓 Workshops

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Built with 💛 by the team from Amsterdam </strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>From idea to Internet of Agents in 2 minutes.</strong><br/>
  <em>Your agent. Your framework. Universal protocols.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Star us on GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Join Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Read the Docs</a>
</p>
