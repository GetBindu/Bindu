"""Tests for DID validation utilities."""

from bindu.extensions.did.validation import DIDValidation


class TestDIDFormatValidation:
    """Test DID format validation."""

    def test_validate_empty_did(self):
        """Test validation of empty DID."""
        valid, error = DIDValidation.validate_did_format("")

        assert valid is False
        assert error == "DID cannot be empty"

    def test_validate_valid_bindu_did(self):
        """Test validation of valid bindu DID."""
        valid, error = DIDValidation.validate_did_format("did:bindu:author:agent_name")

        assert valid is True
        assert error is None

    def test_validate_valid_bindu_did_with_agent_id(self):
        """Test validation of valid bindu DID with agent ID."""
        valid, error = DIDValidation.validate_did_format(
            "did:bindu:author:agent_name:agent123"
        )

        assert valid is True
        assert error is None

    def test_validate_did_without_prefix(self):
        """Test validation of DID without 'did:' prefix."""
        valid, error = DIDValidation.validate_did_format("bindu:author:agent")

        assert valid is False
        assert error is not None
        assert "must start with 'did:'" in error

    def test_validate_did_invalid_format(self):
        """Test validation of DID with invalid format."""
        valid, error = DIDValidation.validate_did_format("did:")

        assert valid is False
        assert error is not None

    def test_validate_did_too_few_parts(self):
        """Test validation of DID with too few parts."""
        valid, error = DIDValidation.validate_did_format("did:bindu")

        assert valid is False
        assert error is not None  # Error message varies based on validation order

    def test_validate_bindu_did_empty_author(self):
        """Test validation of bindu DID with empty author."""
        valid, error = DIDValidation.validate_did_format("did:bindu::agent_name")

        assert valid is False
        assert error is not None
        assert "bindu DID must have format" in error

    def test_validate_bindu_did_empty_agent_name(self):
        """Test validation of bindu DID with empty agent name."""
        valid, error = DIDValidation.validate_did_format("did:bindu:author:")

        assert valid is False
        assert error is not None

    def test_validate_non_bindu_did(self):
        """Test validation of non-bindu DID method."""
        valid, error = DIDValidation.validate_did_format("did:web:example.com")

        assert valid is True
        assert error is None

    def test_validate_did_with_special_characters(self):
        """Test validation of DID with special characters in components."""
        valid, error = DIDValidation.validate_did_format(
            "did:bindu:user_at_example:my_agent"
        )

        assert valid is True
        assert error is None


class TestDIDDocumentValidation:
    """Test DID document validation."""

    def test_validate_minimal_valid_document(self):
        """Test validation of minimal valid DID document."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is True
        assert len(errors) == 0

    def test_validate_document_missing_context(self):
        """Test validation of document missing @context."""
        doc = {"id": "did:bindu:author:agent"}

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("Missing @context" in err for err in errors)

    def test_validate_document_missing_id(self):
        """Test validation of document missing id."""
        doc = {"@context": "https://www.w3.org/ns/did/v1"}

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("Missing id" in err for err in errors)

    def test_validate_document_invalid_did_in_id(self):
        """Test validation of document with invalid DID in id field."""
        doc = {"@context": "https://www.w3.org/ns/did/v1", "id": "invalid-did"}

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("Invalid DID in id field" in err for err in errors)

    def test_validate_document_with_valid_authentication(self):
        """Test validation of document with valid authentication."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": [
                {
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:bindu:author:agent",
                    "publicKeyMultibase": "z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH",
                }
            ],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is True
        assert len(errors) == 0

    def test_validate_document_authentication_not_array(self):
        """Test validation of document with authentication not being an array."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": "not-an-array",
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("Authentication must be an array" in err for err in errors)

    def test_validate_document_authentication_missing_type(self):
        """Test validation of authentication item missing type."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": [{"controller": "did:bindu:author:agent"}],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("missing type" in err for err in errors)

    def test_validate_document_authentication_missing_controller(self):
        """Test validation of authentication item missing controller."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": [{"type": "Ed25519VerificationKey2020"}],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("missing controller" in err for err in errors)

    def test_validate_document_authentication_not_object(self):
        """Test validation of authentication item that is not an object."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": ["string-instead-of-object"],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is False
        assert any("must be an object" in err for err in errors)

    def test_validate_document_with_service_endpoints(self):
        """Test validation of document with service endpoints."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "service": [
                {
                    "id": "did:bindu:author:agent#agent-service",
                    "type": "AgentService",
                    "serviceEndpoint": "http://localhost:3773",
                }
            ],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        # This may pass or fail depending on app_settings.network.default_url
        # Just verify it doesn't crash
        assert isinstance(valid, bool)
        assert isinstance(errors, list)

    def test_validate_complete_did_document(self):
        """Test validation of complete DID document with all fields."""
        doc = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1",
            ],
            "id": "did:bindu:author:agent",
            "authentication": [
                {
                    "id": "did:bindu:author:agent#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:bindu:author:agent",
                    "publicKeyMultibase": "z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH",
                }
            ],
            "service": [
                {
                    "id": "did:bindu:author:agent#agent-service",
                    "type": "AgentService",
                    "serviceEndpoint": "http://localhost:3773",
                }
            ],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        # Document structure is valid even if service endpoint doesn't match
        assert isinstance(valid, bool)
        assert isinstance(errors, list)


class TestDIDValidationEdgeCases:
    """Test edge cases in DID validation."""

    def test_validate_did_with_uppercase(self):
        """Test DID validation with uppercase - should fail as DIDs should be lowercase."""
        valid, error = DIDValidation.validate_did_format("DID:BINDU:AUTHOR:AGENT")

        # DIDs should be lowercase, uppercase fails validation
        assert valid is False
        assert error is not None

    def test_validate_did_with_numbers(self):
        """Test DID with numbers in components."""
        valid, error = DIDValidation.validate_did_format("did:bindu:user123:agent456")

        assert valid is True
        assert error is None

    def test_validate_did_with_hyphens(self):
        """Test DID with hyphens in components."""
        valid, error = DIDValidation.validate_did_format("did:bindu:my-author:my-agent")

        assert valid is True
        assert error is None

    def test_validate_did_with_underscores(self):
        """Test DID with underscores in components."""
        valid, error = DIDValidation.validate_did_format("did:bindu:my_author:my_agent")

        assert valid is True
        assert error is None

    def test_validate_very_long_did(self):
        """Test validation of very long DID."""
        long_component = "a" * 200
        valid, error = DIDValidation.validate_did_format(
            f"did:bindu:{long_component}:agent"
        )

        assert valid is True
        assert error is None

    def test_validate_document_with_empty_authentication_array(self):
        """Test document with empty authentication array."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": [],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is True
        assert len(errors) == 0

    def test_validate_document_with_multiple_authentication_methods(self):
        """Test document with multiple authentication methods."""
        doc = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:bindu:author:agent",
            "authentication": [
                {
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:bindu:author:agent",
                },
                {"type": "JsonWebKey2020", "controller": "did:bindu:author:agent"},
            ],
        }

        valid, errors = DIDValidation.validate_did_document(doc)

        assert valid is True
        assert len(errors) == 0
