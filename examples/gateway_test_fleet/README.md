# Gateway Test Fleet

A reproducible multi-agent setup for exercising the Bindu Gateway end-to-end. Five small Python agents on local ports, a helper script to start them all at once, and a 13-case test matrix that covers the interesting edge behaviors.

## If you're new here

**Don't start with this folder — start with [`docs/GATEWAY.md`](../../docs/GATEWAY.md).** That's the guided walkthrough; this fleet is what it uses under the hood. By Chapter 3 of STORY.md you'll have all five agents running via `start_fleet.sh` and a gateway driving them.

## What's in here

```
examples/gateway_test_fleet/
├── start_fleet.sh          # start all five agents in the background
├── stop_fleet.sh           # stop them cleanly
├── run_matrix.sh           # run the 13-case test matrix (or one case by id)
├── matrix.json             # test case definitions (question + agents to offer)
├── logs/                   # (gitignored) per-agent + per-case SSE logs
├── pids/                   # (gitignored) background process ids for stop_fleet
└── README.md               # this file
```

The five agents themselves live up one level in [`examples/`](../) — see `joke_agent.py`, `math_agent.py`, `poet_agent.py`, `research_agent.py`, `faq_agent.py`. Each is ~60 lines of Python that wires `openai/gpt-4o-mini` to a few lines of instructions.

## Ports

| Agent | Port |
|---|---|
| joke_agent | 3773 |
| math_agent | 3775 |
| poet_agent | 3776 |
| research_agent | 3777 |
| faq_agent | 3778 |

Gateway runs on `3774`.

## Start / stop

```bash
./examples/gateway_test_fleet/start_fleet.sh
./examples/gateway_test_fleet/stop_fleet.sh
```

Logs land in `logs/<agent>.log`. If an agent fails to start, tail its log.

## Running the test matrix

```bash
./examples/gateway_test_fleet/run_matrix.sh              # all 13 cases
./examples/gateway_test_fleet/run_matrix.sh Q_MULTIHOP   # one case
```

Each case writes its full SSE stream to `logs/<ID>.sse`. Open one end-to-end — it's unusually readable once you know what each event means.

| ID | What it tests | Expected outcome |
|---|---|---|
| Q1 | Single-agent joke | real joke returned |
| Q2 | Math query to joke agent | agent politely refuses |
| Q3 | Two agents, independent tasks | both called, both respond |
| Q4 | Ambiguous: "make me smile" | planner picks joke or poet |
| Q5 | Nonsense input | planner handles without crashing |
| Q6 | Empty string question | rejected at boundary with HTTP 400 |
| Q7 | Endpoint that doesn't exist | graceful apology |
| Q8 | Wrong bearer token on peer | agent rejects, planner recovers |
| Q9 | Nonexistent skill | agent responds as best it can |
| Q10 | 30s timeout | succeeds well within limit |
| Q11 | 10KB context | no truncation |
| Q12 | 5 agents, only 1 relevant | planner picks correctly |
| **Q_MULTIHOP** | **3 chained agents** | **Tokyo population → 0.5% → poem** |

## What's going wrong

**Every agent returns "User not found"** → `OPENROUTER_API_KEY` is invalid or out of credit.
`curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key` should return 200.

**Agents start but the gateway can't reach them** → check `gateway/.env.local` — you're probably missing `SUPABASE_URL`.

**All matrix cases fail with HTTP 401** → shell lost your `GATEWAY_API_KEY`. Re-source:
`set -a && source gateway/.env.local && set +a`

**`event: error` with "Invalid Responses API request"** → you're on an older gateway commit. `git pull`.

## Further reading

- [`docs/GATEWAY.md`](../../docs/GATEWAY.md) — the end-to-end story this fleet illustrates
- [`gateway/openapi.yaml`](../../gateway/openapi.yaml) — machine-readable API contract for the gateway
- [`gateway/README.md`](../../gateway/README.md) — operator reference (env vars, /health, DID signing reference)
- [`gateway/recipes/`](../../gateway/recipes/) — seed playbooks you can copy-edit as templates
