"""Comprehensive tests for InMemoryStorage implementation."""

import pytest
from uuid import uuid4

from bindu.common.protocol.types import Message, Artifact, PushNotificationConfig
from bindu.server.storage.memory_storage import InMemoryStorage


@pytest.fixture
def storage():
    """Create a fresh InMemoryStorage instance for each test."""
    return InMemoryStorage()


@pytest.fixture
def sample_context_id():
    """Sample context UUID."""
    return uuid4()


@pytest.fixture
def sample_task_id():
    """Sample task UUID."""
    return uuid4()


@pytest.fixture
def sample_message(sample_task_id, sample_context_id):
    """Sample message for task submission."""
    from bindu.common.protocol.types import TextPart

    return Message(
        message_id=uuid4(),
        task_id=sample_task_id,
        context_id=sample_context_id,
        kind="message",
        role="user",
        parts=[TextPart(kind="text", text="Test message")],
    )


class TestTaskOperations:
    """Test task CRUD operations."""

    @pytest.mark.asyncio
    async def test_submit_new_task(self, storage, sample_context_id, sample_message):
        """Test creating a new task."""
        task = await storage.submit_task(sample_context_id, sample_message)

        assert task["id"] == sample_message["task_id"]
        assert task["context_id"] == sample_context_id
        assert task["kind"] == "task"
        assert task["status"]["state"] == "submitted"
        assert len(task["history"]) == 1
        assert task["history"][0] == sample_message

    @pytest.mark.asyncio
    async def test_submit_task_adds_to_context(
        self, storage, sample_context_id, sample_message
    ):
        """Test that submitting a task adds it to the context."""
        task_id = sample_message["task_id"]
        await storage.submit_task(sample_context_id, sample_message)

        assert sample_context_id in storage.contexts
        assert task_id in storage.contexts[sample_context_id]

    @pytest.mark.asyncio
    async def test_submit_task_with_string_task_id(self, storage, sample_context_id):
        """Test submitting task with string task_id (should convert to UUID)."""
        from bindu.common.protocol.types import TextPart

        task_id = uuid4()
        message = Message(
            message_id=uuid4(),
            task_id=str(task_id),  # type: ignore
            context_id=sample_context_id,
            kind="message",
            role="user",
            parts=[TextPart(kind="text", text="Test")],
        )

        task = await storage.submit_task(sample_context_id, message)
        assert task["id"] == task_id

    @pytest.mark.asyncio
    async def test_submit_task_normalizes_message_ids(
        self, storage, sample_context_id, sample_message
    ):
        """Test that message IDs are normalized to UUIDs."""
        message_id = uuid4()
        sample_message["message_id"] = str(message_id)

        task = await storage.submit_task(sample_context_id, sample_message)
        assert task["history"][0]["message_id"] == message_id

    @pytest.mark.asyncio
    async def test_submit_task_normalizes_reference_task_ids(
        self, storage, sample_context_id, sample_message
    ):
        """Test that reference_task_ids are normalized."""
        ref_id1, ref_id2 = uuid4(), uuid4()
        sample_message["reference_task_ids"] = [str(ref_id1), ref_id2]

        task = await storage.submit_task(sample_context_id, sample_message)
        assert task["history"][0]["reference_task_ids"] == [ref_id1, ref_id2]

    @pytest.mark.asyncio
    async def test_clear_context(self, storage, sample_context_id, sample_message):
        """Test clearing a context."""
        await storage.submit_task(sample_context_id, sample_message)

        await storage.clear_context(sample_context_id)

        contexts = await storage.list_contexts()
        assert sample_context_id not in contexts

    @pytest.mark.asyncio
    async def test_save_and_load_webhook_config(self, storage):
        """Test saving and loading webhook configuration."""
        task_id = uuid4()
        config = {
            "id": task_id,
            "url": "https://example.com/webhook",
            "token": "secret",
        }

        await storage.save_webhook_config(task_id, config)
        loaded = await storage.load_webhook_config(task_id)

        assert loaded == config

    @pytest.mark.asyncio
    async def test_delete_webhook_config(self, storage):
        """Test deleting webhook configuration."""
        task_id = uuid4()
        config = {"id": task_id, "url": "https://example.com/webhook"}

        await storage.save_webhook_config(task_id, config)
        await storage.delete_webhook_config(task_id)

        loaded = await storage.load_webhook_config(task_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_nonexistent_webhook_config(self, storage):
        """Test loading webhook config that doesn't exist."""
        task_id = uuid4()

        loaded = await storage.load_webhook_config(task_id)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook_config(self, storage):
        """Test deleting webhook config that doesn't exist."""
        task_id = uuid4()

        # Should not raise error
        await storage.delete_webhook_config(task_id)

    @pytest.mark.asyncio
    async def test_list_contexts_empty(self, storage):
        """Test listing contexts when none exist."""
        contexts = await storage.list_contexts()

        assert contexts == []

    @pytest.mark.asyncio
    async def test_continue_non_terminal_task(
        self, storage, sample_context_id, sample_message
    ):
        """Test continuing an existing non-terminal task."""
        from bindu.common.protocol.types import TextPart

        task = await storage.submit_task(sample_context_id, sample_message)
        await storage.update_task(task["id"], "working")

        new_message = Message(
            message_id=uuid4(),
            task_id=task["id"],
            context_id=sample_context_id,
            kind="message",
            role="user",
            parts=[TextPart(kind="text", text="Continue task")],
        )

        continued_task = await storage.submit_task(sample_context_id, new_message)

        assert continued_task["id"] == task["id"]
        assert len(continued_task["history"]) == 2
        assert continued_task["status"]["state"] == "submitted"

    @pytest.mark.asyncio
    async def test_submit_terminal_task_raises_error(
        self, storage, sample_context_id, sample_message
    ):
        """Test that continuing a terminal task raises ValueError."""
        from bindu.common.protocol.types import TextPart

        task = await storage.submit_task(sample_context_id, sample_message)
        await storage.update_task(task["id"], "completed")

        new_message = Message(
            message_id=uuid4(),
            task_id=task["id"],
            context_id=sample_context_id,
            kind="message",
            role="user",
            parts=[TextPart(kind="text", text="Try to continue")],
        )

        with pytest.raises(ValueError, match="terminal state"):
            await storage.submit_task(sample_context_id, new_message)

    @pytest.mark.asyncio
    async def test_load_task(self, storage, sample_context_id, sample_message):
        """Test loading an existing task."""
        submitted_task = await storage.submit_task(sample_context_id, sample_message)
        loaded_task = await storage.load_task(submitted_task["id"])

        assert loaded_task is not None
        assert loaded_task["id"] == submitted_task["id"]
        assert loaded_task["context_id"] == sample_context_id

    @pytest.mark.asyncio
    async def test_load_task_returns_deep_copy(
        self, storage, sample_context_id, sample_message
    ):
        """Test that load_task returns a deep copy to prevent mutations."""
        task = await storage.submit_task(sample_context_id, sample_message)
        loaded_task = await storage.load_task(task["id"])

        loaded_task["history"].append({"test": "mutation"})

        reloaded_task = await storage.load_task(task["id"])
        assert len(reloaded_task["history"]) == 1

    @pytest.mark.asyncio
    async def test_load_task_with_history_limit(
        self, storage, sample_context_id, sample_message
    ):
        """Test loading task with history length limit."""
        from bindu.common.protocol.types import TextPart

        task = await storage.submit_task(sample_context_id, sample_message)

        for i in range(5):
            msg = Message(
                message_id=uuid4(),
                task_id=task["id"],
                context_id=sample_context_id,
                kind="message",
                role="agent",
                parts=[TextPart(kind="text", text=f"Message {i}")],
            )
            await storage.update_task(task["id"], "working", new_messages=[msg])

        loaded_task = await storage.load_task(task["id"], history_length=3)
        assert len(loaded_task["history"]) == 3

    @pytest.mark.asyncio
    async def test_load_nonexistent_task(self, storage):
        """Test loading a task that doesn't exist."""
        result = await storage.load_task(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_task_state(self, storage, sample_context_id, sample_message):
        """Test updating task state."""
        task = await storage.submit_task(sample_context_id, sample_message)
        updated_task = await storage.update_task(task["id"], "working")

        assert updated_task["status"]["state"] == "working"
        assert "timestamp" in updated_task["status"]

    @pytest.mark.asyncio
    async def test_update_task_with_artifacts(
        self, storage, sample_context_id, sample_message
    ):
        """Test updating task with artifacts."""
        from bindu.common.protocol.types import TextPart

        task = await storage.submit_task(sample_context_id, sample_message)
        artifacts = [
            Artifact(
                artifact_id=uuid4(), parts=[TextPart(kind="text", text="Result 1")]
            ),
            Artifact(
                artifact_id=uuid4(), parts=[TextPart(kind="text", text="Result 2")]
            ),
        ]

        updated_task = await storage.update_task(
            task["id"], "completed", new_artifacts=artifacts
        )

        assert "artifacts" in updated_task
        assert len(updated_task["artifacts"]) == 2

    @pytest.mark.asyncio
    async def test_update_task_with_messages(
        self, storage, sample_context_id, sample_message
    ):
        """Test updating task with new messages."""
        from bindu.common.protocol.types import TextPart

        task = await storage.submit_task(sample_context_id, sample_message)
        new_messages = [
            Message(
                message_id=uuid4(),
                task_id=task["id"],
                context_id=sample_context_id,
                kind="message",
                role="agent",
                parts=[TextPart(kind="text", text="Response")],
            ),
        ]

        updated_task = await storage.update_task(
            task["id"], "working", new_messages=new_messages
        )

        assert len(updated_task["history"]) == 2
        assert updated_task["history"][1]["task_id"] == task["id"]
        assert updated_task["history"][1]["context_id"] == sample_context_id

    @pytest.mark.asyncio
    async def test_update_task_with_metadata(
        self, storage, sample_context_id, sample_message
    ):
        """Test updating task with metadata."""
        task = await storage.submit_task(sample_context_id, sample_message)
        metadata = {"key1": "value1", "key2": "value2"}

        updated_task = await storage.update_task(
            task["id"], "working", metadata=metadata
        )

        assert "metadata" in updated_task
        assert updated_task["metadata"]["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_update_task_merges_metadata(
        self, storage, sample_context_id, sample_message
    ):
        """Test that metadata updates are merged."""
        task = await storage.submit_task(sample_context_id, sample_message)
        await storage.update_task(task["id"], "working", metadata={"key1": "value1"})
        updated_task = await storage.update_task(
            task["id"], "working", metadata={"key2": "value2"}
        )

        assert updated_task["metadata"]["key1"] == "value1"
        assert updated_task["metadata"]["key2"] == "value2"

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_raises_error(self, storage):
        """Test updating a nonexistent task raises KeyError."""
        with pytest.raises(KeyError):
            await storage.update_task(uuid4(), "working")

    @pytest.mark.asyncio
    async def test_update_task_with_invalid_message_type_raises_error(
        self, storage, sample_context_id, sample_message
    ):
        """Test that invalid message type raises TypeError."""
        task = await storage.submit_task(sample_context_id, sample_message)

        with pytest.raises(TypeError, match="Message must be dict"):
            await storage.update_task(task["id"], "working", new_messages=["invalid"])

    @pytest.mark.asyncio
    async def test_list_tasks(self, storage, sample_context_id):
        """Test listing all tasks."""
        from bindu.common.protocol.types import TextPart

        task_ids = [uuid4() for _ in range(3)]
        for task_id in task_ids:
            msg = Message(
                message_id=uuid4(),
                task_id=task_id,
                context_id=sample_context_id,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text="Test")],
            )
            await storage.submit_task(sample_context_id, msg)

        tasks = await storage.list_tasks()
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_with_limit(self, storage, sample_context_id):
        """Test listing tasks with length limit."""
        from bindu.common.protocol.types import TextPart

        for i in range(5):
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=sample_context_id,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text=f"Test {i}")],
            )
            await storage.submit_task(sample_context_id, msg)

        tasks = await storage.list_tasks(length=3)
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_with_offset(self, storage, sample_context_id):
        """Test listing tasks with offset."""
        from bindu.common.protocol.types import TextPart

        for i in range(5):
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=sample_context_id,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text=f"Test {i}")],
            )
            await storage.submit_task(sample_context_id, msg)

        tasks = await storage.list_tasks(offset=2)
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_count_tasks(self, storage, sample_context_id):
        """Test counting all tasks."""
        from bindu.common.protocol.types import TextPart

        for i in range(3):
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=sample_context_id,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text=f"Test {i}")],
            )
            await storage.submit_task(sample_context_id, msg)

        count = await storage.count_tasks()
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_tasks_by_status(self, storage, sample_context_id):
        """Test counting tasks filtered by status."""
        from bindu.common.protocol.types import TextPart

        for i in range(5):
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=sample_context_id,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text=f"Test {i}")],
            )
            task = await storage.submit_task(sample_context_id, msg)
            if i < 2:
                await storage.update_task(task["id"], "completed")

        completed_count = await storage.count_tasks(status="completed")
        submitted_count = await storage.count_tasks(status="submitted")

        assert completed_count == 2
        assert submitted_count == 3

    @pytest.mark.asyncio
    async def test_list_tasks_by_context(self, storage):
        """Test listing tasks by context."""
        from bindu.common.protocol.types import TextPart

        context1, context2 = uuid4(), uuid4()

        for i in range(3):
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=context1,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text=f"Context1 {i}")],
            )
            await storage.submit_task(context1, msg)

        for i in range(2):
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=context2,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text=f"Context2 {i}")],
            )
            await storage.submit_task(context2, msg)

        context1_tasks = await storage.list_tasks_by_context(context1)
        context2_tasks = await storage.list_tasks_by_context(context2)

        assert len(context1_tasks) == 3
        assert len(context2_tasks) == 2


class TestContextOperations:
    """Test context operations."""

    @pytest.mark.asyncio
    async def test_load_context(self, storage, sample_context_id, sample_message):
        """Test loading context."""
        await storage.submit_task(sample_context_id, sample_message)
        context = await storage.load_context(sample_context_id)

        assert context is not None
        assert "task_ids" in context
        assert sample_message["task_id"] in context["task_ids"]

    @pytest.mark.asyncio
    async def test_load_nonexistent_context(self, storage):
        """Test loading a nonexistent context."""
        result = await storage.load_context(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_context(self, storage, sample_context_id):
        """Test updating context (backward compatibility)."""
        await storage.update_context(sample_context_id, {"key": "value"})

    @pytest.mark.asyncio
    async def test_append_to_contexts(self, storage, sample_context_id):
        """Test appending to contexts (deprecated but should not break)."""
        from bindu.common.protocol.types import TextPart

        messages = [
            Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=sample_context_id,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text="Test")],
            ),
        ]
        await storage.append_to_contexts(sample_context_id, messages)

    @pytest.mark.asyncio
    async def test_append_to_contexts_with_invalid_type_raises_error(
        self, storage, sample_context_id
    ):
        """Test that invalid messages type raises TypeError."""
        with pytest.raises(TypeError, match="messages must be list"):
            await storage.append_to_contexts(sample_context_id, "invalid")

    @pytest.mark.asyncio
    async def test_list_contexts(self, storage):
        """Test listing all contexts."""
        from bindu.common.protocol.types import TextPart

        contexts = [uuid4() for _ in range(3)]
        for ctx in contexts:
            msg = Message(
                message_id=uuid4(),
                task_id=uuid4(),
                context_id=ctx,
                kind="message",
                role="user",
                parts=[TextPart(kind="text", text="Test")],
            )
            await storage.submit_task(ctx, msg)

        context_list = await storage.list_contexts()
        assert len(context_list) == 3
        assert all("context_id" in c for c in context_list)
        assert all("task_count" in c for c in context_list)

    @pytest.mark.asyncio
    async def test_clear_context(self, storage, sample_context_id, sample_message):
        """Test clearing a context."""
        task = await storage.submit_task(sample_context_id, sample_message)
        await storage.store_task_feedback(task["id"], {"rating": 5})

        await storage.clear_context(sample_context_id)

        assert sample_context_id not in storage.contexts
        assert task["id"] not in storage.tasks
        assert task["id"] not in storage.task_feedback

    @pytest.mark.asyncio
    async def test_clear_nonexistent_context_raises_error(self, storage):
        """Test clearing a nonexistent context raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await storage.clear_context(uuid4())


class TestFeedbackOperations:
    """Test feedback operations."""

    @pytest.mark.asyncio
    async def test_store_task_feedback(
        self, storage, sample_context_id, sample_message
    ):
        """Test storing task feedback."""
        task = await storage.submit_task(sample_context_id, sample_message)
        feedback = {"rating": 5, "comment": "Great!"}

        await storage.store_task_feedback(task["id"], feedback)

        assert task["id"] in storage.task_feedback
        assert storage.task_feedback[task["id"]][0] == feedback

    @pytest.mark.asyncio
    async def test_store_multiple_feedback_entries(
        self, storage, sample_context_id, sample_message
    ):
        """Test storing multiple feedback entries for same task."""
        task = await storage.submit_task(sample_context_id, sample_message)

        await storage.store_task_feedback(task["id"], {"rating": 5})
        await storage.store_task_feedback(task["id"], {"rating": 4})

        feedback_list = await storage.get_task_feedback(task["id"])
        assert len(feedback_list) == 2

    @pytest.mark.asyncio
    async def test_store_feedback_with_invalid_type_raises_error(
        self, storage, sample_context_id, sample_message
    ):
        """Test that invalid feedback type raises TypeError."""
        task = await storage.submit_task(sample_context_id, sample_message)

        with pytest.raises(TypeError, match="feedback_data must be dict"):
            await storage.store_task_feedback(task["id"], "invalid")

    @pytest.mark.asyncio
    async def test_get_task_feedback(self, storage, sample_context_id, sample_message):
        """Test retrieving task feedback."""
        task = await storage.submit_task(sample_context_id, sample_message)
        feedback = {"rating": 5}
        await storage.store_task_feedback(task["id"], feedback)

        retrieved = await storage.get_task_feedback(task["id"])
        assert retrieved == [feedback]

    @pytest.mark.asyncio
    async def test_get_feedback_for_nonexistent_task(self, storage):
        """Test getting feedback for nonexistent task returns None."""
        result = await storage.get_task_feedback(uuid4())
        assert result is None


class TestWebhookOperations:
    """Test webhook configuration operations."""

    @pytest.mark.asyncio
    async def test_save_webhook_config(self, storage, sample_task_id):
        """Test saving webhook configuration."""
        config = PushNotificationConfig(id=uuid4(), url="https://example.com/webhook")

        await storage.save_webhook_config(sample_task_id, config)

        assert sample_task_id in storage._webhook_configs
        assert storage._webhook_configs[sample_task_id] == config

    @pytest.mark.asyncio
    async def test_load_webhook_config(self, storage, sample_task_id):
        """Test loading webhook configuration."""
        config = PushNotificationConfig(id=uuid4(), url="https://example.com/webhook")
        await storage.save_webhook_config(sample_task_id, config)

        loaded = await storage.load_webhook_config(sample_task_id)
        assert loaded == config

    @pytest.mark.asyncio
    async def test_load_nonexistent_webhook_config(self, storage):
        """Test loading nonexistent webhook config returns None."""
        result = await storage.load_webhook_config(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_webhook_config(self, storage, sample_task_id):
        """Test deleting webhook configuration."""
        config = PushNotificationConfig(id=uuid4(), url="https://example.com/webhook")
        await storage.save_webhook_config(sample_task_id, config)

        await storage.delete_webhook_config(sample_task_id)

        assert sample_task_id not in storage._webhook_configs

    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook_config(self, storage):
        """Test deleting nonexistent webhook config doesn't raise error."""
        await storage.delete_webhook_config(uuid4())

    @pytest.mark.asyncio
    async def test_load_all_webhook_configs(self, storage):
        """Test loading all webhook configurations."""
        configs = {
            uuid4(): PushNotificationConfig(
                id=uuid4(), url="https://example.com/webhook1"
            ),
            uuid4(): PushNotificationConfig(
                id=uuid4(), url="https://example.com/webhook2"
            ),
        }

        for task_id, config in configs.items():
            await storage.save_webhook_config(task_id, config)

        all_configs = await storage.load_all_webhook_configs()
        assert len(all_configs) == 2


class TestUtilityOperations:
    """Test utility operations."""

    @pytest.mark.asyncio
    async def test_clear_all(self, storage, sample_context_id, sample_message):
        """Test clearing all data."""
        task = await storage.submit_task(sample_context_id, sample_message)
        await storage.store_task_feedback(task["id"], {"rating": 5})
        await storage.save_webhook_config(
            task["id"], PushNotificationConfig(id=uuid4(), url="https://example.com")
        )

        await storage.clear_all()

        assert len(storage.tasks) == 0
        assert len(storage.contexts) == 0
        assert len(storage.task_feedback) == 0
        assert len(storage._webhook_configs) == 0

    @pytest.mark.asyncio
    async def test_close(self, storage, sample_context_id, sample_message):
        """Test closing storage clears all data."""
        await storage.submit_task(sample_context_id, sample_message)

        await storage.close()

        assert len(storage.tasks) == 0


class TestValidation:
    """Test input validation."""

    @pytest.mark.asyncio
    async def test_invalid_task_id_type_raises_error(self, storage):
        """Test that invalid task_id type raises TypeError."""
        with pytest.raises(TypeError):
            await storage.load_task("not-a-uuid")

    @pytest.mark.asyncio
    async def test_invalid_context_id_type_raises_error(self, storage):
        """Test that invalid context_id type raises TypeError."""
        with pytest.raises(TypeError):
            await storage.load_context("not-a-uuid")

    @pytest.mark.asyncio
    async def test_submit_task_with_invalid_task_id_raises_error(
        self, storage, sample_context_id
    ):
        """Test submitting task with invalid task_id raises TypeError."""
        from bindu.common.protocol.types import TextPart

        message = Message(
            message_id=uuid4(),
            task_id=12345,  # type: ignore
            context_id=sample_context_id,
            kind="message",
            role="user",
            parts=[TextPart(kind="text", text="Test")],
        )

        with pytest.raises(TypeError):
            await storage.submit_task(sample_context_id, message)
