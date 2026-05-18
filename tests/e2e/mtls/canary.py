"""Production canary for the mTLS bootstrap path.

Exercises the live stack end-to-end against the production deployment:

  1. Register a throwaway OAuth2 client in Hydra with ``audience=step-ca``
  2. Mint a token via ``client_credentials`` grant, requesting that audience
  3. Verify the token actually carries ``aud=step-ca`` in its claims
  4. Drive ``MTLSAgentExtension.initialize()`` against the real
     ``https://ca.getbindu.com`` using that token
  5. Walk away with a real X.509 cert signed by the live Bindu Intermediate CA
  6. Clean up the OAuth2 client

Every network call hits the real production endpoint — no mocks, no
local docker, no shortcuts. This is the smoke test for "step-ca is alive
and Bindu agents can fetch certs from it."

Running it
----------
    uv run python tests/e2e/mtls/canary.py

The script auto-cleans up its Hydra client at the end, even on failure.
If the cleanup itself fails (network blip, etc.), the leftover client_id
is logged so you can ``curl -X DELETE`` it manually against
``https://hydra-admin.getbindu.com/admin/clients/<id>``.

Not run in CI
-------------
This isn't a pytest test on purpose:

* Each run creates and deletes a real OAuth2 client in production Hydra.
* It depends on DNS for ca.getbindu.com and hydra.getbindu.com working.
* CI sandboxes typically can't reach production from inside their network.

Run it manually when you want to verify the production stack — e.g. after
an infra change to Hydra, a step-ca redeploy, or a Caddyfile shuffle.

Prerequisites
-------------
* ``MTLS__ENABLED`` does NOT need to be set — the canary drives the
  extension directly with explicit URLs.
* Hydra must have ``STRATEGIES_ACCESS_TOKEN=jwt`` set (see
  ``infragrid/bindu-prod-cluster/shelley-deploy/compose/hydra.yml`` for
  the operational note). Without this Hydra returns opaque access tokens
  that step-ca cannot verify.
"""

from __future__ import annotations

import asyncio
import base64
import json
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID

from bindu.extensions.mtls import MTLSAgentExtension
from bindu.extensions.mtls.step_ca_client import StepCAClient
from bindu.utils.http.tokens import get_client_credentials_token


HYDRA_ADMIN = "https://hydra-admin.getbindu.com"
CA_URL = "https://ca.getbindu.com"

CANARY_ID = f"bindu-mtls-canary-{int(time.time())}"
CANARY_SECRET = secrets.token_urlsafe(32)  # pragma: allowlist secret
AGENT_DID = f"did:bindu:test:canary:{int(time.time())}"


def run(cmd: list[str], *, input: bytes | None = None) -> str:
    """Subprocess helper that fails loudly."""
    result = subprocess.run(cmd, input=input, capture_output=True, check=False)
    if result.returncode != 0:
        print(f"  ! cmd failed: {' '.join(cmd)}")
        print(f"    stdout: {result.stdout.decode(errors='replace')[:500]}")
        print(f"    stderr: {result.stderr.decode(errors='replace')[:500]}")
        sys.exit(1)
    return result.stdout.decode()


def decode_jwt_payload(token: str) -> dict:
    """Decode (not verify) a JWT and return the payload."""
    payload = token.split(".")[1]
    # JWT base64 is URL-safe and unpadded; add padding to get back to a
    # multiple of 4 so b64decode doesn't choke.
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def register_canary() -> None:
    """Create the throwaway OAuth2 client in production Hydra."""
    print(f"\n=== Phase 1: register {CANARY_ID} in Hydra ===")
    body = {
        "client_id": CANARY_ID,
        "client_secret": CANARY_SECRET,
        "client_name": "bindu mTLS production canary",
        "grant_types": ["client_credentials"],
        "response_types": ["token"],
        "scope": "openid",
        "audience": ["step-ca"],
        "token_endpoint_auth_method": "client_secret_post",
    }
    out = run(
        [
            "curl",
            "-sfS",
            "-X",
            "POST",
            f"{HYDRA_ADMIN}/admin/clients",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(body),
        ]
    )
    parsed = json.loads(out)
    assert parsed["client_id"] == CANARY_ID
    assert parsed.get("audience") == ["step-ca"], parsed.get("audience")
    print(
        f"  ✓ client registered: client_id={CANARY_ID}, audience={parsed['audience']}"
    )


def cleanup_canary() -> None:
    """Delete the throwaway client. Best-effort; doesn't fail the test."""
    print(f"\n=== Cleanup: delete {CANARY_ID} from Hydra ===")
    result = subprocess.run(
        ["curl", "-sS", "-X", "DELETE", f"{HYDRA_ADMIN}/admin/clients/{CANARY_ID}"],
        capture_output=True,
    )
    if result.returncode == 0:
        print("  ✓ deleted (no traces left in Hydra)")
    else:
        print(f"  ! cleanup failed; remove manually: {CANARY_ID}")


async def phase_2_token_with_audience() -> str:
    """Mint a token and verify it actually carries aud=step-ca."""
    print("\n=== Phase 2: get Hydra token with audience=step-ca ===")
    result = await get_client_credentials_token(
        client_id=CANARY_ID,
        client_secret=CANARY_SECRET,
        scope="openid",
        audience="step-ca",
    )
    assert result is not None, "Hydra returned no token"
    token = result.get("id_token") or result["access_token"]
    print(f"  ✓ Hydra returned a token ({len(token)} chars)")

    payload = decode_jwt_payload(token)
    aud = payload.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    assert aud and "step-ca" in aud, f"aud={aud!r} (expected to contain 'step-ca')"
    print(f"  ✓ token aud claim = {aud}")
    print(f"  ✓ token iss claim = {payload.get('iss')!r}")
    return token


async def phase_3_bootstrap_against_prod(token: str) -> None:
    """Drive MTLSAgentExtension.initialize() against the real ca.getbindu.com."""
    print("\n=== Phase 3: bootstrap cert via production step-ca ===")
    with tempfile.TemporaryDirectory() as d:
        pki_dir = Path(d)
        step_ca = StepCAClient(
            ca_url=CA_URL,
            ca_root_url=f"{CA_URL}/roots.pem",
            verify_ssl=True,
        )

        async def token_provider() -> str:
            return token

        ext = MTLSAgentExtension(
            pki_dir=pki_dir,
            agent_did=AGENT_DID,
            agent_url=None,
            oidc_token_provider=token_provider,
            step_ca=step_ca,
        )

        ok = await ext.initialize()
        await ext.close()
        assert ok, "MTLSAgentExtension.initialize() returned False"

        cert = x509.load_pem_x509_certificate(ext.store.read_cert())
        print(f"  ✓ cert issued by: {cert.issuer.rfc4514_string()}")
        print(f"  ✓ cert subject:   {cert.subject.rfc4514_string()}")
        not_before = getattr(cert, "not_valid_before_utc", cert.not_valid_before)
        not_after = getattr(cert, "not_valid_after_utc", cert.not_valid_after)
        print(f"  ✓ not valid before / after: {not_before} → {not_after}")

        # step-ca's OIDC provisioner ignores the CSR's SANs and synthesizes
        # identity from token claims:
        #   CN      = sub claim (= OAuth client_id under client_credentials)
        #   URI SAN = {iss}#{sub}
        # In production, Bindu agents register their DID as the client_id,
        # so CN ends up being the agent's DID — that's the canonical path
        # MTLSMiddleware._extract_did reads via its CN fallback. The
        # canary uses a synthetic client_id, so we just sanity-check the
        # subject matches whoever holds the credential.
        try:
            san = cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value
            uris = list(san.get_values_for_type(x509.UniformResourceIdentifier))
            dns = list(san.get_values_for_type(x509.DNSName))
            emails = list(san.get_values_for_type(x509.RFC822Name))
            print(f"  ✓ SAN: uris={uris} dns={dns} emails={emails}")
        except x509.ExtensionNotFound:
            print("  ✓ SAN: (none — OIDC provisioner emitted no SAN extension)")

        cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert cn_attrs, "cert has no CN"
        assert cn_attrs[0].value == CANARY_ID, (
            f"cert CN {cn_attrs[0].value!r} != canary client_id {CANARY_ID!r}"
        )
        print("  ✓ cert CN matches the authenticated client_id")

        # Cert file holds leaf + intermediate concatenated; the CA bundle
        # is the trust anchor (root only). Both are verified by parsing.
        chain_pem = ext.store.read_cert()
        chain_certs = []
        for block in chain_pem.split(b"-----BEGIN CERTIFICATE-----"):
            if b"END CERTIFICATE" in block:
                pem = b"-----BEGIN CERTIFICATE-----" + block
                chain_certs.append(x509.load_pem_x509_certificate(pem))
        print(f"  ✓ cert file holds {len(chain_certs)} cert(s) (leaf + intermediate)")
        if len(chain_certs) >= 2:
            print(f"    leaf issuer:       {chain_certs[0].issuer.rfc4514_string()}")
            print(f"    intermediate from: {chain_certs[1].issuer.rfc4514_string()}")

        bundle = x509.load_pem_x509_certificate(ext.store.read_ca_bundle())
        print(f"  ✓ CA bundle (root) subject: {bundle.subject.rfc4514_string()}")
        fp = ext.cert_fingerprint
        assert fp is not None
        print(f"  ✓ SHA-256 fingerprint: {fp[:23]}…")


async def main() -> int:
    """Drive all three phases. Cleanup runs even on failure."""
    register_canary()
    try:
        token = await phase_2_token_with_audience()
        await phase_3_bootstrap_against_prod(token)
        print("\n=== production mTLS canary: all phases passed ===")
        return 0
    finally:
        cleanup_canary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
