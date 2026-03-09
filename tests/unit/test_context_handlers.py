# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Unit tests for ContextHandlers.

Covers list_contexts and clear_context RPC dispatch methods
in isolation using InMemoryStorage.
"""

from uuid import uuid4

import pytest

from bindu.common.protocol.types import (
    ClearContextsRequest,
    ListContextsRequest,
)
from bindu.server.handlers.context_handlers import ContextHandlers
from bindu.server.storage.memory_storage import InMemoryStorage
from tests.utils import (
    assert_jsonrpc_error,
    assert_jsonrpc_success,
    create_test_message,
)


def _make_error_response(response_class, request_id, error_class, message):
    """Mirror TaskManager._create_error_response for handler tests."""
    return response_class(
        jsonrpc="2.0",
        id=request_id,
        error=error_class(code=-32020, message=message),
    )


def _make_handlers(storage):
    return ContextHandlers(
        storage=storage,
        error_response_creator=_make_error_response,
    )


# ---------------------------------------------------------------------------
# list_contexts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_contexts_empty_storage():
    """list_contexts returns an empty list when no contexts exist."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    request: ListContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/list",
        "params": {},
    }

    response = await handlers.list_contexts(request)
    assert_jsonrpc_success(response)
    assert response["result"] == []


@pytest.mark.asyncio
async def test_list_contexts_returns_created_contexts():
    """list_contexts returns one entry per unique context_id submitted."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    msg1 = create_test_message(text="ctx 1")
    msg2 = create_test_message(text="ctx 2")
    await storage.submit_task(msg1["context_id"], msg1)
    await storage.submit_task(msg2["context_id"], msg2)

    request: ListContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/list",
        "params": {},
    }

    response = await handlers.list_contexts(request)
    assert_jsonrpc_success(response)
    assert len(response["result"]) == 2


@pytest.mark.asyncio
async def test_list_contexts_multiple_tasks_same_context():
    """list_contexts returns one context even when it has multiple tasks."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    context_id = uuid4()
    msg1 = create_test_message(text="first", context_id=context_id)
    msg2 = create_test_message(text="second", context_id=context_id)
    await storage.submit_task(context_id, msg1)
    await storage.submit_task(context_id, msg2)

    request: ListContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/list",
        "params": {},
    }

    response = await handlers.list_contexts(request)
    assert_jsonrpc_success(response)
    # Same context_id → only one context entry
    assert len(response["result"]) == 1


@pytest.mark.asyncio
async def test_list_contexts_supports_length_param():
    """list_contexts forwards the length param to storage without error."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    for i in range(4):
        msg = create_test_message(text=f"ctx {i}")
        await storage.submit_task(msg["context_id"], msg)

    request: ListContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/list",
        "params": {"length": 2},
    }

    response = await handlers.list_contexts(request)
    assert_jsonrpc_success(response)
    assert len(response["result"]) <= 2


@pytest.mark.asyncio
async def test_list_contexts_supports_history_length_param():
    """list_contexts accepts the legacy history_length param for backwards compat."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    msg = create_test_message(text="legacy param")
    await storage.submit_task(msg["context_id"], msg)

    request: ListContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/list",
        "params": {"history_length": 10},
    }

    response = await handlers.list_contexts(request)
    assert_jsonrpc_success(response)


# ---------------------------------------------------------------------------
# clear_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_context_removes_existing_context():
    """clear_context removes a context and returns a success message."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="to be cleared")
    context_id = message["context_id"]
    await storage.submit_task(context_id, message)

    request: ClearContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/clear",
        "params": {"contextId": context_id},
    }

    response = await handlers.clear_context(request)
    assert_jsonrpc_success(response)
    assert str(context_id) in response["result"]["message"]


@pytest.mark.asyncio
async def test_clear_context_snake_case_param():
    """clear_context accepts context_id (snake_case) as well as contextId."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="snake case test")
    context_id = message["context_id"]
    await storage.submit_task(context_id, message)

    request: ClearContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/clear",
        "params": {"context_id": context_id},
    }

    response = await handlers.clear_context(request)
    assert_jsonrpc_success(response)


@pytest.mark.asyncio
async def test_clear_context_not_found_returns_error():
    """clear_context returns ContextNotFoundError (-32020) for unknown context."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    request: ClearContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/clear",
        "params": {"contextId": uuid4()},
    }

    response = await handlers.clear_context(request)
    assert_jsonrpc_error(response, -32020)


@pytest.mark.asyncio
async def test_clear_context_removes_all_tasks_in_context():
    """After clearing a context, list_contexts no longer includes it."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    context_id = uuid4()
    msg1 = create_test_message(text="task A", context_id=context_id)
    msg2 = create_test_message(text="task B", context_id=context_id)
    await storage.submit_task(context_id, msg1)
    await storage.submit_task(context_id, msg2)

    clear_request: ClearContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/clear",
        "params": {"contextId": context_id},
    }
    await handlers.clear_context(clear_request)

    list_request: ListContextsRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "contexts/list",
        "params": {},
    }
    response = await handlers.list_contexts(list_request)
    assert_jsonrpc_success(response)
    context_ids = [str(c.get("context_id", "")) for c in response["result"]]
    assert str(context_id) not in context_ids
