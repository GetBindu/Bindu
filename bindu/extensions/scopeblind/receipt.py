"""Receipt data structures and deterministic serialization helpers."""

from __future__ import annotations

import hashlib
import json

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from bindu.common.protocol.types import Artifact
from bindu.settings import app_settings


ScopeBlindDecision = Literal["Allow", "Deny"]


@dataclass(frozen=True)
class ScopeBlindArtifactDigest:
    """Digest entry describing one artifact covered by a receipt."""

    artifact_id: str
    sha256: str


@dataclass(frozen=True)
class ScopeBlindReceiptPayload:
    """Canonical payload that is hashed and signed."""

    version: str
    mode: Literal["enforce", "shadow"]
    decision: ScopeBlindDecision
    issued_at: str
    principal: dict[str, Any]
    action: dict[str, Any]
    resource: dict[str, Any]
    context: dict[str, Any]
    policy_hash: str
    policy_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    task_id: str | None = None
    context_id: str | None = None
    state: str | None = None
    artifacts: list[ScopeBlindArtifactDigest] = field(default_factory=list)


@dataclass(frozen=True)
class ScopeBlindReceipt:
    """Signed authorization receipt."""

    payload: ScopeBlindReceiptPayload
    payload_hash: str
    verification_key: str
    signature: str
    algorithm: str = "ed25519"
    issuer: str | None = None


def _jsonable(value: Any) -> Any:
    """Recursively convert values to deterministic JSON-safe structures."""
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def deterministic_json_dumps(value: Any) -> str:
    """Serialize JSON deterministically for hashing and signing."""
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def sha256_digest(value: Any) -> str:
    """Compute a stable SHA-256 digest for the given value."""
    return hashlib.sha256(deterministic_json_dumps(value).encode("utf-8")).hexdigest()


def receipt_to_dict(receipt: ScopeBlindReceipt) -> dict[str, Any]:
    """Convert a receipt dataclass to a plain JSON-serializable dict."""
    return _jsonable(receipt)


def _artifact_without_scopeblind_metadata(artifact: Artifact) -> dict[str, Any]:
    """Return a copy of the artifact excluding scopeblind receipt metadata."""
    artifact_copy = dict(_jsonable(artifact))
    metadata = artifact_copy.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop(app_settings.scopeblind.meta_receipts_key, None)
        if not metadata:
            artifact_copy.pop("metadata", None)
    return artifact_copy


def build_artifact_digest(artifact: Artifact) -> ScopeBlindArtifactDigest:
    """Build the digest entry used in receipt payloads."""
    artifact_id = artifact.get("artifact_id")
    return ScopeBlindArtifactDigest(
        artifact_id=str(artifact_id) if artifact_id is not None else "",
        sha256=sha256_digest(_artifact_without_scopeblind_metadata(artifact)),
    )


def attach_receipt_to_artifacts(
    artifacts: list[Artifact],
    receipt: ScopeBlindReceipt,
) -> list[Artifact]:
    """Attach the receipt to every artifact's metadata in-place."""
    receipt_dict = receipt_to_dict(receipt)
    for artifact in artifacts:
        metadata = artifact.setdefault("metadata", {})
        if isinstance(metadata, dict):
            receipts = metadata.setdefault(app_settings.scopeblind.meta_receipts_key, [])
            if isinstance(receipts, list):
                receipts.append(receipt_dict)
    return artifacts


def build_task_receipt_metadata(receipt: ScopeBlindReceipt) -> dict[str, Any]:
    """Build task metadata entries for a receipt."""
    receipt_dict = receipt_to_dict(receipt)
    return {
        app_settings.scopeblind.meta_decision_key: receipt.payload.decision.lower(),
        app_settings.scopeblind.meta_mode_key: receipt.payload.mode,
        app_settings.scopeblind.meta_policy_hash_key: receipt.payload.policy_hash,
        app_settings.scopeblind.meta_receipts_key: [receipt_dict],
    }
