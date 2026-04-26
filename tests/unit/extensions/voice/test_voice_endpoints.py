"""Unit tests for voice session endpoints."""

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu.extensions.voice.session_manager import VoiceSessionManager
from bindu.server.endpoints.voice_endpoints import (
    _extract_ws_session_token,
    _has_ws_subprotocols,
    _send_json,
    _trim_overlap_text,
    _VoiceControlState,
    _classify_voice_pipeline_error,
    _rate_limit_allow_ip,
    _voice_control_reader,
    voice_session_end,
    voice_session_start,
    voice_session_status,
)


def _make_mock_app(session_manager=None, voice_ext=None, manifest=None):
    """Create a mock BinduApplication."""
    app = MagicMock()
    app._voice_session_manager = session_manager
    app._voice_ext = voice_ext
    app.manifest = manifest
    return app


@pytest.fixture(autouse=True)
def _enable_voice_for_tests():
    from bindu.server.endpoints import voice_endpoints as module

    original = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    original_session_auth_required = module.app_settings.voice.session_auth_required
    module.app_settings.voice.enabled = True
    module.app_settings.voice.session_auth_required = False
    module.app_settings.voice.stt_api_key = (
        "unit-test-stt-token"  # pragma: allowlist secret
    )
    module.app_settings.voice.tts_api_key = (
        "unit-test-tts-token"  # pragma: allowlist secret
    )
    try:
        yield
    finally:
        module.app_settings.voice.enabled = original
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts
        module.app_settings.voice.session_auth_required = original_session_auth_required


def _make_request(
    method="POST", path="/voice/session/start", body=None, path_params=None
):
    """Create a mock Starlette Request."""
    url = MagicMock()
    url.scheme = "http"
    url.hostname = "localhost"
    url.port = 3773

    request = MagicMock(spec=Request)
    request.method = method
    request.url = url
    request.path_params = path_params or {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    if body is not None:
        request.body = AsyncMock(
            return_value=json.dumps(body).encode("utf-8")
            if not isinstance(body, (bytes, bytearray))
            else body
        )
        request.json = AsyncMock(return_value=body)
    else:
        request.body = AsyncMock(return_value=b"")
        request.json = AsyncMock(side_effect=Exception("No body"))

    return request


class TestVoiceSessionStartEndpoint:
    """Test POST /voice/session/start."""

    @pytest.mark.asyncio
    async def test_voice_not_enabled(self):
        app = _make_mock_app(session_manager=None)
        request = _make_request()
        response = await voice_session_start(app, request)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_missing_provider_keys_returns_503(self, monkeypatch):
        from bindu.server.endpoints import voice_endpoints as module

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(body={})

        monkeypatch.setattr(module.app_settings.voice, "stt_api_key", "")
        monkeypatch.setattr(module.app_settings.voice, "tts_api_key", "")

        response = await voice_session_start(app, request)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_successful_session_start(self):
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(body={})
        response = await voice_session_start(app, request)
        assert response.status_code == 201
        body = json.loads(response.body)
        assert "session_id" in body
        assert "ws_url" in body
        assert "context_id" in body
        assert body["ws_url"].startswith("ws://")
        assert "session_token" not in body

    @pytest.mark.asyncio
    async def test_session_start_includes_session_token_when_required(self):
        from bindu.server.endpoints import voice_endpoints as module

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(body={})

        original_required = module.app_settings.voice.session_auth_required
        original_ttl = module.app_settings.voice.session_token_ttl
        try:
            module.app_settings.voice.session_auth_required = True
            module.app_settings.voice.session_token_ttl = 300
            response = await voice_session_start(app, request)
        finally:
            module.app_settings.voice.session_auth_required = original_required
            module.app_settings.voice.session_token_ttl = original_ttl

        assert response.status_code == 201
        body = json.loads(response.body)
        assert "session_token" in body
        assert isinstance(body["session_token"], str)
        assert body["session_token"]

    @pytest.mark.asyncio
    async def test_session_start_with_context_id(self):
        ctx = str(uuid4())
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(body={"context_id": ctx})
        response = await voice_session_start(app, request)
        body = json.loads(response.body)
        assert body["context_id"] == ctx

    @pytest.mark.asyncio
    async def test_session_start_with_malformed_json(self):
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request()
        request.body = AsyncMock(return_value=b"{not valid json")

        with pytest.raises(HTTPException) as exc_info:
            await voice_session_start(app, request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Malformed JSON payload"

    @pytest.mark.asyncio
    async def test_session_start_max_reached(self):
        manager = VoiceSessionManager(max_sessions=1, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        # Fill the one slot
        await manager.create_session("c1")
        request = _make_request(body={})
        response = await voice_session_start(app, request)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_session_start_rate_limited_by_ip(self):
        from bindu.server.endpoints import voice_endpoints as module

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(body={})
        request.client.host = "127.0.0.123"

        original = module.app_settings.voice.rate_limit_per_ip_per_minute
        try:
            module._VOICE_RATE_LIMIT_IP_BUCKET.clear()
            module.app_settings.voice.rate_limit_per_ip_per_minute = 1
            response1 = await voice_session_start(app, request)
            response2 = await voice_session_start(app, request)
        finally:
            module.app_settings.voice.rate_limit_per_ip_per_minute = original

        assert response1.status_code == 201
        assert response2.status_code == 429


class TestVoiceSessionEndEndpoint:
    """Test DELETE /voice/session/{session_id}."""

    @pytest.mark.asyncio
    async def test_voice_not_enabled(self):
        app = _make_mock_app(session_manager=None)
        request = _make_request(method="DELETE", path_params={"session_id": "x"})
        response = await voice_session_end(app, request)
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_session_not_found(self):
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(
            method="DELETE", path_params={"session_id": "nonexistent"}
        )
        response = await voice_session_end(app, request)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_end_session_success(self):
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session("c1")
        app = _make_mock_app(session_manager=manager)
        request = _make_request(method="DELETE", path_params={"session_id": session.id})
        response = await voice_session_end(app, request)
        assert response.status_code == 200
        body = json.loads(response.body)
        assert body["status"] == "ended"


class TestVoiceSessionStatusEndpoint:
    """Test GET /voice/session/{session_id}/status."""

    @pytest.mark.asyncio
    async def test_voice_not_enabled(self):
        app = _make_mock_app(session_manager=None)
        request = _make_request(method="GET", path_params={"session_id": "x"})
        response = await voice_session_status(app, request)
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_session_not_found(self):
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        request = _make_request(method="GET", path_params={"session_id": "nope"})
        response = await voice_session_status(app, request)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_status_success(self):
        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session("c1")
        await manager.update_state(session.id, "active")
        app = _make_mock_app(session_manager=manager)
        request = _make_request(method="GET", path_params={"session_id": session.id})
        response = await voice_session_status(app, request)
        assert response.status_code == 200
        body = json.loads(response.body)
        assert body["state"] == "active"
        assert body["session_id"] == session.id
        assert body["context_id"] == "c1"
        assert "duration" in body


class TestOverlapTranscriptTrimming:
    """Regression tests for overlap text deduplication between STT chunks."""

    def test_trim_overlap_with_exact_word_prefix_suffix_match(self):
        prev = "hello this is a streaming voice test"
        curr = "a streaming voice test for overlap handling"
        assert _trim_overlap_text(prev, curr) == "for overlap handling"

    def test_trim_overlap_with_no_match_keeps_current(self):
        prev = "completely different words"
        curr = "new sentence starts here"
        assert _trim_overlap_text(prev, curr) == curr

    def test_trim_overlap_with_empty_previous(self):
        curr = "first transcript chunk"
        assert _trim_overlap_text("", curr) == curr

    def test_trim_overlap_with_full_duplicate_returns_empty(self):
        prev = "repeat this chunk"
        curr = "repeat this chunk"
        assert _trim_overlap_text(prev, curr) == ""

    def test_trim_overlap_with_partial_duplicate_case_sensitive(self):
        # Current implementation is exact token matching and case-sensitive.
        prev = "Hello there General Kenobi"
        curr = "General Kenobi you are a bold one"
        assert _trim_overlap_text(prev, curr) == "you are a bold one"

    def test_chunk_sequence_delta_accumulates_without_repetition(self):
        # Simulate adjacent overlapping chunk transcriptions.
        chunks = [
            "hello this is a",
            "is a voice",
            "a voice session",
            "voice session test",
        ]
        prev = ""
        deltas: list[str] = []

        for chunk in chunks:
            delta = _trim_overlap_text(prev, chunk)
            if delta:
                deltas.append(delta)
            prev = chunk

        assert " ".join(deltas) == "hello this is a voice session test"


class TestWebSocketSendHelpers:
    """Regression tests for outbound WebSocket send serialization."""

    @pytest.mark.asyncio
    async def test_send_json_uses_lock_when_provided(self):
        websocket = AsyncMock()
        send_lock = asyncio.Lock()

        await asyncio.gather(
            _send_json(websocket, {"type": "one"}, send_lock),
            _send_json(websocket, {"type": "two"}, send_lock),
        )

        assert websocket.send_text.await_count == 2


class TestVoicePipelineErrorClassification:
    def test_connection_closed_classified(self):
        class ConnectionClosedError(Exception):
            pass

        ConnectionClosedError.__module__ = "websockets.exceptions"  # type: ignore[attr-defined]

        msg, code = _classify_voice_pipeline_error(ConnectionClosedError("closed"))
        assert "connection closed" in msg.lower()
        assert code == 1011


class TestVoiceWebSocketSubprotocolParsing:
    def test_extract_ws_session_token_parses_label_and_token(self):
        websocket = MagicMock()
        websocket.headers = {"sec-websocket-protocol": "bindu.voice.v1, token-abc"}

        label, token = _extract_ws_session_token(websocket)

        assert label == "bindu.voice.v1"
        assert token == "token-abc"

    def test_extract_ws_session_token_falls_back_to_bearer(self):
        websocket = MagicMock()
        websocket.headers = {"authorization": "Bearer token-xyz"}

        label, token = _extract_ws_session_token(websocket)

        assert label is None
        assert token == "token-xyz"

    def test_has_ws_subprotocols_requires_fixed_label(self):
        websocket = MagicMock()
        websocket.headers = {"sec-websocket-protocol": "bindu.voice.v1, token-abc"}
        assert _has_ws_subprotocols(websocket) is True

        websocket.headers = {"sec-websocket-protocol": "other.proto, token-abc"}
        assert _has_ws_subprotocols(websocket) is False


class TestVoiceRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limit_allow_ip_sliding_window(self):
        ip = "10.0.0.1"
        assert await _rate_limit_allow_ip(ip, limit_per_minute=2, now=100.0) is True
        assert await _rate_limit_allow_ip(ip, limit_per_minute=2, now=110.0) is True
        assert await _rate_limit_allow_ip(ip, limit_per_minute=2, now=120.0) is False
        # After 60s window passes, allow again.
        assert await _rate_limit_allow_ip(ip, limit_per_minute=2, now=161.0) is True

    @pytest.mark.asyncio
    async def test_rate_limit_allow_ip_uses_redis_when_configured(self, monkeypatch):
        from bindu.server.endpoints import voice_endpoints as module

        class FakeRedis:
            def __init__(self):
                self.calls = 0

            async def eval(self, *_args):
                self.calls += 1
                return 1

        fake = FakeRedis()
        monkeypatch.setattr(
            module, "_get_rate_limit_redis_client", AsyncMock(return_value=fake)
        )

        original_backend = module.app_settings.voice.rate_limit_backend
        try:
            module.app_settings.voice.rate_limit_backend = "redis"
            allowed = await module._rate_limit_allow_ip(
                "192.168.1.5", limit_per_minute=1, now=100.0
            )
        finally:
            module.app_settings.voice.rate_limit_backend = original_backend

        assert allowed is True
        assert fake.calls == 1


class TestVoiceControlReader:
    """Regression tests for JSON control frame handling."""

    @pytest.mark.asyncio
    async def test_mute_drops_audio_until_unmute(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()

        messages = [
            {"type": "websocket.receive", "text": json.dumps({"type": "mute"})},
            {"type": "websocket.receive", "bytes": b"aaa"},
            {"type": "websocket.receive", "text": json.dumps({"type": "unmute"})},
            {"type": "websocket.receive", "bytes": b"bbb"},
            {"type": "websocket.disconnect", "code": 1000},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=True, send_lock=send_lock
        )

        assert control.muted is False
        forwarded = []
        while not queue.empty():
            forwarded.append(queue.get_nowait())

        assert any(m.get("bytes") == b"bbb" for m in forwarded)
        assert not any(m.get("bytes") == b"aaa" for m in forwarded)

    @pytest.mark.asyncio
    async def test_stop_closes_and_exits(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()

        messages = [
            {"type": "websocket.receive", "text": json.dumps({"type": "stop"})},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=True, send_lock=send_lock
        )

        assert control.stopped is True
        assert websocket.send_text.await_count >= 1
        websocket.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_malformed_json_control_frame_closes(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()

        messages = [
            {"type": "websocket.receive", "text": "{not json"},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=True, send_lock=send_lock
        )

        assert websocket.send_text.await_count >= 1
        websocket.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_oversized_audio_frame_closes(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()

        messages = [
            {"type": "websocket.receive", "bytes": b"x" * (64 * 1024 + 1)},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=True, send_lock=send_lock
        )

        websocket.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_in_flight_limit_closes(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()

        # Pre-fill queue to the max in-flight (10).
        queue: asyncio.Queue[dict] = asyncio.Queue()
        for _ in range(10):
            queue.put_nowait({"type": "websocket.receive", "bytes": b"aaa"})

        messages = [
            {"type": "websocket.receive", "bytes": b"bbb"},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=True, send_lock=send_lock
        )

        websocket.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_commit_turn_is_forwarded_when_vad_disabled(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()

        messages = [
            {"type": "websocket.receive", "text": json.dumps({"type": "commit_turn"})},
            {"type": "websocket.disconnect", "code": 1000},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=False, send_lock=send_lock
        )

        forwarded = []
        while not queue.empty():
            forwarded.append(queue.get_nowait())
        assert any(m.get("text") and "commit_turn" in m.get("text") for m in forwarded)

    @pytest.mark.asyncio
    async def test_commit_turn_is_ignored_when_vad_enabled(self):
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()

        messages = [
            {"type": "websocket.receive", "text": json.dumps({"type": "commit_turn"})},
            {"type": "websocket.disconnect", "code": 1000},
        ]

        async def _recv():
            return messages.pop(0)

        websocket.receive = AsyncMock(side_effect=_recv)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        control = _VoiceControlState()
        send_lock = asyncio.Lock()

        await _voice_control_reader(
            websocket, queue, control, vad_enabled=True, send_lock=send_lock
        )

        forwarded = []
        while not queue.empty():
            forwarded.append(queue.get_nowait())
        assert not any(
            m.get("text") and "commit_turn" in m.get("text") for m in forwarded
        )
