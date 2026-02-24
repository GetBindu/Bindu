from bindu.utils.schema_manager import sanitize_did_for_schema


def test_basic_sanitization():
    did = "did:bindu:alice:agent1:abc123"
    result = sanitize_did_for_schema(did)

    assert result == "did_bindu_alice_agent1_abc123"


def test_lowercasing():
    did = "DID:Bindu:ALICE"
    result = sanitize_did_for_schema(did)

    assert result == "did_bindu_alice"


def test_digit_prefix():
    did = "123:alice"
    result = sanitize_did_for_schema(did)

    assert result.startswith("schema_")
    assert result == "schema_123_alice"


def test_truncation_and_hashing():
    long_did = "did:bindu:" + "a" * 100
    result = sanitize_did_for_schema(long_did)

    # PostgreSQL max length
    assert len(result) <= 63

    # Should contain hash suffix
    assert "_" in result
    assert len(result.split("_")[-1]) == 8


def test_deterministic_hashing():
    long_did = "did:bindu:" + "x" * 100

    result1 = sanitize_did_for_schema(long_did)
    result2 = sanitize_did_for_schema(long_did)

    assert result1 == result2
