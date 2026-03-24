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
uv sync --dev --extra agents
export OPENROUTER_API_KEY="your-key-here"  # pragma: allowlist secret
```

### Run an Agent

```bash
uv run examples/beginner/echo_simple_agent.py
```

Agents run on ports 3773-3780 with UI at `http://localhost:[port]/docs`

You can override the port for any example without editing code:

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

For full URL override, use `BINDU_DEPLOYMENT_URL` (e.g. `http://127.0.0.1:5001`).

## Examples

### Beginner
- `beginner/echo_simple_agent.py` - Minimal echo bot
- `beginner/beginner_zero_config_agent.py` - Zero-config agent with web search
- `beginner/agno_simple_example.py` - Joke generator
- `beginner/agno_example.py` - Research assistant with DuckDuckGo
- `beginner/faq_agent.py` - Documentation search agent
- `beginner/agno_notion_agent.py` - Notion integration
- `beginner/ag2_simple_example.py` - AG2 (AutoGen) simple agent
- `beginner/dspy_agent.py` - DSPy framework integration
- `beginner/agno_paywall_example.py` - Paywall-protected agent
- `beginner/echo_agent_behind_paywall.py` - Echo agent with payment requirement

### Specialized
- `summarizer/` - Text summarization agent
- `weather-research/` - Weather intelligence agent
- `web-scraping-agent/` - AI web scraping agent with ScrapeGraph + Mem0 memory
- `premium-advisor/` - Paid agent with X402 payments (0.01 USDC per query)
- `news-summarizer/` - Real-time news search and summarization using local Ollama
- `document-analyzer/` - PDF/DOCX document analysis and Q&A agent
- `speech-to-text/` - Audio transcription using Gemini 2.0 Flash (MP3, WAV, OGG, M4A)
- `ai-data-analysis-agent/` - Autonomous data analyst with CSV profiling and visualization
- `cybersecurity-newsletter/` - Security news aggregator with CVE tracking

### TypeScript (Language-Agnostic via gRPC)
- `typescript-openai-agent/` - OpenAI SDK agent bindufied with TypeScript SDK
- `typescript-langchain-agent/` - LangChain.js agent bindufied with TypeScript SDK

> TypeScript agents use `@bindu/sdk` which automatically launches the Bindu Python core in the background. Same A2A protocol, same DID, same everything — just a different language. See the [gRPC documentation](../docs/GRPC_LANGUAGE_AGNOSTIC.md) for details.

### Advanced
- `agent_swarm/` - Multi-agent collaboration system
- `cerina_bindu/cbt/` - CBT therapy protocol generator
- `ag2_research_team/` - Multi-agent research pipeline using AG2 (AutoGen)
- `langgraph_blog_writing_agent/` - Map-Reduce blog writing with LangGraph

### Components
- `skills/` - Reusable agent capabilities

## Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here

# Optional
PORT=4000
BINDU_PORT=4000
BINDU_DEPLOYMENT_URL=http://localhost:4000
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
curl -X POST ${BINDU_DEPLOYMENT_URL:-http://localhost:${BINDU_PORT:-3773}}/ \
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
- [gRPC Language-Agnostic Guide](../docs/GRPC_LANGUAGE_AGNOSTIC.md)
- [TypeScript SDK](../sdks/typescript/README.md)
- [Payment Guide](../docs/PAYMENT.md)
- [DID Guide](../docs/DID.md)
- [Skills Guide](../docs/SKILLS.md)

## Contributing

1. Create your agent in the appropriate folder
2. Add README with usage instructions
3. Include .env.example
4. Submit pull request

## License

See [LICENSE.md](../LICENSE.md)
