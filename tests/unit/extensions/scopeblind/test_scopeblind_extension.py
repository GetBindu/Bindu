"""Tests for the ScopeBlind extension and verifier."""

from __future__ import annotations

import json

from pathlib import Path
from uuid import uuid4

from starlette.requests import Request

from bindu.common.protocol.types import Artifact, TextPart
from bindu.extensions.scopeblind import (
    ScopeBlindExtension,
    verify_artifact_receipt,
    verify_receipt,
)


def _write_policy(policy_dir: Path, content: str) -> Path:
    """Write a Cedar policy file into the given directory."""
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_path = policy_dir / "policy.cedar"
    policy_path.write_text(content, encoding="utf-8")
    return policy_path


def _build_request(method_name: str = "message/send") -> Request:
    """Build a Starlette request for authorization evaluation tests."""
    body = json.dumps({"jsonrpc": "2.0", "id": "1", "method": method_name}).encode(
        "utf-8"
    )

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "raw_path": b"/",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }
    request = Request(scope, receive)
    request.state.authenticated = True
    request.state.user = {
        "sub": "alice",
        "is_m2m": False,
        "scope": ["agent:invoke"],
        "client_id": "client-1",
    }
    return request


class TestScopeBlindExtension:
    """Test ScopeBlind extension functionality."""

    def test_agent_extension_metadata(self, tmp_path: Path):
        """Agent card metadata should expose receipt verification details."""
        policy_dir = tmp_path / "policies"
        _write_policy(
            policy_dir,
            'permit(principal, action == Action::"message/send", resource);',
        )
        extension = ScopeBlindExtension(
            mode="enforce",
            cedar_policies=str(policy_dir),
            key_dir=tmp_path / "keys",
        )

        agent_extension = extension.agent_extension

        assert agent_extension["required"] is True
        assert agent_extension["params"]["mode"] == "enforce"
        assert (
            agent_extension["params"]["verification_key"] == extension.public_key_base58
        )
        assert agent_extension["params"]["policy_hash"] == extension.policy_hash

    def test_receipt_verification_and_tampering(self, tmp_path: Path):
        """Receipts should verify cleanly and fail after tampering."""
        policy_dir = tmp_path / "policies"
        _write_policy(
            policy_dir,
            'permit(principal, action == Action::"message/send", resource);',
        )
        extension = ScopeBlindExtension(
            mode="enforce",
            cedar_policies=str(policy_dir),
            key_dir=tmp_path / "keys",
        )
        request = _build_request()
        decision = extension.evaluate_request(
            request,
            "message/send",
            {"jsonrpc": "2.0", "id": "1", "method": "message/send"},
        )
        auth_context = decision.to_context(
            mode=extension.mode,
            policy_hash=extension.policy_hash,
            verification_key=extension.public_key_base58,
            issuer=extension.issuer,
        )

        artifact = Artifact(
            artifact_id=uuid4(),
            name="result",
            parts=[TextPart(kind="text", text="authorized")],
        )
        receipt = extension.create_receipt(
            authorization_context=auth_context,
            artifacts=[artifact],
            task_id=uuid4(),
            context_id=uuid4(),
            state="completed",
        )
        receipt_dict = {
            "payload": {
                **receipt.payload.__dict__,
                "artifacts": [digest.__dict__ for digest in receipt.payload.artifacts],
            },
            "payload_hash": receipt.payload_hash,
            "verification_key": receipt.verification_key,
            "signature": receipt.signature,
            "algorithm": receipt.algorithm,
            "issuer": receipt.issuer,
        }

        verification = verify_receipt(receipt_dict)
        artifact_verification = verify_artifact_receipt(artifact, receipt_dict)

        assert verification.valid is True
        assert artifact_verification.valid is True

        tampered_receipt = dict(receipt_dict)
        tampered_payload = dict(receipt_dict["payload"])
        tampered_payload["decision"] = "Deny"
        tampered_receipt["payload"] = tampered_payload

        tampered_receipt_result = verify_receipt(tampered_receipt)
        assert tampered_receipt_result.valid is False
        assert tampered_receipt_result.error == "payload hash mismatch"

        tampered_artifact = Artifact(
            artifact_id=artifact["artifact_id"],
            name=artifact["name"],
            parts=[TextPart(kind="text", text="tampered")],
        )
        tampered_artifact_result = verify_artifact_receipt(
            tampered_artifact,
            receipt_dict,
        )
        assert tampered_artifact_result.valid is False
        assert tampered_artifact_result.integrity_valid is False
