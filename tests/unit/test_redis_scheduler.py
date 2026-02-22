"""Unit tests for RedisScheduler."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis_lib

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
        assert scheduler.poll_timeout == 1

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        scheduler = RedisScheduler(
            redis_url="redis://custom:6380/1",
            queue_name="custom:queue",
            max_connections=20,
            retry_on_timeout=False,
            poll_timeout=60,
        )
        assert scheduler.redis_url == "redis://custom:6380/1"
        assert scheduler.queue_name == "custom:queue"
        assert scheduler.max_connections == 20
        assert scheduler.retry_on_timeout is False
        assert scheduler.poll_timeout == 60


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
        """Test task operation serialization."""

        scheduler = RedisScheduler(redis_url=redis_url)

        # Create a mock span with proper span context
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.span_id = 0x0123456789ABCDEF
        mock_span_context.trace_id = 0x0123456789ABCDEF0123456789ABCDEF
        mock_span.get_span_context.return_value = mock_span_context

        task_op = {
            "operation": "run",
            "params": {"task_id": "test-123", "context_id": "ctx-456"},
            "_current_span": mock_span,
        }

        serialized = scheduler._serialize_task_operation(task_op)
        data = json.loads(serialized)

        assert data["operation"] == "run"
        assert data["params"]["task_id"] == "test-123"
        assert "span_id" in data
        assert "trace_id" in data

    def test_deserialize_task_operation_run(self, redis_url):
        """Test deserialization of run task operation."""
        scheduler = RedisScheduler(redis_url=redis_url)

        serialized = json.dumps(
            {
                "operation": "run",
                "params": {
                    "task_id": "test-123",
                    "context_id": "ctx-456",
                    "messages": [],
                },
                "span_id": "0123456789abcdef",
                "trace_id": "0123456789abcdef0123456789abcdef",
            }
        )

        task_op = scheduler._deserialize_task_operation(serialized)

        assert task_op["operation"] == "run"
        assert task_op["params"]["task_id"] == "test-123"

    def test_deserialize_task_operation_cancel(self, redis_url):
        """Test deserialization of cancel task operation."""
        scheduler = RedisScheduler(redis_url=redis_url)

        serialized = json.dumps(
            {
                "operation": "cancel",
                "params": {"task_id": "test-123"},
                "span_id": None,
                "trace_id": None,
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
                "span_id": None,
                "trace_id": None,
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


class TestRedisSchedulerBackoff:
    """Test exponential backoff behavior in receive_task_operations."""

    def test_init_stores_backoff_settings(self):
        """Test that backoff parameters are stored on init."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=0.5,
            error_backoff_max=60.0,
        )
        assert scheduler.error_backoff_base == 0.5
        assert scheduler.error_backoff_max == 60.0
        assert scheduler._consecutive_errors == 0

    def test_init_default_backoff_settings(self):
        """Test default backoff parameters."""
        scheduler = RedisScheduler(redis_url="redis://localhost:6379/0")
        assert scheduler.error_backoff_base == 0.1
        assert scheduler.error_backoff_max == 30.0

    def test_compute_backoff_delay_first_error(self):
        """Test backoff delay after first error (base * 2^0 = base)."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=1.0,
            error_backoff_max=30.0,
        )
        scheduler._consecutive_errors = 1

        with patch("bindu.server.scheduler.redis_scheduler.random.uniform", return_value=0):
            delay = scheduler._compute_backoff_delay()
        assert delay == 1.0  # base * 2^0 = 1.0, jitter=0

    def test_compute_backoff_delay_exponential_growth(self):
        """Test that backoff delay grows exponentially."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=1.0,
            error_backoff_max=120.0,
        )

        delays = []
        for i in range(1, 6):
            scheduler._consecutive_errors = i
            with patch("bindu.server.scheduler.redis_scheduler.random.uniform", return_value=0):
                delays.append(scheduler._compute_backoff_delay())

        # Expected: 1, 2, 4, 8, 16 (base * 2^(n-1))
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]

    def test_compute_backoff_delay_capped_at_max(self):
        """Test that backoff delay is capped at error_backoff_max."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=1.0,
            error_backoff_max=5.0,
        )
        scheduler._consecutive_errors = 10  # Would be 512 uncapped

        with patch("bindu.server.scheduler.redis_scheduler.random.uniform", return_value=0):
            delay = scheduler._compute_backoff_delay()
        assert delay == 5.0

    def test_compute_backoff_delay_includes_jitter(self):
        """Test that jitter is added to backoff delay."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=1.0,
            error_backoff_max=30.0,
        )
        scheduler._consecutive_errors = 1

        # jitter is uniform(0, delay * 0.25) = uniform(0, 0.25)
        with patch("bindu.server.scheduler.redis_scheduler.random.uniform", return_value=0.2):
            delay = scheduler._compute_backoff_delay()
        assert delay == 1.2  # 1.0 + 0.2

    @pytest.mark.asyncio
    async def test_receive_backoff_on_redis_error(self, mock_redis_client):
        """Test that Redis errors trigger backoff sleep."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=0.5,
            error_backoff_max=10.0,
        )
        scheduler._redis_client = mock_redis_client

        call_count = 0

        async def blpop_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise redis_lib.RedisError("Connection lost")
            raise asyncio.CancelledError()  # Stop the loop

        mock_redis_client.blpop.side_effect = blpop_side_effect

        with patch("bindu.server.scheduler.redis_scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(asyncio.CancelledError):
                async for _ in scheduler.receive_task_operations():
                    pass

        # Should have slept 3 times with increasing delays
        assert mock_sleep.call_count == 3
        assert scheduler._consecutive_errors == 3

        # Verify delays are increasing
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays[0] < delays[1] < delays[2]

    @pytest.mark.asyncio
    async def test_receive_resets_error_count_on_success(self, mock_redis_client):
        """Test that consecutive error counter resets after successful poll."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=0.5,
            error_backoff_max=10.0,
        )
        scheduler._redis_client = mock_redis_client
        scheduler._consecutive_errors = 5  # Simulate prior errors

        call_count = 0

        async def blpop_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # Successful poll (no task)
            raise asyncio.CancelledError()

        mock_redis_client.blpop.side_effect = blpop_side_effect

        with pytest.raises(asyncio.CancelledError):
            async for _ in scheduler.receive_task_operations():
                pass

        assert scheduler._consecutive_errors == 0

    @pytest.mark.asyncio
    async def test_receive_no_backoff_on_json_decode_error(self, mock_redis_client):
        """Test that JSON decode errors do not trigger backoff."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=0.5,
            error_backoff_max=10.0,
        )
        scheduler._redis_client = mock_redis_client

        call_count = 0

        async def blpop_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ("queue", "not-valid-json{{{")
            raise asyncio.CancelledError()

        mock_redis_client.blpop.side_effect = blpop_side_effect

        with patch("bindu.server.scheduler.redis_scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(asyncio.CancelledError):
                async for _ in scheduler.receive_task_operations():
                    pass

        mock_sleep.assert_not_called()
        assert scheduler._consecutive_errors == 0


class TestRedisSchedulerHealthStatus:
    """Test structured health reporting via get_health_status()."""

    @pytest.mark.asyncio
    async def test_healthy_status(self, mock_redis_client):
        """Test health status when Redis is connected and no errors."""
        scheduler = RedisScheduler(redis_url="redis://localhost:6379/0")
        scheduler._redis_client = mock_redis_client
        mock_redis_client.ping.return_value = True

        status = await scheduler.get_health_status()

        assert status["healthy"] is True
        assert status["consecutive_errors"] == 0
        assert status["backoff_active"] is False
        assert status["current_backoff_delay"] is None
        assert status["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_degraded_status_with_errors(self, mock_redis_client):
        """Test health status reflects degradation after consecutive errors."""
        scheduler = RedisScheduler(
            redis_url="redis://localhost:6379/0",
            error_backoff_base=1.0,
            error_backoff_max=30.0,
        )
        scheduler._redis_client = mock_redis_client
        scheduler._consecutive_errors = 5
        mock_redis_client.ping.return_value = True

        status = await scheduler.get_health_status()

        assert status["healthy"] is True  # ping still works
        assert status["consecutive_errors"] == 5
        assert status["backoff_active"] is True
        assert status["current_backoff_delay"] is not None
        assert status["current_backoff_delay"] > 0
        assert status["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_degraded_status_ping_fails(self, mock_redis_client):
        """Test health status when ping fails."""
        scheduler = RedisScheduler(redis_url="redis://localhost:6379/0")
        scheduler._redis_client = mock_redis_client
        mock_redis_client.ping.side_effect = Exception("Connection refused")

        status = await scheduler.get_health_status()

        assert status["healthy"] is False
        assert status["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_unavailable_status_no_client(self):
        """Test health status when client is not initialized."""
        scheduler = RedisScheduler(redis_url="redis://localhost:6379/0")
        # _redis_client is None by default

        status = await scheduler.get_health_status()

        assert status["healthy"] is False
        assert status["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_status_transitions(self, mock_redis_client):
        """Test that status transitions match error count thresholds."""
        scheduler = RedisScheduler(redis_url="redis://localhost:6379/0")
        scheduler._redis_client = mock_redis_client
        mock_redis_client.ping.return_value = True

        # Healthy: 0 errors
        status = await scheduler.get_health_status()
        assert status["status"] == "healthy"

        # Still healthy: 4 errors (below threshold)
        scheduler._consecutive_errors = 4
        status = await scheduler.get_health_status()
        assert status["status"] == "healthy"
        assert status["backoff_active"] is True

        # Degraded: 5 errors (at threshold)
        scheduler._consecutive_errors = 5
        status = await scheduler.get_health_status()
        assert status["status"] == "degraded"

        # Recovery: reset errors
        scheduler._consecutive_errors = 0
        status = await scheduler.get_health_status()
        assert status["status"] == "healthy"
        assert status["backoff_active"] is False
