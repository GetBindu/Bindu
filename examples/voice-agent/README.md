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
```

You can also copy `.env.example` to `.env` and edit values.

## Run

```bash
uv run examples/voice-agent/main.py
```

## Verify

Check agent health and card:

```bash
curl -sS http://localhost:3773/healthz
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
  "ws_url": "ws://localhost:3773/ws/voice/..."
}
```

## Notes

- The frontend voice panel can connect to this server and stream mic audio.
- If provider keys are missing, voice routes still exist but STT/TTS processing will fail.
- Use `BINDU_PORT` or `BINDU_DEPLOYMENT_URL` to run on a different port.
