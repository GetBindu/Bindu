"""Minimal tests for in-memory scheduler."""

import asyncio
import pytest
from uuid import uuid4

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler


class TestInMemoryScheduler:
    """Test in-memory scheduler functionality."""

    @pytest.mark.asyncio
    async def test_scheduler_context_manager(self):
        """Test scheduler can be used as async context manager."""
        scheduler = InMemoryScheduler()

        async with scheduler:
            assert hasattr(scheduler, "_write_stream")
            assert hasattr(scheduler, "_read_stream")

    @pytest.mark.asyncio
    async def test_run_task(self):
        """Test scheduling a task for execution."""
        scheduler = InMemoryScheduler()

        async with scheduler:
            task_params = {
                "task_id": str(uuid4()),
                "context_id": str(uuid4()),
                "messages": [],
            }

            await scheduler.run_task(task_params)  # type: ignore[arg-type]

            # Verify task was queued
            operation = await scheduler._read_stream.receive()
            assert operation["operation"] == "run"
            assert operation["params"]["task_id"] == task_params["task_id"]

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test canceling a task."""
        scheduler = InMemoryScheduler()

        async with scheduler:
            task_id = str(uuid4())
            params = {"task_id": task_id}

            await scheduler.cancel_task(params)  # type: ignore[arg-type]

            operation = await scheduler._read_stream.receive()
            assert operation["operation"] == "cancel"
            assert operation["params"]["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_pause_task(self):
        """Test pausing a task."""
        scheduler = InMemoryScheduler()

        async with scheduler:
            task_id = str(uuid4())
            params = {"task_id": task_id}

            await scheduler.pause_task(params)  # type: ignore[arg-type]

            operation = await scheduler._read_stream.receive()
            assert operation["operation"] == "pause"
            assert operation["params"]["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_resume_task(self):
        """Test resuming a task."""
        scheduler = InMemoryScheduler()

        async with scheduler:
            task_id = str(uuid4())
            params = {"task_id": task_id}

            await scheduler.resume_task(params)  # type: ignore[arg-type]

            operation = await scheduler._read_stream.receive()
            assert operation["operation"] == "resume"
            assert operation["params"]["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_receive_task_operations(self):
        """Test receiving task operations from scheduler."""
        scheduler = InMemoryScheduler()

        async with scheduler:
            task_id = uuid4()
            context_id = uuid4()
            params = {"task_id": str(task_id)}

            await scheduler.run_task(
                {"task_id": task_id, "context_id": context_id, "message": {}}  # type: ignore[typeddict-item]
            )
            await scheduler.cancel_task(params)  # type: ignore[arg-type]

            operations = []
            async for operation in scheduler.receive_task_operations():
                operations.append(operation)
                if len(operations) == 2:
                    break

            assert len(operations) == 2
            assert operations[0]["operation"] == "run"
            assert operations[1]["operation"] == "cancel"

    @pytest.mark.asyncio
    async def test_send_operation_waits_for_capacity(self, monkeypatch):
        scheduler = InMemoryScheduler()

        async with scheduler:
            release_send = asyncio.Event()
            first_send_started = asyncio.Event()
            second_send_started = asyncio.Event()
            send_call_count = 0

            async def fake_send(_task_op):
                nonlocal send_call_count
                send_call_count += 1
                if send_call_count == 1:
                    first_send_started.set()
                elif send_call_count == 2:
                    second_send_started.set()
                await release_send.wait()

            monkeypatch.setattr(scheduler._write_stream, "send", fake_send)

            first_run = asyncio.create_task(
                scheduler.run_task(  # type: ignore[arg-type]
                    {
                        "task_id": uuid4(),
                        "context_id": uuid4(),
                    }
                )
            )
            await asyncio.wait_for(first_send_started.wait(), timeout=1.0)

            second_run = asyncio.create_task(
                scheduler.run_task(  # type: ignore[arg-type]
                    {
                        "task_id": uuid4(),
                        "context_id": uuid4(),
                    }
                )
            )
            await asyncio.wait_for(second_send_started.wait(), timeout=1.0)

            assert first_run.done() is False
            assert second_run.done() is False

            release_send.set()
            await asyncio.gather(first_run, second_run)

            assert send_call_count == 2
