# Voice Agent Extension — Implementation Plan

> **Status**: Planning  
> **Date**: 12 March 2026  
> **Goal**: Build a real-time voice agent (Vapi/Dograh alternative) into Bindu  
> **Reference repos**: [dograh-hq/dograh](https://github.com/dograh-hq/dograh) · [pipecat-ai/pipecat-examples](https://github.com/pipecat-ai/pipecat-examples)

---

## 1. Overview

Add real-time voice conversation capability to Bindu agents. A user clicks a microphone button in the UI, speaks naturally, and hears the agent respond — just like Vapi or Dograh, but built natively into Bindu's A2A protocol and extension system.

### Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (SvelteKit Frontend)                                       │
│                                                                     │
│  ┌──────────────┐   PCM audio    ┌──────────────────┐               │
│  │ Microphone   │ ──────────────►│ WebSocket Client │               │
│  │ (AudioWorklet│                │ (voice-client.ts)│               │
│  │  16kHz mono) │ ◄──────────────│                  │               │
│  └──────────────┘   TTS audio    └────────┬─────────┘               │
│                                           │                         │
│  ┌──────────────┐                         │ JSON control msgs       │
│  │ VoiceCall    │◄────────────────────────┤ + binary audio frames   │
│  │ Panel.svelte │  transcripts, state     │                         │
│  └──────────────┘                         │                         │
└───────────────────────────────────────────┼────────────────────────-┘
                                            │ ws://host/ws/voice/{id}
                                            ▼
┌────────────────────────────────────────────────────────────────────┐
│  Bindu Server (Starlette ASGI)                                     │
│                                                                    │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐   │
│  │ Voice       │    │  Pipecat Pipeline                        │   │
│  │ Endpoints   │───►│                                          │   │
│  │             │    │  WebSocket    ┌─────┐   ┌───────┐        │   │
│  │ POST /voice │    │  Transport ──►│ STT │──►│ Agent │        │   │
│  │  /session/  │    │  (input)      │Deep-│   │Bridge │        │   │
│  │   start     │    │               │gram │   │(A2A)  │        │   │
│  │             │    │  WebSocket    └─────┘   └───┬───┘        │   │
│  │ WS /ws/     │    │  Transport ◄──┌─────┐      │             │   │
│  │  voice/{id} │    │  (output)     │ TTS │◄─────┘             │   │
│  └─────────────┘    │               │11Lab│                    │   │
│                     │               └─────┘                    │   │
│  ┌─────────────┐    └──────────────────────────────────────────┘   │
│  │ Session     │                                                   │
│  │ Manager     │──── tracks active sessions, timeouts, cleanup     │
│  └─────────────┘                                                   │
│                                                                    │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │ A2A Task    │◄───│ Agent Handler│◄───│ Storage (task history)│  │
│  │ System      │    │ (existing)   │    │ (existing)           │   │
│  └─────────────┘    └──────────────┘    └──────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transport | **WebSocket** | Simpler than WebRTC, no Daily dependency, sufficient for browser voice |
| Pipeline engine | **Pipecat** | Battle-tested framework; handles VAD, interruptions, turn-taking |
| STT | **Deepgram (nova-3)** | Best latency/accuracy in pipecat ecosystem |
| TTS | **ElevenLabs (turbo v2.5)** | Highest voice quality, low latency |
| Audio format | **PCM 16-bit, 16kHz mono** | Universal speech format for all providers |
| Integration | **Bindu extension** | Follows existing x402 pattern; opt-in, discoverable in agent card |
| Telephony | **Not in v1** | Web-only initially; designed for Twilio addition later |

---

## 2. Affected Files

### Existing Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `voice` optional dependency group |
| `bindu/settings.py` | Add `VoiceSettings` pydantic class + `voice` field on `AppSettings` |
| `bindu/extensions/__init__.py` | Document the new voice extension in module docstring |
| `bindu/server/applications.py` | Conditional voice route registration + session manager init in lifespan |
| `bindu/utils/capabilities.py` | Add `get_voice_extension_from_capabilities()` helper |
| `bindu/penguin/bindufy.py` | Accept `voice` config dict, create `VoiceAgentExtension`, add to capabilities |
| `frontend/src/routes/+page.svelte` | Add `VoiceCallButton` alongside chat input |
| `frontend/src/lib/components/chat/ChatWindow.svelte` | Voice session overlay toggle |

### New Files to Create

**Backend — `bindu/extensions/voice/` (7 files)**

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `VoiceAgentExtension` |
| `voice_agent_extension.py` | Extension class (mirrors `X402AgentExtension` pattern) |
| `service_factory.py` | Creates pipecat STT/TTS service instances from config |
| `pipeline_builder.py` | Assembles pipecat pipeline (transport → STT → bridge → TTS → transport) |
| `session_manager.py` | Manages active voice sessions with timeout cleanup |
| `agent_bridge.py` | Custom pipecat `FrameProcessor` bridging STT text ↔ A2A agent handler ↔ TTS |
| `audio_config.py` | Audio format constants (sample rate, channels, encoding) |

**Backend — Server endpoint (1 file)**

| File | Purpose |
|------|---------|
| `bindu/server/endpoints/voice_endpoints.py` | REST + WebSocket endpoints for voice sessions |

**Frontend (5 files)**

| File | Purpose |
|------|---------|
| `frontend/src/lib/services/voice-client.ts` | WebSocket client, AudioWorklet mic capture, PCM playback queue |
| `frontend/src/lib/stores/voice.ts` | Svelte stores for voice state, transcripts, session management |
| `frontend/src/lib/components/voice/VoiceCallPanel.svelte` | Full voice conversation overlay (waveform, transcript, controls) |
| `frontend/src/lib/components/voice/VoiceCallButton.svelte` | Microphone button that appears when agent supports voice |
| `frontend/src/lib/components/voice/LiveTranscript.svelte` | Real-time scrolling transcript, color-coded by speaker |

**Tests (5 files)**

| File | Purpose |
|------|---------|
| `tests/unit/extensions/voice/test_voice_extension.py` | Extension creation, config validation |
| `tests/unit/extensions/voice/test_session_manager.py` | Session lifecycle, timeout cleanup |
| `tests/unit/extensions/voice/test_service_factory.py` | STT/TTS service instantiation |
| `tests/unit/extensions/voice/test_agent_bridge.py` | Frame processor, A2A message conversion |
| `tests/unit/server/endpoints/test_voice_endpoints.py` | REST + WebSocket endpoint tests |

**Docs & Examples (3 files)**

| File | Purpose |
|------|---------|
| `docs/VOICE.md` | Full documentation (setup, architecture, protocol, frontend guide) |
| `examples/voice-agent/main.py` | Example voice-enabled agent using bindufy |
| `examples/voice-agent/config.yaml` | Example YAML config with voice settings |

---

## 3. Implementation Phases

### Phase 1: Backend Voice Extension & Pipeline

> **Blocks all other phases.** This creates the foundation.

#### Step 1.1 — Dependencies

Add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
voice = [
    "pipecat-ai[deepgram,elevenlabs,silero]~=0.0.105",
    "websockets>=14.0",
]
```

The `silero` extra provides Silero VAD for voice activity detection. All three extras
(deepgram, elevenlabs, silero) are pipecat plugin packages.

#### Step 1.2 — `VoiceSettings` in `bindu/settings.py`

New pydantic settings class registered as `app_settings.voice`:

```python
class VoiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VOICE__",
        extra="allow",
    )

    enabled: bool = False

    # Speech-to-Text
    stt_provider: Literal["deepgram"] = "deepgram"
    stt_api_key: str = ""
    stt_model: str = "nova-3"
    stt_language: str = "en"

    # Text-to-Speech
    tts_provider: Literal["elevenlabs"] = "elevenlabs"
    tts_api_key: str = ""
    tts_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs "Rachel"
    tts_model: str = "eleven_turbo_v2_5"

    # Audio
    sample_rate: int = 16000
    audio_channels: int = 1
    audio_encoding: str = "linear16"  # PCM 16-bit

    # Voice Activity Detection
    vad_enabled: bool = True
    vad_threshold: float = 0.5

    # Security & Authentication
    session_auth_required: bool = True  # Require session authentication
    session_token_ttl: int = 600        # Session token time-to-live (seconds)
    session_auth_provider: str | None = None  # Optional: external auth provider id
    per_agent_voice_access: dict | str | None = None  # Per-agent access control or policy id
    rate_limit_per_user: int = 60       # Max requests per user per minute
    rate_limit_per_ip: int = 120        # Max requests per IP per minute
    secret_store: Literal["env", "vault"] = "env"  # Where API keys are stored
    secret_rotation_policy: str = "manual"  # e.g., "manual", "auto-30d"
    encrypt_api_keys_at_rest: bool = True

    # Privacy & Compliance
    store_transcripts: bool = False  # Default to False, require explicit opt-in
    transcript_retention_days: int = 30
    store_audio: bool = False
    audio_retention_days: int = 7
    require_user_consent: bool = True  # Must have user consent before enabling transcripts
    compliance_guidelines: list[str] = ["gdpr", "ccpa"]
    # Enforcement mechanisms:
    # - Validation checks: when store_transcripts=True, enforce PII redaction on transcript content
    # - Automated retention worker: scheduled job using transcript_retention_days and audio_retention_days
    #   to purge expired data
    # - Audit logging: log all consent grant/revoke events and data access events for compliance

    # Behavior
    allow_interruptions: bool = True
    session_timeout: int = 300          # seconds (5 min)
    max_concurrent_sessions: int = 10
    autoscaling_policy: str | None = None  # Reference to autoscaling/capacity profile
    rationale_note: str = "Defaults chosen for balance of UX, cost, and compliance. Infra may override."

    # Extension metadata
    extension_uri: str = "bindu://voice"
    extension_description: str = "Real-time voice conversation for Bindu agents"
```

#### Step 1.3 — Voice Extension Module (`bindu/extensions/voice/`)

**`voice_agent_extension.py`** — follows the `X402AgentExtension` class pattern:

```python
class VoiceAgentExtension:
    """Voice extension for real-time voice agent conversations."""

    def __init__(
        self,
        stt_provider: str = "deepgram",
        stt_model: str = "nova-3",
        stt_language: str = "en",
        tts_provider: str = "elevenlabs",
        tts_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        tts_model: str = "eleven_turbo_v2_5",
        sample_rate: int = 16000,
        allow_interruptions: bool = True,
        vad_enabled: bool = True,
        description: str | None = None,
    ):
        # Store all config...
        pass

    @cached_property
    def agent_extension(self) -> AgentExtension:
        return AgentExtension(
            uri=app_settings.voice.extension_uri,
            description=self._description or app_settings.voice.extension_description,
            required=False,  # Clients can still use text
            params={
                "stt_provider": self.stt_provider,
                "tts_provider": self.tts_provider,
                "sample_rate": self.sample_rate,
                "allow_interruptions": self.allow_interruptions,
            },
        )
```

**`service_factory.py`** — creates pipecat service instances:

```python
def create_stt_service(config: VoiceAgentExtension) -> DeepgramSTTService:
    """Create Deepgram STT service from extension config."""
    return DeepgramSTTService(
        api_key=app_settings.voice.stt_api_key,
        model=config.stt_model,
        language=config.stt_language,
        sample_rate=config.sample_rate,
    )

def create_tts_service(config: VoiceAgentExtension) -> ElevenLabsTTSService:
    """Create ElevenLabs TTS service from extension config."""
    return ElevenLabsTTSService(
        api_key=app_settings.voice.tts_api_key,
        voice_id=config.tts_voice_id,
        model=config.tts_model,
        sample_rate=config.sample_rate,
    )
```

**`pipeline_builder.py`** — assembles the pipecat pipeline:

```python
async def build_voice_pipeline(
    transport: WebSocketTransport,
    agent_handler: Callable,
    voice_ext: VoiceAgentExtension,
    storage: Storage,
    context_id: str,
) -> Pipeline:
    """Build pipecat voice pipeline.

    Pipeline flow:
        Input audio → VAD → STT → Agent Bridge (A2A) → TTS → Output audio
    """
    stt = create_stt_service(voice_ext)
    tts = create_tts_service(voice_ext)
    bridge = AgentBridgeProcessor(agent_handler, storage, context_id)

    pipeline = Pipeline([
        transport.input(),
        stt,
        bridge,
        tts,
        transport.output(),
    ])

    if voice_ext.vad_enabled:
        # Pipecat's Silero VAD handles voice activity detection
        pass  # VAD is configured on the transport level

    return pipeline
```

**`session_manager.py`** — manages active voice sessions:

```python
@dataclass
class VoiceSession:
    id: str
    context_id: str
    task_id: str | None
    pipeline: Pipeline | None
    start_time: float
    state: Literal["connecting", "active", "ending", "ended"]

class VoiceSessionManager:
    """Manages active voice sessions with lifecycle and cleanup."""

    def __init__(self, max_sessions: int, session_timeout: int):
        self._sessions: dict[str, VoiceSession] = {}
        self._max_sessions = max_sessions
        self._session_timeout = session_timeout
        self._cleanup_task: asyncio.Task | None = None

    async def create_session(self, context_id: str) -> VoiceSession: ...
    async def get_session(self, session_id: str) -> VoiceSession | None: ...
    async def end_session(self, session_id: str) -> None: ...
    async def start_cleanup_loop(self) -> None: ...
    async def stop_cleanup_loop(self) -> None: ...
```

**`agent_bridge.py`** — the core bridge between pipecat frames and Bindu's A2A protocol:

```python
class AgentBridgeProcessor(FrameProcessor):
    """Bridges pipecat STT output to Bindu agent handler, then feeds response to TTS.

    Production-grade flow:
        1. Receives TranscriptionFrame from STT (complete utterance)
        2. Creates A2A-compatible message: { role: "user", parts: [{ kind: "text", text }] }
        3. Invokes the agent's handler function (same path as ManifestWorker) in a cancellable asyncio.Task (self._current_task)
        4. Enforces a short agent timeout (e.g., 10s); if exceeded, sends a "thinking..." prompt to TTS, plus a longer total utterance timeout
        5. Catches and logs handler exceptions and invalid/empty responses, converting them to a safe TTS fallback message
        6. Guards storage writes (self._storage) and TTS sends with try/except and retry/fallback paths
        7. Implements cancellation: task.cancel() and await with short grace, then force-cancel if needed; documents non-cancellable handler behavior
        8. Enforces conversation history limits by truncating self._conversation_history to N recent messages and persists metadata on truncation
        9. Detects streaming responses (async iterator) from self._handler and forwards partial text to TTS incrementally, honoring interruptions and finalization
       10. Adds a simple state machine (idle/listening/processing/speaking/interrupted) to coordinate transitions and error recovery

    Handles interruptions: if user speaks while agent is responding, cancels current TTS and agent task.
    """

    def __init__(self, agent_handler, storage, context_id):
        super().__init__()
        self._handler = agent_handler
        self._storage = storage
        self._context_id = context_id
        self._conversation_history: list[dict] = []
        self._current_task_id: str | None = None
        self._current_task: asyncio.Task | None = None
        self._state: Literal["idle", "listening", "processing", "speaking", "interrupted"] = "idle"

    async def process_frame(self, frame, direction):
        # Handle TranscriptionFrame → invoke agent → emit TextFrame
        # 1. Cancel any running agent task if interrupted
        # 2. Start new agent handler in asyncio.Task, enforce timeout
        # 3. On timeout, send "thinking..." to TTS, continue waiting for agent
        # 4. On exception or invalid response, send fallback TTS message
        # 5. On streaming response, forward partials to TTS incrementally
        # 6. Guard storage and TTS sends with try/except
        # 7. Truncate conversation history if needed
        # 8. Update state machine for transitions and error recovery
        ...
```

**`audio_config.py`** — constants:

```python
# Standard speech processing format
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_ENCODING = "linear16"  # PCM 16-bit signed little-endian
BYTES_PER_SAMPLE = 2
FRAME_DURATION_MS = 20  # 20ms frames = 640 bytes at 16kHz mono
FRAME_SIZE = DEFAULT_SAMPLE_RATE * FRAME_DURATION_MS // 1000 * BYTES_PER_SAMPLE
```

#### Step 1.4 — WebSocket Endpoints (`bindu/server/endpoints/voice_endpoints.py`)

Three REST endpoints + one WebSocket:

```
POST   /voice/session/start             → { session_id, session_token, ws_url (wss://...) }
DELETE /voice/session/{session_id}       → { status: "ended" }
GET    /voice/session/{session_id}/status → { state, duration, ... }
WS     /ws/voice/{session_id}            → bidirectional audio stream (wss:// required)
```

**WebSocket protocol and security:**

- POST /voice/session/start requires Authorization: Bearer <user_token> and returns a short-lived session_token
- ws_url is always wss:// (secure transport)
- Client must present session_token in the WebSocket handshake using one of these methods:
  1. Send session_token in the Sec-WebSocket-Protocol header
  2. Send session_token in a custom header such as Authorization: Bearer <session_token>
  3. Perform an application-level handshake by sending session_token as the first text frame after connection
- Query parameter tokens are NOT allowed for security reasons
- Server validates session_token for session ownership from header/handshake mechanisms only
- Input validation: max binary frame size, max frames/sec, reject malformed JSON text frames
- Error handling: explicit error frames ({"type": "error"}), state frames ({"type": "state"}), and clear messages for malformed audio, STT/TTS failures, and network interruptions
- Endpoints referenced: POST /voice/session/start, DELETE /voice/session/{session_id}, GET /voice/session/{session_id}/status, WS /ws/voice/{session_id}

**Frame types:**
```
Direction    Frame Type    Content
─────────    ──────────    ───────────────────────────────────────
Client→Svr   text          { "type": "start", "config": { "sampleRate": 16000 } }
Client→Svr   binary        Raw PCM 16-bit audio frames (20ms chunks)
Client→Svr   text          { "type": "mute" } / { "type": "unmute" }
Client→Svr   text          { "type": "stop" }
Client→Svr   text          session_token (in handshake)

Svr→Client   text          { "type": "transcript", "role": "user",
                             "text": "...", "is_final": true }
Svr→Client   binary        TTS audio (PCM 16-bit, same sample rate)
Svr→Client   text          { "type": "transcript", "role": "agent",
                             "text": "...", "is_final": true }
Svr→Client   text          { "type": "agent_response", "text": "...",
                             "task_id": "..." }
Svr→Client   text          { "type": "state", "state": "agent-speaking" }
Svr→Client   text          { "type": "error", "message": "..." }
```

#### Step 1.5 — Hook Into `BinduApplication`

In `_register_routes()`, add conditional voice endpoint registration (same pattern as x402):

```python
# Voice endpoints (only if voice extension is detected)
from bindu.utils import get_voice_extension_from_capabilities
voice_ext = get_voice_extension_from_capabilities(manifest)
if voice_ext:
    from .endpoints.voice_endpoints import (
        voice_session_start,
        voice_session_end,
        voice_session_status,
        voice_websocket,
    )
    self._add_route("/voice/session/start", voice_session_start, ["POST"], with_app=True)
    self._add_route("/voice/session/{session_id}", voice_session_end, ["DELETE"], with_app=True)
    self._add_route("/voice/session/{session_id}/status", voice_session_status, ["GET"], with_app=True)
    self._add_websocket_route("/ws/voice/{session_id}", voice_websocket)
```

In lifespan, initialize `VoiceSessionManager`:

```python
if voice_ext:
    self._voice_session_manager = VoiceSessionManager(
        max_sessions=app_settings.voice.max_concurrent_sessions,
        session_timeout=app_settings.voice.session_timeout,
    )
    await self._voice_session_manager.start_cleanup_loop()
```

In `bindufy()`, accept `voice` config dict and create extension:

```python
# Voice extension (optional)
voice_config = validated_config.get("voice")
if voice_config and isinstance(voice_config, dict):
    from bindu.extensions.voice import VoiceAgentExtension
    voice_extension = VoiceAgentExtension(**voice_config)
    capabilities = add_extension_to_capabilities(capabilities, voice_extension)
```

---

### Phase 2: Frontend Voice Client

> **Runs in parallel with Phase 3 after Phase 1 is complete.**

#### Step 2.1 — `voice-client.ts` (WebSocket + Audio)

Core class handling the browser side of the voice connection:

```typescript
export class VoiceClient {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private playbackQueue: Float32Array[] = [];

  // Connect to voice session WebSocket
  async connect(wsUrl: string): Promise<void>;

  // Disconnect and release resources
  async disconnect(): Promise<void>;

  // Microphone control
  mute(): void;
  unmute(): void;

  // Event callbacks
  onTranscript: (text: string, role: 'user' | 'agent', isFinal: boolean) => void;
  onAgentAudio: (pcmData: ArrayBuffer) => void;
  onStateChange: (state: VoiceState) => void;
  onError: (error: Error) => void;
}
```

**Audio capture pipeline:**

```
getUserMedia({
    audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
    }
})
    → MediaStreamSource (captures at browser's native sample rate)
    → AudioWorkletNode (resample nativeRate → 16kHz, stereo→mono, Float32→Int16 PCM, chunk into 20ms/320-sample frames)
    → WebSocket.send(binaryFrame)
```

**Audio playback pipeline:**
```
WebSocket.onmessage(binaryFrame)
  → playbackQueue.push(pcmData)
  → AudioBufferSourceNode (sequential playback)
  → AudioContext.destination (speakers)
```

On interruption (user starts speaking), the playback queue is cleared.

#### Step 2.2 — `voice.ts` Store

```typescript
export const voiceSessionId = writable<string | null>(null);
export const voiceState = writable<VoiceState>('idle');
export const isMuted = writable<boolean>(false);
export const transcripts = writable<Transcript[]>([]);
export const currentUserTranscript = writable<string>('');
export const currentAgentTranscript = writable<string>('');

// Actions
export async function startVoiceSession(contextId?: string): Promise<void>;
export async function endVoiceSession(): Promise<void>;
export function toggleMute(): void;
```

`startVoiceSession()` calls `POST /voice/session/start` to get the session ID and WebSocket URL, then instantiates `VoiceClient` and connects.

#### Step 2.3 — Voice UI Components

**`VoiceCallButton.svelte`** — small microphone icon button:
- Only renders if agent card has `bindu://voice` in `capabilities.extensions[]`
- Placed alongside the existing chat input/send button
- Click → calls `startVoiceSession()`
- Shows pulsing animation while connecting

**`VoiceCallPanel.svelte`** — overlay panel when voice session is active:
- Agent name at the top
- Call duration timer
- Live waveform visualization (reuses existing `AudioWaveform.svelte` component)
- Mute/unmute toggle button
- End call button (red)
- `LiveTranscript` component showing conversation

**`LiveTranscript.svelte`** — scrolling real-time transcript:
- User text: left-aligned, gray bubble
- Agent text: right-aligned, themed color bubble
- Partial (in-progress) text: italic styling
- Auto-scrolls to bottom

#### Step 2.4 — Integration

- `+page.svelte`: Import `VoiceCallButton`, place it next to chat input
- When `$voiceSessionId !== null`, render `VoiceCallPanel` as an overlay
- On session end, convert transcripts into chat `DisplayMessage[]` and append to chat store
- Voice transcripts share the same A2A `context_id` as text chat → seamless continuity

---

### Phase 3: Agent Handler Bridge

> **Runs in parallel with Phase 2 after Phase 1 is complete.**

#### Step 3.1 — `AgentBridgeProcessor` Deep Dive

This is the most critical piece. It makes the agent's existing handler function work as a
real-time voice conversation partner.

```
                    ┌─────────────────────────┐
                    │  AgentBridgeProcessor    │
                    │                          │
 TranscriptionFrame─┤  1. Buffer utterance     │
 (from STT)         │  2. Build A2A message    │
                    │  3. Call agent handler    │
                    │  4. Parse response        │
                    │  5. Store in task history │──► Storage
                    │  6. Emit TextFrame        │
                    │     (for TTS)            │
                    └──────────┬───────────────┘
                               │
                         TextFrame (to TTS)
```

**Conversation history management:**
- First utterance → creates A2A task (state: `working`) via storage
- Subsequent utterances → updates same task with new messages
- Agent responses → stored as task messages (role: `agent`)
- Session end → task state → `completed`
- `context_id` links voice and text conversations for continuity

**Interruption flow:**
1. User speaks while agent audio is playing
2. Pipecat's `InterruptionFrame` triggers
3. Bridge cancels in-flight LLM call (if any)
4. TTS output queue is cleared
5. New user utterance is processed normally

#### Step 3.2 — Voice-Aware A2A Task Lifecycle

```
Session Start
    │
    ▼
Create A2A Task (state: "working")
    │
    ▼
┌───────────────────────────────────┐
│ Loop:                             │
│   User speaks → "user" message    │
│   Agent responds → "agent" message│
│   Both stored in task history     │
│   Both emitted as transcripts     │
└──────────────┬────────────────────┘
               │
               ▼
Session End → Task state: "completed"
              Transcripts in task.history[]
              Queryable via GET /tasks/{task_id}
```

---

### Phase 4: Testing, Examples & Documentation

#### Step 4.1 — Unit Tests


**Unit Tests**
| Test File | Covers |
|-----------|--------|
| `test_voice_extension.py` | Extension instantiation, `agent_extension` property, config validation |
| `test_session_manager.py` | Create/get/end sessions, max sessions limit, timeout cleanup |
| `test_service_factory.py` | STT/TTS service creation with various configs |
| `test_agent_bridge.py` | Frame processing, A2A message creation, history management |
| `test_voice_endpoints.py` | REST endpoints (start/end/status) + WebSocket handshake |

**Integration Tests**
- WebSocket lifecycle with pipecat pipeline (connect, send audio, receive transcript, close)
- STT/TTS integration using test audio files and output format validation
- Agent bridge end-to-end handler integration
- Session manager timeout and cleanup scenarios

**End-to-End (E2E) Tests**
- Full voice-call flows: start → speak → agent response → end
- Interruption and reconnection scenarios
- Concurrent session handling and resource cleanup

**Performance Tests**
- Measure STT, agent, and TTS latency
- Load test for max concurrent sessions
- Long-running memory-leak checks

**Frontend/Browser Tests**
- AudioWorklet pipeline and PCM conversion
- Microphone permission flows and error handling
- Playback queue behavior and UI state
- Cross-browser and mobile compatibility (Chrome, Edge, Firefox, Safari)

#### Step 4.2 — Example Voice Agent

```python
# examples/voice-agent/main.py
from bindu.penguin import bindufy

def voice_handler(messages: list[dict]) -> str:
    """Simple voice agent that echoes back with personality.
    
    Args:
        messages: List of message objects from the A2A protocol.
                  Each dict has keys like 'role' and 'content'.
    
    Returns:
        A string response to be spoken by the TTS engine.
    """
    # Extract text from messages - concatenate all user messages
    user_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
    combined = " ".join(user_texts)
    return f"I heard you say: {combined}. That's interesting!"

config = {
    "author": "demo@getbindu.com",
    "name": "voice-demo",
    "description": "A voice-enabled demo agent",
    "deployment": {"url": "http://localhost:3773", "expose": False},
    "voice": {
        "stt_provider": "deepgram",
        "stt_model": "nova-3",
        "tts_provider": "elevenlabs",
        "tts_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "allow_interruptions": True,
    },
}

manifest = bindufy(config=config, handler=voice_handler)
```

```yaml
# examples/voice-agent/config.yaml
author: demo@getbindu.com
name: voice-demo
description: A voice-enabled demo agent

deployment:
  url: http://localhost:3773
  expose: false

voice:
  stt_provider: deepgram
  stt_model: nova-3
  stt_language: en
  tts_provider: elevenlabs
  tts_voice_id: 21m00Tcm4TlvDq8ikWAM
  tts_model: eleven_turbo_v2_5
  allow_interruptions: true
  vad_enabled: true
```

Required environment variables:
```bash
VOICE__STT_API_KEY=your-deepgram-key
VOICE__TTS_API_KEY=your-elevenlabs-key
```

#### Step 4.3 — Documentation (`docs/VOICE.md`)

Sections:
1. Quick Start
2. Configuration Reference (all `VOICE__*` env vars)
3. Architecture Overview (with the diagram from this plan)
4. WebSocket Protocol Specification
5. Frontend Integration Guide
6. Agent Handler Guide (how the bridge works)
7. Troubleshooting

---

## 4. Dependency Graph

```
Phase 1 (Backend Extension)
    │
    ├──► Phase 2 (Frontend Voice Client) ─────┐
    │                                          │
    └──► Phase 3 (Agent Handler Bridge) ───────┤
                                               │
                                               ▼
                                        Phase 4 (Testing & Docs)
```

Phases 2 and 3 can proceed in parallel once Phase 1 is complete.

---

## 5. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VOICE__ENABLED` | `false` | Enable voice extension globally |
| `VOICE__STT_API_KEY` | — | Deepgram API key |
| `VOICE__STT_MODEL` | `nova-3` | Deepgram model |
| `VOICE__STT_LANGUAGE` | `en` | STT language code |
| `VOICE__TTS_API_KEY` | — | ElevenLabs API key |
| `VOICE__TTS_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | ElevenLabs voice ID |
| `VOICE__TTS_MODEL` | `eleven_turbo_v2_5` | ElevenLabs model |
| `VOICE__SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `VOICE__VAD_ENABLED` | `true` | Enable voice activity detection |
| `VOICE__VAD_THRESHOLD` | `0.5` | VAD sensitivity (0-1) |
| `VOICE__ALLOW_INTERRUPTIONS` | `true` | Allow user to interrupt agent |
| `VOICE__SESSION_TIMEOUT` | `300` | Max session duration (seconds) |
| `VOICE__MAX_CONCURRENT_SESSIONS` | `10` | Max simultaneous voice sessions |

---

## 6. Patterns Reused from Existing Codebase

| Pattern | Source | Applied to |
|---------|--------|------------|
| Extension class | `bindu/extensions/x402/x402_agent_extension.py` | `VoiceAgentExtension` |
| Extension extraction | `bindu/utils/capabilities.py` | `get_voice_extension_from_capabilities()` |
| Conditional route registration | `bindu/server/applications.py` (x402 routes) | Voice endpoints |
| Agent handler invocation | `bindu/server/workers/manifest_worker.py` | `AgentBridgeProcessor` |
| Settings class | `bindu/settings.py` (`X402Settings`) | `VoiceSettings` |
| Config in bindufy | `bindufy()` execution_cost handling | `voice` config dict handling |
| Waveform visualization | `frontend/src/lib/components/voice/AudioWaveform.svelte` | `VoiceCallPanel.svelte` |
| Mic capture | `frontend/src/lib/components/chat/VoiceRecorder.svelte` | `voice-client.ts` |
| Svelte stores | `frontend/src/lib/stores/chat.ts` | `voice.ts` |

---

## 7. Patterns Borrowed from Reference Repos

| Pattern | Source | Applied to |
|---------|--------|------------|
| Pipeline builder | Dograh `api/services/pipecat/pipeline_builder.py` | `pipeline_builder.py` |
| Service factory | Dograh `api/services/pipecat/service_factory.py` | `service_factory.py` |
| Session management | Dograh `api/services/pipecat/in_memory_buffers.py` | `session_manager.py` |
| Transport setup | Dograh `api/services/pipecat/transport_setup.py` | Voice endpoint WebSocket handler |
| WebSocket transport | Pipecat-examples `websocket/server/server.py` | WebSocket endpoint + pipeline |
| Event handlers | Dograh `api/services/pipecat/event_handlers.py` | Transcript/state events |
| Turn context | Dograh `api/services/pipecat/turn_context.py` | Conversation turn management |

---

## 8. Verification Checklist

- [ ] `uv run pytest tests/unit/extensions/voice/ -v` — all voice extension tests green
- [ ] `uv run pre-commit run --all-files` — clean lint/formatting
- [ ] WebSocket connectivity: connect to `/ws/voice/{session_id}`, send audio, receive transcript JSON
- [ ] End-to-end voice call: frontend → click microphone → speak → hear agent → see transcript
- [ ] Task persistence: after session, conversation appears via `GET /tasks/{task_id}` (returns a specific conversation by id)
- [ ] Session cleanup: sessions auto-end after timeout, resources freed
- [ ] Agent card: voice-enabled agent shows `bindu://voice` in `capabilities.extensions`
- [ ] Text-voice continuity: switch from voice to text chat in same context
- [ ] `uv run pytest tests/ -v` — all existing tests pass (voice is opt-in, no regressions)

### Security
- [ ] WebSocket authentication required (session_token)
- [ ] No API key exposure in frontend or logs
- [ ] Rate limiting/flood protection tested
- [ ] Input validation for oversized/malformed frames

### Performance
- [ ] STT, TTS, agent, and roundtrip latency meet targets
- [ ] Memory usage per session within limits
- [ ] Max concurrent sessions load test and behavior

### Browser Compatibility
- [ ] Chrome (desktop/mobile)
- [ ] Edge (desktop/mobile)
- [ ] Firefox (desktop/mobile)
- [ ] Safari (desktop/mobile)
- [ ] Microphone permission handling tested

### Accessibility
- [ ] Keyboard navigation for all controls
- [ ] Screen reader announcements for state changes
- [ ] Visual indicators for voice state and errors

---

## 9. Future Extensions (Out of Scope for v1)

| Feature | Notes |
|---------|-------|
| **Telephony (Twilio/Vonage)** | Add `TelephonyTransport` that bridges SIP/PSTN via Twilio into the same pipecat pipeline |
| **WebRTC transport** | Add Daily-based WebRTC for lower latency, NAT traversal |
| **Multi-language** | Swap STT/TTS models per language; detect language from first utterance |
| **Voice cloning** | Use ElevenLabs voice cloning API to let agents have custom voices |
| **Workflow builder** | Dograh-style drag-and-drop voice workflow (IVR trees, branching logic) |
| **Campaign/outbound** | Batch outbound voice calls with Twilio (Dograh's campaign feature) |
| **LoopTalk testing** | AI personas that test voice agents automatically (Dograh's LoopTalk) |
| **Recording & playback** | Record full sessions, store as artifacts, replay in UI |
| **Provider swapping** | Add Google STT/TTS, Cartesia TTS, Azure, AWS Transcribe as alternatives |
| **Function calling** | Voice-triggered tool/function execution during conversation |
