# Bindu Examples

Welcome to the Bindu examples collection! This directory contains ready-to-run agents that demonstrate various capabilities of the Bindu framework, from simple echo bots to advanced payment-gated advisors.

## Quick Start

Ensure you have the dependencies installed:

```bash
uv sync --dev
```

Run any example using `uv run`:

```bash
uv run examples/<example_name>.py
```

## Available Examples

### 1. Basic Agents
These examples demonstrate the fundamental concepts of Bindu.

| File | Description | Key Features |
|------|-------------|--------------|
| `echo_agent.py` | A minimal agent that repeats what you say. | Basics of `bindufy` |
| `echo_simple_agent.py` | An even simpler version of the echo agent. | Minimal config |
| `summarizer_agent.py` | An agent that summarizes text (requires OpenAI key). | Integration with LLMs |

### 2. Framework Integrations
Bindu works seamlessly with other agent frameworks.

| File | Description | Key Features |
|------|-------------|--------------|
| `agno_example.py` | Integrates an [Agno](https://github.com/agno-agi/agno) agent. | Using 3rd party frameworks |

### 3. Advanced Capabilities
Examples showcasing unique Bindu features like payments and webhooks.

| File | Description | Key Features |
|------|-------------|--------------|
| `premium_advisor.py` | **[NEW]** A "Gatekeeper" agent that requires crypto payment. | **X402 Payments**, Middleware |
| `echo_agent_with_webhooks.py` | Demonstrates asynchronous event notification. | Webhooks, A2A Communication |

## Spotlight: Premium Advisor Agent

The `premium_advisor.py` example demonstrates Bindu's unique **X402** payment protocol. This agent is configured to reject any interaction unless a micropayment is made.

**To run it:**
```bash
uv run examples/premium_advisor.py
```

**What happens:**
1.  **Request**: You send a message to the agent.
2.  **402 Payment Required**: The agent intercepts the request and demands payment (e.g., 0.01 USDC).
3.  **Invoice**: The response contains the blockchain details needed to pay.
4.  **Service**: Once paid (proved via signature), the agent releases the advice.

This powerful feature allows you to monetize your agents natively!

## Testing Your Agents

You can interact with your agents using `curl` or any HTTP client.

**Standard Request:**
```bash
curl -X POST http://localhost:3773/ \
     -H "Content-Type: application/json" \
     -d '{
           "jsonrpc": "2.0",
           "method": "message/send",
           "params": {"message": {"role": "user", "content": "Hello!"}},
           "id": 1
         }'
```
