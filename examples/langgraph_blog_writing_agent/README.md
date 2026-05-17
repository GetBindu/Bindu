# LangGraph Blog Writer

Map-reduce blog writing as a LangGraph `StateGraph`. Plan → fan out per-section drafts → reduce into one cohesive post. Pydantic models for typed sections, OpenRouter via `langchain_openai.ChatOpenAI`.

## Setup

```bash
export OPENROUTER_API_KEY=<get one at https://openrouter.ai/keys>
uv sync --extra agents
```

## Run

```bash
uv run examples/langgraph_blog_writing_agent/main.py
# http://localhost:3773
```

> The entry point is `main.py`, **not** `graph.py`. `graph.py` only defines `build_graph()`; `main.py` calls `bindufy()` and wires up the handler.

## Talk to it

With `AUTH__ENABLED=false`:

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"1","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Write a short blog post about why agents need cryptographic identity."}],"kind":"message","messageId":"m1","contextId":"c1","taskId":"t1"}}}'
```

Then `tasks/get` for the structured `AgentResponse` (plan + sections + final). Multi-section fan-out takes 30–60s.

| File | Role |
| --- | --- |
| `main.py` | bindu wrapper + handler (entry point). |
| `graph.py` | `StateGraph` topology: plan → `Send` per section → reduce. |
| `schemas.py` | Pydantic types for plan, section, `AgentResponse`. |

With auth on, sign each body with the agent's DID key — see [`docs/AUTH.md`](../../docs/AUTH.md).
