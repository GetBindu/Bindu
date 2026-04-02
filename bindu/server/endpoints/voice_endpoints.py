"""Voice session REST + WebSocket endpoints.

Provides:
    POST   /voice/session/start             → Start a new voice session
    DELETE /voice/session/{session_id}       → End a voice session
    GET    /voice/session/{session_id}/status → Get session status
    WS     /ws/voice/{session_id}            → Bidirectional audio stream
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.server.endpoints.utils import handle_endpoint_errors

if TYPE_CHECKING:
    from bindu.extensions.voice.agent_bridge import AgentBridgeProcessor
    from bindu.server.applications import BinduApplication

logger = get_logger("bindu.server.endpoints.voice")


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

    # Parse optional context_id from body
    context_id = str(uuid4())
    try:
        body = await request.json()
        if isinstance(body, dict) and "context_id" in body:
            context_id = str(body["context_id"])
    except Exception:
        pass  # empty body is fine, we'll generate a new context_id

    try:
        session = await session_manager.create_session(context_id)
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
    """Bidirectional voice WebSocket handler.

    Protocol:
        Client→Server (text):  { "type": "start", "config": { ... } }
        Client→Server (binary): Raw PCM 16-bit audio frames
        Client→Server (text):  { "type": "mute"/"unmute"/"stop" }

        Server→Client (text):  { "type": "transcript", "role": "user"/"agent", "text": "...", "is_final": true }
        Server→Client (binary): TTS audio (PCM 16-bit)
        Server→Client (text):  { "type": "agent_response", "text": "...", "task_id": "..." }
        Server→Client (text):  { "type": "state", "state": "listening"/"agent-speaking" }
        Server→Client (text):  { "type": "error", "message": "..." }
    """
    app: BinduApplication = websocket.app  # type: ignore[assignment]
    session_id = websocket.path_params.get("session_id", "")

    session_manager = getattr(app, "_voice_session_manager", None)
    if session_manager is None:
        await websocket.close(code=1008, reason="Voice extension is not enabled")
        return

    session = await session_manager.get_session(session_id)
    if session is None:
        await websocket.close(code=1008, reason="Invalid session ID")
        return

    await websocket.accept()
    await session_manager.update_state(session_id, "active")
    send_lock = asyncio.Lock()

    # Build the agent bridge for this session
    voice_ext = getattr(app, "_voice_ext", None)
    manifest = getattr(app, "manifest", None)
    if voice_ext is None or manifest is None or not hasattr(manifest, "run"):
        await _send_json(
            websocket,
            {"type": "error", "message": "Agent not configured for voice"},
            send_lock,
        )
        await websocket.close(code=1011)
        return

    from bindu.extensions.voice.agent_bridge import AgentBridgeProcessor

    bridge = AgentBridgeProcessor(
        manifest_run=manifest.run,
        context_id=session.context_id,
        on_user_transcript=lambda text: _try_send_json(
            websocket,
            {"type": "transcript", "role": "user", "text": text, "is_final": True},
            send_lock,
        ),
        on_agent_response=lambda text: _try_send_json(
            websocket,
            {"type": "agent_response", "text": text, "task_id": session.task_id},
            send_lock,
        ),
    )

    muted = False
    audio_buffer = bytearray()
    last_transcribe_at = 0.0
    chunk_bytes = app_settings.voice.sample_rate * app_settings.voice.audio_channels * 2
    overlap_bytes = int(chunk_bytes * 0.25)  # Keep 250ms audio overlap between chunks.
    last_chunk_transcript = ""
    interim_transcript = ""

    try:
        await _send_json(websocket, {"type": "state", "state": "listening"}, send_lock)

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # Text control messages
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                except (json.JSONDecodeError, TypeError):
                    continue

                msg_type = data.get("type")

                if msg_type == "stop":
                    break

                elif msg_type == "mute":
                    muted = True
                    await _send_json(
                        websocket, {"type": "state", "state": "muted"}, send_lock
                    )

                elif msg_type == "unmute":
                    muted = False
                    await _send_json(
                        websocket, {"type": "state", "state": "listening"}, send_lock
                    )

                elif msg_type == "start":
                    # Client confirms start (config already set on session creation)
                    await _send_json(
                        websocket, {"type": "state", "state": "listening"}, send_lock
                    )

                elif msg_type == "commit_turn":
                    # Deterministic turn boundary: process whatever audio has been buffered.
                    if audio_buffer:
                        transcript = await _transcribe_pcm_buffer(bytes(audio_buffer))
                        audio_buffer.clear()
                        last_transcribe_at = time.monotonic()
                        if transcript:
                            delta = _trim_overlap_text(
                                last_chunk_transcript, transcript
                            )
                            if delta:
                                interim_transcript = (
                                    f"{interim_transcript} {delta}"
                                    if interim_transcript
                                    else delta
                                )

                    if interim_transcript:
                        await _process_user_turn(
                            websocket, bridge, interim_transcript, send_lock
                        )

                    # Reset for next turn
                    last_chunk_transcript = ""
                    interim_transcript = ""

                elif msg_type == "user_text":
                    text = str(data.get("text", "")).strip()
                    if not text:
                        continue

                    last_chunk_transcript = ""
                    interim_transcript = ""
                    audio_buffer.clear()

                    await _process_user_turn(websocket, bridge, text, send_lock)

            # Binary audio frames
            elif "bytes" in message and not muted:
                audio_bytes = message["bytes"]
                if not isinstance(audio_bytes, (bytes, bytearray)):
                    continue

                audio_buffer.extend(audio_bytes)

                # Chunked transcription: process roughly every 1s of audio,
                # throttled to avoid overwhelming the STT provider.
                now = time.monotonic()
                if (
                    len(audio_buffer) >= chunk_bytes
                    and (now - last_transcribe_at) >= 0.8
                ):
                    transcript = await _transcribe_pcm_buffer(bytes(audio_buffer))
                    if overlap_bytes > 0:
                        audio_buffer = bytearray(audio_buffer[-overlap_bytes:])
                    else:
                        audio_buffer.clear()
                    last_transcribe_at = now

                    if transcript:
                        delta = _trim_overlap_text(last_chunk_transcript, transcript)
                        if delta:
                            interim_transcript = (
                                f"{interim_transcript} {delta}"
                                if interim_transcript
                                else delta
                            )
                            await _send_json(
                                websocket,
                                {
                                    "type": "transcript",
                                    "role": "user",
                                    "text": interim_transcript,
                                    "is_final": False,
                                },
                                send_lock,
                            )
                        last_chunk_transcript = transcript

    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {session_id}")
    except Exception:
        logger.exception(f"Error in voice WebSocket: {session_id}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await _send_json(
                websocket,
                {"type": "error", "message": "Internal server error"},
                send_lock,
            )
    finally:
        # Flush any pending audio when the socket is closing.
        try:
            if audio_buffer:
                try:
                    transcript = await _transcribe_pcm_buffer(bytes(audio_buffer))
                    if transcript:
                        delta = _trim_overlap_text(last_chunk_transcript, transcript)
                        if delta:
                            interim_transcript = (
                                f"{interim_transcript} {delta}"
                                if interim_transcript
                                else delta
                            )
                except Exception as e:
                    logger.exception(
                        f"Error during final audio transcription for session {session_id}: {e}"
                    )

            if (
                interim_transcript
                and websocket.client_state == WebSocketState.CONNECTED
            ):
                try:
                    await _process_user_turn(
                        websocket, bridge, interim_transcript, send_lock
                    )
                except Exception as e:
                    logger.exception(
                        f"Error during final turn processing for session {session_id}: {e}"
                    )
        except Exception as e:
            logger.exception(
                f"Error in audio buffer cleanup for session {session_id}: {e}"
            )

        try:
            await session_manager.update_state(session_id, "ending")
        except Exception as e:
            logger.exception(
                f"Error updating session state to 'ending' for session {session_id}: {e}"
            )

        try:
            await session_manager.end_session(session_id)
        except Exception as e:
            logger.exception(f"Error ending session {session_id}: {e}")

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception as e:
            logger.exception(f"Error closing websocket for session {session_id}: {e}")


async def _process_user_turn(
    websocket: WebSocket,
    bridge: "AgentBridgeProcessor",
    text: str,
    send_lock: asyncio.Lock,
) -> None:
    """Process one user turn and stream response artifacts/events."""
    text = text.strip()
    if not text:
        return

    await _send_json(websocket, {"type": "state", "state": "agent-speaking"}, send_lock)
    response_text = await bridge.process_transcription(text)
    if response_text:
        await _send_json(
            websocket,
            {
                "type": "transcript",
                "role": "agent",
                "text": response_text,
                "is_final": True,
            },
            send_lock,
        )

        # Best-effort TTS synthesis and binary streaming.
        tts_audio = await _synthesize_tts_audio(response_text)
        if tts_audio:
            await _send_bytes(websocket, tts_audio, send_lock)

    await _send_json(websocket, {"type": "state", "state": "listening"}, send_lock)


async def _send_json(
    websocket: WebSocket,
    data: dict,
    send_lock: asyncio.Lock | None = None,
) -> None:
    """Send a JSON message over WebSocket."""
    if send_lock is None:
        await websocket.send_text(json.dumps(data))
        return

    async with send_lock:
        await websocket.send_text(json.dumps(data))


async def _send_bytes(
    websocket: WebSocket,
    data: bytes,
    send_lock: asyncio.Lock,
) -> None:
    """Send binary audio over WebSocket without concurrent write races."""
    async with send_lock:
        await websocket.send_bytes(data)


async def _synthesize_tts_audio(text: str) -> bytes | None:
    """Synthesize TTS audio using ElevenLabs and return MPEG bytes.

    This is intentionally best-effort. If credentials are not configured
    or synthesis fails, the voice session continues with text-only output.
    """
    api_key = app_settings.voice.tts_api_key
    voice_id = app_settings.voice.tts_voice_id
    model_id = app_settings.voice.tts_model

    if not api_key or not voice_id:
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
    except Exception:
        logger.exception("TTS synthesis failed")
        return None


async def _transcribe_pcm_buffer(pcm_bytes: bytes) -> str | None:
    """Transcribe PCM16 mono audio buffer with Deepgram prerecorded API."""
    api_key = app_settings.voice.stt_api_key
    if not api_key:
        logger.warning("Deepgram STT API key not configured")
        return None

    if not pcm_bytes:
        logger.debug("Empty audio buffer, skipping transcription")
        return None

    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": app_settings.voice.stt_model,
        "language": app_settings.voice.stt_language,
        "punctuate": "true",
        "smart_format": "true",
    }
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": (
            f"audio/raw;encoding={app_settings.voice.audio_encoding};"
            f"sample_rate={app_settings.voice.sample_rate};"
            f"channels={app_settings.voice.audio_channels}"
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, params=params, headers=headers, content=pcm_bytes
            )
            response.raise_for_status()
            payload = response.json()

        transcript = (
            payload.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )

        text = str(transcript).strip()
        return text if text else None
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Deepgram API error: {e.response.status_code} - {e.response.text}"
        )
        return None
    except Exception as e:
        logger.exception(f"STT transcription failed: {e}")
        return None


def _trim_overlap_text(previous: str, current: str) -> str:
    """Trim repeated overlap words between adjacent chunk transcripts.

    We keep an audio overlap to avoid clipping words, which can cause
    duplicated leading tokens in the next transcript. This helper removes
    the longest matching suffix-prefix word overlap.
    """
    prev = previous.strip()
    curr = current.strip()
    if not curr:
        return ""
    if not prev:
        return curr

    prev_words = prev.split()
    curr_words = curr.split()
    if not curr_words:
        return ""

    max_overlap = min(len(prev_words), len(curr_words), 20)
    overlap = 0
    for k in range(max_overlap, 0, -1):
        if prev_words[-k:] == curr_words[:k]:
            overlap = k
            break

    return " ".join(curr_words[overlap:]).strip()


def _try_send_json(
    websocket: WebSocket,
    data: dict,
    send_lock: asyncio.Lock,
) -> None:
    """Enqueue a JSON send (safe to call from sync callbacks)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send_json(websocket, data, send_lock))
    except RuntimeError:
        pass
