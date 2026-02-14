"""Tests for x402 constants."""

from bindu.extensions.x402.constants import (
    X402_EXTENSION_URI,
    X402Metadata,
    X402Status,
)


class TestX402Constants:
    """Test x402 constants."""

    def test_extension_uri(self):
        """Test x402 extension URI."""
        assert X402_EXTENSION_URI == "https://github.com/google-a2a/a2a-x402/v0.1"


class TestX402Metadata:
    """Test x402 metadata keys."""

    def test_metadata_keys(self):
        """Test all metadata key constants."""
        assert X402Metadata.STATUS_KEY == "x402.payment.status"
        assert X402Metadata.REQUIRED_KEY == "x402.payment.required"
        assert X402Metadata.PAYLOAD_KEY == "x402.payment.payload"
        assert X402Metadata.RECEIPTS_KEY == "x402.payment.receipts"
        assert X402Metadata.ERROR_KEY == "x402.payment.error"


class TestX402Status:
    """Test x402 status values."""

    def test_status_values(self):
        """Test all status value constants."""
        assert X402Status.PAYMENT_REQUIRED == "payment-required"
        assert X402Status.PAYMENT_SUBMITTED == "payment-submitted"
        assert X402Status.PAYMENT_VERIFIED == "payment-verified"
        assert X402Status.PAYMENT_COMPLETED == "payment-completed"
        assert X402Status.PAYMENT_FAILED == "payment-failed"
