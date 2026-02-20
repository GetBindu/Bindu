"""Pydantic models for JSON-RPC request/response validation."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from bindu.common.protocol.types import Message, MessageSendConfiguration


class JSONRPCBaseRequestModel(BaseModel):
    """Validate JSON-RPC 2.0 base request structure."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"]
    id: UUID | str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class AgentTaskPayloadModel(BaseModel):
    """Validate agent task payload structure for message operations."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    configuration: MessageSendConfiguration
    message: Message
    metadata: dict[str, Any] | None = None


class JSONRPCErrorModel(BaseModel):
    """JSON-RPC error object format."""

    model_config = ConfigDict(extra="forbid")

    code: int
    message: str
    data: Any | None = None


class JSONRPCErrorResponseModel(BaseModel):
    """JSON-RPC error response wrapper."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"] = "2.0"
    error: JSONRPCErrorModel
    id: str | int | None = None
