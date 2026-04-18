"""ScopeBlind extension for verifiable authorization receipts.

This extension keeps authorization separate from agent identity. DID signing
continues to answer "who said this?", while ScopeBlind receipts answer
"was this action authorized under policy?".
"""

from __future__ import annotations

from .extension import ScopeBlindAuthorizationContext, ScopeBlindExtension
from .receipt import (
    ScopeBlindArtifactDigest,
    ScopeBlindReceipt,
    ScopeBlindReceiptPayload,
    attach_receipt_to_artifacts,
    build_task_receipt_metadata,
)
from .verifier import (
    VerificationResult,
    verify_artifact_receipt,
    verify_receipt,
)

__all__: list[str] = [
    "ScopeBlindArtifactDigest",
    "ScopeBlindAuthorizationContext",
    "ScopeBlindExtension",
    "ScopeBlindReceipt",
    "ScopeBlindReceiptPayload",
    "VerificationResult",
    "attach_receipt_to_artifacts",
    "build_task_receipt_metadata",
    "verify_artifact_receipt",
    "verify_receipt",
]
