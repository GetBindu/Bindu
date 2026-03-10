"""Payment security utilities for X402 payment integrity.

Provides HMAC signing and verification for payment payloads to prevent
forgery and replay attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.x402.payment_security")


class PaymentSecurity:
    """Handles HMAC signing and verification of payment payloads."""

    def __init__(self, secret_key: str):
        """Initialize payment security with a secret key.

        Args:
            secret_key: Secret key for HMAC operations. Should be a strong,
                       random value (minimum 32 characters recommended).
        """
        if not secret_key or len(secret_key) < 16:
            logger.warning(
                "Payment security secret_key is weak. Minimum 32 characters recommended."
            )
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

    def sign_payload(self, payload: dict[str, Any], timestamp: int | None = None) -> str:
        """Sign a payment payload with HMAC and return the signature.

        Args:
            payload: Payment payload dictionary to sign
            timestamp: Unix timestamp (default: current time). Included in signature
                      to prevent replay attacks.

        Returns:
            Hex-encoded HMAC signature
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Create deterministic JSON representation for consistent hashing
        payload_with_ts = dict(payload)
        payload_with_ts["_hmac_timestamp"] = timestamp

        # Use sorted keys for deterministic JSON encoding
        payload_json = json.dumps(payload_with_ts, sort_keys=True, separators=(",", ":"))

        # Compute HMAC-SHA256
        signature = hmac.new(
            self.secret_key,
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()

        logger.debug(f"Signed payment payload with timestamp={timestamp}")
        return signature

    def verify_payload(
        self,
        payload: dict[str, Any],
        signature: str,
        max_age_seconds: int = 300,
    ) -> tuple[bool, str | None]:
        """Verify a payment payload signature and check timestamp freshness.

        Args:
            payload: Payment payload dictionary
            signature: Hex-encoded HMAC signature to verify
            max_age_seconds: Maximum age of timestamp in seconds (default: 5 min)

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        try:
            # Extract timestamp from payload
            payload_copy = dict(payload)
            timestamp = payload_copy.get("_hmac_timestamp")

            if timestamp is None:
                return False, "Missing _hmac_timestamp in payload"

            # Check timestamp freshness
            current_time = int(time.time())
            age = current_time - timestamp

            if age < 0:
                return False, "Clock skew: timestamp is in the future"

            if age > max_age_seconds:
                return False, f"Timestamp too old: {age} seconds > {max_age_seconds} seconds"

            # Recompute signature
            expected_signature = self.sign_payload(payload, timestamp)

            # Use constant-time comparison to prevent timing attacks
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(
                    f"HMAC signature mismatch. Expected: {expected_signature[:16]}..., Got: {signature[:16]}..."
                )
                return False, "Invalid or tampered signature"

            logger.debug("Payment signature verified successfully")
            return True, None

        except Exception as e:
            logger.error(f"Error verifying payload signature: {e}")
            return False, f"Verification error: {str(e)}"


def get_payment_security(secret_key: str | None = None) -> PaymentSecurity:
    """Get or create a PaymentSecurity instance.

    Args:
        secret_key: Secret key for HMAC (if None, reads from PAYMENT_SECURITY_KEY env)

    Returns:
        PaymentSecurity instance
    """
    if secret_key is None:
        import os
        secret_key = os.getenv(
            "PAYMENT_SECURITY_KEY",
            "bindu-default-payment-key-please-override-in-production",
        )

    return PaymentSecurity(secret_key)
