# Gateway Test Fleet — Walkthrough

This folder is a small working example. You will run it, send one
request, and read the response. Every concept gets introduced when
you need it, in plain words. No prior AI-agent knowledge needed.

By the end (≈15 minutes), you'll have sent a question that involved
three separate AI programs chained together — and you'll be able to
read the output line by line.

---

## What we're building up to

In one terminal:

```bash
curl -N http://localhost:3774/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me a joke about databases.",
    "agents": [
      {
        "name": "joke",
        "endpoint": "http://localhost:3773",
        "auth": { "type": "none" },
        "skills": [{ "id": "tell_joke", "description": "Tell a joke" }]
      }
    ]
  }'
```

That request, one you'll send in Part 4, produces a joke. The rest
of this document is about what each piece of that curl means, what's
running on port 3774, what's running on port 3773, and how to set
them both up.

Let's build it piece by piece.

---

## Part 1 — Install what you need

One-time setup. Skip to Part 2 if you've done this before.

```bash
# Python side — runs the small AI programs we'll call "agents"
uv sync --dev --extra agents

# TypeScript side — runs the coordinator we'll call the "gateway"
cd gateway && npm install && cd ..
```

You also need:
- **An OpenRouter API key.** Sign up at [openrouter.ai](https://openrouter.ai),
  add a few dollars of credit, copy the key from the API section.
  This is what pays for the AI calls.
- **A Supabase project.** Free tier is fine. We use it to store
  conversation history. Get your URL + service role key from the
  project settings.

---

## Part 2 — Fill in the config file

The **gateway** reads its config from `gateway/.env.local`. Start
from the template:

```bash
cp gateway/.env.example gateway/.env.local
```

Open `gateway/.env.local` in an editor. You'll see placeholders.
Fill them in:

```bash
# Supabase (session store)
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your service role key, starts with "eyJ...">

# One bearer token that callers must send to talk to the gateway.
# Make a strong random one:
#   openssl rand -base64 32 | tr -d '=' | tr '+/' '-_'
# Copy the output into the right-hand side:
GATEWAY_API_KEY=<paste the generated token here>

# The planner AI — we only support OpenRouter today.
OPENROUTER_API_KEY=sk-or-v1-<your key>

GATEWAY_PORT=3774
GATEWAY_HOSTNAME=0.0.0.0
```

That's enough for the gateway to start. We'll add DID-signing config
later in Part 6.

### Aside — what's a "bearer token"?

Think of `GATEWAY_API_KEY` like the password on a movie ticket
booth. Whoever holds this string can ask the gateway to do work on
their behalf. The gateway checks it on every request by direct
comparison. Don't paste this into chat apps or commit it.

### The agents also need the OpenRouter key

Copy it into `examples/.env` (this file exists already):

```bash
# examples/.env
OPENROUTER_API_KEY=sk-or-v1-<same key as above>
```

---

## Part 3 — Start the services

Open **two terminal windows**.

### Window 1 — start the five agents

Each agent is one Python file that runs a small AI program on a
specific HTTP port. One-shot script:

```bash
./examples/gateway_test_fleet/start_fleet.sh
```

Expected output (last few lines):

```
  [joke_agent]      started, pid=64945
  [math_agent]      started, pid=64958
  [poet_agent]      started, pid=64969
  [research_agent]  started, pid=64980
  [faq_agent]       started, pid=64993

Fleet started. Tail logs with:
  tail -f /.../logs/*.log
```

Each agent listens on its own port:
- `joke_agent` → port 3773
- `math_agent` → port 3775
- `poet_agent` → port 3776
- `research_agent` → port 3777
- `faq_agent` → port 3778

They all auto-register with a service called **Hydra** (an OAuth
server we run at getbindu.com) on first startup. Takes about 10
seconds. Leave the terminal running.

### Aside — what's an "agent"?

An agent is a program that listens on an HTTP port and responds to
messages with AI-generated answers. Each of our five agents is a
~60-line Python file. Look at
[joke_agent.py](joke_agent.py) — you'll see a tiny configuration
that wires a language model (`openai/gpt-4o-mini`) to a few lines
of instructions ("tell jokes, refuse other requests"). That's
everything. Narrow scope on purpose so mistakes are visible.

### Window 2 — start the gateway

```bash
cd gateway
npm run dev
```

Expected output:

```
[bindu-gateway] no DID identity configured (set BINDU_GATEWAY_DID_SEED...)
[bindu-gateway] listening on http://0.0.0.0:3774
[bindu-gateway] session mode: stateful
```

The "no DID identity configured" warning is fine for now — we'll
add that in Part 6 when we turn on signed requests.

### Verify everything

From a third terminal:

```bash
# The gateway responds
curl -s http://localhost:3774/health
# → {"ok":true,"name":"@bindu/gateway","session":"stateful","supabase":true}

# All five agents respond
for port in 3773 3775 3776 3777 3778; do
  echo "port $port:"
  curl -s --max-time 2 "http://localhost:$port/.well-known/agent.json" | head -c 80
  echo
done
```

If any port fails, check its log file in
`examples/gateway_test_fleet/logs/<agent>.log`.

---

## Part 4 — Send your first request

Load your gateway token into the shell (so you don't have to
copy-paste it):

```bash
set -a && source gateway/.env.local && set +a
```

Now send the request from the top of this document. Take it in
pieces:

```bash
curl -N http://localhost:3774/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me a joke about databases.",
    "agents": [
      {
        "name": "joke",
        "endpoint": "http://localhost:3773",
        "auth": { "type": "none" },
        "skills": [{ "id": "tell_joke", "description": "Tell a joke" }]
      }
    ]
  }'
```

A few things to notice before you run it:

| Piece | Meaning |
|---|---|
| `curl -N` | "No buffering" — show output as it streams in, don't wait for the whole thing. |
| `Authorization: Bearer ${GATEWAY_API_KEY}` | The password from Part 2. Without this the gateway returns 401. |
| `"question"` | What you're asking. Plain English. |
| `"agents"` | The catalog — who the gateway is allowed to call. You include at least one; here it's just the joke agent. |
| `"name": "joke"` | An operator-chosen label. The gateway uses this to name the tool it exposes internally (`call_joke_tell_joke`). |
| `"endpoint"` | Where the agent lives. Port 3773 — that's our joke_agent. |
| `"auth": { "type": "none" }` | Don't try to sign the call. Works for local dev; Part 6 upgrades this to `did_signed`. |
| `"skills"` | What the agent can do. One "skill" per distinct capability. The gateway decides which to call. |

Now run it. Output arrives as a stream — you'll see lines appear
one at a time over ~5 seconds:

```
event: session
data: {"session_id":"2c6d...","external_session_id":null,"created":true}

event: plan
data: {"plan_id":"c0e5...","session_id":"2c6d..."}

event: task.started
data: {"task_id":"call_NFC...","agent":"joke","skill":"tell_joke","input":{"input":"Tell me a joke about databases"}}

event: task.artifact
data: {"task_id":"call_NFC...","content":"<remote_content agent=\"joke\" verified=\"unknown\">\nWhy did the database administrator break up with the database? Because it had too many relationships!\n</remote_content>"}

event: task.finished
data: {"task_id":"call_NFC...","state":"completed"}

event: text.delta
data: {"session_id":"2c6d...","part_id":"71ea...","delta":"Here"}
event: text.delta
data: {"session_id":"2c6d...","part_id":"71ea...","delta":"'s"}
... (many more deltas) ...

event: final
data: {"session_id":"2c6d...","stop_reason":"stop","usage":{"inputTokens":1130,"outputTokens":52,"totalTokens":1182,"cachedInputTokens":0}}

event: done
data: {}
```

You just made a plan.

### Aside — why the response looks like that

This format is called **SSE** (Server-Sent Events). It's plain HTTP
but the server keeps the connection open and writes events one line
at a time. Your `curl -N` shows them as they arrive.

Every event has two parts: `event:` (a label) and `data:` (a JSON
blob). You can pick which events you care about.

### Line by line

1. **`session`** — the gateway opened a new conversation (or resumed
   an old one). `session_id` is the unique handle for this chat.
2. **`plan`** — the gateway committed to a strategy. Here, just one
   step: call the joke agent.
3. **`task.started`** — about to make a call. `agent: joke` = the
   joke agent on port 3773. `input: {input: "..."}` = what the
   gateway decided to ask it.
4. **`task.artifact`** — the agent replied. The text inside the
   `<remote_content>` tags is the actual answer.
5. **`task.finished`** — that one call is done.
6. **`text.delta`** — the gateway is now writing its own final
   answer, one word-or-two at a time.
7. **`final`** — the complete answer is written. `usage` reports
   how many AI tokens this cost.
8. **`done`** — nothing more coming. Close the connection.

---

## Part 5 — A harder request: three agents, chained

The real reason the gateway exists is to coordinate *multiple*
agents automatically. Let's see it.

```bash
curl -N http://localhost:3774/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "First research the current approximate population of Tokyo. Then compute what exactly 0.5% of that population is. Finally write a 4-line poem celebrating that number of people.",
    "agents": [
      {
        "name": "research", "endpoint": "http://localhost:3777",
        "auth": { "type": "none" },
        "skills": [{ "id": "web_research", "description": "Web search and summarize a factual question" }]
      },
      {
        "name": "math", "endpoint": "http://localhost:3775",
        "auth": { "type": "none" },
        "skills": [{ "id": "solve", "description": "Solve math problems step-by-step" }]
      },
      {
        "name": "poet", "endpoint": "http://localhost:3776",
        "auth": { "type": "none" },
        "skills": [{ "id": "write_poem", "description": "Write a short poem" }]
      }
    ]
  }'
```

This takes ~15 seconds and produces three `task.started` events in
order — research, then math, then poet. Real output from a recent
run:

```
task.started  → research called with "What is the current population of Tokyo?"
task.artifact → "Tokyo's metropolitan area has approximately 36.95 million people..."
task.finished → completed

task.started  → math called with "Compute 0.5% of 36,950,000"
task.artifact → "0.005 × 36,950,000 = 184,750"
task.finished → completed

task.started  → poet called with "Write a 4-line poem about 184,750 people"
task.artifact → "In Tokyo's heart, where dreams align, / 184,750 souls brightly shine, / ..."
task.finished → completed

text.delta    → "Step 1 — Population: 36.95 million..."
text.delta    → "Step 2 — Calculation: 184,750..."
text.delta    → "Step 3 — Poem: In Tokyo's heart..."
final
done
```

**The gateway did all three steps without you having to pick which
agent to call, in what order, with what input.** Each agent's output
became the next agent's input. That's the whole point.

### Aside — what's the "gateway" actually doing?

Behind the scenes, the gateway runs its own AI (Claude Sonnet 4.6
by default) with a special prompt: "you have these tools
available, the user asked this, figure it out." Each of your
agents becomes one tool. The AI decides which to call and what to
pass. Anthropic calls this "tool use"; some people call it an
"agentic loop."

The gateway's AI is called the **planner**. It plans the work;
your agents execute it.

---

## Part 6 — Signed requests (optional for local, required for production)

When you call an agent in `auth.type: "none"` mode, the agent has
no way to verify the request is really from the gateway. For
production that's not safe.

**DID signing** fixes this. A DID is a cryptographic identity the
gateway earns on first boot. Every outbound call gets signed; the
agent verifies the signature against the gateway's registered
public key before responding. If someone on the network intercepts
and tampers with the body, verification fails, call rejected.

To turn it on, add to `gateway/.env.local`:

```bash
# Seed is 32 random bytes, base64 encoded. Generate ONCE and keep
# it secret — it's the gateway's private key.
#   python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
BINDU_GATEWAY_DID_SEED=<generated seed>
BINDU_GATEWAY_AUTHOR=you@example.com
BINDU_GATEWAY_NAME=gateway

# Where to register the gateway's DID + public key
BINDU_GATEWAY_HYDRA_ADMIN_URL=https://hydra-admin.getbindu.com
BINDU_GATEWAY_HYDRA_TOKEN_URL=https://hydra.getbindu.com/oauth2/token
```

Restart `npm run dev`. You should now see:

```
[bindu-gateway] DID identity loaded: did:bindu:you_at_example_com:gateway:<uuid>
[bindu-gateway] registering with Hydra at https://hydra-admin.getbindu.com...
[bindu-gateway] Hydra registration confirmed for did:bindu:...
[bindu-gateway] publishing DID document at /.well-known/did.json
[bindu-gateway] listening on http://0.0.0.0:3774
```

Now you can change `"auth": { "type": "none" }` in any request
from Parts 4-5 to `"auth": { "type": "did_signed" }`. The gateway
automatically:

1. Signs the request body with its private key
2. Gets an OAuth token from Hydra
3. Sends both to the agent

The agent verifies the signature, checks the token is valid, and
only then responds.

---

## Part 7 — Running the full matrix

We have 13 pre-built test cases covering different situations. Run
all of them:

```bash
./examples/gateway_test_fleet/run_matrix.sh
```

Or just one:

```bash
./examples/gateway_test_fleet/run_matrix.sh Q_MULTIHOP
```

The cases:

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

Each run writes its full SSE stream to
`examples/gateway_test_fleet/logs/<ID>.sse`. Open the files to see
exactly what happened.

---

## Part 8 — Stopping everything

Window 1:

```bash
./examples/gateway_test_fleet/stop_fleet.sh
```

Window 2: Ctrl-C the gateway.

---

## When things go wrong

**Every agent returns "User not found."**
→ Your `OPENROUTER_API_KEY` is invalid or out of credit.
Check: `curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key`
(should return 200, not 401.)

**Gateway says "SUPABASE_URL" is missing.**
→ You're running `npm run dev` from somewhere other than the
`gateway/` directory, or you forgot to fill in
`gateway/.env.local`.

**The `event: error` SSE event appears with "Invalid Responses API request".**
→ You're on an older gateway commit. The fix is in
[`gateway/src/provider/index.ts`](../../gateway/src/provider/index.ts):
use `.chat()` not the default callable when creating the OpenAI
client against OpenRouter.

**Planner says "no 'planner' agent configured".**
→ Gateway couldn't find `gateway/agents/planner.md`. Make sure
you're running `npm run dev` from the repo root or `gateway/`
directory.

**All 13 matrix cases fail with HTTP 401.**
→ Shell lost your `GATEWAY_API_KEY` env. Re-source it:
`set -a && source gateway/.env.local && set +a`.

---

## Glossary (reference)

| Term | Short definition |
|---|---|
| **Agent** | A program that listens on an HTTP port and answers AI-generated questions. |
| **Gateway** | The coordinator that listens on port 3774 and calls multiple agents to answer one user question. |
| **Planner** | The AI inside the gateway that decides which agents to call, in what order. |
| **DID** | A long cryptographic identifier unique to each agent and to the gateway. Like a passport — hard to forge. |
| **Hydra** | An OAuth 2.0 server we run at `hydra-admin.getbindu.com`. Hands out bearer tokens the gateway uses to prove its identity. |
| **OpenRouter** | A paid service that proxies to dozens of language models under one API. We use it to avoid maintaining five separate model-provider accounts. |
| **SSE** | Server-Sent Events — the streaming response format. Plain HTTP, one line per event. |
| **/plan** | The gateway's one HTTP endpoint. POST JSON in, get a stream of events back. |
| **Bearer token** | A long random string that proves "I have permission." Attached as `Authorization: Bearer <token>` on every request. Whoever holds it, has access. |
| **Tool** (planner) | In the planner's AI prompt, each agent's skill becomes one tool it can call. Named `call_{agent}_{skill}`. |
| **Artifact** | The content returned by an agent for one task. |
| **Skill** | One specific thing an agent can do. An agent can have several. The catalog in `/plan` lists them. |

---

## What to look at next

- Read a real SSE log end to end: open `logs/Q_MULTIHOP.sse` after
  running the matrix. It's surprisingly readable once you know
  what each event means.
- Open one agent file (say [poet_agent.py](poet_agent.py)) and
  change its instructions. Restart the fleet. Re-run the matrix.
  Watch how the gateway's answer changes. Fastest way to build
  intuition.
- Read the planner's own prompt at
  [`gateway/agents/planner.md`](../../gateway/agents/planner.md).
  That's the instructions the coordinator AI follows.
