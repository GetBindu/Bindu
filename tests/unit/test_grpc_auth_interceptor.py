"""Unit tests for gRPC auth interceptor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import grpc
import jwt
import pytest

from bindu.server.grpc.auth import GrpcAuthInterceptor, HydraTokenValidator
from bindu.settings import AuthSettings


class DummyAbortError(Exception):
    """Raised when a test context aborts a gRPC call."""


class DummyContext:
    """Minimal context to capture abort status and details."""

    def __init__(self) -> None:
        self.abort_status: grpc.StatusCode | None = None
        self.abort_details: str | None = None

    async def abort(self, code: grpc.StatusCode, details: str) -> None:
        self.abort_status = code
        self.abort_details = details
        raise DummyAbortError()


class FailOnAbortContext:
    """Context that fails if abort is called."""

    async def abort(self, _code: grpc.StatusCode, _details: str) -> None:
        raise AssertionError("abort should not be called for valid tokens")


@dataclass(frozen=True)
class DummyHandlerCallDetails:
    """Minimal stand-in for handler call details."""

    method: str
    invocation_metadata: Sequence[tuple[str, str]] | None = None


def _make_handler(*, should_raise: bool = False):
    async def handler_fn(_request, _context):
        if should_raise:
            raise AssertionError("handler should not be called")
        return "ok"

    return grpc.unary_unary_rpc_method_handler(handler_fn)


@pytest.mark.asyncio
async def test_grpc_auth_interceptor_missing_token_aborts():
    interceptor = GrpcAuthInterceptor(AuthSettings())
    handler = _make_handler(should_raise=True)

    async def continuation(_details):
        return handler

    call_details = DummyHandlerCallDetails(
        method="/bindu.A2AService/ListTasks",
        invocation_metadata=[],
    )

    intercepted = await interceptor.intercept_service(continuation, call_details)
    context = DummyContext()

    with pytest.raises(DummyAbortError):
        await intercepted.unary_unary(None, context)

    assert context.abort_status == grpc.StatusCode.UNAUTHENTICATED
    assert context.abort_details == "Missing authorization token"


@pytest.mark.asyncio
async def test_grpc_auth_interceptor_invalid_token_aborts(monkeypatch):
    def _raise_invalid(self, _token):  # noqa: ARG001
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(HydraTokenValidator, "validate_token", _raise_invalid)

    interceptor = GrpcAuthInterceptor(AuthSettings())
    handler = _make_handler(should_raise=True)

    async def continuation(_details):
        return handler

    call_details = DummyHandlerCallDetails(
        method="/bindu.A2AService/ListTasks",
        invocation_metadata=[("authorization", "Bearer invalid")],
    )

    intercepted = await interceptor.intercept_service(continuation, call_details)
    context = DummyContext()

    with pytest.raises(DummyAbortError):
        await intercepted.unary_unary(None, context)

    assert context.abort_status == grpc.StatusCode.UNAUTHENTICATED
    assert context.abort_details == "Invalid authorization token"


@pytest.mark.asyncio
async def test_grpc_auth_interceptor_valid_token_allows(monkeypatch):
    def _validate_ok(self, _token):  # noqa: ARG001
        return {"sub": "test-user"}

    monkeypatch.setattr(HydraTokenValidator, "validate_token", _validate_ok)

    interceptor = GrpcAuthInterceptor(AuthSettings())
    handler = _make_handler()

    async def continuation(_details):
        return handler

    call_details = DummyHandlerCallDetails(
        method="/bindu.A2AService/ListTasks",
        invocation_metadata=[("authorization", "Bearer valid-token")],
    )

    intercepted = await interceptor.intercept_service(continuation, call_details)
    result = await intercepted.unary_unary(None, FailOnAbortContext())

    assert result == "ok"
