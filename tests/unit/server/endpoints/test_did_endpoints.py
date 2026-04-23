"""Tests for ``did_endpoints._normalize_did_document_keys``.

The DID document is assembled as a plain dict by the DID extension
rather than a pydantic model (the W3C ``@context`` key is not a valid
Python identifier). The ``/did/resolve`` endpoint must still emit
camelCase on the wire to match the rest of the A2A protocol. These
tests guard that guarantee so a future extension adding a
snake_case field cannot silently leak through.

See ``bugs/core/2026-04-19-did-document-endpoint-raw-dict.md`` for
context.
"""

from __future__ import annotations

from bindu.server.endpoints.did_endpoints import _normalize_did_document_keys


class TestNormalizeDidDocumentKeys:
    """Guard the camelCase contract on DID document serialization."""

    def test_today_w3c_document_passes_through_unchanged(self):
        """Current ``get_did_document()`` output is already W3C-correct.
        Normalizer must not damage it — no over-eager transforms."""
        today = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://getbindu.com/ns/v1",
            ],
            "id": "did:bindu:raahul_dutta_at_example_com:joke_agent:x",
            "created": "2026-04-18T00:00:00+00:00",
            "authentication": [
                {
                    "id": "did:bindu:x#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:bindu:x",
                    "publicKeyBase58": "7dNzT2ZzYKsibUFirPVWZheh2TGKZuy3fGdCkcq2f2RM",
                }
            ],
        }
        assert _normalize_did_document_keys(today) == today

    def test_at_context_preserved(self):
        """W3C JSON-LD uses ``@context`` — the ``@`` prefix is
        intentional and must pass through."""
        doc = {"@context": ["https://example.com"]}
        assert _normalize_did_document_keys(doc) == doc

    def test_snake_case_converted_to_camel(self):
        """This is the fix — a future extension adds snake_case,
        it comes out camelCase."""
        doc = {"service_endpoint": "https://example.com/svc"}
        assert _normalize_did_document_keys(doc) == {
            "serviceEndpoint": "https://example.com/svc"
        }

    def test_already_camel_passes_through(self):
        """Don't double-transform already-camelCase keys."""
        doc = {"publicKeyBase58": "ABC", "keyAgreement": []}
        assert _normalize_did_document_keys(doc) == doc

    def test_nested_dicts_normalized(self):
        """snake_case inside a nested object must also convert."""
        doc = {
            "authentication": [
                {
                    "public_key_base58": "X",
                    "verification_method": "vm",
                }
            ],
        }
        out = _normalize_did_document_keys(doc)
        assert out["authentication"][0] == {
            "publicKeyBase58": "X",
            "verificationMethod": "vm",
        }

    def test_mixed_keys_in_same_object(self):
        """A realistic future document: W3C keys + Bindu-specific ones."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:x",
            "agent_trust": {
                "identity_provider": "hydra",
                "inherited_roles": [],
                "creator_id": "system",
            },
        }
        out = _normalize_did_document_keys(doc)
        assert "@context" in out
        assert "id" in out
        assert "agentTrust" in out and "agent_trust" not in out
        assert out["agentTrust"] == {
            "identityProvider": "hydra",
            "inheritedRoles": [],
            "creatorId": "system",
        }

    def test_scalars_and_none_pass_through(self):
        """Non-dict / non-list values at the top level return unchanged."""
        assert _normalize_did_document_keys("did:bindu:x") == "did:bindu:x"
        assert _normalize_did_document_keys(42) == 42
        assert _normalize_did_document_keys(None) is None
        assert _normalize_did_document_keys(True) is True

    def test_empty_containers(self):
        """Empty dicts and lists are valid JSON — must round-trip."""
        assert _normalize_did_document_keys({}) == {}
        assert _normalize_did_document_keys([]) == []

    def test_list_of_mixed_types(self):
        """Lists can contain a mix of dicts, lists, and scalars."""
        value = [{"snake_key": 1}, ["nested"], "scalar", 42]
        assert _normalize_did_document_keys(value) == [
            {"snakeKey": 1},
            ["nested"],
            "scalar",
            42,
        ]
