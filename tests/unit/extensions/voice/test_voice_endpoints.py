"""Unit tests for voice session endpoints."""

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu.extensions.voice.session_manager import VoiceSessionManager
from bindu.server.endpoints.voice_endpoints import (
    _send_json,
    _trim_overlap_text,
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

    if body is not None:
        request.json = AsyncMock(return_value=body)
    else:
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
    async def test_session_start_max_reached(self):
        manager = VoiceSessionManager(max_sessions=1, session_timeout=300)
        app = _make_mock_app(session_manager=manager)
        # Fill the one slot
        await manager.create_session("c1")
        request = _make_request(body={})
        response = await voice_session_start(app, request)
        assert response.status_code == 429


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
