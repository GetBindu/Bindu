"""Unit tests for DID signature utilities."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bindu.utils.did_signature import (
    create_signature_payload,
    sign_request,
    verify_signature,
    extract_signature_headers,
    validate_timestamp,
    create_signed_request_headers,
)


class TestSignaturePayload:
    """Test signature payload creation."""

    def test_create_signature_payload_with_dict(self):
        """Test creating signature payload from dict."""
        body = {"key": "value", "number": 123}
        did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
        timestamp = 1234567890

        payload = create_signature_payload(body, did, timestamp)

        assert payload["did"] == did
        assert payload["timestamp"] == timestamp
        assert json.loads(payload["body"]) == body

    def test_create_signature_payload_with_string(self):
        """Test creating signature payload from string."""
        body = "test body"
        did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
        timestamp = 1234567890

        payload = create_signature_payload(body, did, timestamp)

        assert payload["body"] == body
        assert payload["did"] == did
        assert payload["timestamp"] == timestamp

    def test_create_signature_payload_with_bytes(self):
        """Test creating signature payload from bytes."""
        body = b"test body bytes"
        did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"

        payload = create_signature_payload(body, did)

        assert payload["body"] == "test body bytes"
        assert payload["did"] == did
        assert isinstance(payload["timestamp"], int)

    def test_create_signature_payload_auto_timestamp(self):
        """Test that timestamp is auto-generated if not provided."""
        body = "test"
        did = "did:key:test"

        before = int(time.time())
        payload = create_signature_payload(body, did)
        after = int(time.time())

        assert before <= payload["timestamp"] <= after


class TestSignRequest:
    """Test request signing."""

    def test_sign_request_returns_headers(self):
        """Test that sign_request returns correct headers."""
        body = {"test": "data"}
        did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"

        mock_did_ext = MagicMock()
        mock_did_ext.sign_message.return_value = "mock_signature_12345"

        headers = sign_request(body, did, mock_did_ext, timestamp=1234567890)

        assert headers["X-DID"] == did
        assert headers["X-DID-Signature"] == "mock_signature_12345"
        assert headers["X-DID-Timestamp"] == "1234567890"

        # Verify sign_message was called
        mock_did_ext.sign_message.assert_called_once()


class TestVerifySignature:
    """Test signature verification."""

    @patch("base58.b58decode")
    @patch("nacl.signing.VerifyKey")
    def test_verify_signature_valid(self, mock_verify_key_class, mock_b58decode):
        """Test verifying a valid signature."""
        # Mock base58 decoding to return fake bytes
        mock_b58decode.return_value = b"fake_decoded_bytes"

        # Mock the verify method to not raise an exception (valid signature)
        mock_verify_key = mock_verify_key_class.return_value
        mock_verify_key.verify.return_value = None  # No exception = valid

        body = {"test": "data"}
        signature = "valid_signature"
        did = "did:key:test"
        timestamp = int(time.time())
        public_key = "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"  # pragma: allowlist secret

        result = verify_signature(body, signature, did, timestamp, public_key)

        assert result is True

    def test_verify_signature_expired_timestamp(self):
        """Test that expired timestamps are rejected."""
        body = {"test": "data"}
        signature = "signature"
        did = "did:key:test"
        timestamp = int(time.time()) - 600  # 10 minutes ago
        public_key = "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"  # pragma: allowlist secret

        # Should fail due to timestamp, not signature verification
        result = verify_signature(
            body, signature, did, timestamp, public_key, max_age_seconds=300
        )

        assert result is False

    @patch("base58.b58decode")
    @patch("nacl.signing.VerifyKey")
    def test_verify_signature_invalid(self, mock_verify_key_class, mock_b58decode):
        """Test verifying an invalid signature."""
        from nacl.exceptions import BadSignatureError

        # Mock base58 decoding to return fake bytes
        mock_b58decode.return_value = b"fake_decoded_bytes"

        # Mock the verify method to raise BadSignatureError (invalid signature)
        mock_verify_key = mock_verify_key_class.return_value
        mock_verify_key.verify.side_effect = BadSignatureError("Invalid signature")

        body = {"test": "data"}
        signature = "invalid_signature"
        did = "did:key:test"
        timestamp = int(time.time())
        public_key = "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"  # pragma: allowlist secret

        result = verify_signature(body, signature, did, timestamp, public_key)

        assert result is False


class TestExtractSignatureHeaders:
    """Test extracting signature headers from requests."""

    def test_extract_signature_headers_success(self):
        """Test extracting valid signature headers."""
        headers = {
            "X-DID": "did:key:test",
            "X-DID-Signature": "signature123",
            "X-DID-Timestamp": "1234567890",
        }

        result = extract_signature_headers(headers)

        assert result is not None
        assert result["did"] == "did:key:test"
        assert result["signature"] == "signature123"
        assert result["timestamp"] == 1234567890

    def test_extract_signature_headers_lowercase(self):
        """Test extracting headers with lowercase keys."""
        headers = {
            "x-did": "did:key:test",
            "x-did-signature": "signature123",
            "x-did-timestamp": "1234567890",
        }

        result = extract_signature_headers(headers)

        assert result is not None
        assert result["did"] == "did:key:test"

    def test_extract_signature_headers_missing(self):
        """Test that missing headers return None."""
        headers = {
            "X-DID": "did:key:test",
            # Missing signature and timestamp
        }

        result = extract_signature_headers(headers)

        assert result is None

    def test_extract_signature_headers_invalid_timestamp(self):
        """Test that invalid timestamp format returns None."""
        headers = {
            "X-DID": "did:key:test",
            "X-DID-Signature": "signature123",
            "X-DID-Timestamp": "not_a_number",
        }

        result = extract_signature_headers(headers)

        assert result is None


class TestValidateTimestamp:
    """Test timestamp validation."""

    def test_validate_timestamp_valid(self):
        """Test validating a recent timestamp."""
        timestamp = int(time.time())

        result = validate_timestamp(timestamp, max_age_seconds=300)

        assert result is True

    def test_validate_timestamp_expired(self):
        """Test that old timestamps are rejected."""
        timestamp = int(time.time()) - 600  # 10 minutes ago

        result = validate_timestamp(timestamp, max_age_seconds=300)

        assert result is False

    def test_validate_timestamp_future(self):
        """Test that future timestamps within tolerance are accepted."""
        timestamp = int(time.time()) + 10  # 10 seconds in future

        result = validate_timestamp(timestamp, max_age_seconds=300)

        assert result is True


@pytest.mark.asyncio
class TestGetPublicKeyFromHydra:
    """Test getting public key from Hydra metadata."""

    async def test_get_public_key_success(self):
        """Test successfully getting public key."""
        from bindu.utils.did_signature import get_public_key_from_hydra

        mock_hydra = AsyncMock()
        mock_hydra.get_oauth_client.return_value = {
            "client_id": "did:key:test",
            "metadata": {
                "public_key": "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"  # pragma: allowlist secret
            },
        }

        public_key = await get_public_key_from_hydra("did:key:test", mock_hydra)

        assert (
            public_key
            == "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"  # pragma: allowlist secret
        )

    async def test_get_public_key_not_found(self):
        """Test when client is not found."""
        from bindu.utils.did_signature import get_public_key_from_hydra

        mock_hydra = AsyncMock()
        mock_hydra.get_oauth_client.return_value = None

        public_key = await get_public_key_from_hydra("did:key:test", mock_hydra)

        assert public_key is None

    async def test_get_public_key_no_metadata(self):
        """Test when client has no public key in metadata."""
        from bindu.utils.did_signature import get_public_key_from_hydra

        mock_hydra = AsyncMock()
        mock_hydra.get_oauth_client.return_value = {
            "client_id": "did:key:test",
            "metadata": {},
        }

        public_key = await get_public_key_from_hydra("did:key:test", mock_hydra)

        assert public_key is None

    async def test_get_public_key_exception(self):
        """Test exception handling in get_public_key_from_hydra."""
        from bindu.utils.did_signature import get_public_key_from_hydra

        mock_hydra = AsyncMock()
        mock_hydra.get_oauth_client.side_effect = Exception("Connection error")

        public_key = await get_public_key_from_hydra("did:key:test", mock_hydra)

        assert public_key is None


class TestVerifySignatureException:
    """Test verify_signature exception handling."""

    @patch("base58.b58decode")
    def test_verify_signature_exception_handling(self, mock_b58decode):
        """Test exception handling in verify_signature."""
        from bindu.utils.did_signature import verify_signature
        import time

        # Make b58decode raise an exception
        mock_b58decode.side_effect = Exception("Decoding error")

        body = {"test": "data"}
        signature = "invalid_signature"
        did = "did:key:test"
        timestamp = int(time.time())
        public_key = "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"  # pragma: allowlist secret

        result = verify_signature(body, signature, did, timestamp, public_key)

        assert result is False


class TestCreateSignedRequestHeaders:
    """Test creating signed request headers."""

    def test_create_signed_request_headers(self):
        """Test creating complete signed request headers."""

        mock_did_ext = MagicMock()
        mock_did_ext.sign_message.return_value = "test_signature"

        body = {"test": "data"}
        did = "did:key:test"
        bearer_token = "test_bearer_token"  # pragma: allowlist secret

        with patch("bindu.utils.did_signature.int") as mock_int:
            mock_int.return_value = 1234567890

            headers = create_signed_request_headers(
                body, did, mock_did_ext, bearer_token
            )

            assert "Authorization" in headers
            assert (
                headers["Authorization"] == "Bearer test_bearer_token"
            )  # pragma: allowlist secret
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"
            assert "X-DID" in headers
            assert "X-DID-Signature" in headers
            assert "X-DID-Timestamp" in headers
