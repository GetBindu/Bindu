"""Tolerance tests for camelCase ↔ snake_case on the A2A types.

Before the A2A_MODEL_CONFIG refactor, every TypedDict in
``bindu/common/protocol/types.py`` was configured with
``ConfigDict(alias_generator=to_camel)`` only. That produced a one-way
door: output was camelCase (A2A spec-compliant) but input was
*strictly* camelCase — a Python client that hand-built a request with
``message_id`` would see pydantic silently drop the key and then
complain that ``messageId`` was missing.

Adding ``populate_by_name=True`` to the shared config teaches pydantic
to accept either form on input while keeping camelCase-only on output
via ``by_alias=True``. This test file guards both halves of that
contract so a future change cannot reintroduce the asymmetry.

See ``bugs/2026-04-18-types-populate-by-name.md`` for the full story.
"""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import TypeAdapter

from bindu.common.protocol.types import (
    A2A_MODEL_CONFIG,
    Artifact,
    Message,
    Task,
    a2a_request_ta,
)


# ---------------------------------------------------------------------------
# Config guard — belt-and-braces check so the populate_by_name flag
# can't be silently dropped later.
# ---------------------------------------------------------------------------


def test_shared_config_has_populate_by_name_enabled():
    """A2A_MODEL_CONFIG must allow snake_case keys on input."""
    assert A2A_MODEL_CONFIG.get("populate_by_name") is True


def test_shared_config_has_alias_generator():
    """Aliases must still be generated so output stays camelCase."""
    assert A2A_MODEL_CONFIG.get("alias_generator") is not None


# ---------------------------------------------------------------------------
# Input tolerance — either case accepted.
# ---------------------------------------------------------------------------


def _msg(case: str) -> dict:
    if case == "camel":
        return {
            "kind": "message",
            "messageId": "00000000-0000-0000-0000-000000000001",
            "contextId": "00000000-0000-0000-0000-000000000002",
            "taskId": "00000000-0000-0000-0000-000000000003",
            "role": "user",
            "parts": [{"kind": "text", "text": "hi"}],
        }
    return {
        "kind": "message",
        "message_id": "00000000-0000-0000-0000-000000000001",
        "context_id": "00000000-0000-0000-0000-000000000002",
        "task_id": "00000000-0000-0000-0000-000000000003",
        "role": "user",
        "parts": [{"kind": "text", "text": "hi"}],
    }


class TestInputAcceptsBothCases:
    """Python clients writing snake_case must not be silently rejected."""

    def test_message_accepts_camel_case(self):
        parsed = TypeAdapter(Message).validate_python(_msg("camel"))
        assert parsed["message_id"] == UUID("00000000-0000-0000-0000-000000000001")
        assert parsed["context_id"] == UUID("00000000-0000-0000-0000-000000000002")
        assert parsed["task_id"] == UUID("00000000-0000-0000-0000-000000000003")

    def test_message_accepts_snake_case(self):
        parsed = TypeAdapter(Message).validate_python(_msg("snake"))
        assert parsed["message_id"] == UUID("00000000-0000-0000-0000-000000000001")
        assert parsed["context_id"] == UUID("00000000-0000-0000-0000-000000000002")
        assert parsed["task_id"] == UUID("00000000-0000-0000-0000-000000000003")

    def test_artifact_accepts_snake_case(self):
        """Spot-check a non-Message type — the guarantee must be
        uniform across the whole types module."""
        parsed = TypeAdapter(Artifact).validate_python(
            {
                "artifact_id": "00000000-0000-0000-0000-000000000004",
                "name": "result",
                "parts": [{"kind": "text", "text": "hello"}],
            }
        )
        assert parsed["artifact_id"] == UUID("00000000-0000-0000-0000-000000000004")

    def test_full_a2a_request_accepts_snake_case(self):
        """End-to-end via the module-level TypeAdapter used by the
        server endpoint. Uses snake_case on both the message and the
        configuration sub-object to exercise deep tolerance."""
        req = {
            "jsonrpc": "2.0",
            "id": "00000000-0000-0000-0000-000000000099",
            "method": "message/send",
            "params": {
                "message": _msg("snake"),
                "configuration": {
                    # snake_case here too — pydantic alias is
                    # acceptedOutputModes in camelCase.
                    "accepted_output_modes": ["text"],
                },
            },
        }
        # validate_json matches the server's exact entry point in
        # bindu/server/endpoints/a2a_protocol.py.
        a2a_request_ta.validate_json(json.dumps(req))


# ---------------------------------------------------------------------------
# Output contract — wire format stays camelCase, always.
# ---------------------------------------------------------------------------


class TestOutputRemainsCamelCase:
    """The A2A spec mandates camelCase on the wire. Input tolerance
    must not leak into output."""

    def test_message_dumps_as_camel_case_by_alias(self):
        parsed = TypeAdapter(Message).validate_python(_msg("snake"))
        out = TypeAdapter(Message).dump_python(parsed, by_alias=True)
        assert "messageId" in out
        assert "contextId" in out
        assert "taskId" in out
        assert "message_id" not in out
        assert "context_id" not in out
        assert "task_id" not in out

    def test_message_camel_input_round_trips_camel_output(self):
        """No matter which case the input used, output is camelCase."""
        parsed = TypeAdapter(Message).validate_python(_msg("camel"))
        out = TypeAdapter(Message).dump_python(parsed, by_alias=True)
        assert "messageId" in out and "message_id" not in out

    def test_task_dumps_camel_case(self):
        """A Task validated from snake_case dumps as camelCase."""
        task = TypeAdapter(Task).validate_python(
            {
                "id": "00000000-0000-0000-0000-000000000010",
                "context_id": "00000000-0000-0000-0000-000000000011",
                "kind": "task",
                "status": {
                    "state": "submitted",
                    "timestamp": "2026-04-18T00:00:00Z",
                },
                "history": [],
            }
        )
        out = TypeAdapter(Task).dump_python(task, by_alias=True)
        assert "contextId" in out and "context_id" not in out
