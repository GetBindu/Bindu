"""DID (Decentralized Identifier) utilities for Bindu.

This package provides utilities for DID signature creation, verification,
and validation.
"""

from .signature import (
    create_signature_payload,
    extract_signature_headers,
    sign_request,
    verify_signature,
)
from .validation import check_did_match, validate_did_extension

__all__ = [
    # Signature utilities
    "create_signature_payload",
    "sign_request",
    "verify_signature",
    "extract_signature_headers",
    # Validation utilities
    "validate_did_extension",
    "check_did_match",
]
