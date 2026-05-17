"""Tests for the MTLSAgentExtension orchestrator.

Mocks StepCAClient and the OIDC token provider so the bootstrap logic can be
exercised in isolation, without a live step-ca or Hydra instance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from bindu.extensions.mtls import CertStore, MTLSAgentExtension
from bindu.extensions.mtls.step_ca_client import StepCAError


# ---------------------------------------------------------------------------
# Test fixtures: build a real signed cert PEM step-ca would plausibly return.
# ---------------------------------------------------------------------------


def _build_signed_cert(*, hours_valid: int) -> bytes:
    """Build a self-signed cert PEM with the requested validity window."""
    pk = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .public_key(pk.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=hours_valid))
        .sign(pk, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


CA_BUNDLE = b"-----BEGIN CERTIFICATE-----\nCA-CONTENT\n-----END CERTIFICATE-----\n"
DID = "did:bindu:raahul:test:abc123"
AGENT_URL = "https://agent.example.com"


@pytest.fixture
def fake_step_ca() -> MagicMock:
    """A StepCAClient stand-in whose methods are AsyncMocks."""
    ca = MagicMock()
    ca.fetch_root_ca = AsyncMock(return_value=CA_BUNDLE)
    ca.sign_csr = AsyncMock(
        return_value=(_build_signed_cert(hours_valid=24), CA_BUNDLE)
    )
    ca.close = AsyncMock()
    return ca


@pytest.fixture
def token_provider() -> AsyncMock:
    return AsyncMock(return_value="fake-oidc-token")


def _make_extension(
    tmp_path: Path,
    *,
    step_ca=None,
    oidc_token_provider=None,
    cert_store=None,
) -> MTLSAgentExtension:
    return MTLSAgentExtension(
        pki_dir=tmp_path,
        agent_did=DID,
        agent_url=AGENT_URL,
        step_ca=step_ca,
        oidc_token_provider=oidc_token_provider,
        cert_store=cert_store,
    )


class TestInitializeHappyPath:
    @pytest.mark.asyncio
    async def test_full_bootstrap_writes_cert_key_and_bundle(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
        )
        ok = await ext.initialize()
        assert ok is True
        assert ext.initialized is True
        store = ext.store
        assert store.has_cert()
        assert store.has_ca_bundle()
        # CSR was built with the DID
        assert b"BEGIN CERTIFICATE REQUEST" in store.csr_path.read_bytes()

    @pytest.mark.asyncio
    async def test_passes_oidc_token_to_sign_request(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
        )
        await ext.initialize()
        token_provider.assert_awaited_once()
        fake_step_ca.sign_csr.assert_awaited_once()
        _, called_token = fake_step_ca.sign_csr.call_args.args
        assert called_token == "fake-oidc-token"

    @pytest.mark.asyncio
    async def test_skips_root_fetch_when_bundle_present(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        store = CertStore(tmp_path)
        store.write_ca_bundle(CA_BUNDLE)
        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
            cert_store=store,
        )
        await ext.initialize()
        fake_step_ca.fetch_root_ca.assert_not_awaited()
        fake_step_ca.sign_csr.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reuses_valid_cert_on_disk(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        # Pre-seed a valid cert + key + bundle.
        store = CertStore(tmp_path)
        store.write_ca_bundle(CA_BUNDLE)
        pk, _ = store.generate_keypair()
        # Build a cert whose private key matches what's on disk so it parses
        # cleanly; the cert content itself doesn't matter — the store only
        # checks notAfter.
        cert_pem = _build_signed_cert(hours_valid=24)
        store.write_cert(cert_pem)

        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
            cert_store=store,
        )
        ok = await ext.initialize()
        assert ok is True
        fake_step_ca.sign_csr.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_force_renew_triggers_resign(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        store = CertStore(tmp_path)
        store.write_ca_bundle(CA_BUNDLE)
        store.generate_keypair()
        store.write_cert(_build_signed_cert(hours_valid=24))

        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
            cert_store=store,
        )
        await ext.initialize(force_renew=True)
        fake_step_ca.sign_csr.assert_awaited_once()


class TestInitializeFailureModes:
    @pytest.mark.asyncio
    async def test_missing_token_provider_raises_runtime_error(
        self, tmp_path: Path, fake_step_ca: MagicMock
    ) -> None:
        ext = _make_extension(tmp_path, step_ca=fake_step_ca)
        with pytest.raises(RuntimeError, match="oidc_token_provider"):
            await ext.initialize()

    @pytest.mark.asyncio
    async def test_step_ca_error_returns_false(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        fake_step_ca.sign_csr.side_effect = StepCAError("CA exploded")
        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
        )
        ok = await ext.initialize()
        assert ok is False
        assert ext.initialized is False

    @pytest.mark.asyncio
    async def test_empty_oidc_token_raises_step_ca_error(
        self, tmp_path: Path, fake_step_ca: MagicMock
    ) -> None:
        provider = AsyncMock(return_value="")
        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=provider,
        )
        ok = await ext.initialize()
        # initialize() catches StepCAError and returns False.
        assert ok is False
        fake_step_ca.sign_csr.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_false_not_raises(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        fake_step_ca.fetch_root_ca.side_effect = ConnectionError("network down")
        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
        )
        ok = await ext.initialize()
        assert ok is False
