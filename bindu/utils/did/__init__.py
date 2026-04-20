"""DID (Decentralized Identifier) utilities for Bindu.

This package provides utilities for DID signature creation, verification,
and validation.
"""

from .signature import (
    create_signature_payload,
    sign_request,
    verify_signature,
    extract_signature_headers,
)
from .validation import validate_did_extension, check_did_match

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
