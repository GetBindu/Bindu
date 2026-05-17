# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Context handlers for Bindu server.

This module handles context-related RPC requests including
listing and clearing contexts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bindu.common.protocol.types import (
    ClearContextsRequest,
    ClearContextsResponse,
    ContextNotFoundError,
    ListContextsRequest,
    ListContextsResponse,
)

from bindu.utils.task_telemetry import trace_context_operation

from bindu.server.storage import Storage


@dataclass
class ContextHandlers:
    """Handles context-related RPC requests."""

    storage: Storage[Any]
    error_response_creator: Any = None

    @staticmethod
    def _parse_non_negative_length(value: Any, field_name: str) -> int | None:
        """Validate optional non-negative integer length parameters."""
        if value is None:
            return None

        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"Field '{field_name}' must be a non-negative integer")

        return value

    @trace_context_operation("list_contexts")
    async def list_contexts(
        self,
        request: ListContextsRequest,
        caller_did: str | None = None,
    ) -> ListContextsResponse:
        """List contexts owned by the caller.

        When ``caller_did`` is non-None, storage filters by the owner index so
        only the caller's contexts are returned. Unfiltered when None (auth
        disabled).
        """
        # Support both 'length' and 'history_length' for backwards compatibility
        params = request.get("params", {})
        if "length" in params:
            length = self._parse_non_negative_length(params["length"], "length")
        else:
            length = self._parse_non_negative_length(
                params.get("history_length"), "history_length"
            )

        contexts = await self.storage.list_contexts(length, owner_did=caller_did)

        # Return empty list if no contexts, not an error
        if contexts is None:
            contexts = []

        return ListContextsResponse(jsonrpc="2.0", id=request["id"], result=contexts)

    @trace_context_operation("clear_context")
    async def clear_context(
        self,
        request: ClearContextsRequest,
        caller_did: str | None = None,
    ) -> ClearContextsResponse:
        """Clear a context from storage. Only the context owner may clear it."""
        # Support both contextId (camelCase) and context_id (snake_case)
        params = request.get("params", {})
        context_id = params.get("contextId") or params.get("context_id")

        # Ownership check — "not yours" returns the same error as "not found"
        # to avoid leaking which context IDs exist across tenants. The
        # ``owner != caller_did`` comparison naturally handles all four
        # combinations: None==None (unauthenticated caller on unowned context,
        # dev-mode), str==str (owner match), None vs str / str vs None, and
        # str1 vs str2 (cross-tenant). A nonexistent context returns owner=None
        # and is rejected when caller_did is a string; when caller_did is None
        # too, we fall through and let storage.clear_context raise the
        # existing ValueError for missing rows.
        owner = await self.storage.get_context_owner(context_id)
        if owner != caller_did:
            return self.error_response_creator(
                ClearContextsResponse,
                request["id"],
                ContextNotFoundError,
                f"Context {context_id} not found",
            )

        try:
            await self.storage.clear_context(context_id)
        except ValueError as e:
            # Context not found (e.g. in-memory impl raises for missing ID)
            return self.error_response_creator(
                ClearContextsResponse, request["id"], ContextNotFoundError, str(e)
            )

        # The declared response type is `JSONRPCResponse[Context, ...]` but
        # this endpoint returns a simple success message rather than a Context
        # row. Aligning the protocol type to a fresh `ContextClearedResult`
        # TypedDict is a follow-up; for now we silence the shape mismatch.
        return ClearContextsResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={
                "message": f"Context {context_id} and all associated tasks cleared successfully"  # ty: ignore[invalid-key]
            },  # ty: ignore[missing-typed-dict-key]
        )
