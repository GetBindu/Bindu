"""Lightweight integration tests for voice_websocket without external providers.

These tests stub Pipecat classes so we can exercise endpoint glue code:
- session_token handshake via Sec-WebSocket-Protocol
- initial state frames
- cleanup / ended state on shutdown
"""

import asyncio
import json
import types
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.websockets import WebSocketState

from bindu.extensions.voice.session_manager import VoiceSessionManager
from bindu.server.endpoints.voice_endpoints import voice_websocket


@pytest.fixture
def mock_pipecat_modules(monkeypatch, request):
    """Stub Pipecat modules used by the voice websocket endpoint."""
    runner_delay = getattr(request, "param", 0)

    pipecat_mod = types.ModuleType("pipecat")
    pipecat_mod.__path__ = []

    transports_mod = types.ModuleType("pipecat.transports")
    transports_mod.__path__ = []

    websocket_mod = types.ModuleType("pipecat.transports.websocket")
    websocket_mod.__path__ = []

    pipeline_pkg_mod = types.ModuleType("pipecat.pipeline")
    pipeline_pkg_mod.__path__ = []

    fastapi_mod = types.ModuleType("pipecat.transports.websocket.fastapi")

    class FastAPIWebsocketParams:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FastAPIWebsocketTransport:
        def __init__(self, websocket, params):
            self._ws = websocket
            self._params = params

        def input(self):
            return object()

        def output(self):
            return object()

    fastapi_mod.FastAPIWebsocketTransport = FastAPIWebsocketTransport
    fastapi_mod.FastAPIWebsocketParams = FastAPIWebsocketParams

    pipeline_mod = types.ModuleType("pipecat.pipeline.pipeline")

    class Pipeline:
        def __init__(self, items):
            self.items = items

    pipeline_mod.Pipeline = Pipeline

    task_mod = types.ModuleType("pipecat.pipeline.task")

    class PipelineTask:
        def __init__(self, pipeline):
            self.pipeline = pipeline

    task_mod.PipelineTask = PipelineTask

    runner_mod = types.ModuleType("pipecat.pipeline.runner")

    class PipelineRunner:
        async def run(self, task):
            await asyncio.sleep(runner_delay)

    runner_mod.PipelineRunner = PipelineRunner

    pipecat_mod.transports = transports_mod
    pipecat_mod.pipeline = pipeline_pkg_mod
    transports_mod.websocket = websocket_mod
    websocket_mod.fastapi = fastapi_mod
    pipeline_pkg_mod.pipeline = pipeline_mod
    pipeline_pkg_mod.task = task_mod
    pipeline_pkg_mod.runner = runner_mod

    monkeypatch.setitem(sys.modules, "pipecat", pipecat_mod)
    monkeypatch.setitem(sys.modules, "pipecat.transports", transports_mod)
    monkeypatch.setitem(sys.modules, "pipecat.transports.websocket", websocket_mod)
    monkeypatch.setitem(
        sys.modules, "pipecat.transports.websocket.fastapi", fastapi_mod
    )
    monkeypatch.setitem(sys.modules, "pipecat.pipeline", pipeline_pkg_mod)
    monkeypatch.setitem(sys.modules, "pipecat.pipeline.pipeline", pipeline_mod)
    monkeypatch.setitem(sys.modules, "pipecat.pipeline.task", task_mod)
    monkeypatch.setitem(sys.modules, "pipecat.pipeline.runner", runner_mod)


@pytest.mark.asyncio
async def test_voice_websocket_accepts_subprotocol_session_token(
    monkeypatch, mock_pipecat_modules
):
    # Stub build_voice_pipeline to avoid creating real provider clients.
    pipeline_builder = __import__(
        "bindu.extensions.voice.pipeline_builder", fromlist=["build_voice_pipeline"]
    )

    async def _noop(*_args, **_kwargs):
        return None

    dummy_bridge = MagicMock()
    dummy_bridge.cleanup_background_tasks = AsyncMock()
    dummy_bridge.process_transcription = AsyncMock(return_value="ok")

    def fake_build_voice_pipeline(**_kwargs):
        return {"stt": object(), "tts": object(), "bridge": dummy_bridge, "vad": None}

    monkeypatch.setattr(
        pipeline_builder, "build_voice_pipeline", fake_build_voice_pipeline
    )

    # Enable session auth for the handshake.
    from bindu.server.endpoints import voice_endpoints as module

    original_required = module.app_settings.voice.session_auth_required
    original_timeout = module.app_settings.voice.session_timeout
    original_enabled = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    try:
        module.app_settings.voice.session_auth_required = True
        module.app_settings.voice.session_timeout = 300
        module.app_settings.voice.enabled = True
        module.app_settings.voice.stt_api_key = (
            "unit-test-stt-token"  # pragma: allowlist secret
        )
        module.app_settings.voice.tts_api_key = (
            "unit-test-tts-token"  # pragma: allowlist secret
        )

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session(
            "ctx",
            session_token="token-abc",  # noqa: S106
            session_token_expires_at=1e12,
        )

        app = MagicMock()
        app._voice_session_manager = manager
        app._voice_ext = MagicMock(allow_interruptions=True)
        app.manifest = MagicMock(run=lambda _h: "ok")

        websocket = AsyncMock()
        websocket.app = app
        websocket.path_params = {"session_id": session.id}
        websocket.headers = {"sec-websocket-protocol": "bindu.voice.v1, token-abc"}
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_text = AsyncMock()

        async def receive():
            await asyncio.sleep(0.1)
            return {"type": "websocket.disconnect", "code": 1000}

        websocket.receive = AsyncMock(side_effect=receive)
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()

        await voice_websocket(websocket)

        websocket.accept.assert_awaited()
        # Should negotiate the fixed voice websocket protocol, not the token.
        assert (
            websocket.accept.await_args.kwargs.get("subprotocol")
            == "bindu.voice.v1"
        )

        sent = [
            json.loads(call.args[0]) for call in websocket.send_text.await_args_list
        ]
        assert any(
            item.get("type") == "state" and item.get("state") == "listening"
            for item in sent
        )
        assert any(
            item.get("type") == "state" and item.get("state") == "ended"
            for item in sent
        )
    finally:
        module.app_settings.voice.session_auth_required = original_required
        module.app_settings.voice.session_timeout = original_timeout
        module.app_settings.voice.enabled = original_enabled
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts


@pytest.mark.asyncio
async def test_voice_websocket_rejects_invalid_subprotocol_label(
    monkeypatch, mock_pipecat_modules
):
    pipeline_builder = __import__(
        "bindu.extensions.voice.pipeline_builder", fromlist=["build_voice_pipeline"]
    )

    dummy_bridge = MagicMock()
    dummy_bridge.cleanup_background_tasks = AsyncMock()
    dummy_bridge.process_transcription = AsyncMock(return_value="ok")

    def fake_build_voice_pipeline(**_kwargs):
        return {"stt": object(), "tts": object(), "bridge": dummy_bridge, "vad": None}

    monkeypatch.setattr(
        pipeline_builder, "build_voice_pipeline", fake_build_voice_pipeline
    )

    from bindu.server.endpoints import voice_endpoints as module

    original_required = module.app_settings.voice.session_auth_required
    original_timeout = module.app_settings.voice.session_timeout
    original_enabled = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    try:
        module.app_settings.voice.session_auth_required = True
        module.app_settings.voice.session_timeout = 300
        module.app_settings.voice.enabled = True
        module.app_settings.voice.stt_api_key = (
            "unit-test-stt-token"  # pragma: allowlist secret
        )
        module.app_settings.voice.tts_api_key = (
            "unit-test-tts-token"  # pragma: allowlist secret
        )

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session(
            "ctx",
            session_token="token-abc",  # noqa: S106
            session_token_expires_at=1e12,
        )

        app = MagicMock()
        app._voice_session_manager = manager
        app._voice_ext = MagicMock(allow_interruptions=True)
        app.manifest = MagicMock(run=lambda _h: "ok")

        websocket = AsyncMock()
        websocket.app = app
        websocket.path_params = {"session_id": session.id}
        websocket.headers = {"sec-websocket-protocol": "wrong.label, token-abc"}
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_text = AsyncMock()
        websocket.receive = AsyncMock()
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()

        await voice_websocket(websocket)

        websocket.accept.assert_not_awaited()
        websocket.close.assert_awaited()
        assert websocket.close.await_args.kwargs.get("code") == 1008
    finally:
        module.app_settings.voice.session_auth_required = original_required
        module.app_settings.voice.session_timeout = original_timeout
        module.app_settings.voice.enabled = original_enabled
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts


@pytest.mark.asyncio
async def test_voice_websocket_accepts_legacy_token_only_subprotocol(
    monkeypatch, mock_pipecat_modules
):
    pipeline_builder = __import__(
        "bindu.extensions.voice.pipeline_builder", fromlist=["build_voice_pipeline"]
    )

    dummy_bridge = MagicMock()
    dummy_bridge.cleanup_background_tasks = AsyncMock()
    dummy_bridge.process_transcription = AsyncMock(return_value="ok")

    def fake_build_voice_pipeline(**_kwargs):
        return {"stt": object(), "tts": object(), "bridge": dummy_bridge, "vad": None}

    monkeypatch.setattr(
        pipeline_builder, "build_voice_pipeline", fake_build_voice_pipeline
    )

    from bindu.server.endpoints import voice_endpoints as module

    original_required = module.app_settings.voice.session_auth_required
    original_timeout = module.app_settings.voice.session_timeout
    original_enabled = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    try:
        module.app_settings.voice.session_auth_required = True
        module.app_settings.voice.session_timeout = 300
        module.app_settings.voice.enabled = True
        module.app_settings.voice.stt_api_key = (
            "unit-test-stt-token"  # pragma: allowlist secret
        )
        module.app_settings.voice.tts_api_key = (
            "unit-test-tts-token"  # pragma: allowlist secret
        )

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session(
            "ctx",
            session_token="token-abc",  # noqa: S106
            session_token_expires_at=1e12,
        )

        app = MagicMock()
        app._voice_session_manager = manager
        app._voice_ext = MagicMock(allow_interruptions=True)
        app.manifest = MagicMock(run=lambda _h: "ok")

        websocket = AsyncMock()
        websocket.app = app
        websocket.path_params = {"session_id": session.id}
        websocket.headers = {"sec-websocket-protocol": "token-abc"}
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_text = AsyncMock()
        websocket.receive = AsyncMock()
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()

        await voice_websocket(websocket)

        websocket.accept.assert_awaited()
        assert websocket.accept.await_args.kwargs.get("subprotocol") is None

        sent = [
            json.loads(call.args[0]) for call in websocket.send_text.await_args_list
        ]
        assert any(
            item.get("type") == "state" and item.get("state") == "listening"
            for item in sent
        )
        assert any(
            item.get("type") == "state" and item.get("state") == "ended"
            for item in sent
        )
    finally:
        module.app_settings.voice.session_auth_required = original_required
        module.app_settings.voice.session_timeout = original_timeout
        module.app_settings.voice.enabled = original_enabled
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts


@pytest.mark.asyncio
async def test_voice_websocket_accepts_before_receiving_in_band_token(
    monkeypatch, mock_pipecat_modules
):
    pipeline_builder = __import__(
        "bindu.extensions.voice.pipeline_builder", fromlist=["build_voice_pipeline"]
    )

    dummy_bridge = MagicMock()
    dummy_bridge.cleanup_background_tasks = AsyncMock()
    dummy_bridge.process_transcription = AsyncMock(return_value="ok")

    def fake_build_voice_pipeline(**_kwargs):
        return {"stt": object(), "tts": object(), "bridge": dummy_bridge, "vad": None}

    monkeypatch.setattr(
        pipeline_builder, "build_voice_pipeline", fake_build_voice_pipeline
    )

    from bindu.server.endpoints import voice_endpoints as module

    original_required = module.app_settings.voice.session_auth_required
    original_timeout = module.app_settings.voice.session_timeout
    original_enabled = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    try:
        module.app_settings.voice.session_auth_required = True
        module.app_settings.voice.session_timeout = 300
        module.app_settings.voice.enabled = True
        module.app_settings.voice.stt_api_key = (
            "unit-test-stt-token"  # pragma: allowlist secret
        )
        module.app_settings.voice.tts_api_key = (
            "unit-test-tts-token"  # pragma: allowlist secret
        )

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session(
            "ctx",
            session_token="token-abc",  # noqa: S106
            session_token_expires_at=1e12,
        )

        app = MagicMock()
        app._voice_session_manager = manager
        app._voice_ext = MagicMock(allow_interruptions=True)
        app.manifest = MagicMock(run=lambda _h: "ok")

        accepted = False

        websocket = AsyncMock()
        websocket.app = app
        websocket.path_params = {"session_id": session.id}
        websocket.headers = {}
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_text = AsyncMock()

        async def accept(*_args, **_kwargs):
            nonlocal accepted
            accepted = True

        async def receive_text():
            assert accepted is True
            return "token-abc"

        websocket.receive = AsyncMock(
            side_effect=lambda: {"type": "websocket.disconnect", "code": 1000}
        )
        websocket.receive_text = AsyncMock(side_effect=receive_text)
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock(side_effect=accept)

        await voice_websocket(websocket)

        websocket.accept.assert_awaited()
        websocket.receive_text.assert_awaited()
        assert websocket.accept.await_count == 1
    finally:
        module.app_settings.voice.session_auth_required = original_required
        module.app_settings.voice.session_timeout = original_timeout
        module.app_settings.voice.enabled = original_enabled
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_pipecat_modules", [0.05], indirect=True)
async def test_voice_websocket_times_out_and_sends_error(
    monkeypatch, mock_pipecat_modules
):
    pipeline_builder = __import__(
        "bindu.extensions.voice.pipeline_builder", fromlist=["build_voice_pipeline"]
    )
    dummy_bridge = MagicMock()
    dummy_bridge.cleanup_background_tasks = AsyncMock()
    dummy_bridge.process_transcription = AsyncMock(return_value="ok")

    def fake_build_voice_pipeline(**_kwargs):
        return {"stt": object(), "tts": object(), "bridge": dummy_bridge, "vad": None}

    monkeypatch.setattr(
        pipeline_builder, "build_voice_pipeline", fake_build_voice_pipeline
    )

    from bindu.server.endpoints import voice_endpoints as module

    original_required = module.app_settings.voice.session_auth_required
    original_timeout = module.app_settings.voice.session_timeout
    original_enabled = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    try:
        module.app_settings.voice.session_auth_required = False
        module.app_settings.voice.session_timeout = 0.01
        module.app_settings.voice.enabled = True
        module.app_settings.voice.stt_api_key = (
            "unit-test-stt-token"  # pragma: allowlist secret
        )
        module.app_settings.voice.tts_api_key = (
            "unit-test-tts-token"  # pragma: allowlist secret
        )

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session("ctx")

        app = MagicMock()
        app._voice_session_manager = manager
        app._voice_ext = MagicMock(allow_interruptions=True)
        app.manifest = MagicMock(run=lambda _h: "ok")

        websocket = AsyncMock()
        websocket.app = app
        websocket.path_params = {"session_id": session.id}
        websocket.headers = {}
        websocket.client = MagicMock()
        websocket.client.host = "127.0.0.1"
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_text = AsyncMock()
        websocket.receive = AsyncMock(
            return_value={"type": "websocket.disconnect", "code": 1000}
        )
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()

        await voice_websocket(websocket)

        sent = [
            json.loads(call.args[0]) for call in websocket.send_text.await_args_list
        ]
        assert any(
            item.get("type") == "error" and "timed out" in item.get("message", "")
            for item in sent
        )
    finally:
        module.app_settings.voice.session_auth_required = original_required
        module.app_settings.voice.session_timeout = original_timeout
        module.app_settings.voice.enabled = original_enabled
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts


@pytest.mark.asyncio
async def test_voice_websocket_ends_session_when_pipeline_build_fails(
    monkeypatch, mock_pipecat_modules
):
    pipeline_builder = __import__(
        "bindu.extensions.voice.pipeline_builder", fromlist=["build_voice_pipeline"]
    )

    def fake_build_voice_pipeline(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        pipeline_builder, "build_voice_pipeline", fake_build_voice_pipeline
    )

    from bindu.server.endpoints import voice_endpoints as module

    original_required = module.app_settings.voice.session_auth_required
    original_timeout = module.app_settings.voice.session_timeout
    original_enabled = module.app_settings.voice.enabled
    original_stt = module.app_settings.voice.stt_api_key
    original_tts = module.app_settings.voice.tts_api_key
    try:
        module.app_settings.voice.session_auth_required = False
        module.app_settings.voice.session_timeout = 300
        module.app_settings.voice.enabled = True
        module.app_settings.voice.stt_api_key = (
            "unit-test-stt-token"  # pragma: allowlist secret
        )
        module.app_settings.voice.tts_api_key = (
            "unit-test-tts-token"  # pragma: allowlist secret
        )

        manager = VoiceSessionManager(max_sessions=5, session_timeout=300)
        session = await manager.create_session("ctx")

        app = MagicMock()
        app._voice_session_manager = manager
        app._voice_ext = MagicMock(allow_interruptions=True)
        app.manifest = MagicMock(run=lambda _h: "ok")

        websocket = AsyncMock()
        websocket.app = app
        websocket.path_params = {"session_id": session.id}
        websocket.headers = {}
        websocket.client = None
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_text = AsyncMock()
        websocket.receive = AsyncMock()
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()

        await voice_websocket(websocket)

        assert await manager.get_session(session.id) is None
    finally:
        module.app_settings.voice.session_auth_required = original_required
        module.app_settings.voice.session_timeout = original_timeout
        module.app_settings.voice.enabled = original_enabled
        module.app_settings.voice.stt_api_key = original_stt
        module.app_settings.voice.tts_api_key = original_tts
