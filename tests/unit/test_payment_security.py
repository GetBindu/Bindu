"""Tests for payment security (HMAC signing/verification)."""

import json
import time
from unittest.mock import patch

import pytest

from bindu.server.middleware.x402.payment_security import PaymentSecurity, get_payment_security


class TestPaymentSecurity:
    """Test payment security HMAC operations."""

    def test_sign_payload(self):
        """Test signing a payment payload."""
        sec = PaymentSecurity("my-secret-key")
        payload = {"amount": "100", "network": "base-sepolia"}

        signature = sec.sign_payload(payload, timestamp=1000)

        assert signature is not None
        assert len(signature) == 64  # SHA256 hex is 64 chars
        assert isinstance(signature, str)

    def test_sign_payload_deterministic(self):
        """Signing the same payload with same timestamp produces same signature."""
        sec = PaymentSecurity("my-secret-key")
        payload = {"amount": "100", "network": "base-sepolia"}

        sig1 = sec.sign_payload(payload, timestamp=1000)
        sig2 = sec.sign_payload(payload, timestamp=1000)

        assert sig1 == sig2

    def test_sign_payload_different_secret(self):
        """Different secrets produce different signatures."""
        payload = {"amount": "100", "network": "base-sepolia"}

        sec1 = PaymentSecurity("secret1")
        sec2 = PaymentSecurity("secret2")

        sig1 = sec1.sign_payload(payload, timestamp=1000)
        sig2 = sec2.sign_payload(payload, timestamp=1000)

        assert sig1 != sig2

    def test_verify_payload_valid(self):
        """Verify signature on valid payload."""
        sec = PaymentSecurity("my-secret-key")
        payload = {"amount": "100", "network": "base-sepolia"}
        signature = sec.sign_payload(payload, timestamp=int(time.time()))

        is_valid, error_msg = sec.verify_payload(payload, signature)

        assert is_valid is True
        assert error_msg is None

    def test_verify_payload_invalid_signature(self):
        """Reject payload with invalid signature."""
        sec = PaymentSecurity("my-secret-key")
        payload = {"amount": "100", "network": "base-sepolia", "_hmac_timestamp": int(time.time())}
        bad_signature = "0" * 64

        is_valid, error_msg = sec.verify_payload(payload, bad_signature)

        assert is_valid is False
        assert "Invalid or tampered" in error_msg

    def test_verify_payload_missing_timestamp(self):
        """Reject payload without timestamp."""
        sec = PaymentSecurity("my-secret-key")
        payload = {"amount": "100", "network": "base-sepolia"}
        signature = "anything"

        is_valid, error_msg = sec.verify_payload(payload, signature)

        assert is_valid is False
        assert "Missing _hmac_timestamp" in error_msg

    def test_verify_payload_timestamp_too_old(self):
        """Reject payload with timestamp older than max_age."""
        sec = PaymentSecurity("my-secret-key")
        old_time = int(time.time()) - 600  # 10 minutes ago
        payload = {"amount": "100", "network": "base-sepolia"}
        signature = sec.sign_payload(payload, timestamp=old_time)

        is_valid, error_msg = sec.verify_payload(
            payload, signature, max_age_seconds=300
        )

        assert is_valid is False
        assert "too old" in error_msg.lower()

    def test_verify_payload_future_timestamp(self):
        """Reject payload with future timestamp (clock skew)."""
        sec = PaymentSecurity("my-secret-key")
        future_time = int(time.time()) + 60
        payload = {"amount": "100", "network": "base-sepolia"}
        signature = sec.sign_payload(payload, timestamp=future_time)

        is_valid, error_msg = sec.verify_payload(payload, signature)

        assert is_valid is False
        assert "future" in error_msg.lower()

    def test_get_payment_security_default(self):
        """Get default PaymentSecurity instance."""
        sec = get_payment_security()

        assert sec is not None
        assert isinstance(sec, PaymentSecurity)

    def test_get_payment_security_custom_secret(self):
        """Get PaymentSecurity with custom secret."""
        sec = get_payment_security("custom-secret-123")

        assert sec is not None
        payload = {"test": "data"}
        sig = sec.sign_payload(payload, timestamp=1000)

        # Verify with same instance
        is_valid, _ = sec.verify_payload(payload, sig)
        assert is_valid is True

    def test_sign_and_verify_roundtrip(self):
        """Sign a payload and verify it works end-to-end."""
        sec = PaymentSecurity("production-secret")
        payload = {
            "x402_version": 1,
            "scheme": "exact",
            "network": "base-sepolia",
            "amount": "1000000000000000000",  # 1 token
            "from": "0x1234567890123456789012345678901234567890",
        }

        # Sign with current timestamp
        current_time = int(time.time())
        signature = sec.sign_payload(payload, timestamp=current_time)

        # Verify
        is_valid, error_msg = sec.verify_payload(payload, signature)

        assert is_valid is True
        assert error_msg is None

    def test_tampered_payload_detection(self):
        """Detect when payload has been tampered with."""
        sec = PaymentSecurity("secret-key")
        payload = {"amount": "100", "network": "base-sepolia"}
        signature = sec.sign_payload(payload, timestamp=1000)

        # Tamper with payload
        payload["amount"] = "1000000"

        is_valid, error_msg = sec.verify_payload(payload, signature)

        assert is_valid is False
        assert "Invalid" in error_msg
