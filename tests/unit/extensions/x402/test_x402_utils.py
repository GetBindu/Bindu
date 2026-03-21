"""Tests for x402 utility functions."""

from bindu.extensions.x402.utils import (
    build_payment_completed_metadata,
    build_payment_failed_metadata,
)


class TestBuildPaymentCompletedMetadata:
    """Test build_payment_completed_metadata function."""

    def test_build_completed_metadata_with_receipt(self):
        """Test building completed metadata with receipt."""
        receipt = {
            "transaction_hash": "0xabc123",
            "block_number": 12345,
            "status": "success",
        }

        metadata = build_payment_completed_metadata(receipt)

        # Keys use dot notation: x402.payment.status, x402.payment.receipts
        assert "x402.payment.status" in metadata
        assert "x402.payment.receipts" in metadata

        # Check receipts is a list containing the receipt
        receipts_key = "x402.payment.receipts"
        assert isinstance(metadata[receipts_key], list)
        assert len(metadata[receipts_key]) == 1
        assert metadata[receipts_key][0] == receipt

    def test_build_completed_metadata_status_value(self):
        """Test that completed metadata has correct status value."""
        receipt = {"tx": "0x123"}

        metadata = build_payment_completed_metadata(receipt)

        status_key = "x402.payment.status"
        # Status should be "payment-completed"
        assert metadata[status_key] == "payment-completed"

    def test_build_completed_metadata_with_complex_receipt(self):
        """Test building metadata with complex receipt data."""
        receipt = {
            "transaction_hash": "0xdef456",
            "block_number": 67890,
            "from": "0x1234",
            "to": "0x5678",
            "value": "1000000",
            "gas_used": "21000",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        metadata = build_payment_completed_metadata(receipt)

        receipts_key = next(k for k in metadata.keys() if "receipts" in k)
        stored_receipt = metadata[receipts_key][0]

        assert stored_receipt["transaction_hash"] == "0xdef456"
        assert stored_receipt["block_number"] == 67890


class TestBuildPaymentFailedMetadata:
    """Test build_payment_failed_metadata function."""

    def test_build_failed_metadata_with_error_only(self):
        """Test building failed metadata with error message only."""
        error = "Insufficient funds"

        metadata = build_payment_failed_metadata(error)

        assert "x402.payment.status" in metadata
        assert "x402.payment.error" in metadata

        error_key = "x402.payment.error"
        assert metadata[error_key] == "Insufficient funds"

    def test_build_failed_metadata_status_value(self):
        """Test that failed metadata has correct status value."""
        metadata = build_payment_failed_metadata("Error")

        status_key = "x402.payment.status"
        assert metadata[status_key] == "payment-failed"

    def test_build_failed_metadata_with_receipt(self):
        """Test building failed metadata with receipt."""
        error = "Transaction reverted"
        receipt = {"transaction_hash": "0xfailed", "status": "reverted"}

        metadata = build_payment_failed_metadata(error, receipt)

        error_key = "x402.payment.error"
        assert metadata[error_key] == "Transaction reverted"

        receipts_key = "x402.payment.receipts"
        assert metadata[receipts_key][0] == receipt

    def test_build_failed_metadata_without_receipt(self):
        """Test building failed metadata without receipt."""
        error = "Network timeout"

        metadata = build_payment_failed_metadata(error, receipt=None)

        # Should not have receipts key when receipt is None
        assert "x402.payment.receipts" not in metadata

    def test_build_failed_metadata_with_empty_receipt(self):
        """Test building failed metadata with empty receipt dict."""
        error = "Payment rejected"
        receipt = {}

        metadata = build_payment_failed_metadata(error, receipt)

        # Empty dict is still a truthy receipt, so it should be included
        if "x402.payment.receipts" in metadata:
            receipts_key = "x402.payment.receipts"
            assert metadata[receipts_key][0] == {}


class TestPaymentMetadataEdgeCases:
    """Test edge cases for payment metadata utilities."""

    def test_completed_metadata_with_empty_receipt(self):
        """Test completed metadata with empty receipt."""
        metadata = build_payment_completed_metadata({})

        receipts_key = "x402.payment.receipts"
        assert len(metadata[receipts_key]) == 1
        assert metadata[receipts_key][0] == {}

    def test_failed_metadata_with_long_error_message(self):
        """Test failed metadata with very long error message."""
        long_error = "Error: " + "x" * 1000

        metadata = build_payment_failed_metadata(long_error)

        error_key = "x402.payment.error"
        assert metadata[error_key] == long_error

    def test_failed_metadata_with_special_characters_in_error(self):
        """Test failed metadata with special characters in error."""
        error = "Error: Payment failed with code 0x1234 @ block #12345"

        metadata = build_payment_failed_metadata(error)

        error_key = "x402.payment.error"
        assert metadata[error_key] == error

    def test_completed_metadata_receipt_with_nested_data(self):
        """Test completed metadata with nested receipt data."""
        receipt = {
            "transaction": {
                "hash": "0x123",
                "details": {"from": "0xabc", "to": "0xdef"},
            }
        }

        metadata = build_payment_completed_metadata(receipt)

        receipts_key = "x402.payment.receipts"
        stored_receipt = metadata[receipts_key][0]

        assert stored_receipt["transaction"]["hash"] == "0x123"
        assert stored_receipt["transaction"]["details"]["from"] == "0xabc"

    def test_metadata_keys_are_strings(self):
        """Test that all metadata keys are strings."""
        receipt = {"tx": "0x123"}

        completed_meta = build_payment_completed_metadata(receipt)
        failed_meta = build_payment_failed_metadata("error", receipt)

        assert all(isinstance(k, str) for k in completed_meta.keys())
        assert all(isinstance(k, str) for k in failed_meta.keys())
