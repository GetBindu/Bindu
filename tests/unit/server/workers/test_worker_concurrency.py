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
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import anyio
import pytest
import pytest_asyncio

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
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


class FlakyReceiptStorage(InMemoryStorage):
    """Refuses exactly the upfront metadata-only receipt write.

    Matches the settle-time persist's call shape (state=None, no guard,
    metadata set); every guarded or state-changing write still works, so
    the recovery paths that re-attach the receipt can be observed.
    """

    async def update_task(
        self,
        task_id,
        state=None,
        new_artifacts=None,
        new_messages=None,
        metadata=None,
        expected_states=None,
    ):
        if state is None and expected_states is None and metadata:
            raise RuntimeError("receipt write refused")
        return await super().update_task(
            task_id,
            state=state,
            new_artifacts=new_artifacts,
            new_messages=new_messages,
            metadata=metadata,
            expected_states=expected_states,
        )


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


class TestTerminalWriteGuards:
    """Follow-up to the #619 review: worker writes must lose races against
    terminal transitions made by other writers, settled payments must keep
    their receipts when a run is interrupted, and graceful shutdown must
    hand un-started operations back to the scheduler.
    """

    @pytest.mark.asyncio
    async def test_delayed_cancel_signal_cannot_be_overwritten(
        self, scheduler, memory_storage
    ):
        """The API handler CAS-cancels mid-run but the worker's interrupt
        never arrives (delayed or misrouted scheduler delivery). The run
        finishes anyway — its late result must be discarded, never committed
        over 'canceled'."""
        manifest = ScriptedManifest()
        gate = Gate()
        after = Gate()
        after.release.set()
        manifest.scripts = {"race": gate.script("late-result"), "after": after.script()}
        ctx = uuid4()
        task_id = await submit(memory_storage, ctx, "race")
        task_after = await submit(memory_storage, uuid4(), "after")

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:
            await scheduler.run_task({"task_id": task_id, "context_id": ctx})
            with anyio.fail_after(WAIT):
                await gate.started.wait()

            # task_handlers.cancel_task's CAS — with NO scheduler signal
            # afterwards, simulating delivery that never reached this worker.
            assert await memory_storage.update_task_state_if(
                task_id, from_state="working", to_state="canceled"
            )
            gate.release.set()

            # The handler runs to completion; its write must be rejected.
            # Explicit checkpoint: wait until the worker has finished
            # processing the run (scope deregistered AFTER all writes), so
            # the assertion cannot race a still-pending late write.
            with anyio.fail_after(WAIT):
                while not gate.completed or worker._in_flight_scopes:
                    await anyio.sleep(0.01)

            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "canceled"
            assert not task.get("artifacts"), "late artifacts must be discarded"
            assert all(m.get("role") != "agent" for m in task.get("history", [])), (
                "late agent messages must be discarded"
            )

            # The discarded result did not wedge the loop.
            await scheduler.run_task({"task_id": task_after, "context_id": uuid4()})
            await wait_for_state(memory_storage, task_after, "completed")

    @pytest.mark.asyncio
    async def test_failure_after_cancel_stays_canceled(self, scheduler, memory_storage):
        """A handler that raises after a cancel already landed must not
        re-mark the canceled task as failed."""
        manifest = ScriptedManifest()
        gate = Gate()

        async def fail_after_release():
            gate.started.set()
            await gate.release.wait()
            raise RuntimeError("boom after cancel")

        manifest.scripts = {"failrace": fail_after_release}
        ctx = uuid4()
        task_id = await submit(memory_storage, ctx, "failrace")

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:
            await scheduler.run_task({"task_id": task_id, "context_id": ctx})
            with anyio.fail_after(WAIT):
                await gate.started.wait()

            assert await memory_storage.update_task_state_if(
                task_id, from_state="working", to_state="canceled"
            )
            gate.release.set()
            # Explicit checkpoint: the failure write has happened (or been
            # rejected) once the run deregisters its scope.
            with anyio.fail_after(WAIT):
                while worker._in_flight_scopes:
                    await anyio.sleep(0.01)

            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "canceled", (
                "failure path must not overwrite a terminal state"
            )

    @pytest.mark.asyncio
    async def test_cancel_mid_run_keeps_settlement_receipt(
        self, scheduler, memory_storage
    ):
        """settle-first + cancel: the receipt is persisted before the handler
        runs and re-tagged payment-orphaned when the run is interrupted, so
        a canceled-but-paid task stays reconcilable."""
        from bindu.settings import app_settings

        manifest = ScriptedManifest()
        stalled = Gate()  # never released: cancel interrupts it
        manifest.scripts = {"paid": stalled.script("paid-result")}
        ctx = uuid4()
        task_id = await submit(memory_storage, ctx, "paid")

        receipt = {
            app_settings.x402.meta_status_key: app_settings.x402.status_completed,
            "x402.payment.receipts": [{"transaction": "0xabc", "network": "base"}],
        }

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:

            async def fake_settle(payment_context):
                return dict(receipt)

            worker._settle_payment = fake_settle  # simulated successful settle

            await scheduler.run_task(
                {
                    "task_id": task_id,
                    "context_id": ctx,
                    "payment_context": {"simulated": True},
                }
            )
            with anyio.fail_after(WAIT):
                await stalled.started.wait()

            # Receipt was persisted BEFORE the handler ran (settle-time write).
            task = await memory_storage.load_task(task_id)
            metadata = task.get("metadata") or {}
            assert metadata.get("x402.payment.receipts"), (
                "receipt must be durable before execution"
            )

            # Real cancel sequence: API CAS, then the scheduler signal.
            assert await memory_storage.update_task_state_if(
                task_id, from_state="working", to_state="canceled"
            )
            await scheduler.cancel_task({"task_id": task_id})
            await wait_for_state(memory_storage, task_id, "canceled")

            # Interrupt re-tags the settled payment for reconciliation.
            with anyio.fail_after(WAIT):
                while True:
                    task = await memory_storage.load_task(task_id)
                    metadata = task.get("metadata") or {}
                    if (
                        metadata.get(app_settings.x402.meta_status_key)
                        == "payment-orphaned"
                    ):
                        break
                    await anyio.sleep(0.01)
            assert metadata["x402.payment.receipts"][0]["transaction"] == "0xabc"
            assert not stalled.completed

    @pytest.mark.asyncio
    async def test_cancel_during_settlement_tags_orphan_on_skip(
        self, scheduler, memory_storage
    ):
        """A cancel landing while settlement is in its shielded block makes
        the working guard skip the run — the settled payment must still be
        recorded as orphaned even though the handler never executed."""
        from bindu.settings import app_settings

        manifest = ScriptedManifest()
        never = Gate()  # must never start
        manifest.scripts = {"paidskip": never.script()}
        ctx = uuid4()
        task_id = await submit(memory_storage, ctx, "paidskip")

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:

            async def settle_and_lose_race(payment_context):
                # The API cancel CAS lands while settlement is in flight.
                await memory_storage.update_task_state_if(
                    task_id, from_state="submitted", to_state="canceled"
                )
                return {
                    app_settings.x402.meta_status_key: (
                        app_settings.x402.status_completed
                    ),
                    "x402.payment.receipts": [{"transaction": "0xskip"}],
                }

            worker._settle_payment = settle_and_lose_race

            await scheduler.run_task(
                {
                    "task_id": task_id,
                    "context_id": ctx,
                    "payment_context": {"simulated": True},
                }
            )

            with anyio.fail_after(WAIT):
                while True:
                    task = await memory_storage.load_task(task_id)
                    metadata = task.get("metadata") or {}
                    if (
                        metadata.get(app_settings.x402.meta_status_key)
                        == "payment-orphaned"
                    ):
                        break
                    await anyio.sleep(0.01)

            assert task["status"]["state"] == "canceled"
            assert metadata["x402.payment.receipts"][0]["transaction"] == "0xskip"
            assert not never.started.is_set(), "the run must be skipped entirely"

    @pytest.mark.asyncio
    async def test_discarded_paid_completion_tags_orphan(
        self, scheduler, memory_storage
    ):
        """Delayed-signal race on a PAID run: the API cancels in storage but
        the interrupt never arrives, the handler completes, and the guard
        discards the late result — the settled payment must then be
        recorded as orphaned (money moved, nothing delivered)."""
        from bindu.settings import app_settings

        manifest = ScriptedManifest()
        gate = Gate()
        manifest.scripts = {"paidrace": gate.script("late-paid-result")}
        ctx = uuid4()
        task_id = await submit(memory_storage, ctx, "paidrace")

        receipt = {
            app_settings.x402.meta_status_key: app_settings.x402.status_completed,
            "x402.payment.receipts": [{"transaction": "0xrace"}],
        }

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:

            async def fake_settle(payment_context):
                return dict(receipt)

            worker._settle_payment = fake_settle

            await scheduler.run_task(
                {
                    "task_id": task_id,
                    "context_id": ctx,
                    "payment_context": {"simulated": True},
                }
            )
            with anyio.fail_after(WAIT):
                await gate.started.wait()

            # API CAS with NO scheduler signal — the interrupt never lands.
            assert await memory_storage.update_task_state_if(
                task_id, from_state="working", to_state="canceled"
            )
            gate.release.set()

            with anyio.fail_after(WAIT):
                while not gate.completed or worker._in_flight_scopes:
                    await anyio.sleep(0.01)

            task = await memory_storage.load_task(task_id)
            assert task["status"]["state"] == "canceled"
            assert not task.get("artifacts"), "late artifacts must be discarded"
            metadata = task.get("metadata") or {}
            assert (
                metadata.get(app_settings.x402.meta_status_key) == "payment-orphaned"
            ), "a discarded paid completion must be recorded as orphaned"
            assert metadata["x402.payment.receipts"][0]["transaction"] == "0xrace"

    @pytest.mark.asyncio
    async def test_cancel_signal_during_shielded_settlement_tags_orphan(
        self, scheduler, memory_storage
    ):
        """The real cancel interrupt arrives while settlement sits in its
        shielded block: the shield defers it, the deferred cancellation
        lands at a post-settlement checkpoint, and the settled payment is
        still tagged orphaned with no deliverable committed."""
        from bindu.settings import app_settings

        manifest = ScriptedManifest()
        handler_gate = Gate()
        manifest.scripts = {"paidsig": handler_gate.script("never-delivered")}
        ctx = uuid4()
        task_id = await submit(memory_storage, ctx, "paidsig")

        settle_entered = anyio.Event()
        release_settle = anyio.Event()

        async with running_worker(scheduler, memory_storage, manifest, cap=1) as worker:

            async def blocking_settle(payment_context):
                settle_entered.set()
                # The cancel interrupt arrives while we sit here, shielded.
                await release_settle.wait()
                return {
                    app_settings.x402.meta_status_key: (
                        app_settings.x402.status_completed
                    ),
                    "x402.payment.receipts": [{"transaction": "0xsig"}],
                }

            worker._settle_payment = blocking_settle

            # Deliver the deferred cancellation AT the working write: every
            # update_task call passes a cancellable checkpoint first, so
            # the interrupt deferred by the settle shield lands inside the
            # expanded cancellation handler — not in the working guard's
            # skip branch, which could satisfy the assertions on its own.
            real_update = memory_storage.update_task

            async def checkpointing_update(*args, **kwargs):
                await anyio.sleep(0)  # cancellable checkpoint
                return await real_update(*args, **kwargs)

            memory_storage.update_task = checkpointing_update

            await scheduler.run_task(
                {
                    "task_id": task_id,
                    "context_id": ctx,
                    "payment_context": {"simulated": True},
                }
            )
            with anyio.fail_after(WAIT):
                await settle_entered.wait()

            # Real cancel path: wait for the scope interrupt itself (not
            # the storage state) before releasing settlement, so the orphan
            # tag demonstrably comes from the cancellation handler.
            await scheduler.cancel_task({"task_id": task_id})
            with anyio.fail_after(WAIT):
                while True:
                    scope = worker._in_flight_scopes.get(task_id)
                    if scope is not None and scope.cancel_called:
                        break
                    await anyio.sleep(0.01)
            release_settle.set()

            with anyio.fail_after(WAIT):
                while True:
                    task = await memory_storage.load_task(task_id)
                    metadata = task.get("metadata") or {}
                    if (
                        metadata.get(app_settings.x402.meta_status_key)
                        == "payment-orphaned"
                    ):
                        break
                    await anyio.sleep(0.01)

            assert task["status"]["state"] == "canceled"
            assert not task.get("artifacts"), "no deliverable may be committed"
            assert not handler_gate.started.is_set(), (
                "cancellation landed before the handler, so it must never start"
            )
            assert not handler_gate.completed, "the run must never complete"
            assert metadata["x402.payment.receipts"][0]["transaction"] == "0xsig"

    @pytest.mark.asyncio
    async def test_paid_run_survives_failed_upfront_receipt_write(self, scheduler):
        """The bounded settle-time persist is best-effort: when it fails,
        the paid run still executes (aborting would guarantee an orphan)
        and the completion write re-attaches the receipt."""
        from bindu.settings import app_settings

        storage = FlakyReceiptStorage()
        manifest = ScriptedManifest()
        done = Gate()
        done.release.set()
        manifest.scripts = {"paidflaky": done.script("delivered")}
        ctx = uuid4()
        task_id = await submit(storage, ctx, "paidflaky")

        receipt = {
            app_settings.x402.meta_status_key: app_settings.x402.status_completed,
            "x402.payment.receipts": [{"transaction": "0xflaky"}],
        }

        async with running_worker(scheduler, storage, manifest, cap=1) as worker:

            async def fake_settle(payment_context):
                return dict(receipt)

            worker._settle_payment = fake_settle

            await scheduler.run_task(
                {
                    "task_id": task_id,
                    "context_id": ctx,
                    "payment_context": {"simulated": True},
                }
            )
            task = await wait_for_state(storage, task_id, "completed")

        metadata = task.get("metadata") or {}
        assert (
            metadata.get(app_settings.x402.meta_status_key)
            == app_settings.x402.status_completed
        )
        assert metadata["x402.payment.receipts"][0]["transaction"] == "0xflaky"
        assert task.get("artifacts"), "the deliverable must be committed"

    @pytest.mark.asyncio
    async def test_intermediate_pause_reattaches_receipt(self, scheduler):
        """If the upfront receipt persist failed and the paid run pauses on
        input-required, the committed intermediate write re-attaches the
        receipt — it must not exist only in run_task's locals once the run
        returns."""
        from bindu.settings import app_settings

        storage = FlakyReceiptStorage()
        manifest = ScriptedManifest()

        async def pause_script():
            return {"state": "input-required", "prompt": "which year?"}

        manifest.scripts = {"paidpause": pause_script}
        ctx = uuid4()
        task_id = await submit(storage, ctx, "paidpause")

        receipt = {
            app_settings.x402.meta_status_key: app_settings.x402.status_completed,
            "x402.payment.receipts": [{"transaction": "0xpause"}],
        }

        async with running_worker(scheduler, storage, manifest, cap=1) as worker:

            async def fake_settle(payment_context):
                return dict(receipt)

            worker._settle_payment = fake_settle

            await scheduler.run_task(
                {
                    "task_id": task_id,
                    "context_id": ctx,
                    "payment_context": {"simulated": True},
                }
            )
            task = await wait_for_state(storage, task_id, "input-required")

        metadata = task.get("metadata") or {}
        assert (
            metadata.get(app_settings.x402.meta_status_key)
            == app_settings.x402.status_completed
        ), "the paused paid task must carry its settlement receipt"
        assert metadata["x402.payment.receipts"][0]["transaction"] == "0xpause"

    @pytest.mark.asyncio
    async def test_transient_error_before_handler_is_retried(self, scheduler):
        """A retryable infrastructure error on the working write must leave
        the task 'submitted' so the retry decorator can re-run it — not
        mark it failed, which would make the retry a no-op against the
        working guard."""
        from bindu.server.storage.memory_storage import InMemoryStorage

        class FlakyWorkingWriteStorage(InMemoryStorage):
            """First working transition raises a TRANSIENT_EXCEPTIONS error."""

            def __init__(self):
                super().__init__()
                self.working_write_attempts = 0

            async def update_task(
                self,
                task_id,
                state=None,
                new_artifacts=None,
                new_messages=None,
                metadata=None,
                expected_states=None,
            ):
                if state == "working":
                    self.working_write_attempts += 1
                    if self.working_write_attempts == 1:
                        raise ConnectionError("transient storage blip")
                return await super().update_task(
                    task_id,
                    state=state,
                    new_artifacts=new_artifacts,
                    new_messages=new_messages,
                    metadata=metadata,
                    expected_states=expected_states,
                )

        storage = FlakyWorkingWriteStorage()
        manifest = ScriptedManifest()
        done = Gate()
        done.release.set()
        manifest.scripts = {"retryme": done.script("recovered")}
        ctx = uuid4()
        task_id = await submit(storage, ctx, "retryme")

        async with running_worker(scheduler, storage, manifest, cap=1):
            await scheduler.run_task({"task_id": task_id, "context_id": ctx})
            # Generous timeout: the retry decorator backs off with jitter
            # before the second attempt. wait_for_state fails fast if the
            # task is wrongly marked 'failed'.
            task = await wait_for_state(storage, task_id, "completed", timeout=15)

        assert storage.working_write_attempts == 2, "the run must be retried"
        assert task["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_transient_history_error_is_retried(self, scheduler):
        """Transient failure AFTER the working write (history load): the
        working transition is stepped back to 'submitted' so the retry
        re-runs cleanly instead of dying on state validation."""
        storage = InMemoryStorage()
        manifest = ScriptedManifest()
        done = Gate()
        done.release.set()
        manifest.scripts = {"histretry": done.script("ok")}
        ctx = uuid4()
        task_id = await submit(storage, ctx, "histretry")

        async with running_worker(scheduler, storage, manifest, cap=1) as worker:
            real_build = worker._build_complete_message_history
            calls = {"n": 0}

            async def flaky_build(task):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise ConnectionError("transient read blip")
                return await real_build(task)

            worker._build_complete_message_history = flaky_build

            await scheduler.run_task({"task_id": task_id, "context_id": ctx})
            await wait_for_state(storage, task_id, "completed", timeout=15)

        assert calls["n"] == 2, "the run must be retried after the history error"

    @pytest.mark.asyncio
    async def test_shutdown_requeues_unstarted_task(self, scheduler, memory_storage):
        """Graceful shutdown: the running task is finalized as canceled, but a
        task still waiting on the concurrency gates goes back to the scheduler
        (eager dispatch consumed its operation) and a restarted worker runs it.
        """
        if not getattr(scheduler, "requeue_survives_shutdown", False):
            pytest.skip("requeue applies to durable schedulers; memory cancels")

        class SchedulerSpy:
            """Counts run sends so the requeue is asserted, not assumed."""

            def __init__(self, inner):
                self.inner = inner
                self.run_sends = 0

            async def run_task(self, params):
                self.run_sends += 1
                await self.inner.run_task(params)

            def __getattr__(self, name):
                return getattr(self.inner, name)

        spy = SchedulerSpy(scheduler)
        manifest = ScriptedManifest()
        g_running, g_queued = Gate(), Gate()
        manifest.scripts = {
            "running": g_running.script(),
            "queued": g_queued.script(),
        }
        ctx1, ctx2 = uuid4(), uuid4()
        t_running = await submit(memory_storage, ctx1, "running")
        t_queued = await submit(memory_storage, ctx2, "queued")

        async with running_worker(spy, memory_storage, manifest, cap=1) as worker:
            await spy.run_task({"task_id": t_running, "context_id": ctx1})
            await spy.run_task({"task_id": t_queued, "context_id": ctx2})
            with anyio.fail_after(WAIT):
                await g_running.started.wait()
            # Explicit checkpoint: the queued operation has been consumed by
            # eager dispatch once its context guard registers — it is then
            # parked on the semaphore and must be requeued at shutdown.
            with anyio.fail_after(WAIT):
                while str(ctx2) not in worker._context_lock_refs:
                    await anyio.sleep(0.01)

        assert spy.run_sends == 3, "shutdown must requeue the un-started run"
        assert (await memory_storage.load_task(t_running))["status"][
            "state"
        ] == "canceled"
        assert (await memory_storage.load_task(t_queued))["status"][
            "state"
        ] == "submitted", "an un-started task must stay submitted, not canceled"

        # A restarted worker picks the requeued operation up and completes it.
        g_queued.release.set()
        async with running_worker(spy, memory_storage, manifest, cap=1):
            await wait_for_state(memory_storage, t_queued, "completed")


class TestGuardFallbackBranches:
    """Direct-call coverage of the guard-failure branches: what each write
    path does when another writer already made the task terminal."""

    @staticmethod
    def make_worker(memory_storage, scheduler=None):
        return ManifestWorker(
            manifest=Mock(),  # type: ignore[arg-type]
            scheduler=scheduler or Mock(),
            storage=memory_storage,
        )

    @pytest.mark.asyncio
    async def test_requeue_failure_leaves_task_submitted(self, memory_storage):
        """Durable scheduler whose requeue send fails at shutdown: the task
        stays 'submitted' (recoverable by re-enqueue) rather than being
        canceled — canceling is final, submitted is not."""

        class RefusingDurableScheduler:
            requeue_survives_shutdown = True

            async def run_task(self, params):
                raise RuntimeError("broker unreachable")

        worker = self.make_worker(memory_storage, scheduler=RefusingDurableScheduler())
        task_id = await submit(memory_storage, uuid4(), "lost")

        await worker._requeue_task_operation(
            {"operation": "run", "params": {"task_id": task_id}}  # type: ignore[typeddict-item]
        )

        task = await memory_storage.load_task(task_id)
        assert task["status"]["state"] == "submitted"

    @pytest.mark.asyncio
    async def test_requeue_on_memory_scheduler_cancels_instead(self, memory_storage):
        """A non-durable scheduler's stream dies with the process, so an
        un-started task is finalized as canceled, not requeued into a
        buffer nobody will ever read."""

        class VolatileScheduler:  # requeue_survives_shutdown defaults False
            async def run_task(self, params):
                raise AssertionError("must not requeue into a volatile scheduler")

        worker = self.make_worker(memory_storage, scheduler=VolatileScheduler())
        task_id = await submit(memory_storage, uuid4(), "volatile")

        await worker._requeue_task_operation(
            {"operation": "run", "params": {"task_id": task_id}}  # type: ignore[typeddict-item]
        )

        task = await memory_storage.load_task(task_id)
        assert task["status"]["state"] == "canceled"

    @pytest.mark.asyncio
    async def test_settlement_failure_skips_terminal_task(self, memory_storage):
        """A settlement-failure write only lands while the task is still
        'submitted'; a canceled task is left untouched."""
        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "paid")
        await memory_storage.update_task(task_id, state="canceled")
        task = await memory_storage.load_task(task_id)

        await worker._handle_settlement_failure(task, {"error": "insufficient"})

        reloaded = await memory_storage.load_task(task_id)
        assert reloaded["status"]["state"] == "canceled"
        assert all(m.get("role") != "agent" for m in reloaded.get("history", [])), (
            "no failure message may be appended to a terminal task"
        )

    @pytest.mark.asyncio
    async def test_task_failure_after_cancel_keeps_orphan_metadata(
        self, memory_storage
    ):
        """_handle_task_failure losing the race to a cancel must still
        persist the orphan-payment reconciliation data, without flipping
        the state to failed."""
        from bindu.settings import app_settings

        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "paid")
        await memory_storage.update_task(task_id, state="canceled")
        task = await memory_storage.load_task(task_id)

        await worker._handle_task_failure(
            task,
            "boom",
            settlement_metadata={
                app_settings.x402.meta_status_key: app_settings.x402.status_completed,
                "x402.payment.receipts": [{"transaction": "0xdef"}],
            },
        )

        reloaded = await memory_storage.load_task(task_id)
        assert reloaded["status"]["state"] == "canceled"
        metadata = reloaded.get("metadata") or {}
        assert metadata.get(app_settings.x402.meta_status_key) == "payment-orphaned"
        assert metadata["x402.payment.receipts"][0]["transaction"] == "0xdef"

    @pytest.mark.asyncio
    async def test_intermediate_state_discarded_when_not_working(self, memory_storage):
        """A late input-required transition is discarded once the task is
        no longer 'working'."""
        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "ask")
        await memory_storage.update_task(task_id, state="canceled")
        task = await memory_storage.load_task(task_id)

        await worker._handle_intermediate_state(task, "input-required", "more info?")

        reloaded = await memory_storage.load_task(task_id)
        assert reloaded["status"]["state"] == "canceled"
        assert all(m.get("role") != "agent" for m in reloaded.get("history", []))

    @pytest.mark.asyncio
    async def test_orphan_tag_never_lands_on_completed_task(self, memory_storage):
        """An interrupt after the completion write committed (e.g. during
        the notification awaits) must not re-tag a delivered task: the
        payment stays payment-completed."""
        from bindu.settings import app_settings

        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "done")
        receipt = {
            app_settings.x402.meta_status_key: app_settings.x402.status_completed,
            "x402.payment.receipts": [{"transaction": "0xdone"}],
        }
        await memory_storage.update_task(task_id, state="working")
        await memory_storage.update_task(
            task_id, state="completed", metadata=dict(receipt)
        )

        await worker._record_orphaned_payment(task_id, dict(receipt))

        reloaded = await memory_storage.load_task(task_id)
        assert (
            reloaded["metadata"][app_settings.x402.meta_status_key]
            == app_settings.x402.status_completed
        ), "a committed deliverable keeps its payment-completed status"

    @pytest.mark.asyncio
    async def test_orphan_tag_lands_on_independently_failed_task(self, memory_storage):
        """A writer that knows nothing about payments (e.g. the stream
        error handler) can mark a paid task failed; the orphan re-tag must
        still land there — only 'completed' proves a deliverable."""
        from bindu.settings import app_settings

        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "streamfail")
        await memory_storage.update_task(task_id, state="working")
        await memory_storage.update_task(task_id, state="failed")

        await worker._record_orphaned_payment(
            task_id,
            {
                app_settings.x402.meta_status_key: app_settings.x402.status_completed,
                "x402.payment.receipts": [{"transaction": "0xsfail"}],
            },
        )

        reloaded = await memory_storage.load_task(task_id)
        assert reloaded["status"]["state"] == "failed"
        metadata = reloaded.get("metadata") or {}
        assert metadata.get(app_settings.x402.meta_status_key) == "payment-orphaned"
        assert metadata["x402.payment.receipts"][0]["transaction"] == "0xsfail"

    @pytest.mark.asyncio
    async def test_orphan_tag_is_best_effort_on_storage_failure(self, memory_storage):
        """The shielded, bounded orphan write must never raise out of the
        shutdown/cancel path — and when it fails (so the upfront receipt
        write may have failed too), the error log itself must carry the
        reconciliation data as the record of last resort."""
        from bindu.server.workers import manifest_worker as mw

        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "broken")

        async def broken_update(*args, **kwargs):
            raise RuntimeError("storage down")

        memory_storage.update_task = broken_update  # instance-level stub

        with patch.object(mw.logger, "error") as log_error:
            # Must not raise.
            await worker._record_orphaned_payment(
                task_id,
                {"x402.payment.receipts": [{"transaction": "0xlastresort"}]},
            )

        assert log_error.called, "the combined failure must be logged"
        assert "0xlastresort" in str(log_error.call_args), (
            "the log line must carry the reconciliation data"
        )

    @pytest.mark.asyncio
    async def test_discarded_intermediate_prompt_tags_orphan(self, memory_storage):
        """A paid handler returning input-required after a cancel landed in
        storage: the prompt is discarded, and the settled payment must be
        recorded as orphaned — nothing was delivered."""
        from bindu.settings import app_settings

        worker = self.make_worker(memory_storage)
        task_id = await submit(memory_storage, uuid4(), "paidask")
        await memory_storage.update_task(task_id, state="canceled")
        task = await memory_storage.load_task(task_id)

        await worker._handle_intermediate_state(
            task,
            "input-required",
            "need more?",
            settlement_metadata={
                app_settings.x402.meta_status_key: app_settings.x402.status_completed,
                "x402.payment.receipts": [{"transaction": "0xint"}],
            },
        )

        reloaded = await memory_storage.load_task(task_id)
        assert reloaded["status"]["state"] == "canceled"
        metadata = reloaded.get("metadata") or {}
        assert metadata.get(app_settings.x402.meta_status_key) == "payment-orphaned"
        assert metadata["x402.payment.receipts"][0]["transaction"] == "0xint"
        assert all(m.get("role") != "agent" for m in reloaded.get("history", []))
