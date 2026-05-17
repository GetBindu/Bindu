# Weather Research

Ask it for the weather in any city. Agno + OpenRouter (`openai/gpt-oss-120b`) + DuckDuckGo search. The agent synthesises the search hits into one report — current conditions, temperature, short forecast — instead of dumping raw results.

## Setup

```bash
export OPENROUTER_API_KEY=<get one at https://openrouter.ai/keys>
uv sync --extra agents
```

## Run

```bash
uv run examples/weather-research/weather_research_agent.py
# http://localhost:3773
```

## Talk to it

With `AUTH__ENABLED=false`:

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"1","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Weather in Tokyo right now?"}],"kind":"message","messageId":"m1","contextId":"c1","taskId":"t1"}}}'
```

Then `tasks/get` with the same `taskId`. With auth on, sign each body with the agent's DID key — see [`docs/AUTH.md`](../../docs/AUTH.md).
