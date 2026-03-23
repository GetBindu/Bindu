# AG2 Research Team

A multi-agent research pipeline using AG2 (formerly AutoGen) integrated
with Bindu's protocol layer (A2A, DID identity, optional X402 payments).

## Architecture

Three specialists collaborate under GroupChat with LLM-driven speaker
selection, exposed as a single Bindu agent:

```
User (A2A protocol) → Bindu handler → AG2 GroupChat
    ├── researcher — gathers facts and sources
    ├── analyst   — evaluates trends and risks
    └── writer    — produces the final report
```

## Quick Start

```bash
pip install "ag2[openai]>=0.11.0" python-dotenv
export OPENAI_API_KEY=<your-key>
python main.py
```

## AG2 Features Demonstrated

- **AutoPattern** — LLM-driven dynamic speaker selection
- **Multi-agent collaboration** — three agents with distinct roles
- **Stateless per-request** — fresh agents for each call
