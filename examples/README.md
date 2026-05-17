# Examples

A working catalog of bindu agents — every one is a single command away from running on your machine, signing its own A2A traffic with a DID, and being reachable on `http://localhost:3773`. Pick an example, open its folder README, follow the four steps in it.

Each folder has its own README with the specific keys, run command, and curl recipe. This page is just the map.

## Prereqs (one-time)

```bash
git clone https://github.com/getbindu/Bindu.git && cd Bindu
uv sync --extra agents
export OPENROUTER_API_KEY=<get one at https://openrouter.ai/keys>
```

`OPENROUTER_API_KEY` is the single key the whole catalog runs on by default — most examples point their LLM client at OpenRouter regardless of framework, so one key unlocks the Agno, LangChain, AG2, and TypeScript agents alike. A few examples need additional service keys (Mem0, ScrapeGraph, Notte, etc.); their READMEs spell that out. One alternative: `beginner/minimax_example.py` uses the MiniMax API instead — set `MINIMAX_API_KEY` (from [platform.minimaxi.com](https://platform.minimaxi.com)) to try that one.

`AUTH__ENABLED=true` is the default. Every request needs an OAuth token from Hydra plus a DID-signed body — see [`docs/AUTH.md`](../docs/AUTH.md). To poke around without that ceremony, set `AUTH__ENABLED=false` in `examples/.env` and use plain curl.

## Python — single agent

The cleanest starting point. Each is one file, one framework, runnable in under a minute.

| Folder | What it is | Notable |
| --- | --- | --- |
| [`beginner/`](beginner/) | Twelve small agents in one folder — echo, agno, ag2, dspy, paywall variants. | Start here. |
| [`summarizer/`](summarizer/) | Text → 2–3 sentence summary. | Agno + OpenRouter. |
| [`weather-research/`](weather-research/) | Weather report for any city. | DuckDuckGo search. |
| [`medical_agent/`](medical_agent/) | Educational medical Q&A with disclaimers baked into the prompt. | DuckDuckGo. |
| [`cybersecurity-newsletter/`](cybersecurity-newsletter/) | Topic → headlines + CVEs + brief. | DuckDuckGo. |
| [`document-analyzer/`](document-analyzer/) | PDF/DOCX → Q&A. | Reads the document from a `file` part. |
| [`pdf_research_agent/`](pdf_research_agent/) | PDF → summary by host path or `file` part. | `pypdf`. |
| [`speech-to-text/`](speech-to-text/) | Audio → transcript. | Gemini 2.0 Flash via OpenRouter. |
| [`ai-data-analysis-agent/`](ai-data-analysis-agent/) | CSV → profile + chart. | pandas + matplotlib + seaborn. |
| [`news-summarizer/`](news-summarizer/) | News headlines + sentiment, **local LLM**. | Ollama, no API key. |
| [`multilingual-collab-agent/`](multilingual-collab-agent/) | English/Hindi/Bengali, persistent memory. | Mem0. |
| [`web-scraping-agent/`](web-scraping-agent/) | URL + prompt → structured JSON. | ScrapeGraph + Mem0. |
| [`notte-browser-agent/`](notte-browser-agent/) | Drives a real headless browser. | Notte SDK. |

## Python — multi-agent

Where you see what bindu was actually built for.

| Folder | What it is | Notable |
| --- | --- | --- |
| [`agent_swarm/`](agent_swarm/) | Planner → Researcher → Summarizer → Critic → Reflection. | 5-stage in-process chain. |
| [`ag2_research_team/`](ag2_research_team/) | researcher / analyst / writer under AutoPattern GroupChat. | AG2 (AutoGen) with LLM-driven speaker selection. |
| [`cerina_bindu/`](cerina_bindu/cbt/) | CBT exercise generator: Drafter → SafetyGuardian → ClinicalCritic, supervised. | Real LangGraph `StateGraph`. |
| [`langgraph_blog_writing_agent/`](langgraph_blog_writing_agent/) | Plan → fan out → reduce, map-reduce style. | LangGraph `Send` for fan-out. |
| [`hermes_agent/`](hermes_agent/) | Nous Research's hermes-agent (web/file/code tools) with tiered safety. | Includes `call.py` — the reference signed-request client. |
| [`gateway_test_fleet/`](gateway_test_fleet/) | Five agents on local ports + a 13-case test matrix for the Gateway. | What `docs/GATEWAY.md` uses. |

## Payments + private surface

| Folder | What it is |
| --- | --- |
| [`premium-advisor/`](premium-advisor/) | x402 paywall: 0.01 USDC on Base Sepolia per query. |
| [`beginner/echo_agent_behind_paywall.py`](beginner/) | Echo agent gated by x402. |
| [`beginner/agno_paywall_example.py`](beginner/) | Agno + paywall. |
| [`private_skills_agent/`](private_skills_agent/) | Public vs `/agent/private.json` with `allowed_dids` gating. |

## TypeScript

Same `bindufy(config, handler)` shape, written in TypeScript via [`@bindu/sdk`](../sdks/typescript/). The SDK launches the Python core in the background; you only see your language.

| Folder | What it is |
| --- | --- |
| [`typescript-openai-agent/`](typescript-openai-agent/) | OpenAI SDK assistant, pointed at OpenRouter. |
| [`typescript-langchain-agent/`](typescript-langchain-agent/) | LangChain.js research agent. |
| [`typescript-langchain-quiz-agent/`](typescript-langchain-quiz-agent/) | LangChain.js quiz generator. |

## Kotlin

| Folder | What it is |
| --- | --- |
| [`kotlin-openai-agent/`](kotlin-openai-agent/) | Kotlin assistant via [`sdks/kotlin/`](../sdks/kotlin/), pointed at OpenRouter. Needs JDK 17 + gradle. |

## Deployment

| Folder | What it is |
| --- | --- |
| [`runtime-boxd-agent/`](runtime-boxd-agent/) | Same vanilla agent code, deploys to a [boxd](https://boxd.sh) microVM via `bindu deploy --runtime=boxd`. |

## Shared bits

| Folder | What it is |
| --- | --- |
| [`skills/`](skills/) | Reusable `skill.yaml` definitions referenced by agents via `config["skills"]`. |

## Sending a message in 30 seconds

Once an agent is running on `:3773` with `AUTH__ENABLED=false`:

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"00000000-0000-0000-0000-000000000004","params":{"message":{"role":"user","parts":[{"kind":"text","text":"hello"}],"kind":"message","messageId":"00000000-0000-0000-0000-000000000001","contextId":"00000000-0000-0000-0000-000000000002","taskId":"00000000-0000-0000-0000-000000000003"},"configuration":{"acceptedOutputModes":["application/json"]}}}'
```

That returns a `Task` object. Poll `tasks/get` with the same `taskId` for the final artifact. With auth on, sign each body with the agent's DID key — `examples/hermes_agent/call.py` is the working reference client.

## Building your own

Start from the smallest possible shape:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return f"You said: {messages[-1]['content']}"

bindufy(
    {
        "author": "you@example.com",
        "name": "my_agent",
        "description": "what my agent does",
        "deployment": {"url": "http://localhost:3773", "expose": True},
        "skills": [],
    },
    handler,
)
```

That's a live agent at `http://localhost:3773` with a DID, an agent card at `/.well-known/agent.json`, A2A, and (by default) auth. Swap in your framework — Agno, LangChain, DSPy, OpenAI SDK directly, your own thing — and you're done.

Beyond this page: [docs.getbindu.com](https://docs.getbindu.com) for the full reference, [`docs/`](../docs/) for the deep dives, [Discord](https://discord.gg/3w5zuYUuwt) when you get stuck.
