# Voice Agent Example

This example runs a voice-enabled Bindu agent with the custom voice extension.

## Prerequisites

- Python 3.12+
- `uv` installed
- Voice dependencies installed:

```bash
uv sync --dev --extra agents --extra voice
```

- API keys in environment:

```bash
export VOICE__STT_API_KEY="your-deepgram-api-key" # pragma: allowlist secret
export VOICE__TTS_API_KEY="your-elevenlabs-api-key" # pragma: allowlist secret
export OPENROUTER_API_KEY="your-openrouter-api-key" # optional, enables full LLM responses
export OPENROUTER_MODEL="openai/gpt-4o-mini" # optional
export OPENROUTER_MEMORY_TURNS="4" # optional, recent turns to keep in prompt
export VOICE_MAX_SENTENCES="2" # optional, hard cap for spoken response length
```

You can also copy `.env.example` to `.env` and edit values.

## Run

```bash
uv run examples/voice-agent/main.py
```

## Verify

Check agent health and card:

```bash
curl -sS http://localhost:3773/health
curl -sS http://localhost:3773/.well-known/agent.json
```

Start a voice session:

```bash
curl -sS -X POST http://localhost:3773/voice/session/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected response:

```json
{
  "session_id": "...",
  "context_id": "...",
  "ws_url": "ws://localhost:3773/ws/voice/...",
  "session_token": "..."
}
```

Note: `session_token` is only included when `VOICE__SESSION_AUTH_REQUIRED=true`.

## Notes

- The frontend voice panel can connect to this server and stream mic audio.
- If provider keys are missing, voice routes still exist but STT/TTS processing will fail.
- If `OPENROUTER_API_KEY` is not set, the example falls back to a local template response mode.
- `OPENROUTER_MEMORY_TURNS` controls lightweight context memory (default: 4 turns).
- `VOICE_MAX_SENTENCES` hard-limits spoken output length (default: 2).
- Use `BINDU_PORT` or `BINDU_DEPLOYMENT_URL` to run on a different port.
- When `VOICE__SESSION_AUTH_REQUIRED=true`, the frontend sends the `session_token` via `Sec-WebSocket-Protocol`.
- If `VOICE__VAD_ENABLED=false`, the backend relies on `{ "type": "commit_turn" }` to end user turns.
- `examples/voice-agent/main.py` uses an async-generator handler to demonstrate token streaming (lower latency to first audio).
