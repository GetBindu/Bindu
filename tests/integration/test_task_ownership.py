"""Cross-tenant isolation coverage for the A2A handlers.

Wires up a real InMemoryStorage + InMemoryScheduler under the real
TaskManager and drives it through the public handler surface with two
synthetic caller DIDs. Confirms that every public handler that reads,
mutates, or destroys a task/context refuses access when the caller does
not own the resource.

This is the regression test for the IDOR fix tracked at
bugs/2026-04-18-idor-task-ownership.md. Every assertion here corresponds
to one cross-tenant attack vector that the fix closes.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager

ALICE = "did:bindu:alice"
BOB = "did:bindu:bob"


def _send_request(message_id, context_id, task_id, text="hi"):
    return {
        "jsonrpc": "2.0",
        "id": str(message_id),
        "method": "message/send",
        "params": {
            "message": {
                "message_id": message_id,
                "context_id": context_id,
                "task_id": task_id,
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }


def _get_request(task_id):
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tasks/get",
        "params": {"task_id": task_id},
    }


def _cancel_request(task_id):
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tasks/cancel",
        "params": {"task_id": task_id},
    }


def _list_tasks_request():
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tasks/list",
        "params": {},
    }


def _list_contexts_request():
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "contexts/list",
        "params": {},
    }


def _clear_context_request(context_id):
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "contexts/clear",
        "params": {"contextId": str(context_id)},
    }


def _task_feedback_request(task_id):
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tasks/feedback",
        "params": {
            "task_id": task_id,
            "feedback": "good",
            "rating": 5,
            "metadata": {},
        },
    }


@pytest_asyncio.fixture
async def manager():
    storage = InMemoryStorage()
    scheduler = InMemoryScheduler()
    mgr = TaskManager(scheduler=scheduler, storage=storage, manifest=None)
    async with mgr:
        yield mgr


def _is_not_found(response, expected_code=-32001):
    """Match the error_response_creator output. JSONRPCError is a TypedDict
    so the error payload is a plain dict, not an object."""
    return "error" in response and response["error"]["code"] == expected_code


class TestTaskOwnershipIsolation:
    """Every public A2A handler must refuse cross-tenant access."""

    @pytest.mark.asyncio
    async def test_submit_task_stamps_caller_as_owner(self, manager):
        ctx = uuid4()
        tid = uuid4()
        resp = await manager.send_message(
            _send_request(uuid4(), ctx, tid), caller_did=ALICE
        )
        assert "result" in resp
        assert await manager.storage.get_task_owner(tid) == ALICE
        assert await manager.storage.get_context_owner(ctx) == ALICE

    @pytest.mark.asyncio
    async def test_get_task_blocks_cross_tenant(self, manager):
        ctx, tid = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ctx, tid), caller_did=ALICE)

        alice_ok = await manager.get_task(_get_request(tid), caller_did=ALICE)
        assert "result" in alice_ok
        assert alice_ok["result"]["id"] == tid

        bob_blocked = await manager.get_task(_get_request(tid), caller_did=BOB)
        assert _is_not_found(bob_blocked)

    @pytest.mark.asyncio
    async def test_cancel_task_blocks_cross_tenant(self, manager):
        ctx, tid = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ctx, tid), caller_did=ALICE)

        bob_blocked = await manager.cancel_task(_cancel_request(tid), caller_did=BOB)
        assert _is_not_found(bob_blocked)

        # Alice can still cancel her own task. May error on terminal-state
        # or cancel successfully — either way, the error code must NOT be
        # "not found" (i.e., the owner check passed).
        alice_resp = await manager.cancel_task(_cancel_request(tid), caller_did=ALICE)
        if "error" in alice_resp:
            # If her cancel errored, the reason must not be ownership.
            # Scheduler backpressure / terminal-state are acceptable.
            assert "not found" not in alice_resp["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_task_feedback_blocks_cross_tenant(self, manager):
        ctx, tid = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ctx, tid), caller_did=ALICE)

        bob_blocked = await manager.task_feedback(
            _task_feedback_request(tid), caller_did=BOB
        )
        assert _is_not_found(bob_blocked)

    @pytest.mark.asyncio
    async def test_list_tasks_scopes_to_caller(self, manager):
        # Alice submits two tasks across two contexts
        ac1, at1 = uuid4(), uuid4()
        ac2, at2 = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ac1, at1), caller_did=ALICE)
        await manager.send_message(_send_request(uuid4(), ac2, at2), caller_did=ALICE)
        # Bob submits one
        bc1, bt1 = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), bc1, bt1), caller_did=BOB)

        alice_list = await manager.list_tasks(_list_tasks_request(), caller_did=ALICE)
        bob_list = await manager.list_tasks(_list_tasks_request(), caller_did=BOB)

        alice_ids = {t["id"] for t in alice_list["result"]}
        bob_ids = {t["id"] for t in bob_list["result"]}
        assert alice_ids == {at1, at2}
        assert bob_ids == {bt1}

    @pytest.mark.asyncio
    async def test_list_contexts_scopes_to_caller(self, manager):
        ac, at = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ac, at), caller_did=ALICE)
        bc, bt = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), bc, bt), caller_did=BOB)

        alice_ctx = await manager.list_contexts(
            _list_contexts_request(), caller_did=ALICE
        )
        bob_ctx = await manager.list_contexts(_list_contexts_request(), caller_did=BOB)

        alice_ctx_ids = {c["context_id"] for c in alice_ctx["result"]}
        bob_ctx_ids = {c["context_id"] for c in bob_ctx["result"]}
        assert alice_ctx_ids == {ac}
        assert bob_ctx_ids == {bc}

    @pytest.mark.asyncio
    async def test_clear_context_blocks_cross_tenant(self, manager):
        ac, at = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ac, at), caller_did=ALICE)

        bob_blocked = await manager.clear_context(
            _clear_context_request(ac), caller_did=BOB
        )
        assert _is_not_found(bob_blocked)

        # Alice's context must still exist and hold her task.
        assert await manager.storage.get_context_owner(ac) == ALICE

    @pytest.mark.asyncio
    async def test_submit_task_on_foreign_context_blocked(self, manager):
        """An attacker guessing a context_id cannot hijack the conversation."""
        ac = uuid4()
        at1 = uuid4()
        await manager.send_message(_send_request(uuid4(), ac, at1), caller_did=ALICE)

        # Bob tries to submit to Alice's context. Storage raises
        # OwnershipError; handler translates to ContextNotFoundError.
        bob_task_id = uuid4()
        resp = await manager.send_message(
            _send_request(uuid4(), ac, bob_task_id), caller_did=BOB
        )
        assert _is_not_found(resp)

        # Verify Bob's task was NOT created and Alice's context owner is
        # unchanged.
        assert await manager.storage.get_task_owner(bob_task_id) is None
        assert await manager.storage.get_context_owner(ac) == ALICE


class TestUnauthenticatedCaller:
    """caller_did=None (auth disabled) shares a single tenancy with other
    unauthenticated callers. This preserves today's dev-mode behavior."""

    @pytest.mark.asyncio
    async def test_null_owner_is_visible_to_null_caller(self, manager):
        ctx, tid = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ctx, tid), caller_did=None)

        resp = await manager.get_task(_get_request(tid), caller_did=None)
        assert "result" in resp
        assert resp["result"]["id"] == tid

    @pytest.mark.asyncio
    async def test_null_owner_hidden_from_authenticated_caller(self, manager):
        ctx, tid = uuid4(), uuid4()
        await manager.send_message(_send_request(uuid4(), ctx, tid), caller_did=None)

        resp = await manager.get_task(_get_request(tid), caller_did=ALICE)
        assert _is_not_found(resp)
