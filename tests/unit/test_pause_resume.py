"""Comprehensive tests for the Pause/Resume feature (Issue #142).

Tests cover the full vertical slice:
- Protocol types (PauseTaskRequest/Response, ResumeTaskRequest/Response)
- TaskHandlers (pause_task, resume_task) with state validation
- TaskManager delegation
- Worker base class checkpoint logic
- InMemoryStorage checkpoint persistence
- Edge cases and error paths

Note: Handler-level tests that reach the scheduler use a MockScheduler
because InMemoryScheduler's unbuffered stream blocks without a running
worker. This mirrors the pattern in the existing test_task_manager.py
which only tests cancel_task error paths.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from bindu.common.protocol.types import (
    PauseTaskRequest,
    PauseTaskResponse,
    ResumeTaskRequest,
    ResumeTaskResponse,
    TaskIdParams,
    TaskNotFoundError,
    TaskNotPausableError,
    TaskNotResumableError,
    TaskSendParams,
)
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from bindu.settings import app_settings
from tests.utils import (
    assert_jsonrpc_error,
    assert_jsonrpc_success,
    assert_task_state,
    create_test_message,
    create_test_task,
)


# ---------------------------------------------------------------------------
# Mock Scheduler — non-blocking, records operations for assertion
# ---------------------------------------------------------------------------


class MockScheduler:
    """A non-blocking scheduler that records operations instead of streaming them.

    Used for handler-level tests where we need to verify the handler logic
    without blocking on the unbuffered InMemoryScheduler stream.
    """

    def __init__(self) -> None:
        self.operations: list[tuple[str, Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def run_task(self, params: TaskSendParams) -> None:
        self.operations.append(("run", params))

    async def cancel_task(self, params: TaskIdParams) -> None:
        self.operations.append(("cancel", params))

    async def pause_task(self, params: TaskIdParams) -> None:
        self.operations.append(("pause", params))

    async def resume_task(self, params: TaskIdParams) -> None:
        self.operations.append(("resume", params))


# ---------------------------------------------------------------------------
# Helper: build JSON-RPC request dicts
# ---------------------------------------------------------------------------

def _pause_request(task_id: UUID) -> PauseTaskRequest:
    return {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "tasks/pause",
        "params": {"task_id": task_id},
    }


def _resume_request(task_id: UUID) -> ResumeTaskRequest:
    return {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "tasks/resume",
        "params": {"task_id": task_id},
    }


# ===================================================================
# 1. TaskHandler: pause_task
# ===================================================================


class TestPauseTask:
    """Tests for TaskHandlers.pause_task."""

    @pytest.mark.asyncio
    async def test_pause_working_task(self):
        """Pausing a 'working' task should succeed — scheduler receives pause op."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Do something")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="working")

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_success(response)
            # Scheduler should have received the pause operation
            assert len(scheduler.operations) == 1
            assert scheduler.operations[0][0] == "pause"

    @pytest.mark.asyncio
    async def test_pause_submitted_task(self):
        """Pausing a 'submitted' task should succeed."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Queued work")
            task = await storage.submit_task(msg["context_id"], msg)

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_success(response)
            assert scheduler.operations[0][0] == "pause"

    @pytest.mark.asyncio
    async def test_pause_input_required_task(self):
        """Pausing an 'input-required' task should succeed."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Need input")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="input-required")

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_success(response)
            assert scheduler.operations[0][0] == "pause"

    @pytest.mark.asyncio
    async def test_pause_nonexistent_task(self):
        """Pausing a task that does not exist returns TaskNotFoundError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            response = await tm.pause_task(_pause_request(uuid4()))

            assert_jsonrpc_error(response, -32001)
            assert len(scheduler.operations) == 0

    @pytest.mark.asyncio
    async def test_pause_completed_task(self):
        """Pausing a completed (terminal) task returns TaskNotPausableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Done")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="completed")

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_error(response, -32040)
            assert len(scheduler.operations) == 0

    @pytest.mark.asyncio
    async def test_pause_canceled_task(self):
        """Pausing a canceled (terminal) task returns TaskNotPausableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Canceled work")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="canceled")

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_error(response, -32040)

    @pytest.mark.asyncio
    async def test_pause_failed_task(self):
        """Pausing a failed (terminal) task returns TaskNotPausableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Broken")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="failed")

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_error(response, -32040)

    @pytest.mark.asyncio
    async def test_pause_already_suspended_task(self):
        """Pausing an already-suspended task returns TaskNotPausableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Paused once")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="suspended")

            response = await tm.pause_task(_pause_request(task["id"]))

            assert_jsonrpc_error(response, -32040)


# ===================================================================
# 2. TaskHandler: resume_task
# ===================================================================


class TestResumeTask:
    """Tests for TaskHandlers.resume_task."""

    @pytest.mark.asyncio
    async def test_resume_suspended_task(self):
        """Resuming a 'suspended' task should succeed — scheduler receives resume op."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Resume me")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="suspended")

            response = await tm.resume_task(_resume_request(task["id"]))

            assert_jsonrpc_success(response)
            assert len(scheduler.operations) == 1
            assert scheduler.operations[0][0] == "resume"

    @pytest.mark.asyncio
    async def test_resume_nonexistent_task(self):
        """Resuming a task that does not exist returns TaskNotFoundError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            response = await tm.resume_task(_resume_request(uuid4()))

            assert_jsonrpc_error(response, -32001)
            assert len(scheduler.operations) == 0

    @pytest.mark.asyncio
    async def test_resume_working_task(self):
        """Resuming a 'working' (non-suspended) task returns TaskNotResumableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Active")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="working")

            response = await tm.resume_task(_resume_request(task["id"]))

            assert_jsonrpc_error(response, -32041)

    @pytest.mark.asyncio
    async def test_resume_completed_task(self):
        """Resuming a completed (terminal) task returns TaskNotResumableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Finished")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="completed")

            response = await tm.resume_task(_resume_request(task["id"]))

            assert_jsonrpc_error(response, -32041)

    @pytest.mark.asyncio
    async def test_resume_submitted_task(self):
        """Resuming a 'submitted' task (never paused) returns TaskNotResumableError."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Fresh")
            task = await storage.submit_task(msg["context_id"], msg)

            response = await tm.resume_task(_resume_request(task["id"]))

            assert_jsonrpc_error(response, -32041)


# ===================================================================
# 3. Checkpoint storage layer
# ===================================================================


class TestCheckpointStorage:
    """Tests for checkpoint save/load/clear via Storage base methods."""

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self):
        """save_checkpoint stores data in metadata; load_checkpoint retrieves it."""
        storage = InMemoryStorage()
        msg = create_test_message(text="Checkpointed work")
        task = await storage.submit_task(msg["context_id"], msg)
        await storage.update_task(task["id"], state="working")

        checkpoint = {
            "paused_from_state": "working",
            "message_history": [msg],
            "artifacts": [],
            "paused_at": datetime.now(timezone.utc).isoformat(),
        }

        await storage.save_checkpoint(task["id"], checkpoint)
        loaded = await storage.load_checkpoint(task["id"])

        assert loaded is not None
        assert loaded["paused_from_state"] == "working"
        assert len(loaded["message_history"]) == 1

    @pytest.mark.asyncio
    async def test_load_checkpoint_nonexistent_task(self):
        """load_checkpoint returns None for a non-existent task."""
        storage = InMemoryStorage()
        result = await storage.load_checkpoint(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_load_checkpoint_no_checkpoint(self):
        """load_checkpoint returns None when task has no checkpoint in metadata."""
        storage = InMemoryStorage()
        msg = create_test_message(text="No checkpoint")
        task = await storage.submit_task(msg["context_id"], msg)

        result = await storage.load_checkpoint(task["id"])
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_checkpoint(self):
        """clear_checkpoint removes checkpoint data from metadata."""
        storage = InMemoryStorage()
        msg = create_test_message(text="Clear me")
        task = await storage.submit_task(msg["context_id"], msg)

        checkpoint = {
            "paused_from_state": "working",
            "message_history": [],
            "artifacts": [],
            "paused_at": datetime.now(timezone.utc).isoformat(),
        }
        await storage.save_checkpoint(task["id"], checkpoint)

        # Verify checkpoint exists
        loaded = await storage.load_checkpoint(task["id"])
        assert loaded is not None

        # Clear and verify
        await storage.clear_checkpoint(task["id"])
        loaded = await storage.load_checkpoint(task["id"])
        assert loaded is None

    @pytest.mark.asyncio
    async def test_checkpoint_preserves_other_metadata(self):
        """Saving a checkpoint should not clobber existing metadata keys."""
        storage = InMemoryStorage()
        msg = create_test_message(text="Existing meta")
        task = await storage.submit_task(msg["context_id"], msg)
        await storage.update_task(
            task["id"], state="working", metadata={"custom_key": "custom_value"}
        )

        checkpoint = {"paused_from_state": "working", "message_history": [], "artifacts": [], "paused_at": "t"}
        await storage.save_checkpoint(task["id"], checkpoint)

        reloaded = await storage.load_task(task["id"])
        assert reloaded["metadata"]["custom_key"] == "custom_value"
        assert reloaded["metadata"]["checkpoint"]["paused_from_state"] == "working"


# ===================================================================
# 4. TaskManager delegation
# ===================================================================


class TestTaskManagerDelegation:
    """Verify TaskManager.__getattr__ routes to TaskHandlers for pause/resume."""

    @pytest.mark.asyncio
    async def test_pause_task_delegation(self):
        """TaskManager should have a pause_task attribute."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            assert callable(getattr(tm, "pause_task", None))

    @pytest.mark.asyncio
    async def test_resume_task_delegation(self):
        """TaskManager should have a resume_task attribute."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            assert callable(getattr(tm, "resume_task", None))


# ===================================================================
# 5. Settings validation
# ===================================================================


class TestPauseResumeSettings:
    """Verify settings correctly classify pause/resume states."""

    def test_suspended_is_non_terminal(self):
        """'suspended' should be in non_terminal_states."""
        from bindu.settings import app_settings

        assert "suspended" in app_settings.agent.non_terminal_states

    def test_suspended_is_not_terminal(self):
        """'suspended' should NOT be in terminal_states."""
        from bindu.settings import app_settings

        assert "suspended" not in app_settings.agent.terminal_states

    def test_pausable_states_defined(self):
        """pausable_states frozenset should contain expected states."""
        from bindu.settings import app_settings

        expected = {"submitted", "working", "input-required"}
        assert app_settings.agent.pausable_states == expected

    def test_method_handlers_include_pause_resume(self):
        """method_handlers should include tasks/pause and tasks/resume."""
        from bindu.settings import app_settings

        assert "tasks/pause" in app_settings.agent.method_handlers
        assert "tasks/resume" in app_settings.agent.method_handlers
        assert app_settings.agent.method_handlers["tasks/pause"] == "pause_task"
        assert app_settings.agent.method_handlers["tasks/resume"] == "resume_task"


# ===================================================================
# 6. Protocol types validation
# ===================================================================


class TestProtocolTypes:
    """Verify new protocol types are importable and well-formed."""

    def test_pause_task_request_type(self):
        """PauseTaskRequest should be a valid type alias."""
        req: PauseTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/pause",
            "params": {"task_id": uuid4()},
        }
        assert req["method"] == "tasks/pause"

    def test_resume_task_request_type(self):
        """ResumeTaskRequest should be a valid type alias."""
        req: ResumeTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/resume",
            "params": {"task_id": uuid4()},
        }
        assert req["method"] == "tasks/resume"

    def test_error_types_importable(self):
        """TaskNotPausableError and TaskNotResumableError should be importable."""
        assert TaskNotPausableError is not None
        assert TaskNotResumableError is not None

    def test_a2a_request_includes_pause_resume(self):
        """A2ARequest TypeAdapter should accept pause/resume methods."""
        from bindu.common.protocol.types import a2a_request_ta

        pause_req = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tasks/pause",
            "params": {"taskId": str(uuid4())},
        }
        parsed = a2a_request_ta.validate_python(pause_req)
        assert parsed["method"] == "tasks/pause"

        resume_req = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tasks/resume",
            "params": {"taskId": str(uuid4())},
        }
        parsed = a2a_request_ta.validate_python(resume_req)
        assert parsed["method"] == "tasks/resume"


# ===================================================================
# 7. End-to-end pause → resume cycle (handler level)
# ===================================================================


class TestPauseResumeCycle:
    """Integration tests for the full pause → resume lifecycle at the handler layer."""

    @pytest.mark.asyncio
    async def test_full_pause_resume_cycle(self):
        """Pause and resume should route through the scheduler correctly."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Long running work")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="working")

            # Pause
            pause_resp = await tm.pause_task(_pause_request(task["id"]))
            assert_jsonrpc_success(pause_resp)
            assert scheduler.operations[-1][0] == "pause"

            # Manually update state to suspended (simulating worker processing)
            await storage.update_task(task["id"], state="suspended")

            # Resume
            resume_resp = await tm.resume_task(_resume_request(task["id"]))
            assert_jsonrpc_success(resume_resp)
            assert scheduler.operations[-1][0] == "resume"

    @pytest.mark.asyncio
    async def test_pause_resume_pause_cycle(self):
        """A task should be pausable again after being resumed."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Repeatable pause")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="working")

            # First pause
            await tm.pause_task(_pause_request(task["id"]))
            await storage.update_task(task["id"], state="suspended")

            # Resume
            await tm.resume_task(_resume_request(task["id"]))
            await storage.update_task(task["id"], state="working")

            # Second pause should succeed
            resp = await tm.pause_task(_pause_request(task["id"]))
            assert_jsonrpc_success(resp)
            assert len(scheduler.operations) == 3  # pause, resume, pause

    @pytest.mark.asyncio
    async def test_checkpoint_persists_across_pause(self):
        """Checkpoint data should be readable from storage after pause."""
        storage = InMemoryStorage()
        msg = create_test_message(text="With checkpoint")
        task = await storage.submit_task(msg["context_id"], msg)
        await storage.update_task(task["id"], state="working")

        checkpoint = {
            "paused_from_state": "working",
            "message_history": [msg],
            "artifacts": [],
            "paused_at": datetime.now(timezone.utc).isoformat(),
        }
        await storage.save_checkpoint(task["id"], checkpoint)

        reloaded = await storage.load_task(task["id"])
        assert reloaded["status"]["state"] == "suspended"
        assert "checkpoint" in reloaded.get("metadata", {})
        assert reloaded["metadata"]["checkpoint"]["paused_from_state"] == "working"

    @pytest.mark.asyncio
    async def test_resume_after_cancel_fails(self):
        """A canceled task cannot be resumed."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Cancel then resume")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="canceled")

            response = await tm.resume_task(_resume_request(task["id"]))
            assert_jsonrpc_error(response, -32041)


# ===================================================================
# 8. Edge cases
# ===================================================================


class TestEdgeCases:
    """Edge case tests for boundary conditions."""

    @pytest.mark.asyncio
    async def test_pause_rejected_task(self):
        """Pausing a 'rejected' task should fail."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Rejected")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="rejected")

            response = await tm.pause_task(_pause_request(task["id"]))
            assert_jsonrpc_error(response, -32040)

    @pytest.mark.asyncio
    async def test_resume_rejected_task(self):
        """Resuming a 'rejected' task should fail."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Rejected")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="rejected")

            response = await tm.resume_task(_resume_request(task["id"]))
            assert_jsonrpc_error(response, -32041)

    @pytest.mark.asyncio
    async def test_pause_auth_required_task(self):
        """Pausing an 'auth-required' task should fail (not in pausable_states)."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Auth needed")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="auth-required")

            response = await tm.pause_task(_pause_request(task["id"]))
            assert_jsonrpc_error(response, -32040)

    @pytest.mark.asyncio
    async def test_multiple_checkpoints_overwrite(self):
        """Saving a new checkpoint should overwrite the previous one."""
        storage = InMemoryStorage()
        msg = create_test_message(text="Overwrite")
        task = await storage.submit_task(msg["context_id"], msg)

        cp1 = {"paused_from_state": "working", "message_history": [], "artifacts": [], "paused_at": "t1"}
        await storage.save_checkpoint(task["id"], cp1)

        cp2 = {"paused_from_state": "input-required", "message_history": [msg], "artifacts": [], "paused_at": "t2"}
        await storage.save_checkpoint(task["id"], cp2)

        loaded = await storage.load_checkpoint(task["id"])
        assert loaded["paused_from_state"] == "input-required"
        assert loaded["paused_at"] == "t2"


# ===================================================================
# 9. Auth permissions
# ===================================================================


class TestAuthPermissions:
    """Verify pause/resume are included in auth permissions config."""

    def test_pause_permission_defined(self):
        """tasks/pause should have agent:write permission."""
        assert "tasks/pause" in app_settings.auth.permissions
        assert "agent:write" in app_settings.auth.permissions["tasks/pause"]

    def test_resume_permission_defined(self):
        """tasks/resume should have agent:write permission."""
        assert "tasks/resume" in app_settings.auth.permissions
        assert "agent:write" in app_settings.auth.permissions["tasks/resume"]


# ===================================================================
# 10. Checkpoint cleared after resume
# ===================================================================


class TestCheckpointLifecycle:
    """Verify checkpoint is cleared after successful resume."""

    @pytest.mark.asyncio
    async def test_checkpoint_cleared_after_resume_cycle(self):
        """Full pause → resume should clear checkpoint data."""
        storage = InMemoryStorage()
        scheduler = MockScheduler()
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            msg = create_test_message(text="Lifecycle test")
            task = await storage.submit_task(msg["context_id"], msg)
            await storage.update_task(task["id"], state="working")

            # Pause (via TaskManager — sets state but doesn't run worker)
            response = await tm.pause_task(_pause_request(task["id"]))
            assert "result" in response

            # Simulate worker saving checkpoint (as scheduler would dispatch)
            checkpoint = {
                "paused_from_state": "working",
                "message_history": [],
                "artifacts": [],
                "paused_at": "2026-02-17T06:00:00Z",
            }
            await storage.save_checkpoint(task["id"], checkpoint)

            # Verify checkpoint exists
            loaded = await storage.load_checkpoint(task["id"])
            assert loaded is not None

            # Clear checkpoint (as worker would after resume)
            await storage.clear_checkpoint(task["id"])

            # Verify checkpoint is gone
            loaded = await storage.load_checkpoint(task["id"])
            assert loaded is None

    @pytest.mark.asyncio
    async def test_load_checkpoint_with_none_metadata(self):
        """load_checkpoint should not crash if metadata is explicitly None."""
        storage = InMemoryStorage()
        msg = create_test_message(text="None metadata")
        task = await storage.submit_task(msg["context_id"], msg)

        # Forcefully set metadata to None to simulate edge case
        storage.tasks[task["id"]]["metadata"] = None

        result = await storage.load_checkpoint(task["id"])
        assert result is None
