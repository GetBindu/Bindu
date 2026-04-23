"""Tests for ``create_signature_payload`` and ``sign_request`` contract.

The single invariant these tests guard: **the caller must serialize
its body to bytes/str exactly once, and both the signing path and
the wire must use those exact bytes.** The pre-cleanup function
silently canonicalized a dict into a different string than the
bytes that would hit the wire, which caused dict-caller +
bytes-verifier pairs to disagree on the signature even when they
were signing the same logical data.

The cleanup removes the ``dict`` input branch — callers with a dict
now have to serialize explicitly, which surfaces the choice of
canonicalization and prevents the silent-mismatch bug.

See ``bugs/core/2026-04-19-create-signature-payload-dict-branch.md``
when it lands for the full story.
"""

from __future__ import annotations

import json

import pytest

from bindu.utils.did.signature import create_signature_payload, sign_request


class TestCreateSignaturePayload:
    def test_bytes_input_decoded_raw(self):
        body = b'{"x": 1}'
        out = create_signature_payload(body, did="did:bindu:test", timestamp=1000)
        assert out == {
            "body": '{"x": 1}',
            "did": "did:bindu:test",
            "timestamp": 1000,
        }

    def test_str_input_passes_through_unchanged(self):
        body = '{"x": 1}'
        out = create_signature_payload(body, did="did:bindu:test", timestamp=1000)
        assert out["body"] == body

    def test_bytes_with_non_ascii_content(self):
        """UTF-8 content round-trips through decode()."""
        body = '{"msg": "hëllo"}'.encode("utf-8")
        out = create_signature_payload(body, did="did:bindu:test", timestamp=1000)
        assert out["body"] == '{"msg": "hëllo"}'

    def test_dict_input_rejected(self):
        """A dict used to be silently canonicalized with
        ``json.dumps(body, sort_keys=True)``. That produced a string
        different from the wire bytes any normal JSON encoder would
        produce, and the signing side and verifying side disagreed.

        Post-cleanup: dict is explicitly rejected so callers must
        serialize ONCE and use the same bytes for signing and for the
        HTTP body."""
        with pytest.raises(TypeError, match="json.dumps"):
            create_signature_payload(
                {"x": 1},  # type: ignore[arg-type]
                did="did:bindu:test",
                timestamp=1000,
            )

    def test_list_input_rejected(self):
        """Any non-str/bytes rejected — not just dict."""
        with pytest.raises(TypeError, match="str or bytes"):
            create_signature_payload(
                [1, 2, 3],  # type: ignore[arg-type]
                did="did:bindu:test",
                timestamp=1000,
            )

    def test_timestamp_defaults_to_now_if_none(self):
        """Default timestamp is current time to within a second."""
        import time

        before = int(time.time())
        out = create_signature_payload(b"{}", did="did:bindu:test")
        after = int(time.time())
        assert before <= out["timestamp"] <= after

    def test_returns_stable_keys(self):
        """The returned dict has exactly these three keys, in any
        order — the caller does ``json.dumps(..., sort_keys=True)``
        before signing."""
        out = create_signature_payload(b"{}", did="did:bindu:x", timestamp=1)
        assert set(out.keys()) == {"body", "did", "timestamp"}


class TestSignRequest:
    """``sign_request`` is the thin wrapper that produces the three
    X-DID-* headers. It delegates serialization to
    ``create_signature_payload``, so the same type contract applies."""

    class _FakeExt:
        calls: list[str] = []

        def sign_message(self, text: str) -> str:
            # Record the exact payload the signer was asked to sign —
            # tests assert on this to prove the canonicalization path.
            self.calls.append(text)
            return "dummy-signature"

    def test_bytes_body_produces_headers(self):
        ext = self._FakeExt()
        headers = sign_request(
            body=b'{"x": 1}',
            did="did:bindu:test",
            did_extension=ext,
            timestamp=1000,
        )
        assert headers["X-DID"] == "did:bindu:test"
        assert headers["X-DID-Timestamp"] == "1000"
        assert headers["X-DID-Signature"] == "dummy-signature"

    def test_signer_sees_canonical_payload_with_body_as_is(self):
        """Guards the ``body`` string is passed through unchanged, not
        re-serialized. A body of ``'{"x": 1}'`` must appear in the
        signed payload with that exact content — any whitespace
        difference from a re-parse-and-redump would produce a
        different signature than the server will reconstruct from the
        wire bytes."""
        ext = self._FakeExt()
        sign_request(
            body=b'{"x": 1}',
            did="did:bindu:t",
            did_extension=ext,
            timestamp=1000,
        )
        # The payload handed to sign_message contains the body as-is.
        signed_payload = json.loads(ext.calls[0])
        assert signed_payload["body"] == '{"x": 1}'

    def test_dict_body_rejected(self):
        """Same TypeError as create_signature_payload — dict is out."""
        with pytest.raises(TypeError):
            sign_request(
                body={"x": 1},  # type: ignore[arg-type]
                did="did:bindu:t",
                did_extension=self._FakeExt(),
                timestamp=1000,
            )
