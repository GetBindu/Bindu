"""Unit tests for RedisScheduler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.server.scheduler.redis_scheduler import RedisScheduler


@pytest.fixture
def redis_url():
    """Redis URL for testing."""
    return "redis://localhost:6379/0"


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.ping = AsyncMock()
    client.rpush = AsyncMock()
    client.blpop = AsyncMock()
    client.llen = AsyncMock(return_value=0)
    client.delete = AsyncMock(return_value=0)
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def scheduler(redis_url, mock_redis_client):
    """Create a RedisScheduler instance with mocked Redis client."""
    with patch("redis.asyncio.from_url", return_value=mock_redis_client):
        sched = RedisScheduler(redis_url=redis_url)
        # Manually set the client to bypass async context manager
        sched._redis_client = mock_redis_client
        return sched


class TestRedisSchedulerInit:
    """Test RedisScheduler initialization."""

    def test_init_with_defaults(self, redis_url):
        """Test initialization with default parameters."""
        scheduler = RedisScheduler(redis_url=redis_url)
        assert scheduler.redis_url == redis_url
        assert scheduler.queue_name == "bindu:tasks"
        assert scheduler.max_connections == 10
        assert scheduler.retry_on_timeout is True

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        scheduler = RedisScheduler(
            redis_url="redis://custom:6380/1",
            queue_name="custom:queue",
            max_connections=20,
            retry_on_timeout=False,
        )
        assert scheduler.redis_url == "redis://custom:6380/1"
        assert scheduler.queue_name == "custom:queue"
        assert scheduler.max_connections == 20
        assert scheduler.retry_on_timeout is False


class TestRedisSchedulerConnection:
    """Test RedisScheduler connection management."""

    @pytest.mark.asyncio
    async def test_context_manager_success(self, redis_url, mock_redis_client):
        """Test successful context manager entry and exit."""
        with patch("redis.asyncio.from_url", return_value=mock_redis_client):
            scheduler = RedisScheduler(redis_url=redis_url)

            async with scheduler:
                assert scheduler._redis_client is not None
                mock_redis_client.ping.assert_called_once()

            # After exit, client should be closed
            mock_redis_client.aclose.assert_called_once()
            assert scheduler._redis_client is None

    @pytest.mark.asyncio
    async def test_context_manager_connection_failure(self, redis_url):
        """Test context manager with connection failure."""
        import redis.asyncio as redis_lib

        mock_client = AsyncMock()
        mock_client.ping.side_effect = redis_lib.RedisError("Connection failed")

        with patch("redis.asyncio.from_url", return_value=mock_client):
            scheduler = RedisScheduler(redis_url=redis_url)

            with pytest.raises(ConnectionError, match="Unable to connect to Redis"):
                await scheduler.__aenter__()


class TestRedisSchedulerTaskOperations:
    """Test RedisScheduler task operations."""

    @pytest.mark.asyncio
    async def test_run_task(self, scheduler, mock_redis_client):
        """Test scheduling a run task."""
        params = TaskSendParams(
            task_id="test-task-123",
            context_id="test-context-456",
            messages=[{"role": "user", "content": "test"}],
        )

        await scheduler.run_task(params)

        # Verify rpush was called
        mock_redis_client.rpush.assert_called_once()
        call_args = mock_redis_client.rpush.call_args
        assert call_args[0][0] == "bindu:tasks"

        # Verify serialized data
        serialized = call_args[0][1]
        data = json.loads(serialized)
        assert data["operation"] == "run"
        assert data["params"]["task_id"] == "test-task-123"

    @pytest.mark.asyncio
    async def test_cancel_task(self, scheduler, mock_redis_client):
        """Test scheduling a cancel task."""
        params = TaskIdParams(task_id="test-task-123")

        await scheduler.cancel_task(params)

        mock_redis_client.rpush.assert_called_once()
        call_args = mock_redis_client.rpush.call_args
        serialized = call_args[0][1]
        data = json.loads(serialized)
        assert data["operation"] == "cancel"
        assert data["params"]["task_id"] == "test-task-123"

    @pytest.mark.asyncio
    async def test_pause_task(self, scheduler, mock_redis_client):
        """Test scheduling a pause task."""
        params = TaskIdParams(task_id="test-task-123")

        await scheduler.pause_task(params)

        mock_redis_client.rpush.assert_called_once()
        call_args = mock_redis_client.rpush.call_args
        serialized = call_args[0][1]
        data = json.loads(serialized)
        assert data["operation"] == "pause"

    @pytest.mark.asyncio
    async def test_resume_task(self, scheduler, mock_redis_client):
        """Test scheduling a resume task."""
        params = TaskIdParams(task_id="test-task-123")

        await scheduler.resume_task(params)

        mock_redis_client.rpush.assert_called_once()
        call_args = mock_redis_client.rpush.call_args
        serialized = call_args[0][1]
        data = json.loads(serialized)
        assert data["operation"] == "resume"


class TestRedisSchedulerSerialization:
    """Test RedisScheduler serialization and deserialization."""

    def test_serialize_task_operation(self, redis_url):
        """Test task operation serialization includes W3C trace_context."""
        scheduler = RedisScheduler(redis_url=redis_url)

        task_op = {
            "operation": "run",
            "params": {"task_id": "test-123", "context_id": "ctx-456"},
            "_current_span": MagicMock(),
        }

        serialized = scheduler._serialize_task_operation(task_op)
        data = json.loads(serialized)

        assert data["operation"] == "run"
        assert data["params"]["task_id"] == "test-123"
    # Step 3: span_id/trace_id replaced by W3C traceparent carrier
        assert "trace_context" in data
        assert isinstance(data["trace_context"], dict)
        assert "span_id" not in data
        assert "trace_id" not in data

    def test_deserialize_task_operation_run(self, redis_url):
        """Test deserialization of run task operation with trace_context."""
        scheduler = RedisScheduler(redis_url=redis_url)

        serialized = json.dumps(
            {
                "operation": "run",
                "params": {
                    "task_id": "test-123",
                    "context_id": "ctx-456",
                    "messages": [],
                },
                "trace_context": {}, 
            }
        )

        task_op = scheduler._deserialize_task_operation(serialized)

        assert task_op["operation"] == "run"
        assert task_op["params"]["task_id"] == "test-123"
        assert "_current_span" in task_op

    def test_deserialize_task_operation_cancel(self, redis_url):
        """Test deserialization of cancel task operation."""
        scheduler = RedisScheduler(redis_url=redis_url)

        serialized = json.dumps(
            {
                "operation": "cancel",
                "params": {"task_id": "test-123"},
                "trace_context": {},
            }
        )

        task_op = scheduler._deserialize_task_operation(serialized)

        assert task_op["operation"] == "cancel"
        assert task_op["params"]["task_id"] == "test-123"

    def test_deserialize_unknown_operation(self, redis_url):
        """Test deserialization with unknown operation type."""
        scheduler = RedisScheduler(redis_url=redis_url)

        serialized = json.dumps(
            {
                "operation": "unknown",
                "params": {},
                "trace_context": {},
            }
        )

        with pytest.raises(ValueError, match="Unknown operation type"):
            scheduler._deserialize_task_operation(serialized)


class TestRedisSchedulerUtilities:
    """Test RedisScheduler utility methods."""

    @pytest.mark.asyncio
    async def test_get_queue_length(self, scheduler, mock_redis_client):
        """Test getting queue length."""
        mock_redis_client.llen.return_value = 5

        length = await scheduler.get_queue_length()

        assert length == 5
        mock_redis_client.llen.assert_called_once_with("bindu:tasks")

    @pytest.mark.asyncio
    async def test_clear_queue(self, scheduler, mock_redis_client):
        """Test clearing the queue."""
        mock_redis_client.delete.return_value = 3

        removed = await scheduler.clear_queue()

        assert removed == 3
        mock_redis_client.delete.assert_called_once_with("bindu:tasks")

    @pytest.mark.asyncio
    async def test_health_check_success(self, scheduler, mock_redis_client):
        """Test successful health check."""
        mock_redis_client.ping.return_value = True

        is_healthy = await scheduler.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, scheduler, mock_redis_client):
        """Test failed health check."""
        mock_redis_client.ping.side_effect = Exception("Connection lost")

        is_healthy = await scheduler.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_no_client(self, redis_url):
        """Test health check with no client initialized."""
        scheduler = RedisScheduler(redis_url=redis_url)

        is_healthy = await scheduler.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_receive_task_operations_backs_off_on_redis_error(
        self, redis_url, mock_redis_client
        ):
        """Test that receive_task_operations backs off on RedisError (Step 1)."""
        import redis.asyncio as redis_lib

        call_count = [0]

        async def blpop_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise redis_lib.RedisError("Simulated Redis failure")
            return ("bindu:tasks", json.dumps({
                "operation": "run",
                "params": {"task_id": "test-backoff"},
                "trace_context": {},
            }))

        mock_redis_client.blpop.side_effect = blpop_side_effect

        scheduler = RedisScheduler(redis_url=redis_url)
        scheduler._redis_client = mock_redis_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            async for task in scheduler.receive_task_operations():
                assert task["operation"] == "run"
                break

        # sleep called twice — once for each RedisError before success
        assert mock_sleep.call_count == 2
    # backoff doubled: first 2.0s, then 4.0s
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [2.0, 4.0]