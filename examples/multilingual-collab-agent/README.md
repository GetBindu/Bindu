# Multilingual Collaborative Agent

This example is a Bindu agent that can:

- detect whether a user is writing in English, Hindi, or Bengali
- respond in the same language
- research current topics using DuckDuckGo
- translate between English, Hindi, and Bengali
- help draft collaborative content such as emails, messages, and summaries
- use Mem0 for persistent memory across sessions

The agent is implemented in [main.py](/F:/Bindu/examples/multilingual-collab-agent/main.py) and configured through [agent_config.json](/F:/Bindu/examples/multilingual-collab-agent/agent_config.json).

## Features

- Multilingual responses for English, Hindi, and Bengali
- Identity-aware Bindu agent deployment
- Web research via DuckDuckGo
- Translation workflows for EN/HI/BN
- Collaboration and drafting support
- Persistent memory with Mem0
- OpenRouter-backed LLM configuration

## Project Structure

```text
multilingual-collab-agent/
├── main.py
├── agent_config.json
├── requirements.txt
├── .env.example
└── skills/
    ├── research/
    │   └── skill.yaml
    ├── translate/
    │   └── skill.yaml
    └── collaborate/
        └── skill.yaml
```

## Requirements

- Python 3.10 or newer recommended
- A working virtual environment
- An OpenRouter API key
- A Mem0 API key

Python dependencies are listed in [requirements.txt](/F:/Bindu/examples/multilingual-collab-agent/requirements.txt).

## Environment Variables

Create a `.env` file in the project root using [.env.example](/F:/Bindu/examples/multilingual-collab-agent/.env.example) as a template:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
MEM0_API_KEY=your_mem0_api_key_here
MODEL_NAME=openai/gpt-4o-mini
```

Notes:

- `OPENROUTER_API_KEY` is required for model access
- `MEM0_API_KEY` is required for memory features
- `MODEL_NAME` is optional and defaults to `openai/gpt-4o-mini`

## Setup

From [F:\Bindu\examples\multilingual-collab-agent](/F:/Bindu/examples/multilingual-collab-agent), run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Then edit `.env` and add your real API keys.

## Running The Agent

Start the agent with:

```powershell
python main.py
```

Based on [agent_config.json](/F:/Bindu/examples/multilingual-collab-agent/agent_config.json), the agent is configured to run on:

```text
http://0.0.0.0:3773
```

It also enables:

- `debug_mode: true`
- `agent_trust: low`
- three registered skills under `skills/`

## Skills

### `research`

Defined in [skills/research/skill.yaml](/F:/Bindu/examples/multilingual-collab-agent/skills/research/skill.yaml).

Use this skill for:

- factual lookups
- recent information
- topic summaries
- web-backed research in English, Hindi, or Bengali

Example prompts:

- `What is the Bindu framework?`
- `Latest news about AI agents`

### `translate`

Defined in [skills/translate/skill.yaml](/F:/Bindu/examples/multilingual-collab-agent/skills/translate/skill.yaml).

Use this skill for:

- English to Hindi translation
- English to Bengali translation
- Hindi to Bengali translation
- technical translation with preserved terminology

Example prompts:

- `Translate to Hindi: The Bindu framework enables agent communication`
- `Translate this email to Bengali`

### `collaborate`

Defined in [skills/collaborate/skill.yaml](/F:/Bindu/examples/multilingual-collab-agent/skills/collaborate/skill.yaml).

Use this skill for:

- drafting emails and messages
- writing summaries
- cross-language communication support
- memory-assisted collaborative workflows

Example prompts:

- `Help me write an email to my team about the Bindu integration`
- `Draft a summary of our conversation so far`

## How It Works

At startup, [main.py](/F:/Bindu/examples/multilingual-collab-agent/main.py):

- loads environment variables from `.env`
- reads [agent_config.json](/F:/Bindu/examples/multilingual-collab-agent/agent_config.json)
- builds an Agno `Agent`
- attaches DuckDuckGo search tools
- attempts to attach Mem0 tools
- starts the Bindu agent server with `bindufy(...)`

The agent instance is initialized lazily on first request, so the model and tools are created only when needed.

## Example Use Cases

- Ask a research question in English and receive an English answer
- Ask a Bindu question in Hindi and receive a Hindi answer
- Translate technical agent-related content into Bengali
- Draft multilingual team updates with memory-backed context

## Troubleshooting

### Missing API keys

If you see an error about missing environment variables, make sure `.env` contains:

- `OPENROUTER_API_KEY`
- `MEM0_API_KEY`

### Mem0 unavailable

If Mem0 initialization fails, the agent continues without persistent memory. This fallback is handled in [main.py](/F:/Bindu/examples/multilingual-collab-agent/main.py).

### PowerShell virtual environment activation

Use:

```powershell
.\.venv\Scripts\Activate.ps1
```

If execution policy blocks scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Customization

You can customize the agent by updating:

- [main.py](/F:/Bindu/examples/multilingual-collab-agent/main.py) for model logic, instructions, and tool wiring
- [agent_config.json](/F:/Bindu/examples/multilingual-collab-agent/agent_config.json) for deployment and runtime configuration
- the `skills/*/skill.yaml` files for skill metadata and routing behavior

## License

Add the license that matches your parent project or repository policy.
