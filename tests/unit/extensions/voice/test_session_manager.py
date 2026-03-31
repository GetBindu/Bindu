"""Unit tests for VoiceSessionManager."""

import asyncio
import time

import pytest

from bindu.extensions.voice.session_manager import VoiceSession, VoiceSessionManager


class TestVoiceSession:
    """Test VoiceSession dataclass."""

    def test_session_creation(self):
        session = VoiceSession(id="abc123", context_id="ctx-1")
        assert session.id == "abc123"
        assert session.context_id == "ctx-1"
        assert session.task_id is None
        assert session.state == "connecting"

    def test_duration_seconds(self):
        session = VoiceSession(id="s1", context_id="c1")
        # duration should be >=0 immediately
        assert session.duration_seconds >= 0

    def test_duration_uses_epoch_time(self):
        session = VoiceSession(id="s1", context_id="c1", start_time=time.time() - 5)
        assert 4 <= session.duration_seconds <= 6

    def test_from_dict_uses_epoch_start_time(self):
        session = VoiceSession.from_dict(
            {
                "id": "abc123",
                "context_id": "ctx-1",
                "start_time": time.time() - 3,
                "state": "active",
            }
        )
        assert 2 <= session.duration_seconds <= 4
        assert session.state == "active"


class TestVoiceSessionManager:
    """Test VoiceSessionManager lifecycle."""

    @pytest.fixture
    def manager(self):
        return VoiceSessionManager(max_sessions=3, session_timeout=60)

    @pytest.mark.asyncio
    async def test_create_session(self, manager):
        session = await manager.create_session("ctx-1")
        assert session.context_id == "ctx-1"
        assert session.state == "connecting"
        assert manager.active_count == 1

    @pytest.mark.asyncio
    async def test_get_session(self, manager):
        session = await manager.create_session("ctx-1")
        found = await manager.get_session(session.id)
        assert found is session

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, manager):
        found = await manager.get_session("nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_end_session(self, manager):
        session = await manager.create_session("ctx-1")
        await manager.end_session(session.id)
        found = await manager.get_session(session.id)
        assert found is None
        assert manager.active_count == 0

    @pytest.mark.asyncio
    async def test_end_nonexistent_session(self, manager):
        # Should not raise
        await manager.end_session("nonexistent")

    @pytest.mark.asyncio
    async def test_max_sessions_enforced(self, manager):
        await manager.create_session("c1")
        await manager.create_session("c2")
        await manager.create_session("c3")
        with pytest.raises(RuntimeError, match="Maximum concurrent"):
            await manager.create_session("c4")

    @pytest.mark.asyncio
    async def test_ended_sessions_pruned_on_create(self, manager):
        s1 = await manager.create_session("c1")
        await manager.create_session("c2")
        await manager.create_session("c3")
        # End one to free a slot
        await manager.end_session(s1.id)
        # Now we should be able to create another
        s4 = await manager.create_session("c4")
        assert s4 is not None

    @pytest.mark.asyncio
    async def test_update_state(self, manager):
        session = await manager.create_session("ctx-1")
        await manager.update_state(session.id, "active")
        found = await manager.get_session(session.id)
        assert found.state == "active"

    @pytest.mark.asyncio
    async def test_cleanup_loop_starts_and_stops(self, manager):
        await manager.start_cleanup_loop()
        assert manager._cleanup_task is not None
        await manager.stop_cleanup_loop()
        assert manager._cleanup_task is None

    @pytest.mark.asyncio
    async def test_timeout_expiration(self):
        """Test that sessions exceeding timeout are expired."""
        manager = VoiceSessionManager(max_sessions=5, session_timeout=0)
        session = await manager.create_session("ctx-1")
        # Wait a tiny bit so duration > 0 (which > timeout of 0)
        await asyncio.sleep(0.01)
        await manager._expire_timed_out_sessions()
        found = await manager.get_session(session.id)
        assert found is None
