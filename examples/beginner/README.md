# Bindu Beginner Examples

A collection of beginner-friendly agents to help you get started with the Bindu framework.
Each example is self-contained and runnable in under 2 minutes.

---

## Prerequisites

- Python 3.12+
- UV package manager
- OpenRouter API key (free tier): https://openrouter.ai

```bash
# Install dependencies
uv sync --dev

# Set up environment
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
```

---

## Examples

### 1. Zero Config Agent — `beginner_zero_config_agent.py`
**The simplest possible starting point.**
Runs a fully functional Bindu agent with zero external dependencies — no Postgres, no Redis, no cloud services. Uses in-memory storage and scheduler.

```bash
python beginner_zero_config_agent.py
```

---

### 2. Echo Agent — `echo_simple_agent.py`
**Hello World for Bindu.**
Returns exactly what you send it. Perfect for testing your setup and understanding the message/send → tasks/get flow.

```bash
python echo_simple_agent.py
```

---

### 3. Agno Agent — `agno_example.py`
**A joke-telling agent using Agno + OpenRouter.**
Demonstrates how to wrap an Agno agent with `bindufy()`. Tells puns, dad jokes, and tech humor on demand.

```bash
python agno_example.py
```

---

### 4. Agno Simple Agent — `agno_simple_example.py`
**Minimal Agno integration.**
The cleanest possible example of an Agno agent bindufied — no tools, no extras. Good template to copy from.

```bash
python agno_simple_example.py
```

---

### 5. AG2 Simple Agent — `ag2_simple_example.py`
**AG2 (formerly AutoGen) integration.**
Shows how to wrap an AG2 agent with Bindu. Demonstrates framework-agnostic bindufying.

```bash
python ag2_simple_example.py
```

---

### 6. FAQ Agent — `faq_agent.py`
**A knowledge base agent.**
Answers frequently asked questions from a structured knowledge base. Good example of a static-knowledge agent pattern.

```bash
python faq_agent.py
```

---

### 7. DSPy Agent — `dspy_agent.py`
**DSPy framework integration.**
Demonstrates how to use DSPy structured prompting with Bindu. Shows the framework-agnostic nature of `bindufy()`.

```bash
python dspy_agent.py
```

---

### 8. Agno Notion Agent — `agno_notion_agent.py`
**An agent that reads from Notion.**
Connects to a Notion workspace and answers questions about its content. Requires a Notion API key.

```bash
python agno_notion_agent.py
```

---

### 9. Echo Agent Behind Paywall — `echo_agent_behind_paywall.py`
**X402 payment integration.**
Same as the echo agent but requires USDC payment before responding. Demonstrates Bindu built-in payment capabilities.

```bash
python echo_agent_behind_paywall.py
```

---

### 10. Agno Paywall Agent — `agno_paywall_example.py`
**Full agent + X402 payments.**
A complete agent with web search capabilities behind an X402 paywall. Shows how to monetize your agent.

```bash
python agno_paywall_example.py
```

---

## How Bindu Works

Every example follows the same pattern:

```python
from bindu.penguin.bindufy import bindufy

# 1. Define your agent (any framework)
agent = YourAgent(...)

# 2. Write a handler
def handler(messages: list[dict]) -> str:
    return agent.run(messages[-1]["content"])

# 3. Configure
config = {
    "author": "your.email@example.com",
    "name": "my_agent",
    "description": "What my agent does",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
}

# 4. Bindufy it — one line makes it a live microservice
bindufy(config, handler)
```

Your agent is now running at `http://localhost:3773` with:
- A unique DID identity
- A discoverable agent card at `/.well-known/agent.json`
- Full A2A protocol support
- Built-in metrics at `/metrics`

---

## Testing Your Agent

Once running, send a message:

**Linux/macOS:**
```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello!"}],
        "kind": "message",
        "messageId": "00000000-0000-0000-0000-000000000001",
        "contextId": "00000000-0000-0000-0000-000000000002",
        "taskId": "00000000-0000-0000-0000-000000000003"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "00000000-0000-0000-0000-000000000004"
  }'
```

**Windows PowerShell:**
```powershell
Invoke-WebRequest -Uri "http://localhost:3773/" `
  -Method POST `
  -ContentType "application/json" `
  -UseBasicParsing `
  -Body '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Hello!"}],"kind":"message","messageId":"00000000-0000-0000-0000-000000000001","contextId":"00000000-0000-0000-0000-000000000002","taskId":"00000000-0000-0000-0000-000000000003"},"configuration":{"acceptedOutputModes":["application/json"]}},"id":"00000000-0000-0000-0000-000000000004"}' | Select-Object -ExpandProperty Content
```

Then poll for the result:

```powershell
Invoke-WebRequest -Uri "http://localhost:3773/" `
  -Method POST `
  -ContentType "application/json" `
  -UseBasicParsing `
  -Body '{"jsonrpc":"2.0","method":"tasks/get","params":{"taskId":"00000000-0000-0000-0000-000000000003"},"id":"00000000-0000-0000-0000-000000000005"}' | Select-Object -ExpandProperty Content
```

---

## Next Steps

Once comfortable with these examples, explore:

- `examples/collaborative-agents/` — multi-agent A2A communication
- `examples/agent_swarm/` — agent swarm patterns
- `examples/ag2_research_team/` — multi-agent research team
- [Bindu Documentation](https://docs.getbindu.com)
- [Discord Community](https://discord.gg/3w5zuYUuwt)
