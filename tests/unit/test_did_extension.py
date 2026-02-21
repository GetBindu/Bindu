"""Unit tests for DID Agent Extension and related utilities."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from bindu.extensions.did.did_agent_extension import DIDAgentExtension
from bindu.settings import app_settings

# Import the sanitize_did_for_schema for schema utility tests
from bindu.utils.schema_manager import sanitize_did_for_schema

class TestDIDAgentExtension:
    """Test suite for DID Agent Extension."""

    @pytest.fixture
    def temp_key_dir(self):
        """Create a temporary directory for keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def did_extension(self, temp_key_dir):
        """Create a DID extension instance."""
        return DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

    # --- Begin tests for sanitize_did_for_schema ---

    @pytest.mark.parametrize(
        "did,expected",
        [
            # Test lowercase conversion and replacement
            ("did:Bindu:Bob:Example/ABC.123", "did_bindu_bob_example_abc_123"),
            ("DID:TEST:ABC", "did_test_abc"),
            # Test non-alphanumeric replacement
            ("did:Bindu:Name-With*Special#Chars", "did_bindu_name_with_special_chars"),
            # Test numeric prefix becomes 'schema_' prefix
            ("1did:bindu:abc", "schema_1did_bindu_abc"),
            ("7_PREFIX:foo", "schema_7_prefix_foo"),
            # Already starts with underscore is okay
            ("_abc:def", "_abc_def"),
            # Already starts with a letter is preserved
            ("abc:def:ghi", "abc_def_ghi"),
        ]
    )
    def test_sanitize_did_for_schema_basic(self, did, expected):
        """Test DID schema sanitization - lowercase and underscore rules, digit prefix."""
        schema = sanitize_did_for_schema(did)
        assert schema == expected

    def test_truncation_and_hash(self):
        """Test schema truncation at 63 chars with hash suffix for long names."""
        import hashlib

        # Build a DID such that, after norm/replacement, it's >63 chars
        base = "did:bindu:" + "a" * 60  # base replaced will be ~71 chars
        schema = sanitize_did_for_schema(base)
        # Should be exactly 63 chars
        assert len(schema) == 63

        # It should end with _ + 8 hex chars (from sha256), and up to 54 base chars
        base_replaced = "did_bindu_" + "a" * 60
        hash_suffix = hashlib.sha256(base_replaced.encode()).hexdigest()[:8]
        expected_prefix = base_replaced[:54]
        assert schema == f"{expected_prefix}_{hash_suffix}"

        # Test that the hash is actually derived from the full original string
        # Even for different long DIDs, hash should be different if string differs
        base2 = "did:bindu:" + "b" * 60
        schema2 = sanitize_did_for_schema(base2)
        assert schema != schema2

    @pytest.mark.parametrize(
        "orig,expected_prefix",
        [
            # Truncation should still apply even if prefix is added
            ("8" + "b" * 70, "schema_8" + "b" * 45),  # schema_ + 8 + 45*'b' = 54 chars before _hash
        ],
    )
    def test_schema_prefix_and_truncation(self, orig, expected_prefix):
        """Test digit prefix and truncation."""
        import hashlib

        replaced = "".join(["_" if not c.isalnum() else c.lower() for c in orig])
        # In the logic, if it begins with digit, shows as 'schema_' + replaced.
        if replaced[0].isdigit():
            candidate = f"schema_{replaced}"
        else:
            candidate = replaced

        hash_suffix = hashlib.sha256(candidate.encode()).hexdigest()[:8]
        # Full final name = up to 54 chars + _ + hash (8 chars)
        expected = f"{expected_prefix}_{hash_suffix}"
        result = sanitize_did_for_schema(orig)
        assert result == expected
        assert len(result) == 63

    # --- End tests for sanitize_did_for_schema ---

    def test_initialization(self, temp_key_dir):
        """Test DID extension initialization."""
        agent_id = str(uuid4())
        ext = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="alice@example.com",
            agent_name="travel_agent",
            agent_id=agent_id,
        )

        assert ext.author == "alice@example.com"
        assert ext.agent_name == "travel_agent"
        assert ext.agent_id == agent_id
        assert (
            ext.private_key_path == temp_key_dir / app_settings.did.private_key_filename
        )
        assert (
            ext.public_key_path == temp_key_dir / app_settings.did.public_key_filename
        )

    def test_initialization_with_password(self, temp_key_dir):
        """Test DID extension initialization with password."""
        ext = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password="test-password",
        )

        assert ext.key_password == b"test-password"

    def test_generate_and_save_key_pair(self, did_extension):
        """Test key pair generation and saving."""
        paths = did_extension.generate_and_save_key_pair()

        assert "private_key_path" in paths
        assert "public_key_path" in paths
        assert Path(paths["private_key_path"]).exists()
        assert Path(paths["public_key_path"]).exists()

    def test_generate_and_save_key_pair_skip_existing(self, did_extension):
        """Test that key generation is skipped if keys exist."""
        # Generate keys first time
        did_extension.generate_and_save_key_pair()

        # Create new extension with same dir, recreate_keys=False
        ext2 = DIDAgentExtension(
            recreate_keys=False,
            key_dir=did_extension._key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        # Should skip generation
        paths = ext2.generate_and_save_key_pair()
        assert Path(paths["private_key_path"]).exists()

    def test_generate_and_save_key_pair_recreate(self, did_extension):
        """Test that keys are recreated when recreate_keys=True."""
        # Generate keys first time
        did_extension.generate_and_save_key_pair()
        first_private_key = did_extension.private_key_path.read_bytes()

        # Create new extension with recreate_keys=True
        ext2 = DIDAgentExtension(
            recreate_keys=True,
            key_dir=did_extension._key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        # Should regenerate
        ext2.generate_and_save_key_pair()
        second_private_key = ext2.private_key_path.read_bytes()

        # Keys should be different
        assert first_private_key != second_private_key

    def test_load_private_key(self, did_extension):
        """Test loading private key from file."""
        did_extension.generate_and_save_key_pair()
        private_key = did_extension.private_key

        assert private_key is not None
        from cryptography.hazmat.primitives.asymmetric import ed25519

        assert isinstance(private_key, ed25519.Ed25519PrivateKey)

    def test_load_public_key(self, did_extension):
        """Test loading public key from file."""
        did_extension.generate_and_save_key_pair()
        public_key = did_extension.public_key

        assert public_key is not None
        from cryptography.hazmat.primitives.asymmetric import ed25519

        assert isinstance(public_key, ed25519.Ed25519PublicKey)

    def test_load_key_file_not_found(self, temp_key_dir):
        """Test error when key file doesn't exist."""
        ext = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        with pytest.raises(FileNotFoundError):
            _ = ext.private_key

    def test_sign_and_verify_text(self, did_extension):
        """Test signing and verifying text."""
        did_extension.generate_and_save_key_pair()

        text = "Hello, World!"
        signature = did_extension.sign_text(text)

        assert signature is not None
        assert isinstance(signature, str)
        assert did_extension.verify_text(text, signature) is True

    def test_verify_invalid_signature(self, did_extension):
        """Test verifying invalid signature."""
        did_extension.generate_and_save_key_pair()

        text = "Hello, World!"
        signature = did_extension.sign_text(text)

        # Verify with different text should fail
        assert did_extension.verify_text("Different text", signature) is False

    def test_verify_malformed_signature(self, did_extension):
        """Test verifying malformed signature."""
        did_extension.generate_and_save_key_pair()

        # Should return False for invalid signature
        assert did_extension.verify_text("test", "invalid-signature") is False

    def test_custom_did_format(self, temp_key_dir):
        """Test custom bindu DID format."""
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        ext = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="alice@example.com",
            agent_name="Travel Agent",
            agent_id=agent_id,
        )
        ext.generate_and_save_key_pair()

        did = ext.did
        assert did.startswith("did:bindu:")
        assert "alice_at_example_com" in did
        assert "travel_agent" in did
        assert agent_id in did

    def test_fallback_did_format(self, temp_key_dir):
        """Test fallback to did:key format when author/name not provided."""
        ext = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
        )
        ext.generate_and_save_key_pair()

        did = ext.did
        assert did.startswith("did:key:")

    def test_get_did_document(self, did_extension):
        """Test generating DID document."""
        did_extension.generate_and_save_key_pair()

        doc = did_extension.get_did_document()

        assert "@context" in doc
        assert doc["id"] == did_extension.did
        assert "created" in doc
        assert "authentication" in doc
        assert len(doc["authentication"]) == 1
        assert (
            doc["authentication"][0]["type"] == app_settings.did.verification_key_type
        )

    def test_public_key_base58(self, did_extension):
        """Test base58-encoded public key."""
        did_extension.generate_and_save_key_pair()

        pub_key_b58 = did_extension.public_key_base58
        assert pub_key_b58 is not None
        assert isinstance(pub_key_b58, str)
        assert len(pub_key_b58) > 0

    def test_encrypted_key_without_password(self, temp_key_dir):
        """Test loading encrypted key without password raises error."""
        # Create extension with password and generate keys
        ext1 = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password="test-password",
        )
        ext1.generate_and_save_key_pair()

        # Try to load with different extension without password
        ext2 = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        with pytest.raises(ValueError, match="Private key is encrypted"):
            _ = ext2.private_key

    def test_key_with_correct_password(self, temp_key_dir):
        """Test loading encrypted key with correct password."""
        password = "secure-password"

        # Create and save encrypted keys
        ext1 = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password=password,
        )
        ext1.generate_and_save_key_pair()

        # Load with same password
        ext2 = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password=password,
        )

        # Should load successfully
        private_key = ext2.private_key
        assert private_key is not None

    def test_file_permissions(self, did_extension):
        """Test that private key has correct file permissions."""
        did_extension.generate_and_save_key_pair()

        # Check private key permissions (should be 0o600)
        import stat

        private_key_stat = did_extension.private_key_path.stat()
        private_key_mode = stat.S_IMODE(private_key_stat.st_mode)
        assert private_key_mode == 0o600

        # Check public key permissions (should be 0o644)
        public_key_stat = did_extension.public_key_path.stat()
        public_key_mode = stat.S_IMODE(public_key_stat.st_mode)
        assert public_key_mode == 0o644
