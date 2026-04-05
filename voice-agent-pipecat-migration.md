# Pipecat Real-Time Voice Migration Plan

## Objective
Migrate the existing voice agent implementation in Bindu from a manual, HTTP-chunked request-response model to a true real-time streaming pipeline using **Pipecat**. This will resolve the current issues with high Time-to-First-Byte (TTFB), lack of Voice Activity Detection (VAD) endpointing, and missing barge-in (interruption) support, making it perform similarly to Vapi.

## Background & Motivation
Currently, `bindu/server/endpoints/voice_endpoints.py` manually buffers 1-second chunks of audio and sends them to Deepgram's prerecorded REST API. It then waits for the full LLM response and sends the entire text to ElevenLabs' REST API for TTS synthesis. This results in significant latency, rigid turn-taking, and no ability for the user to interrupt the agent.

By adopting Pipecat (as originally outlined in `docs/VOICE_AGENT_PLAN.md`), we can leverage WebSockets for continuous streaming Speech-to-Text (STT), token-by-token Text-to-Speech (TTS) generation, local Silero VAD for natural endpointing, and native interruption handling.

## Scope & Impact
This migration primarily affects the backend voice extension implementation (`bindu/extensions/voice/` and `bindu/server/endpoints/voice_endpoints.py`).

WebSocket contract impact:
- Potentially breaking if the backend starts enforcing stricter framing or changes audio/control message ordering.
- Plan: ship a feature-flagged **dual-mode** backend that accepts both the legacy WebSocket frames and the Pipecat transport path during a migration window.

## Proposed Solution: Implementation Steps

### Phase 1: Environment & Dependencies
1. **Update `pyproject.toml`:** Ensure `pipecat-ai[deepgram,elevenlabs,silero]` is added to the dependencies.
2. **Verify Settings & Credentials:**
   - Ensure `VoiceSettings` in `bindu/settings.py` includes provider credentials (`VOICE__STT_API_KEY`, `VOICE__TTS_API_KEY`) and streaming-friendly knobs (timeouts, retries, VAD threshold, interruptions).
   - Document/implement token lifecycle if using short-lived credentials:
     - `token_refresh_endpoint` (where a service token can be renewed)
     - `token_expiry` tracking + refresh-before-expiry behavior
   - WebSocket auth: specify how session tokens are passed (e.g., `Sec-WebSocket-Protocol`) and validated server-side.

### Phase 2: Implement Pipecat Pipeline Components
Create the foundational Pipecat modules in `bindu/extensions/voice/` (as per `docs/VOICE_AGENT_PLAN.md`):
1. **`service_factory.py`:** Implement functions to instantiate `DeepgramSTTService` and `ElevenLabsTTSService` using credentials from settings.
2. **`agent_bridge.py`:** Create `AgentBridgeProcessor` (inheriting from Pipecat's `FrameProcessor`).
   - Listen for `TranscriptionFrame`.
   - Forward the text to the Bindu Agent Handler (LLM).
   - Stream the LLM response back as `TextFrame`s to feed the TTS engine.
   - Handle `InterruptionFrame` by cancelling the ongoing LLM task and clearing the TTS buffer.
3. **`pipeline_builder.py`:** Implement `build_voice_pipeline` to string together:
   `WebSocketTransport (input) -> Silero VAD -> Deepgram STT -> AgentBridgeProcessor -> ElevenLabs TTS -> WebSocketTransport (output)`

### Phase 3: Rewrite `voice_endpoints.py`
Replace the manual buffering logic in `voice_websocket` with a Pipecat pipeline execution:
1. Initialize a `FastAPIWebsocketTransport` (or Pipecat's equivalent ASGI WebSocket transport).
2. Call `build_voice_pipeline()` with the configured transport and services.
3. Create a `PipelineRunner` or `PipelineTask` and execute it (`await task.run()`).
4. Ensure custom control messages (`start`, `mute`, `stop`) from the frontend are routed into Pipecat as custom frames or handled by the transport.

### Phase 4: Integration & Fallbacks
1. Ensure the A2A (Agent-to-Agent) task history is correctly updated via `AgentBridgeProcessor`.
2. Implement resilience patterns for streaming provider disconnects (Deepgram/ElevenLabs drops):
   - Retry with exponential backoff + jitter (configurable `maxRetries`, `maxElapsedTime`).
   - Partial-failure behavior:
     - If STT fails: keep the session alive, stop microphone streaming, notify client, allow retry/reconnect.
     - If TTS fails: continue STT + agent responses, but notify client audio is unavailable and optionally fall back to text-only transcript streaming.
   - Circuit breaker per external service (thresholds + cooldown) to avoid thrashing under repeated failures.
   - Fallback to the legacy HTTP-chunked flow if streaming repeatedly fails (feature-flag controlled).
   - Ensure disconnect handlers perform graceful pipeline close/restart and free resources deterministically.

## Verification & Testing
- Monitoring/observability requirements:
  - Latency metrics: p50/p95/p99 TTFB, end-to-end utterance latency.
  - Error rates: STT/TTS error counts, disconnects, retries, circuit breaker state transitions.
  - Pipeline health: active sessions, restart rates, cancellation/interruption counts.
  - Audio quality (where feasible): dropped frames, input RMS/clip indicators.

- Functional verification:
  - Latency: audio playback starts before full LLM completion.
  - VAD endpointing: natural pauses trigger agent response.
  - Barge-in: user speech interrupts agent audio and cancels in-flight handler work.

- Load testing:
  - Validate concurrent session capacity under realistic CPU/memory/network usage.
  - Verify behavior during spikes (backpressure, rate limits, circuit breakers).

- Integration tests:
  - Staging runs against real Deepgram/ElevenLabs.
  - Extend `tests/unit/extensions/voice/` to cover failure/restart scenarios and metric emission.

## Rollback Strategy
If the Pipecat migration introduces instability, the previous HTTP-based `_transcribe_pcm_buffer` and `_synthesize_tts_audio` logic can be restored via Git reversion, as the changes are isolated to the voice endpoints and extension modules.

## Rollout Plan (Phased)
1. Feature flag: `VOICE__PIPELINE_MODE=legacy|pipecat|dual` (or equivalent).
2. Canary deployment:
   - Start with a small percentage of sessions on Pipecat.
   - Define rollback criteria (error rate, latency regressions, crash loops).
3. Migration window:
   - Support concurrent transports (legacy + Pipecat) for a fixed window.
   - Drain existing legacy WebSocket sessions before cutover.
4. Cutover:
   - Flip default to Pipecat once SLOs are met.
