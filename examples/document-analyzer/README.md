# Document Analyzer Agent

A specialized Bindu agent that ingests uploaded PDF/DOCX documents and answers
user prompts by extracting and reasoning over the document contents.

## What is This?

This is a **document analysis agent** that:

- Accepts PDF and Microsoft Word (DOCX) files sent via the A2A messaging
  protocol
- Extracts plain text from the uploaded documents
- Uses a language model to answer questions or summarise based solely on the
  document text
- Demonstrates file‑handling, MIME‑type dispatch and prompt‑driven workflows
  in Bindu

## Features

- **Multi‑format support**: PDF and DOCX parsing
- **Prompt‑driven analysis**: Users ask questions and the agent responds with
  document‑aware answers
- **Graceful error handling**: Unsupported files and bad bytes are reported but
  don’t crash the agent
- **Multi‑file conversations**: Combine several documents in one request
- **Simple handler API**: `handler(messages)` processes A2A message objects

## Quick Start

### Prerequisites

- Python 3.12+
- OpenRouter API key (or substitute your preferred LLM provider)
- `uv` package manager (used by the project workspace)
- Bindu project dependencies installed (run `uv sync` from repo root)

### 1. Set Environment Variables

Create a `.env` file in `examples/document-analyzer/`:

```bash
cp .env.example .env
# edit .env and add your OpenRouter API key
```

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 2. Install Dependencies

```bash
# from the repository root
uv sync
```

### 3. Start the Agent

```bash
# from the Bindu root directory
cd examples/document-analyzer
uv run python document_analyzer.py
```

The agent will listen on `http://localhost:3773` by default.

### 4. Send a Test Request

Use curl to upload a PDF and prompt the agent:

```bash
curl --location 'http://localhost:3773/' \
  --header 'Content-Type: application/json' \
  --data-raw '{
  "jsonrpc": "2.0",
  "id": "3f3c7c9c-1c84-4c59-a61e-8e8c2c1e0c01",
  "method": "message/send",
  "params": {
    "configuration": {
      "acceptedOutputModes": ["text"]
    },
    "message": {
      "messageId": "c1c6c0f3-2c5a-4d1e-bc5e-b0c2a7b0d001",
      "contextId": "6f1b8e52-7f3d-4c2c-b9f0-9b5a9e8f2c11",
      "taskId": "a2d4c1e3-5f79-4a1d-8c34-1b2c9f3e7d29",
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Analyze the uploaded document and summarize."
        },
        {
          "kind": "file",
          "text": "Uploaded document",
          "file": {
            "name": "paper.pdf",
            "mimeType": "application/pdf",
            "bytes": "<pdf base64>"
          }
        }
      ]
    }
  }
}'
```

### 5. Observe the Response

The agent will return analysis text derived from the document content.

### 6. Query Task Status

You can poll the task's state using the `tasks/get` method. Replace the
`taskId` with the identifier returned by the agent (the example below uses the
same static `taskId` shown in the request above):

```bash
curl --location 'http://localhost:3773/' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "jsonrpc": "2.0",
    "id": "9a1d5bfa-4c52-4a0a-9f02-1e1f54d52c01",
    "method": "tasks/get",
    "params": { "taskId": "a2d4c1e3-5f79-4a1d-8c34-1b2c9f3e7d29" }
  }'
```

The response includes the full task record, including history entries and any
artifacts produced by the agent.



## Architecture

### File Structure

```
examples/document-analyzer/
├── document_analyzer.py        # main agent script
├── skills/
│   └── document-processing/
│       └── skill.yaml          # Bindu skill manifest
├── .env.example                # environment template
└── README.md                   # this file
```

### Agent Configuration (`document_analyzer.py`)

The agent definition looks like:

```python
agent = Agent(
    instructions="""
You are an advanced document analysis assistant.
…
""",
    model = OpenRouter(
        id = "arcee-ai/trinity-large-preview:free",
        api_key = os.getenv("OPENROUTER_API_KEY"),
    ),
)
```

`handler(messages)` loops over A2A messages, collects the last text prompt and
any attached files, uses helper functions to extract text, and finally calls
`agent.run(input=...)` with a combined prompt+document string.

### Model Configuration

- **Provider**: OpenRouter (configurable via environment)
- **Model**: `arcee-ai/trinity-large-preview:free` (example)

Feel free to swap in any other supported model by editing the `OpenRouter`
instantiation.

## Skills Integration

The accompanying skill definition (`skills/document-processing/skill.yaml`) adds
metadata used during negotiation and skill discovery. It declares the agent’s
ability to process documents with `application/pdf` and the DOCX MIME type.

## Example Interaction

**User input** (text part + file part):

```json
{
  "kind": "message",
  "role": "user",
  "parts": [
    {"kind": "text", "text": "What is the methodology?"},
    {
      "kind": "file",
      "text": "Attached document",
      "file": {"bytes": "…", "mimeType": "application/pdf"}
    }
  ],
  …
}
```

**Agent output**: a string response crafted by the LLM that references the
PDF’s text, e.g. “The paper uses a randomized controlled trial design…”

## Development

To modify behaviour:

- edit `instructions` to change the assistant’s persona or output style
- adjust the prompt formatting in `handler()`
- add new MIME types to `extract_document_text()`
- update the skill.yaml tags or input/output types

## Use Cases

- Research paper analysis
- Invoice or contract review
- Multi‑document summarization
- Any scenario where users upload PDFs/DOCX and need natural‑language
  answers

## Dependencies

Managed via the top‑level `pyproject.toml`:

```toml
# picks up core bindu/agno dependencies
```

## Notes

The agent is deliberately minimal; it’s intended as a template for file‑based
agents. You can extend it with streaming, external tool calls, or real file
storage by looking at other examples in the repo.

---

For more information about writing Bindu agents, see the main README and the
`docs/` directory in the repository.
