# Voice (Pipecat) — Runbook

This document describes how to run and verify Bindu’s real-time voice agent pipeline (Pipecat-based) end-to-end.

## 1) Install dependencies

```bash
uv sync --dev --extra agents --extra voice
```

## 2) Configure environment

Minimum:

```bash
export VOICE__STT_API_KEY="..."   # Deepgram
export VOICE__TTS_API_KEY="..."   # ElevenLabs
```

Recommended:

```bash
export VOICE__ENABLED=true
export VOICE__VAD_ENABLED=true
export VOICE__ALLOW_INTERRUPTIONS=true
export VOICE__SESSION_AUTH_REQUIRED=true
export VOICE__SESSION_TOKEN_TTL=600
```

## 3) Run the example agent

```bash
uv run examples/voice-agent/main.py
```

## 4) Sanity check

```bash
curl -sS http://localhost:3773/health
curl -sS http://localhost:3773/.well-known/agent.json
```

## 5) Start a voice session

```bash
curl -sS -X POST http://localhost:3773/voice/session/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response:
- Always: `session_id`, `context_id`, `ws_url`
- If `VOICE__SESSION_AUTH_REQUIRED=true`: also `session_token`

## 6) WebSocket auth handshake

When session auth is required, the client should send the `session_token` in this order:
1. `Sec-WebSocket-Protocol` (recommended; supported by browsers)
2. `Authorization: Bearer <session_token>` (non-browser clients)
3. First text frame after connect (fallback)

The Svelte frontend uses (1) and only uses (3) if subprotocol negotiation didn’t succeed.

## 7) Turn taking (VAD vs `commit_turn`)

- If `VOICE__VAD_ENABLED=true`: end-of-utterance is detected automatically (recommended).
- If `VOICE__VAD_ENABLED=false`: the backend forwards `{ "type": "commit_turn" }` to the transport so the client can explicitly end a turn.

## 8) What to verify

- **Low latency**: agent audio starts before the full response is finished (requires a streaming handler).
- **VAD endpointing**: stop speaking → agent starts responding.
- **Barge-in**: speak while agent is talking → agent stops and listens again.
- **State frames**: server emits `{ "type": "state", "state": "agent-speaking" | "listening" | "ended" }`.
