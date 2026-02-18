# Bindu Examples

Example agents demonstrating Bindu's capabilities - from simple bots to multi-agent systems with payments.

## Quick Start

### Prerequisites
- Python 3.12+
- uv package manager
- OpenRouter API key

### Setup

```bash
git clone https://github.com/getbindu/bindu.git
cd bindu
uv sync --dev
export OPENROUTER_API_KEY="your-key-here"  # pragma: allowlist secret
```

### Run an Agent

```bash
uv run examples/beginner/echo_simple_agent.py
```

Agents run on ports 3773-3780 with UI at `http://localhost:[port]/docs`

## Examples

### Beginner
- `beginner/echo_simple_agent.py` - Minimal echo bot
- `beginner/beginner_zero_config_agent.py` - Zero-config agent with web search
- `beginner/agno_simple_example.py` - Joke generator
- `beginner/agno_example.py` - Research assistant with DuckDuckGo
- `beginner/faq_agent.py` - Documentation search agent
- `beginner/agno_notion_agent.py` - Notion integration

### Specialized
- `summarizer/` - Text summarization agent
- `weather-research/` - Weather intelligence agent
- `premium-advisor/` - Paid agent with X402 payments (0.01 USDC per query)

### Advanced
- `agent_swarm/` - Multi-agent collaboration system
- `cerina_bindu/cbt/` - CBT therapy protocol generator

### Components
- `skills/` - Reusable agent capabilities

## Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here

# Optional
HYDRA__ADMIN_URL=https://hydra-admin.getbindu.com
HYDRA__PUBLIC_URL=https://hydra.getbindu.com
DATABASE_URL=postgresql+asyncpg://user:pass@host/db  # pragma: allowlist secret
REDIS_URL=rediss://default:pass@host:6379  # pragma: allowlist secret
```

## X402 Payments

The `premium-advisor/` example shows how to monetize agents with X402 payments:

```bash
uv run examples/premium-advisor/premium_advisor.py
```

Users must pay 0.01 USDC before the agent responds.

## Testing

### Web UI
```bash
cd frontend
npm run dev
```

### API
```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{...},"id":"1"}'
```

## Building Your Own

```python
from bindu import Agent

agent = Agent(
    name="My Agent",
    description="What it does",
    model="openai/gpt-4o",
)

agent.instructions = ["Behavior guidelines"]

if __name__ == "__main__":
    agent.serve(port=3773)
```

## Documentation

- [Bindu Docs](https://docs.getbindu.com)
- [API Reference](../openapi.yaml)
- [Payment Guide](../docs/PAYMENT.md)
- [DID Guide](../docs/DID.md)
- [Skills Guide](../docs/SKILLS.md)

## Contributing

1. Create your agent in the appropriate folder
2. Add README with usage instructions
3. Include .env.example
4. Submit pull request

## License

See [LICENSE.md](LICENSE.md)
Temporary test change for PR verification.
