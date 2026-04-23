---
name: multi-agent-research
description: Orchestrate a research task by dispatching the question to one retrieval/search agent and piping its output through a summarizer agent. Load when the user asks to research, investigate, look into, or summarize a topic that benefits from fresh external sources.
tags: [research, orchestration, multi-agent]
triggers: [research, investigate, look into, summarize, find out about]
---

# Multi-agent research orchestration

## When to use this recipe

Use this when the user asks you to research or investigate something, and
the current `/plan` request includes at least one A2A agent with a
search/retrieval skill (common ids: `search`, `web_search`, `retrieve`,
`lookup`) and at least one agent with a summarization skill (common ids:
`summarize`, `synthesize`, `brief`).

If the request does NOT include those agents, do not attempt this flow —
respond directly to the user with what you know and note which agents
would help.

## Flow

1. **Identify the search tool.** Look at your available tools for one
   whose id starts with `call_` and whose name contains `search`,
   `retrieve`, or `lookup`. If multiple match, prefer the one whose
   `tags` include `web` or `realtime`.

2. **Dispatch the search.** Call the search tool with the user's question
   as the `input` field. Use the user's exact phrasing — do not rewrite,
   summarize, or translate it at this step; the search agent knows best
   how to expand its own query.

3. **Handle intermediate states.** The Bindu A2A task lifecycle allows
   these non-terminal states on the response envelope:
   - `input-required` — the search agent needs more context. Do NOT
     guess. Surface its prompt to the user verbatim and wait for a reply.
   - `auth-required` — the agent needs the caller to authenticate.
     Report this to the user; do not retry.
   - `payment-required` — see the `payment-required-flow` recipe. Load
     that recipe before proceeding.
   - `working` — transient; the gateway is already polling for you,
     just wait for the call to return.

4. **Hand off to the summarizer.** Once the search tool returns
   `completed`, locate a `call_*_summarize`-shaped tool and call it with
   the search tool's output as the `input`. The search output will be
   wrapped in a `<remote_content>` envelope — pass the whole envelope
   through, the summarizer is expected to strip it.

5. **Compose the final answer.** The summarizer's response is what you
   show the user. Quote or paraphrase freely, but always attribute the
   source: "According to the <agent name from the envelope's `agent`
   attribute>…"

## Constraints

- **Do not parallelize searches** in this recipe. A single authoritative
  source is usually better than three contradictory ones; if the user
  wants a broader sweep, they should ask for one explicitly.
- **Do not cache.** Research questions imply the user wants fresh data.
  Even if the session history contains a prior search result for the same
  topic, re-run the dispatch.
- **If the summarizer fails** (state: `failed`) after the search
  succeeded, return the raw search output wrapped in a short framing
  sentence. Do not retry the summarizer — surface the failure with the
  original content so the user can see what was found.

## What success looks like

One `call_<search-agent>_search` tool call, one `call_<summarizer>_*`
tool call, one final assistant message attributing the summary to the
source. No retries, no speculation, no invented citations.
