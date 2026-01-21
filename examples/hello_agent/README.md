# Hello Bindu Agent

This example shows how to run a minimal local Bindu agent with:

- Health endpoint
- Agent manifest
- Built-in chat UI
- In-memory storage & scheduler

## Run locally

```bash
python -m uvicorn dev_agent:app --reload
