"""Voice session REST + WebSocket endpoints.

Provides:
    POST   /voice/session/start             → Start a new voice session
    DELETE /voice/session/{session_id}       → End a voice session
    GET    /voice/session/{session_id}/status → Get session status
    WS     /ws/voice/{session_id}            → Bidirectional audio stream
"""

from __future__ import annotations

import json
import asyncio
import importlib
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.server.endpoints.utils import handle_endpoint_errors

if TYPE_CHECKING:
    from bindu.server.applications import BinduApplication

logger = get_logger("bindu.server.endpoints.voice")

_BACKGROUND_TASKS: set[asyncio.Task[None]] = set()
_VOICE_RATE_LIMIT_LOCK = asyncio.Lock()
_VOICE_RATE_LIMIT_IP_BUCKET: dict[str, list[float]] = {}
_VOICE_RATE_LIMIT_REDIS_LOCK = asyncio.Lock()
_VOICE_RATE_LIMIT_REDIS_CLIENT: Any | None = None

try:
    import redis.asyncio as _redis_async  # type: ignore[import-not-found]

    _REDIS_AVAILABLE = True
except Exception:  # pragma: no cover
    _redis_async = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False


_RATE_LIMIT_LUA = """
-- Sliding-window rate limit using a sorted set.
-- KEYS[1] = zset key
-- ARGV[1] = now (seconds)
-- ARGV[2] = cutoff (seconds)
-- ARGV[3] = member (unique)
-- ARGV[4] = limit (int)
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, tonumber(ARGV[2]))
redis.call('ZADD', KEYS[1], tonumber(ARGV[1]), ARGV[3])
local count = redis.call('ZCARD', KEYS[1])
redis.call('EXPIRE', KEYS[1], 120)
if count > tonumber(ARGV[4]) then
  return 0
end
return 1
"""


async def _get_rate_limit_redis_client() -> Any | None:
    """Lazy init a Redis client for rate limiting (best-effort)."""
    global _VOICE_RATE_LIMIT_REDIS_CLIENT
    if _VOICE_RATE_LIMIT_REDIS_CLIENT is not None:
        return _VOICE_RATE_LIMIT_REDIS_CLIENT

    if not _REDIS_AVAILABLE:
        return None

    redis_url = app_settings.voice.redis_url
    if not redis_url:
        return None

    async with _VOICE_RATE_LIMIT_REDIS_LOCK:
        if _VOICE_RATE_LIMIT_REDIS_CLIENT is not None:
            return _VOICE_RATE_LIMIT_REDIS_CLIENT
        try:
            _VOICE_RATE_LIMIT_REDIS_CLIENT = _redis_async.from_url(  # type: ignore[union-attr]
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            return _VOICE_RATE_LIMIT_REDIS_CLIENT
        except Exception:
            logger.exception("Failed to initialize Redis rate limiter client")
            _VOICE_RATE_LIMIT_REDIS_CLIENT = None
            return None


async def _rate_limit_allow_ip(
    ip: str,
    *,
    limit_per_minute: int,
    now: float | None = None,
) -> bool:
    """Allow an IP through the sliding-window rate limiter."""
    if limit_per_minute <= 0:
        return True
    t = float(time.time() if now is None else now)
    cutoff = t - 60.0

    if app_settings.voice.rate_limit_backend == "redis":
        client = await _get_rate_limit_redis_client()
        if client is not None:
            key = f"voice:rate_limit:ip:{ip}"
            member = f"{t}:{time.time_ns()}"
            try:
                allowed = await client.eval(
                    _RATE_LIMIT_LUA,
                    1,
                    key,
                    t,
                    cutoff,
                    member,
                    int(limit_per_minute),
                )
                return bool(allowed)
            except Exception:
                logger.exception("Redis rate limiter failed; falling back to memory")

    async with _VOICE_RATE_LIMIT_LOCK:
        window = _VOICE_RATE_LIMIT_IP_BUCKET.get(ip, [])
        window = [ts for ts in window if ts >= cutoff]

        if not window:
            _VOICE_RATE_LIMIT_IP_BUCKET.pop(ip, None)

        if len(window) >= limit_per_minute:
            if window:
                _VOICE_RATE_LIMIT_IP_BUCKET[ip] = window
            return False
        window.append(t)
        _VOICE_RATE_LIMIT_IP_BUCKET[ip] = window
        return True


@dataclass
class _VoiceControlState:
    muted: bool = False
    stopped: bool = False
    suppress_audio_until: float = 0.0


class _FilteredWebSocket:
    """WebSocket wrapper that filters inbound frames.

    Used to keep Pipecat's transport focused on audio frames while this endpoint
    consumes and handles JSON control messages (start/mute/unmute/stop/etc).
    """

    def __init__(self, websocket: WebSocket, queue: asyncio.Queue[dict[str, Any]]):
        self._ws = websocket
        self._queue = queue

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ws, name)

    async def receive(self) -> dict[str, Any]:
        msg = await self._queue.get()
        msg_type = msg.get("type", "unknown")
        data_bytes = msg.get("bytes")
        logger.info(
            f"FilteredWebSocket.receive: type={msg_type}, bytes={len(data_bytes) if data_bytes else 0}"
        )
        return msg

    async def receive_text(self) -> str:
        message = await self.receive()
        if message.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect(code=message.get("code", 1000))
        text = message.get("text")
        if text is None:
            raise RuntimeError("Expected text WebSocket message")
        return text

    async def receive_bytes(self) -> bytes:
        message = await self.receive()
        if message.get("type") == "websocket.disconnect":
            logger.info("FilteredWebSocket.receive_bytes: disconnect received")
            raise WebSocketDisconnect(code=message.get("code", 1000))
        data = message.get("bytes")
        logger.debug(
            f"FilteredWebSocket.receive_bytes: got {len(data) if data else 0} bytes"
        )
        if data is None:
            raise RuntimeError("Expected bytes WebSocket message")
        return data


try:
    from pipecat.serializers.base_serializer import (
        FrameSerializer as _PipecatFrameSerializer,
    )
except Exception:  # pragma: no cover

    class _PipecatFrameSerializer:  # type: ignore[too-many-ancestors]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


class _RawAudioFrameSerializer(_PipecatFrameSerializer):
    """Serializer for raw PCM audio over WebSocket.

    Converts inbound binary frames into Pipecat input audio frames and sends
    outbound audio frames as raw bytes for browser playback.
    """

    def __init__(self, sample_rate: int, num_channels: int):
        super().__init__()
        self._sample_rate = sample_rate
        self._num_channels = num_channels

    async def setup(self, _frame: Any) -> None:
        return

    async def serialize(self, frame: Any) -> str | bytes | None:
        from pipecat.frames.frames import (
            OutputAudioRawFrame,
            OutputTransportMessageFrame,
            OutputTransportMessageUrgentFrame,
        )

        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio

        if isinstance(
            frame, (OutputTransportMessageFrame, OutputTransportMessageUrgentFrame)
        ):
            return json.dumps(frame.message)

        return None

    async def deserialize(self, data: str | bytes) -> Any | None:
        from pipecat.frames.frames import InputAudioRawFrame, InputTransportMessageFrame

        if isinstance(data, (bytes, bytearray)):
            return InputAudioRawFrame(
                audio=bytes(data),
                sample_rate=self._sample_rate,
                num_channels=self._num_channels,
            )

        if isinstance(data, str):
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                return None
            return InputTransportMessageFrame(message=payload)

        return None


async def _send_json(
    websocket: Any,
    payload: dict[str, Any],
    send_lock: asyncio.Lock | None = None,
) -> bool:
    """Send a JSON payload over a WebSocket safely.

    If a lock is provided, it is used to serialize concurrent send_text calls.
    """
    try:
        client_state = getattr(websocket, "client_state", None)
        application_state = getattr(websocket, "application_state", None)
        if (
            client_state == WebSocketState.DISCONNECTED
            or application_state == WebSocketState.DISCONNECTED
        ):
            return False
    except Exception:
        # If state inspection fails, still attempt the send below.
        pass

    data = json.dumps(payload)
    try:
        if send_lock is None:
            await websocket.send_text(data)
            return True
        async with send_lock:
            await websocket.send_text(data)
            return True
    except (WebSocketDisconnect, RuntimeError):
        # RuntimeError is raised by Starlette after a close frame is sent.
        return False


def _trim_overlap_text(previous: str, current: str) -> str:
    """Trim repeated word-overlap between adjacent transcript chunks.

    Returns only the delta portion of ``current`` that does not duplicate
    the suffix of ``previous``.
    """
    prev = (previous or "").strip()
    curr = (current or "").strip()
    if not prev:
        return curr
    if prev == curr:
        return ""

    prev_tokens = prev.split()
    curr_tokens = curr.split()
    max_overlap = min(len(prev_tokens), len(curr_tokens))

    for overlap in range(max_overlap, 0, -1):
        if prev_tokens[-overlap:] == curr_tokens[:overlap]:
            return " ".join(curr_tokens[overlap:]).strip()

    return curr


def _extract_bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1].strip()
        return token or None
    return None


def _extract_ws_session_token(websocket: WebSocket) -> str | None:
    """Extract session token from WS headers (subprotocol or Authorization)."""
    subprotocols = websocket.headers.get("sec-websocket-protocol")
    if subprotocols:
        # Starlette exposes the raw comma-separated list.
        for item in subprotocols.split(","):
            token = item.strip()
            if token:
                return token

    return _extract_bearer_token(websocket.headers.get("authorization"))


def _has_ws_subprotocols(websocket: WebSocket) -> bool:
    return bool(websocket.headers.get("sec-websocket-protocol"))


def _classify_voice_pipeline_error(exc: Exception) -> tuple[str, int]:
    """Map internal pipeline exceptions to a user-facing error + close code."""
    module = type(exc).__module__
    name = type(exc).__name__
    message = str(exc)

    if isinstance(exc, asyncio.TimeoutError) or name == "TimeoutError":
        return ("Voice pipeline timed out", 1011)

    if module.startswith("websockets") or "ConnectionClosed" in name:
        return ("Voice provider connection closed", 1011)

    lowered = message.lower()
    if "deepgram" in lowered and ("disconnect" in lowered or "closed" in lowered):
        return ("Deepgram connection closed", 1011)
    if "elevenlabs" in lowered and ("disconnect" in lowered or "closed" in lowered):
        return ("ElevenLabs connection closed", 1011)

    return ("Voice pipeline error", 1011)


def _voice_preflight_error() -> str | None:
    """Return a user-facing error if voice is not runnable in this process."""
    # Ensure optional dependency group is installed.
    try:
        importlib.import_module("pipecat")
    except Exception:
        return "Voice dependencies are not installed. Install with: pip install 'bindu[voice]'"

    # Ensure provider keys exist (provider-dependent).
    if app_settings.voice.stt_provider == "deepgram" and not app_settings.voice.stt_api_key:
        return "VOICE__STT_API_KEY is required when VOICE__STT_PROVIDER=deepgram"

    tts_provider = app_settings.voice.tts_provider
    if tts_provider == "elevenlabs" and not app_settings.voice.tts_api_key:
        return "VOICE__TTS_API_KEY is required when VOICE__TTS_PROVIDER=elevenlabs"
    if tts_provider == "azure":
        if not app_settings.voice.azure_tts_api_key:
            return "VOICE__AZURE_TTS_API_KEY is required when VOICE__TTS_PROVIDER=azure"
        if not app_settings.voice.azure_tts_region:
            return "VOICE__AZURE_TTS_REGION is required when VOICE__TTS_PROVIDER=azure"
    if tts_provider not in {"elevenlabs", "piper", "azure"}:
        return f"Unsupported VOICE__TTS_PROVIDER={tts_provider!r}"

    return None


async def _send_error_and_close(
    websocket: WebSocket,
    message: str,
    *,
    send_lock: asyncio.Lock,
    close_code: int = 1008,
) -> None:
    try:
        await _send_json(websocket, {"type": "error", "message": message}, send_lock)
    finally:
        try:
            await websocket.close(code=close_code, reason=message)
        except Exception:
            pass


async def _voice_control_reader(
    websocket: WebSocket,
    inbound_queue: asyncio.Queue[dict[str, Any]],
    control: _VoiceControlState,
    *,
    vad_enabled: bool,
    send_lock: asyncio.Lock,
    on_user_text: Any | None = None,
) -> None:
    """Read from the real WebSocket and push only audio frames to the queue."""
    max_binary_frame_bytes = 64 * 1024
    max_frames_per_second = 50
    max_frames_in_flight = 10

    window_started_at = time.monotonic()
    window_count = 0

    while True:
        message: dict[str, Any] = await websocket.receive()
        message_type = message.get("type")

        if message_type == "websocket.disconnect":
            await inbound_queue.put(message)
            return

        if message_type != "websocket.receive":
            await inbound_queue.put(message)
            continue

        text = message.get("text")
        if text is not None:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                await _send_error_and_close(
                    websocket,
                    "Malformed JSON control frame",
                    send_lock=send_lock,
                )
                return

            frame_type = payload.get("type")
            if frame_type == "mute":
                control.muted = True
                await _send_json(
                    websocket, {"type": "state", "state": "muted"}, send_lock
                )
                continue
            if frame_type == "unmute":
                control.muted = False
                await _send_json(
                    websocket, {"type": "state", "state": "listening"}, send_lock
                )
                continue
            if frame_type == "stop":
                control.stopped = True
                await _send_json(
                    websocket, {"type": "state", "state": "ended"}, send_lock
                )
                try:
                    await websocket.close()
                finally:
                    return
            if frame_type == "user_text":
                user_text = payload.get("text")
                if isinstance(user_text, str) and user_text.strip() and on_user_text:
                    try:
                        await on_user_text(user_text.strip())
                    except Exception:
                        logger.exception("Failed to handle user_text control frame")
                continue
            if frame_type in {"start", "commit_turn"}:
                # If VAD is disabled, the transport/STT may rely on explicit turn boundary
                # control frames (e.g. commit_turn). Forward these to the transport.
                if not vad_enabled:
                    await inbound_queue.put(message)
                continue

            # Unknown control frame: ignore to preserve forward-compat.
            continue

        data = message.get("bytes")
        if data is None:
            logger.debug("Voice control reader: no bytes in message, skipping")
            continue

        logger.info(f"Voice control reader: received audio frame, {len(data)} bytes")

        now_monotonic = time.monotonic()
        if control.muted or now_monotonic < float(control.suppress_audio_until):
            continue

        if len(data) > max_binary_frame_bytes:
            await _send_error_and_close(
                websocket,
                f"Audio frame too large (max {max_binary_frame_bytes} bytes)",
                send_lock=send_lock,
            )
            return

        if now_monotonic - window_started_at >= 1.0:
            window_started_at = now_monotonic
            window_count = 0
        window_count += 1
        if window_count > max_frames_per_second:
            await _send_error_and_close(
                websocket,
                f"Too many audio frames per second (max {max_frames_per_second})",
                send_lock=send_lock,
            )
            return

        if inbound_queue.qsize() >= max_frames_in_flight:
            await _send_error_and_close(
                websocket,
                f"Too many audio frames in flight (max {max_frames_in_flight})",
                send_lock=send_lock,
            )
            return

        await inbound_queue.put(message)


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------


@handle_endpoint_errors("start voice session")
async def voice_session_start(app: BinduApplication, request: Request) -> Response:
    """Start a new voice session.

    Request body (optional JSON):
        { "context_id": "<uuid>" }

    Returns:
        { "session_id": "...", "ws_url": "ws://host/ws/voice/{session_id}" }
    """
    session_manager = getattr(app, "_voice_session_manager", None)
    if session_manager is None:
        return JSONResponse(
            {"error": "Voice extension is not enabled"}, status_code=501
        )

    if not app_settings.voice.enabled:
        return JSONResponse({"error": "Voice is disabled"}, status_code=501)

    preflight_error = _voice_preflight_error()
    if preflight_error:
        return JSONResponse({"error": preflight_error}, status_code=503)

    # Per-IP rate limit (best-effort; request.client may be missing in tests/proxies)
    client_host = request.client.host if request.client else None
    if client_host:
        allowed = await _rate_limit_allow_ip(
            client_host,
            limit_per_minute=int(app_settings.voice.rate_limit_per_ip_per_minute),
        )
        if not allowed:
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    # Parse optional context_id from body
    context_id = str(uuid4())
    raw_body = await request.body()
    if raw_body:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail="Malformed JSON payload"
            ) from exc

        if isinstance(body, dict) and "context_id" in body:
            raw_context_id = body["context_id"]
            if not isinstance(raw_context_id, str) or not raw_context_id.strip():
                raise HTTPException(
                    status_code=400,
                    detail="context_id must be a non-empty string",
                )
            context_id = raw_context_id.strip()

    session_token: str | None = None
    session_token_expires_at: float | None = None
    if app_settings.voice.session_auth_required:
        session_token = secrets.token_urlsafe(32)
        session_token_expires_at = time.time() + max(
            1, int(app_settings.voice.session_token_ttl)
        )

    try:
        session = await session_manager.create_session(
            context_id,
            session_token=session_token,
            session_token_expires_at=session_token_expires_at,
        )
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=429)

    # Build WebSocket URL from request
    scheme = "wss" if request.url.scheme == "https" else "ws"
    # Use hostname from request, fallback to client host, or raise error if unavailable
    host = request.url.hostname or (request.client.host if request.client else None)
    if not host:
        return JSONResponse(
            {"error": "Unable to determine host for WebSocket URL"},
            status_code=400,
        )
    ws_url = f"{scheme}://{host}"
    if request.url.port:
        ws_url += f":{request.url.port}"
    ws_url += f"/ws/voice/{session.id}"

    return JSONResponse(
        {
            "session_id": session.id,
            "context_id": session.context_id,
            "ws_url": ws_url,
            **({"session_token": session_token} if session_token else {}),
        },
        status_code=201,
    )


@handle_endpoint_errors("end voice session")
async def voice_session_end(app: BinduApplication, request: Request) -> Response:
    """End a voice session.

    Path params:
        session_id: The voice session ID

    Returns:
        { "status": "ended" }
    """
    session_manager = getattr(app, "_voice_session_manager", None)
    if session_manager is None:
        return JSONResponse(
            {"error": "Voice extension is not enabled"}, status_code=501
        )

    session_id = request.path_params["session_id"]
    session = await session_manager.get_session(session_id)
    if session is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    await session_manager.end_session(session_id)
    return JSONResponse({"status": "ended"})


@handle_endpoint_errors("voice session status")
async def voice_session_status(app: BinduApplication, request: Request) -> Response:
    """Get voice session status.

    Path params:
        session_id: The voice session ID

    Returns:
        { "session_id": "...", "state": "...", "duration": 12.3, "context_id": "..." }
    """
    session_manager = getattr(app, "_voice_session_manager", None)
    if session_manager is None:
        return JSONResponse(
            {"error": "Voice extension is not enabled"}, status_code=501
        )

    session_id = request.path_params["session_id"]
    session = await session_manager.get_session(session_id)
    if session is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    return JSONResponse(
        {
            "session_id": session.id,
            "context_id": session.context_id,
            "state": session.state,
            "duration": round(session.duration_seconds, 1),
            "task_id": session.task_id,
        }
    )


# ---------------------------------------------------------------------------
# WebSocket Handler
# ---------------------------------------------------------------------------


async def voice_websocket(websocket: WebSocket) -> None:
    """Bidirectional voice WebSocket handler using Pipecat pipeline."""
    app: BinduApplication = websocket.app  # type: ignore[assignment]
    session_id = websocket.path_params.get("session_id", "")

    session_manager = getattr(app, "_voice_session_manager", None)
    if session_manager is None:
        await websocket.close(code=1008, reason="Voice extension is not enabled")
        return
    if not app_settings.voice.enabled:
        await websocket.close(code=1008, reason="Voice is disabled")
        return

    preflight_error = _voice_preflight_error()
    if preflight_error:
        await websocket.close(code=1008, reason=preflight_error)
        return

    session = await session_manager.get_session(session_id)
    if session is None:
        await websocket.close(code=1008, reason="Invalid session ID")
        return

    # Per-IP rate limit on websocket connects (best-effort)
    client_host = websocket.client.host if websocket.client else None
    if client_host:
        allowed = await _rate_limit_allow_ip(
            client_host,
            limit_per_minute=int(app_settings.voice.rate_limit_per_ip_per_minute),
        )
        if not allowed:
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return

    if app_settings.voice.session_auth_required:
        expected = getattr(session, "session_token", None)
        expires_at = getattr(session, "session_token_expires_at", None)
        provided = _extract_ws_session_token(websocket)

        # If the client sent Sec-WebSocket-Protocol, the server should select one.
        # We select the token itself as the negotiated subprotocol.
        if provided and _has_ws_subprotocols(websocket):
            await websocket.accept(subprotocol=provided)
        else:
            await websocket.accept()
        if not provided:
            try:
                provided = (
                    await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=float(app_settings.voice.ws_token_read_timeout_secs),
                    )
                ).strip()
            except asyncio.TimeoutError:
                await websocket.close(code=1008, reason="Missing session token")
                return
            except Exception:
                await websocket.close(code=1008, reason="Missing session token")
                return

        if not expected or provided != expected:
            await websocket.close(code=1008, reason="Invalid session token")
            return
        if isinstance(expires_at, (int, float)) and time.time() > float(expires_at):
            await websocket.close(code=1008, reason="Session token expired")
            return
    else:
        await websocket.accept()

    send_lock = asyncio.Lock()
    components: dict[str, Any] | None = None

    async def _on_user_transcript(text: str) -> None:
        await _send_json(
            websocket,
            {"type": "transcript", "role": "user", "text": text, "is_final": True},
            send_lock,
        )

    async def _on_agent_response(text: str) -> None:
        control.suppress_audio_until = max(
            float(control.suppress_audio_until), time.monotonic() + 0.6
        )
        await _send_json(
            websocket,
            {"type": "agent_response", "text": text, "task_id": session.task_id},
            send_lock,
        )

    async def _on_state_change(state: str) -> None:
        if state == "agent-speaking":
            control.suppress_audio_until = max(
                float(control.suppress_audio_until), time.monotonic() + 1.0
            )
        elif state == "listening":
            control.suppress_audio_until = max(
                float(control.suppress_audio_until), time.monotonic() + 0.35
            )
        await _send_json(websocket, {"type": "state", "state": state}, send_lock)

    async def _on_agent_transcript(text: str, is_final: bool) -> None:
        control.suppress_audio_until = max(
            float(control.suppress_audio_until),
            time.monotonic() + (0.6 if is_final else 0.9),
        )
        logger.info(
            f"on_agent_transcript: got text='{text[:50]}...' is_final={is_final}"
        )
        await _send_json(
            websocket,
            {
                "type": "transcript",
                "role": "agent",
                "text": text,
                "is_final": is_final,
            },
            send_lock,
        )

    control = _VoiceControlState()
    inbound_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10)
    filtered_ws = _FilteredWebSocket(websocket, inbound_queue)

    async def _handle_user_text(text: str) -> None:
        await _send_json(
            websocket,
            {"type": "transcript", "role": "user", "text": text, "is_final": True},
            send_lock,
        )
        response = await components["bridge"].process_transcription(
            text, emit_frames=True
        )
        if response:
            await _on_agent_response(response)

    reader_task: asyncio.Task[Any] | None = None
    runner_task: asyncio.Task[Any] | None = None

    try:
        await session_manager.update_state(session_id, "active")

        voice_ext = getattr(app, "_voice_ext", None)
        manifest = getattr(app, "manifest", None)
        if voice_ext is None or manifest is None or not hasattr(manifest, "run"):
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Agent not configured for voice"})
            )
            await websocket.close(code=1011)
            return

        from bindu.extensions.voice.pipeline_builder import build_voice_pipeline
        from pipecat.transports.websocket.fastapi import (
            FastAPIWebsocketTransport,
            FastAPIWebsocketParams,
        )
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.task import PipelineTask
        from pipecat.pipeline.runner import PipelineRunner

        components = build_voice_pipeline(
            voice_ext=voice_ext,
            manifest_run=manifest.run,
            context_id=session.context_id,
            on_state_change=_on_state_change,
            on_user_transcript=_on_user_transcript,
            on_agent_response=_on_agent_response,
            on_agent_transcript=_on_agent_transcript,
        )

        # Notify UI we are listening
        await _send_json(websocket, {"type": "state", "state": "listening"}, send_lock)

        transport = FastAPIWebsocketTransport(
            websocket=filtered_ws,  # type: ignore[arg-type]
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_sample_rate=app_settings.voice.sample_rate,
                audio_out_sample_rate=app_settings.voice.sample_rate,
                add_wav_header=False,
                serializer=_RawAudioFrameSerializer(
                    sample_rate=app_settings.voice.sample_rate,
                    num_channels=app_settings.voice.audio_channels,
                ),
            ),
        )

        logger.info(
            f"Voice pipeline: transport created, sample_rate={app_settings.voice.sample_rate}"
        )
        logger.info(
            f"Voice pipeline: components - STT={type(components['stt']).__name__}, "
            f"Bridge={type(components['bridge']).__name__}, TTS={type(components['tts']).__name__}"
        )

        pipeline_components = [transport.input()]
        if components.get("vad"):
            pipeline_components.append(components["vad"])
            logger.info("Voice pipeline: VAD enabled and added")

        pipeline_components.extend(
            [
                components["stt"],
                components["bridge"],
                components["tts"],
                transport.output(),
            ]
        )
        logger.info(
            f"Voice pipeline: total components in pipeline: {len(pipeline_components)}"
        )

        pipeline = Pipeline(pipeline_components)
        logger.info("Voice pipeline: Pipeline created successfully")

        task = PipelineTask(pipeline)
        logger.info("Voice pipeline: PipelineTask created, starting runner...")
        runner = PipelineRunner()

        runner_task = asyncio.create_task(runner.run(task))

        # Start reading control/audio only after pipeline runner is live so
        # user_text cannot emit TTS frames before StartFrame initialization.
        reader_task = asyncio.create_task(
            _voice_control_reader(
                websocket,
                inbound_queue,
                control,
                vad_enabled=app_settings.voice.vad_enabled,
                send_lock=send_lock,
                on_user_text=_handle_user_text,
            )
        )

        async with asyncio.timeout(float(app_settings.voice.session_timeout)):
            await runner_task
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {session_id}")
    except TimeoutError:
        logger.info(f"Voice session timed out: {session_id}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await _send_json(
                websocket,
                {"type": "error", "message": "Voice session timed out"},
                send_lock,
            )
    except Exception as e:
        logger.exception(f"Error in voice WebSocket: {session_id}: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            user_message, close_code = _classify_voice_pipeline_error(e)
            await _send_json(
                websocket, {"type": "error", "message": user_message}, send_lock
            )
            try:
                await websocket.close(code=close_code, reason=user_message)
            except Exception:
                pass
    finally:
        if runner_task and not runner_task.done():
            runner_task.cancel()
            try:
                await runner_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Voice pipeline runner task failed")

        if reader_task and not reader_task.done():
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Voice control reader task failed")

        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await _send_json(
                    websocket, {"type": "state", "state": "ended"}, send_lock
                )
            except Exception:
                pass

        try:
            await session_manager.update_state(session_id, "ending")
        except Exception:
            pass
        try:
            if components is not None:
                await components["bridge"].cleanup_background_tasks()
        except Exception:
            pass
        try:
            await session_manager.end_session(session_id)
        except Exception:
            pass
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception:
                pass
