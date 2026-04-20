<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>The identity, communication & payments layer for AI agents</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.de.md">🇩🇪 Deutsch</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.fr.md">🇫🇷 Français</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Nederlands</a> •
  <a href="README.ta.md">🇮🇳 தமிழ்</a>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img src="https://hits.sh/github.com/Saptha-me/Bindu.svg" alt="Hits"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
  <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
  <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
  <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
</p>

<br/>

<p align="center">
  <img src="assets/sunflower-mountains.jpeg" alt="Bindu — The Internet of Agents" width="720" />
</p>

<p align="center">
  <em>"Like sunflowers turning toward the light, agents collaborate in swarms - each one independent, yet together they create something greater."</em>
</p>

<br/>

<div align="center">
  <h3>Onboard your agent in one line</h3>
</div>

<div align="center">
  <pre><code>curl -fsSL https://getbindu.com/install-bindu.sh | bash</code></pre>
</div>

---

**Bindu** (read: _binduu_) turns any AI agent into a production microservice. Build your agent in any framework — Agno, LangChain, OpenAI SDK, even plain TypeScript — call `bindufy()`, and get a service with DID identity, A2A protocol, OAuth2 auth, and crypto payments. No infrastructure code. No rewriting.

Works with Python, TypeScript, and Kotlin. Built on open protocols: **A2A**, **AP2**, and **X402**.

<p align="center">
  <strong>🌟 <a href="https://getbindu.com">Register your agent</a> • 🌻 <a href="https://docs.getbindu.com">Documentation</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord Community</a></strong>
</p>


---

<br/>

## 🎥 Watch Bindu in Action

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

<br/>

## 📋 Prerequisites

Before installing Bindu, ensure you have:

- **Python 3.12 or higher** - [Download here](https://www.python.org/downloads/)
- **UV package manager** - [Installation guide](https://github.com/astral-sh/uv)
- **API Key Required**: Set `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `MINIMAX_API_KEY` in your environment variables. Free OpenRouter models are available for testing. [MiniMax AI](https://platform.minimaxi.com) offers M2.7 with 1M context window.


### Verify Your Setup

```bash
# Check Python version
uv run python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 Installation
<details>
<summary><b>Users note (Git & GitHub Desktop)</b></summary>

On some Windows systems, git may not be recognized in Command Prompt even after installation due to PATH configuration issues.

If you face this issue, you can use *GitHub Desktop* as an alternative:

1. Install GitHub Desktop from https://desktop.github.com/
2. Sign in with your GitHub account
3. Clone the repository using the repository URL:
   https://github.com/getbindu/Bindu.git

GitHub Desktop allows you to clone, manage branches, commit changes, and open pull requests without using the command line.

</details>

```bash
# Install Bindu
uv add bindu

# For development (if contributing to Bindu)
# Create and activate virtual environment
uv venv --python 3.12.9
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

uv sync --dev
```

<details>
<summary><b>Common Installation Issues</b> (click to expand)</summary>

<br/>

| Issue | Solution |
|-------|----------|
| `uv: command not found` | Restart your terminal after installing UV. On Windows, use PowerShell |
| `Python version not supported` | Install Python 3.12+ from [python.org](https://www.python.org/downloads/) |
| Virtual environment not activating (Windows) | Use PowerShell and run `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Download [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activate venv and run `uv sync --dev` |

</details>

---

<br/>

## 🚀 Quick Start

### Option 1: Manual Setup

Create your agent script `my_agent.py`:

```python
import os

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy it
bindufy(config, handler)

# Use tunnel to expose your agent to the internet
# bindufy(config, handler, launch=True)
```

![Sample Agent](assets/agno-simple.png)

Your agent is now live at the URL configured in `deployment.url`.

Set a custom port without code changes:

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

Existing examples that use `http://localhost:3773` are automatically overridden when `BINDU_PORT` is set.

### Option 2: TypeScript Agent

Same pattern, different language. Create `index.ts`:

```typescript
import { bindufy } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI();

bindufy({
  author: "your.email@example.com",
  name: "research_agent",
  description: "A research assistant agent",
  deployment: { url: "http://localhost:3773", expose: true },
  skills: ["skills/question-answering"],
}, async (messages) => {
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: messages.map(m => ({
      role: m.role as "user" | "assistant" | "system",
      content: m.content,
    })),
  });
  return response.choices[0].message.content || "";
});
```

Run it:

```bash
npm install @bindu/sdk openai
npx tsx index.ts
```

The SDK launches the Bindu core automatically in the background. Your agent is live at `http://localhost:3773` — same A2A protocol, same DID, same everything.

> See [examples/typescript-openai-agent/](examples/typescript-openai-agent/) for the full working example with setup instructions.

### Option 3: Zero-Config Local Agent

Try Bindu without setting up Postgres, Redis, or any cloud services. Runs entirely locally using in-memory storage and scheduler.

```bash
python examples/beginner_zero_config_agent.py
```

### Option 4: Minimal Echo Agent (Testing)

<details>
<summary><b>View minimal example</b> (click to expand)</summary>

Smallest possible working agent:

```python
import os

from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}

bindufy(config, handler)

# Use tunnel to expose your agent to the internet
# bindufy(config, handler, launch=True)
```

**Run the agent:**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Test the agent with curl</b> (click to expand)</summary>

<br/>

Input:
```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--data '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Quote"
                }
            ],
            "kind": "message",
            "messageId": "550e8400-e29b-41d4-a716-446655440038",
            "contextId": "550e8400-e29b-41d4-a716-446655440038",
            "taskId": "550e8400-e29b-41d4-a716-446655440300"
        },
        "configuration": {
            "acceptedOutputModes": [
                "application/json"
            ]
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
}'
```

Output:
```bash
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440024",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440301",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "submitted",
            "timestamp": "2025-12-16T17:10:32.116980+00:00"
        },
        "history": [
            {
                "message_id": "550e8400-e29b-41d4-a716-446655440038",
                "context_id": "550e8400-e29b-41d4-a716-446655440038",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "kind": "message",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "role": "user"
            }
        ]
    }
}
```

Check the status of the task
```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440301"
    },
    "id": "550e8400-e29b-41d4-a716-446655440025"
}'
```

Output:
```bash
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440025",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440301",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "completed",
            "timestamp": "2025-12-16T17:10:32.122360+00:00"
        },
        "history": [
            {
                "message_id": "550e8400-e29b-41d4-a716-446655440038",
                "context_id": "550e8400-e29b-41d4-a716-446655440038",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "kind": "message",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "role": "user"
            },
            {
                "role": "assistant",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "kind": "message",
                "message_id": "2f2c1a8e-68fa-4bb7-91c2-eac223e6650b",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "context_id": "550e8400-e29b-41d4-a716-446655440038"
            }
        ],
        "artifacts": [
            {
                "artifact_id": "22ac0080-804e-4ff6-b01c-77e6b5aea7e8",
                "name": "result",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote",
                        "metadata": {
                            "did.message.signature": "5opJuKrBDW4woezujm88FzTqRDWAB62qD3wxKz96Bt2izfuzsneo3zY7yqHnV77cq3BDKepdcro2puiGTVAB52qf"  # pragma: allowlist secret
                        }
                    }
                ]
            }
        ]
    }
}
```

</details>

 

---

 

## 🚀 Core Features

| Feature | Description | Documentation |
|---------|-------------|---------------|
| 🔐 **Authentication** | Secure API access with Ory Hydra OAuth2 (optional for development) | [Guide →](docs/AUTHENTICATION.md) |
| 💰 **Payment Integration (X402)** | Accept USDC payments on Base blockchain before executing protected methods | [Guide →](docs/PAYMENT.md) |
| 💾 **PostgreSQL Storage** | Persistent storage for production deployments (optional - InMemoryStorage by default) | [Guide →](docs/STORAGE.md) |
| 📋 **Redis Scheduler** | Distributed task scheduling for multi-worker deployments (optional - InMemoryScheduler by default) | [Guide →](docs/SCHEDULER.md) |
| 🎯 **Skills System** | Reusable capabilities that agents advertise and execute for intelligent task routing | [Guide →](docs/SKILLS.md) |
| 🤝 **Agent Negotiation** | Capability-based agent selection for intelligent orchestration | [Guide →](docs/NEGOTIATION.md) |
| 🌐 **Tunneling** | Expose local agents to the internet for testing (**local development only, not for production**) | [Guide →](docs/TUNNELING.md) |
| 📬 **Push Notifications** | Real-time webhook notifications for task updates - no polling required | [Guide →](docs/NOTIFICATIONS.md) |
| 📊 **Observability & Monitoring** | Track performance and debug issues with OpenTelemetry and Sentry | [Guide →](docs/OBSERVABILITY.md) |
| 🔄 **Retry Mechanism** | Automatic retry with exponential backoff for resilient agents | [Guide →](https://docs.getbindu.com/bindu/learn/retry/overview) |
| 🔑 **Decentralized Identifiers (DIDs)** | Cryptographic identity for verifiable, secure agent interactions and payment integration | [Guide →](docs/DID.md) |
| 🏥 **Health Check & Metrics** | Monitor agent health and performance with built-in endpoints | [Guide →](docs/HEALTH_METRICS.md) |
| 🌍 **Language-Agnostic (gRPC)** | Bindufy agents written in TypeScript, Kotlin, Rust, or any language via gRPC adapter | [Guide →](docs/GRPC_LANGUAGE_AGNOSTIC.md) |

---

<br/>

## 🎨 Chat UI

Bindu includes a beautiful chat interface at `http://localhost:5173`. Navigate to the `frontend` folder and run `npm run dev` to start the server.

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 GetBindu.com

[**GetBindu.com**](https://getbindu.com) is a public registry of Bindu agents — discoverable and accessible to the broader agent ecosystem. Register your agent and make it available to other agents and orchestrators.

---

<br/>

## 🛠️ Supported Agent Frameworks

Bindu is **framework-agnostic** and tested with:

**Python:**
- **AG2** (formerly AutoGen)
- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

**TypeScript:**
- **OpenAI SDK**
- **LangChain.js**

**Kotlin:**
- **OpenAI Kotlin SDK**

Bindu is language-agnostic via gRPC — see [docs/grpc/](docs/grpc/) for how it works and how to add new languages.

**Compatible LLM Providers:**
- **OpenRouter** — Access 100+ models through a single API
- **OpenAI** — GPT-4o, GPT-5, and more
- **[MiniMax AI](https://platform.minimaxi.com)** — M2.7 (1M context), M2.5, M2.5-highspeed (204K context) via OpenAI-compatible API

Want integration with your favorite framework? [Let us know on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Testing

Bindu maintains **70%+ test coverage** (target: 80%+):

```bash
# Unit tests (fast, in pre-commit)
uv run pytest tests/unit/ -v

# E2E gRPC integration tests (real servers, full round-trip)
uv run pytest tests/integration/grpc/ -v -m e2e

# All tests with coverage
uv run pytest -n auto --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

**CI runs automatically on every PR** — unit tests, E2E gRPC tests, and TypeScript SDK build verification. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

<br/>

## 🔧 Troubleshooting

<details>
<summary>Common Issues</summary>

<br/>

| Issue | Solution |
|-------|----------|
| `Python 3.12 not found` | Install Python 3.12+ and set in PATH, or use `pyenv` |
| `bindu: command not found` | Activate virtual environment: `source .venv/bin/activate` |
| `Port 3773 already in use` | Set `BINDU_PORT=4000` or override URL with `BINDU_DEPLOYMENT_URL=http://localhost:4000` |
| Pre-commit fails | Run `pre-commit run --all-files` |
| Tests fail | Install dev dependencies: `uv sync --dev` |
| `Permission denied` (macOS) | Run `xattr -cr .` to clear extended attributes |

**Reset environment:**
```bash
rm -rf .venv
uv venv --python 3.12.9
uv sync --dev
```

**Windows PowerShell:**
```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

</details>

---

<br/>

## ⚠️ Known Issues

Before running Bindu in production you should read
[`bugs/known-issues.md`](./bugs/known-issues.md) — a per-subsystem
catalog of current limitations and sharp edges, with workarounds
for each. Postmortems for already-fixed bugs live alongside it
under [`bugs/core/`](./bugs/core/), [`bugs/gateway/`](./bugs/gateway/),
[`bugs/sdk/`](./bugs/sdk/), and [`bugs/frontend/`](./bugs/frontend/).

### Current high-severity issues

These are the ones most likely to bite you. Each links to a
story-format entry in `known-issues.md` explaining the scenario,
the root cause, and the workaround.

| Subsystem | Slug | What it looks like from outside |
|---|---|---|
| Core | [`x402-middleware-fails-open-on-body-parse`](./bugs/known-issues.md#x402-middleware-fails-open-on-body-parse) | Malformed JSON body bypasses payment check |
| Core | [`x402-no-replay-prevention`](./bugs/known-issues.md#x402-no-replay-prevention) | One payment buys unlimited work until `validBefore` |
| Core | [`x402-no-signature-verification`](./bugs/known-issues.md#x402-no-signature-verification) | EIP-3009 authorization signature is never verified |
| Core | [`x402-balance-check-skipped-on-missing-contract-code`](./bugs/known-issues.md#x402-balance-check-skipped-on-missing-contract-code) | Misconfigured RPC silently skips balance check |
| Gateway | [`context-window-hardcoded`](./bugs/known-issues.md#context-window-hardcoded) | Compaction threshold assumes 200k-token window |
| Gateway | [`poll-budget-unbounded-wall-clock`](./bugs/known-issues.md#poll-budget-unbounded-wall-clock) | `sendAndPoll` can stall 5 minutes per tool call |
| Gateway | [`no-session-concurrency-guard`](./bugs/known-issues.md#no-session-concurrency-guard) | Two `/plan` calls on the same session tangle histories |

### Issue counts by subsystem

| Subsystem | High | Medium | Low | Nit |
|---|---:|---:|---:|---:|
| Gateway | 3 | 11 | 13 | 4 |
| Bindu Core (Python) | 4 | 7 | 2 | 0 |
| SDKs (TypeScript) | — | — | — | — |
| Frontend | — | — | — | — |

**Found a new issue?** Open a GitHub Issue referencing the slug
(e.g. *"Fixes `context-window-hardcoded`"*). **Fixed one?** Remove
its entry from `known-issues.md` and add a dated postmortem under
the matching `bugs/<subsystem>/` folder — see
[`bugs/README.md`](./bugs/README.md) for the template.

---

<br/>

## 🤝 Contributing

We welcome contributions! Join us on [Discord](https://discord.gg/3w5zuYUuwt). Pick the channel that best matches your contribution.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Contributing Guidelines](.github/contributing.md)

---

<br/>

## 📜 License

Bindu is open-source under the [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos—your contributions make Bindu better.

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) for discussions and support
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) if you find it useful!

---

<br/>

## 👥 Active Moderators

Our dedicated moderators help maintain a welcoming and productive community:

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/raahulrahl">
        <img src="https://avatars.githubusercontent.com/u/157174139?v=4" width="100px;" alt="Raahul Dutta"/>
        <br />
        <sub><b>Raahul Dutta</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/Paraschamoli">
        <img src="https://avatars.githubusercontent.com/u/157124537?v=4" width="100px;" alt="Paras Chamoli"/>
        <br />
        <sub><b>Paras Chamoli</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/chandan-1427">
        <img src="https://avatars.githubusercontent.com/u/202320492?v=4" width="100px;" alt="Chandan"/>
        <br />
        <sub><b>Chandan</b></sub>
      </a>
      <br />
    </td>
    </tr>
</table>

> Want to become a moderator? Reach out on [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🙏 Acknowledgements

Grateful to these projects:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [Huggingface chatui](https://github.com/huggingface/chat-ui)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🌌 The Vision

```
a peek into the night sky
}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}
{{            +             +                  +   @          {{
}}   |                *           o     +                .    }}
{{  -O-    o               .               .          +       {{
}}   |                    _,.-----.,_         o    |          }}
{{           +    *    .-'.         .'-.          -O-         {{
}}      *            .'.-'   .---.   `'.'.         |     *    }}
{{ .                /_.-'   /     \   .'-.\.                   {{
}}         ' -=*<  |-._.-  |   @   |   '-._|  >*=-    .     + }}
{{ -- )--           \`-.    \     /    .-'/                   }}
}}       *     +     `.'.    '---'    .'.'    +       o       }}
{{                  .  '-._         _.-'  .                   }}
}}         |               `~~~~~~~`       - --===D       @   }}
{{   o    -O-      *   .                  *        +          {{
}}         |                      +         .            +    }}
{{ jgs          .     @      o                        *       {{
}}       o                          *          o           .  }}
{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
```

_Each symbol is an agent — a spark of intelligence. The tiny dot is Bindu, the origin point in the Internet of Agents._

### NightSky Connection (In Progress)

NightSky enables swarms of agents. Each Bindu is a dot annotating agents with the shared language of A2A, AP2, and X402. Agents can be hosted anywhere — laptops, clouds, or clusters — yet speak the same protocol, trust each other by design, and work together as a single, distributed mind.

---

<br/>

## 🗺️ Roadmap

- [x] gRPC transport + language-agnostic SDKs (TypeScript, Kotlin)
- [ ] Increase test coverage to 80% (in progress)
- [ ] AP2 end-to-end support
- [ ] DSPy integration (in progress)
- [ ] Rust SDK
- [ ] MLTS support
- [ ] X402 support with other facilitators

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## [We will make this agents bidufied and we do need your help.](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)

---

<br/>

## 🎓 Workshops

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-Amsterdam && India/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Built with 💛 by the team from Amsterdam && India </strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>From idea to Internet of Agents in 2 minutes.</strong><br/>
  <em>Your agent. Your framework. Universal protocols.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Star us on GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Join Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Read the Docs</a>
</p>

<br/>

<p align="center">
  <img src="assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>"We believe in the sunflower theory - standing tall together, bringing hope and light to the Internet of Agents."</em>
</p>
