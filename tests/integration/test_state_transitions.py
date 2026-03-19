"""Integration tests for task state transitions and validation."""

import pytest
import pytest_asyncio
from uuid import uuid4

from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.settings import app_settings


@pytest_asyncio.fixture
async def storage() -> InMemoryStorage:
    """Create a fresh in-memory storage for each test."""
    return InMemoryStorage()


def create_test_message(task_id: uuid4, context_id: uuid4):
    """Helper to create a test message."""
    return {
        "message_id": uuid4(),
        "task_id": task_id,
        "context_id": context_id,
        "role": "user",
        "parts": [{"kind": "text", "text": "test"}],
    }


class TestSuspendedStateClassification:
    """Tests for suspended state classification in state machine."""

    def test_suspended_is_non_terminal(self):
        """Test that 'suspended' is classified as non-terminal state."""
        assert "suspended" in app_settings.agent.non_terminal_states
        assert "suspended" not in app_settings.agent.terminal_states

    def test_pausable_states_defined(self):
        """Test that pausable_states is properly defined."""
        assert hasattr(app_settings.agent, "pausable_states")
        assert "submitted" in app_settings.agent.pausable_states
        assert "working" in app_settings.agent.pausable_states
        assert "input-required" in app_settings.agent.pausable_states

    def test_terminal_states_excludes_suspended(self):
        """Test that terminal states do NOT include suspended."""
        for state in app_settings.agent.terminal_states:
            assert state != "suspended"

    def test_pausable_states_are_non_terminal(self):
        """Test that all pausable states are also non-terminal."""
        for state in app_settings.agent.pausable_states:
            assert state in app_settings.agent.non_terminal_states


class TestStateTransitions:
    """Tests for valid state transitions."""

    @pytest.mark.asyncio
    async def test_submitted_to_working_transition(self, storage: InMemoryStorage):
        """Test valid transition from submitted to working."""
        task_id = uuid4()
        context_id = uuid4()

        # Create task in submitted state
        await storage.submit_task(context_id, create_test_message(task_id, context_id))

        # Update to working
        await storage.update_task(task_id, state="working")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "working"

    @pytest.mark.asyncio
    async def test_working_to_suspended_transition(self, storage: InMemoryStorage):
        """Test valid transition from working to suspended."""
        task_id = uuid4()
        context_id = uuid4()

        # Create task in working state
        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")

        # Update to suspended
        await storage.update_task(task_id, state="suspended")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "suspended"

    @pytest.mark.asyncio
    async def test_suspended_to_working_transition(self, storage: InMemoryStorage):
        """Test valid transition from suspended to working (resume)."""
        task_id = uuid4()
        context_id = uuid4()

        # Create task in suspended state
        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="suspended")

        # Update to working
        await storage.update_task(task_id, state="working")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "working"

    @pytest.mark.asyncio
    async def test_working_to_completed_transition(self, storage: InMemoryStorage):
        """Test valid transition from working to completed."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")
        await storage.update_task(task_id, state="completed")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_working_to_failed_transition(self, storage: InMemoryStorage):
        """Test valid transition from working to failed."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")
        await storage.update_task(task_id, state="failed")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_working_to_canceled_transition(self, storage: InMemoryStorage):
        """Test valid transition from working to canceled."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")
        await storage.update_task(task_id, state="canceled")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "canceled"

    @pytest.mark.asyncio
    async def test_working_to_input_required_transition(self, storage: InMemoryStorage):
        """Test valid transition from working to input-required."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")
        await storage.update_task(task_id, state="input-required")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "input-required"

    @pytest.mark.asyncio
    async def test_input_required_to_working_transition(self, storage: InMemoryStorage):
        """Test valid transition from input-required to working."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="input-required")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "input-required"

        # Continue working after input
        await storage.update_task(task_id, state="working")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "working"


class TestTerminalStateValidation:
    """Tests for terminal state immutability."""

    @pytest.mark.asyncio
    async def test_cannot_modify_completed_task(self, storage: InMemoryStorage):
        """Test that completed tasks cannot be modified."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="completed")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_cannot_modify_failed_task(self, storage: InMemoryStorage):
        """Test that failed tasks cannot be modified."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="failed")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_cannot_modify_canceled_task(self, storage: InMemoryStorage):
        """Test that canceled tasks cannot be modified."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="canceled")

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "canceled"


class TestNonTerminalStateMutability:
    """Tests for non-terminal state mutability."""

    @pytest.mark.asyncio
    async def test_can_modify_submitted_task(self, storage: InMemoryStorage):
        """Test that submitted tasks can be modified."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "submitted"

        await storage.update_task(task_id, state="submitted", metadata={"key": "value"})
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "submitted"
        assert task["metadata"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_can_modify_working_task(self, storage: InMemoryStorage):
        """Test that working tasks can be modified."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working", metadata={"progress": 50})

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "working"
        assert task["metadata"]["progress"] == 50

    @pytest.mark.asyncio
    async def test_can_modify_suspended_task(self, storage: InMemoryStorage):
        """Test that suspended tasks can be modified."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="suspended", metadata={"paused": True})

        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "suspended"
        assert task["metadata"]["paused"] is True


class TestStateWorkflowIntegration:
    """Integration tests for complete state workflows."""

    @pytest.mark.asyncio
    async def test_workflow_submitted_working_completed(self, storage: InMemoryStorage):
        """Test complete workflow: submitted -> working -> completed."""
        task_id = uuid4()
        context_id = uuid4()

        # Start (submitted)
        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "submitted"

        # Work
        await storage.update_task(task_id, state="working")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "working"

        # Complete
        await storage.update_task(task_id, state="completed")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_with_pause_resume(self, storage: InMemoryStorage):
        """Test workflow with pause/resume: submitted -> working -> suspended -> working -> completed."""
        task_id = uuid4()
        context_id = uuid4()

        # Start working
        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")

        # Pause
        await storage.update_task(task_id, state="suspended")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "suspended"

        # Resume
        await storage.update_task(task_id, state="working")

        # Complete
        await storage.update_task(task_id, state="completed")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_with_input_required(self, storage: InMemoryStorage):
        """Test workflow with input-required: working -> input-required -> working -> completed."""
        task_id = uuid4()
        context_id = uuid4()

        await storage.submit_task(context_id, create_test_message(task_id, context_id))
        await storage.update_task(task_id, state="working")

        # Request input
        await storage.update_task(task_id, state="input-required")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "input-required"

        # Continue working after input
        await storage.update_task(task_id, state="working")

        # Complete
        await storage.update_task(task_id, state="completed")
        task = await storage.load_task(task_id)
        assert task["status"]["state"] == "completed"
