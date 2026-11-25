"""Concurrent task execution and real cancellation (worker dispatch).

Pins the fix for the 2026-11-25 serialization incident: the worker's
single consumer loop awaited every task operation to completion, so one
stalled provider call queued every later task (and even the cancel that
targeted it) behind itself.

Contract pinned here:
- Runs in DIFFERENT contexts overlap (up to max_concurrent_tasks).
- Runs in the SAME context never overlap and execute in arrival order.
- One task's exception neither cancels siblings nor kills the loop.
- The concurrency cap is honoured.
- tasks/cancel interrupts a mid-flight run promptly — without queueing
  behind it — and the abandoned handler never completes.
- A task canceled while still queued is skipped (stays canceled, never
  flips to failed).
- Worker shutdown does not strand an in-flight task in 'working'.
"""

import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from unittest.mock import Mock
from uuid import UUID, uuid4

import anyio
import pytest
import pytest_asyncio

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.workers.manifest_worker import ManifestWorker

WAIT = 5  # seconds; every blocking wait in these tests is bounded


@pytest_asyncio.fixture(params=["memory", "redis"])
async def scheduler(request):
    """Both scheduler backends hand operations to the same worker contract.

    The redis leg runs only when BINDU_TEST_REDIS_URL points at a live
    Redis (CI service container or local docker); it covers the JSON
    round-trip where params come back deserialized and _current_span is
    absent from the operation dict.
    """
    if request.param == "memory":
        async with InMemoryScheduler() as sched:
            yield sched
        return

    redis_url = os.environ.get("BINDU_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("BINDU_TEST_REDIS_URL not set; redis scheduler leg skipped")
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    sched = RedisScheduler(redis_url=redis_url, queue_name=f"bindu:test:{uuid4()}")
    async with sched:
        yield sched


class ScriptedManifest:
    """Manifest stub whose handler awaits a per-task script.

    ManifestWorker treats ``run()``'s async-generator result like a real
    provider call: the ``await`` inside the generator is where a stalled
    model call would sit, and where cancellation must land.
    """

    def __init__(self) -> None:
        self.name = "concurrency-stub"
        self.enable_system_message = False
        self.enable_context_based_history = False
        self.did_extension = Mock()
        self.did_extension.did = "did:bindu:concurrency-stub"
        self.scripts: dict[str, Callable[[], Awaitable[object]]] = {}

    def run(self, message_history: list) -> object:
        label = message_history[-1]["parts"][0]["text"]
        script = self.scripts[label]

        async def _gen():
            yield await script()

        return _gen()


async def submit(storage, context_id: UUID, label: str) -> UUID:
    """Create a submitted task whose first message carries ``label``."""
    task_id = uuid4()
    message = {
        "role": "user",
        "kind": "message",
        "message_id": uuid4(),
        "task_id": task_id,
        "context_id": context_id,
        "parts": [{"kind": "text", "text": label}],
    }
    await storage.submit_task(context_id, message)
    return task_id


@asynccontextmanager
async def running_worker(scheduler, storage, manifest, cap: int):
    worker = ManifestWorker(
        manifest=manifest,  # type: ignore[arg-type]
        scheduler=scheduler,
        storage=storage,
        max_concurrent_tasks=cap,
    )
    async with worker.run():
        yield worker


async def wait_for_state(storage, task_id: UUID, state: str, timeout: float = WAIT):
    with anyio.fail_after(timeout):
        while True:
            task = await storage.load_task(task_id)
            if task and task["status"]["state"] == state:
                return task
            await anyio.sleep(0.01)


class Gate:
    """started/release event pair standing in for one provider call."""

    def __init__(self) -> None:
        self.started = anyio.Event()
        self.release = anyio.Event()
        self.completed = False

    def script(self, result: str = "done"):
        async def _run():
            self.started.set()
            await self.release.wait()
            self.completed = True
            return result

        return _run


class TestConcurrentExecution:
    """Phase 1: fan-out across contexts, strict serial within one."""

    @pytest.mark.asyncio
    async def test_different_contexts_overlap(self, scheduler, memory_storage):
        """Two runs in different contexts execute at the same time.

        The 2026-11-25 signature was strictly end-to-start execution with
        5-11 ms gaps; here both tasks must be mid-flight simultaneously.
        """
        manifest = ScriptedManifest()
        gates = {"a": Gate(), "b": Gate()}
        manifest.scripts = {k: g.script(f"done-{k}") for k, g in gates.items()}

        task_a = await submit(memory_storage, uuid4(), "a")
        task_b = await submit(memory_storage, uuid4(), "b")

        async with running_worker(scheduler, memory_storage, manifest, cap=2):
            await scheduler.run_task({"task_id": task_a, "context_id": uuid4()})
            await scheduler.run_task({"task_id": task_b, "context_id": uuid4()})

            # Both handlers are started while NEITHER has been released:
            # the executions overlap, which the serial loop could never do.
            with anyio.fail_after(WAIT):
                await gates["a"].started.wait()
                await gates["b"].started.wait()

            gates["a"].release.set()
            gates["b"].release.set()
            await wait_for_state(memory_storage, task_a, "completed")
            await wait_for_state(memory_storage, task_b, "completed")

    @pytest.mark.asyncio
    async def test_same_context_serial_in_arrival_order(
        self, scheduler, memory_storage
    ):
        """Same-context runs never overlap and run in arrival order.

        Context-history agents (enable_context_based_history) read the
        pre-turn context history; overlapping same-context runs would read
        the same history and write over each other.
        """
        manifest = ScriptedManifest()
        context_id = uuid4()
        order: list[str] = []
        in_context = {"current": 0, "max": 0}

        def make_script(label: str):
            async def _run():
                order.append(label)
                in_context["current"] += 1
                in_context["max"] = max(in_context["max"], in_context["current"])
                await anyio.sleep(0.02)
                in_context["current"] -= 1
                return f"done-{label}"

            return _run

        labels = ["first", "second", "third"]
        manifest.scripts = {label: make_script(label) for label in labels}
        task_ids = [await submit(memory_storage, context_id, lb) for lb in labels]

        async with running_worker(scheduler, memory_storage, manifest, cap=4):
            for task_id in task_ids:
                await scheduler.run_task({"task_id": task_id, "context_id": context_id})
            for task_id in task_ids:
                await wait_for_state(memory_storage, task_id, "completed")

        assert order == labels, "same-context tasks must run in arrival order"
        assert in_context["max"] == 1, "same-context tasks must never overlap"

    @pytest.mark.asyncio
    async def test_failure_is_isolated_and_loop_survives(
        self, scheduler, memory_storage
    ):
        """One task raising marks only that task failed; siblings and the
        dispatch loop keep going."""
        manifest = ScriptedManifest()
        sibling = Gate()

        async def explode():
            raise RuntimeError("boom")

        after = Gate()
        after.release.set()  # completes as soon as it runs
        manifest.scripts = {
            "explode": explode,
            "sibling": sibling.script(),
            "after": after.script(),
        }

        task_sibling = await submit(memory_storage, uuid4(), "sibling")
        task_explode = await submit(memory_storage, uuid4(), "explode")
        task_after = await submit(memory_storage, uuid4(), "after")

        async with running_worker(scheduler, memory_storage, manifest, cap=3):
            await scheduler.run_task({"task_id": task_sibling, "context_id": uuid4()})
            with anyio.fail_after(WAIT):
                await sibling.started.wait()

            # Explodes while the sibling is mid-flight.
            await scheduler.run_task({"task_id": task_explode, "context_id": uuid4()})
            await wait_for_state(memory_storage, task_explode, "failed")

            # Sibling was not collateral damage.
            sibling.release.set()
            await wait_for_state(memory_storage, task_sibling, "completed")

            # The loop still serves new work after the failure.
            await scheduler.run_task({"task_id": task_after, "context_id": uuid4()})
            await wait_for_state(memory_storage, task_after, "completed")

    @pytest.mark.asyncio
    async def test_cap_is_honoured(self, scheduler, memory_storage):
        """With cap N, the N+1th concurrent arrival waits for a slot."""
        manifest = ScriptedManifest()
        gates = {"a": Gate(), "b": Gate(), "c": Gate()}
        manifest.scripts = {k: g.script() for k, g in gates.items()}
        task_ids = {k: await submit(memory_storage, uuid4(), k) for k in gates}

        async with running_worker(scheduler, memory_storage, manifest, cap=2):
            for key in ("a", "b", "c"):
                await scheduler.run_task(
                    {"task_id": task_ids[key], "context_id": uuid4()}
                )
            with anyio.fail_after(WAIT):
                await gates["a"].started.wait()
                await gates["b"].started.wait()

            await anyio.sleep(0.1)
            assert not gates["c"].started.is_set(), "cap=2 must hold back task #3"

            gates["a"].release.set()  # frees a slot
            with anyio.fail_after(WAIT):
                await gates["c"].started.wait()

            gates["b"].release.set()
            gates["c"].release.set()
            for task_id in task_ids.values():
                await wait_for_state(memory_storage, task_id, "completed")


class TestCancelActuallyCancels:
    """Phase 2: tasks/cancel interrupts the run instead of just flipping a row."""

    @pytest.mark.asyncio
    async def test_cancel_interrupts_mid_flight_run(self, scheduler, memory_storage):
        """cap=1 and a handler stalled forever: the cancel must still be
        processed promptly (it may not queue behind its own target), the
        task ends canceled, and the stalled handler is abandoned."""
        manifest = ScriptedManifest()
        stalled = Gate()  # release is never set: a hung provider call
        manifest.scripts = {"stalled": stalled.script()}
        task_id = await submit(memory_storage, uuid4(), "stalled")

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:
            await scheduler.run_task({"task_id": task_id, "context_id": uuid4()})
            with anyio.fail_after(WAIT):
                await stalled.started.wait()

            await scheduler.cancel_task({"task_id": task_id})
            await wait_for_state(memory_storage, task_id, "canceled")

            # The run was truly torn down, not left burning in the background.
            with anyio.fail_after(WAIT):
                while worker._in_flight_scopes:
                    await anyio.sleep(0.01)

            # Releasing now proves the handler was cancelled, not resumed.
            stalled.release.set()
            await anyio.sleep(0.05)
            assert not stalled.completed, "provider call must be abandoned"
            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_of_queued_task_skips_execution(
        self, scheduler, memory_storage
    ):
        """Canceling a task still waiting for a slot takes effect while an
        unrelated run is in flight; the canceled task never executes and
        never flips to failed."""
        manifest = ScriptedManifest()
        running = Gate()
        queued = Gate()
        manifest.scripts = {"running": running.script(), "queued": queued.script()}
        task_running = await submit(memory_storage, uuid4(), "running")
        task_queued = await submit(memory_storage, uuid4(), "queued")

        async with running_worker(scheduler, memory_storage, manifest, cap=1):
            await scheduler.run_task({"task_id": task_running, "context_id": uuid4()})
            with anyio.fail_after(WAIT):
                await running.started.wait()

            await scheduler.run_task({"task_id": task_queued, "context_id": uuid4()})
            # Cancel lands while the target is queued behind the cap —
            # and while another task is mid-flight.
            await scheduler.cancel_task({"task_id": task_queued})
            await wait_for_state(memory_storage, task_queued, "canceled")

            running.release.set()
            await wait_for_state(memory_storage, task_running, "completed")

            # The slot freed up; the canceled task must NOT have run, and
            # must stay canceled (not re-marked failed by state validation).
            await anyio.sleep(0.05)
            assert not queued.started.is_set(), "canceled task must never execute"
            task = await memory_storage.load_task(task_queued)
            assert task["status"]["state"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_via_api_sequence_interrupts_run(
        self, scheduler, memory_storage
    ):
        """The REAL tasks/cancel path: the API handler CAS-flips the task to
        'canceled' BEFORE signaling the scheduler (task_handlers.cancel_task).
        The worker must still interrupt the in-flight run even though the
        storage row already reads 'canceled' when the operation arrives."""
        manifest = ScriptedManifest()
        stalled = Gate()  # never released
        manifest.scripts = {"stalled": stalled.script()}
        task_id = await submit(memory_storage, uuid4(), "stalled")

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:
            await scheduler.run_task({"task_id": task_id, "context_id": uuid4()})
            with anyio.fail_after(WAIT):
                await stalled.started.wait()

            # Mirror task_handlers.cancel_task exactly: claim the transition,
            # then signal the scheduler.
            assert await memory_storage.update_task_state_if(
                task_id, from_state="working", to_state="canceled"
            )
            await scheduler.cancel_task({"task_id": task_id})

            # The run must be torn down despite the already-canceled row.
            with anyio.fail_after(WAIT):
                while worker._in_flight_scopes:
                    await anyio.sleep(0.01)

            stalled.release.set()
            await anyio.sleep(0.05)
            assert not stalled.completed, "provider call must be abandoned"
            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_of_terminal_task_is_noop(self, scheduler, memory_storage):
        """A2A: terminal tasks are immutable — cancel leaves completed alone."""
        manifest = ScriptedManifest()
        done = Gate()
        done.release.set()
        manifest.scripts = {"done": done.script()}
        task_id = await submit(memory_storage, uuid4(), "done")

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:
            await scheduler.run_task({"task_id": task_id, "context_id": uuid4()})
            await wait_for_state(memory_storage, task_id, "completed")

            await worker.cancel_task({"task_id": task_id})
            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_shutdown_does_not_strand_working_task(
        self, scheduler, memory_storage
    ):
        """Exiting worker.run() with a run in flight must not leave the
        storage row in 'working' forever."""
        manifest = ScriptedManifest()
        stalled = Gate()  # never released
        manifest.scripts = {"stalled": stalled.script()}
        task_id = await submit(memory_storage, uuid4(), "stalled")

        async with running_worker(scheduler, memory_storage, manifest, cap=1):
            await scheduler.run_task({"task_id": task_id, "context_id": uuid4()})
            with anyio.fail_after(WAIT):
                await stalled.started.wait()
            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "working"

        task = await memory_storage.load_task(task_id)
        assert task["status"]["state"] == "canceled"
        assert not stalled.completed
