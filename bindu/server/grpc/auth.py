"""gRPC authentication interceptor for Bindu."""

from __future__ import annotations

from collections.abc import Iterable
import inspect
from typing import Any

import grpc
from grpc import aio as grpc_aio  # type: ignore[attr-defined]

from bindu.auth.hydra.client import HydraClient
from bindu.settings import AuthSettings, HydraSettings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.auth")


def _metadata_value(metadata: Iterable[tuple[str, Any]] | None, key: str) -> str | None:
    if not metadata:
        return None
    target = key.lower()
    for meta_key, meta_value in metadata:
        if meta_key.lower() != target:
            continue
        if isinstance(meta_value, bytes):
            return meta_value.decode("utf-8", errors="replace")
        return str(meta_value)
    return None


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    parts = authorization_header.strip().split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


class HydraTokenValidator:
    """Validate access tokens via Ory Hydra introspection."""

    def __init__(self, auth_config: AuthSettings, hydra_config: HydraSettings) -> None:
        """Initialize the HydraTokenValidator with auth and Hydra settings."""
        self._auth_config = auth_config
        self._hydra_client = HydraClient(
            admin_url=hydra_config.admin_url,
            public_url=hydra_config.public_url,
            timeout=hydra_config.timeout,
            verify_ssl=hydra_config.verify_ssl,
        )

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate an access token via Hydra introspection and return the introspection result."""
        introspection = await self._hydra_client.introspect_token(token)
        if not introspection.get("active", False):
            raise ValueError("Token is not active")
        return introspection


def _abort_handler(
    handler: grpc.RpcMethodHandler,
    status: grpc.StatusCode,
    details: str,
) -> grpc.RpcMethodHandler:
    request_deserializer = getattr(handler, "request_deserializer", None)
    response_serializer = getattr(handler, "response_serializer", None)

    async def abort_unary_unary(_request, context):
        await context.abort(status, details)

    async def abort_stream_unary(_request_iterator, context):
        await context.abort(status, details)

    async def abort_unary_stream(_request, context):
        await context.abort(status, details)
        if False:
            yield None

    async def abort_stream_stream(_request_iterator, context):
        await context.abort(status, details)
        if False:
            yield None

    request_streaming = bool(getattr(handler, "request_streaming", False))
    response_streaming = bool(getattr(handler, "response_streaming", False))

    if request_streaming and response_streaming:
        return grpc.stream_stream_rpc_method_handler(
            abort_stream_stream,
            request_deserializer=request_deserializer,
            response_serializer=response_serializer,
        )
    if request_streaming:
        return grpc.stream_unary_rpc_method_handler(
            abort_stream_unary,
            request_deserializer=request_deserializer,
            response_serializer=response_serializer,
        )
    if response_streaming:
        return grpc.unary_stream_rpc_method_handler(
            abort_unary_stream,
            request_deserializer=request_deserializer,
            response_serializer=response_serializer,
        )
    return grpc.unary_unary_rpc_method_handler(
        abort_unary_unary,
        request_deserializer=request_deserializer,
        response_serializer=response_serializer,
    )


class GrpcAuthInterceptor(grpc_aio.ServerInterceptor):
    """Server interceptor that enforces JWT auth via metadata."""

    def __init__(
        self,
        auth_config: AuthSettings,
        hydra_config: HydraSettings | None = None,
        validator: HydraTokenValidator | None = None,
    ) -> None:
        """Initialize the interceptor with auth settings and JWT validator.

        Args:
            auth_config: Authentication configuration for gRPC requests.
            hydra_config: Optional Hydra configuration override.
            validator: Optional token validator override.
        """
        self._auth_config = auth_config
        self._validator = validator or HydraTokenValidator(
            auth_config,
            hydra_config or HydraSettings(),
        )

    async def intercept_service(self, continuation, handler_call_details):
        """Authorize gRPC calls and return an authenticated handler.

        Args:
            continuation: gRPC continuation that resolves the RPC handler.
            handler_call_details: Call details including method and metadata.

        Returns:
            The RPC handler (or an aborting handler) for the call.
        """
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        method = handler_call_details.method or "<unknown>"
        authorization = _metadata_value(
            handler_call_details.invocation_metadata, "authorization"
        )
        token = _extract_bearer_token(authorization)
        if not token:
            logger.warning(f"Missing authorization metadata for gRPC call {method}")
            return _abort_handler(
                handler,
                grpc.StatusCode.UNAUTHENTICATED,
                "Missing authorization token",
            )

        try:
            validation_result = self._validator.validate_token(token)
            if inspect.isawaitable(validation_result):
                await validation_result
        except Exception as exc:
            logger.warning(f"Invalid authorization token for gRPC call {method}: {exc}")
            return _abort_handler(
                handler,
                grpc.StatusCode.UNAUTHENTICATED,
                "Invalid authorization token",
            )

        return handler
