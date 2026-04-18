"""Verification helpers for ScopeBlind receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import base58
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from bindu.common.protocol.types import Artifact

from .receipt import build_artifact_digest, sha256_digest


@dataclass(frozen=True)
class VerificationResult:
    """Structured verification outcome."""

    valid: bool
    signature_valid: bool
    integrity_valid: bool
    error: str | None = None


def _payload_hash(payload: dict[str, Any]) -> str:
    """Hash a receipt payload deterministically."""
    return sha256_digest(payload)


def _decode_public_key(base58_key: str) -> ed25519.Ed25519PublicKey:
    """Decode a base58-encoded raw Ed25519 public key."""
    raw_key = base58.b58decode(base58_key)
    return ed25519.Ed25519PublicKey.from_public_bytes(raw_key)


def verify_receipt(
    receipt: dict[str, Any],
    verification_key: str | None = None,
) -> VerificationResult:
    """Verify receipt integrity and signature.

    The verifier can use the embedded verification key, which keeps receipt
    verification separate from DID identity and other issuer infrastructure.
    """
    try:
        payload = receipt["payload"]
        expected_hash = _payload_hash(payload)
        payload_hash = receipt.get("payload_hash")
        if not isinstance(payload_hash, str) or expected_hash != payload_hash:
            return VerificationResult(
                valid=False,
                signature_valid=False,
                integrity_valid=False,
                error="payload hash mismatch",
            )

        key = verification_key or receipt.get("verification_key")
        if not isinstance(key, str) or not key:
            return VerificationResult(
                valid=False,
                signature_valid=False,
                integrity_valid=True,
                error="missing verification key",
            )

        public_key = _decode_public_key(key)
        signature = base58.b58decode(receipt["signature"])
        public_key.verify(signature, payload_hash.encode("utf-8"))
        return VerificationResult(
            valid=True,
            signature_valid=True,
            integrity_valid=True,
        )
    except (InvalidSignature, KeyError, TypeError, ValueError) as error:
        return VerificationResult(
            valid=False,
            signature_valid=False,
            integrity_valid=False,
            error=str(error),
        )


def verify_artifact_receipt(
    artifact: Artifact,
    receipt: dict[str, Any],
    verification_key: str | None = None,
) -> VerificationResult:
    """Verify that an artifact still matches the digest embedded in a receipt."""
    receipt_result = verify_receipt(receipt, verification_key=verification_key)
    if not receipt_result.valid:
        return receipt_result

    artifact_id = str(artifact.get("artifact_id", ""))
    artifact_digests = receipt.get("payload", {}).get("artifacts", [])
    matching_digest = next(
        (
            digest
            for digest in artifact_digests
            if digest.get("artifact_id") == artifact_id
        ),
        None,
    )
    if matching_digest is None:
        return VerificationResult(
            valid=False,
            signature_valid=True,
            integrity_valid=False,
            error="artifact digest missing from receipt",
        )

    actual_digest = build_artifact_digest(artifact).sha256
    expected_digest = matching_digest.get("sha256")
    integrity_valid = actual_digest == expected_digest
    return VerificationResult(
        valid=receipt_result.signature_valid and integrity_valid,
        signature_valid=receipt_result.signature_valid,
        integrity_valid=integrity_valid,
        error=None if integrity_valid else "artifact digest mismatch",
    )
