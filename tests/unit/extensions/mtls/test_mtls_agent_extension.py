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


class TestServerMaterial:
    """Phase 3: server-side TLS material builders."""

    def _seed_extension_with_real_pki(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> MTLSAgentExtension:
        """Run a real bootstrap so the on-disk PEM files exist for SSLContext."""
        import asyncio

        ext = _make_extension(
            tmp_path,
            step_ca=fake_step_ca,
            oidc_token_provider=token_provider,
        )
        # Replace the fake's returned cert with one whose key actually matches
        # what generate_keypair() writes — ssl.SSLContext.load_cert_chain
        # checks that the cert's public key is the pair of the private key.
        store = ext.store
        pk, _ = store.generate_keypair()
        from datetime import timedelta
        from cryptography.x509 import (
            CertificateBuilder,
            Name,
            NameAttribute,
            random_serial_number,
        )

        now = datetime.now(timezone.utc)
        cert = (
            CertificateBuilder()
            .subject_name(Name([NameAttribute(NameOID.COMMON_NAME, "test")]))
            .issuer_name(Name([NameAttribute(NameOID.COMMON_NAME, "test")]))
            .public_key(pk.public_key())
            .serial_number(random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(hours=24))
            .sign(pk, hashes.SHA256())
        )
        store.write_cert(cert.public_bytes(serialization.Encoding.PEM))
        # CA bundle just needs to be a valid PEM cert for SSLContext.load_verify_locations.
        store.write_ca_bundle(cert.public_bytes(serialization.Encoding.PEM))
        # Mark as initialized so the require_initialized guard passes.
        ext._initialized = True
        asyncio.run(ext.close())
        return ext

    def test_build_server_ssl_context_returns_configured_context(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        import ssl

        ext = self._seed_extension_with_real_pki(tmp_path, fake_step_ca, token_provider)
        ctx = ext.build_server_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)
        # Default settings: require_client_cert=True
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_get_uvicorn_ssl_kwargs_returns_file_paths(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        import ssl

        ext = self._seed_extension_with_real_pki(tmp_path, fake_step_ca, token_provider)
        kwargs = ext.get_uvicorn_ssl_kwargs()
        assert kwargs["ssl_certfile"] == str(ext.store.cert_path)
        assert kwargs["ssl_keyfile"] == str(ext.store.key_path)
        assert kwargs["ssl_ca_certs"] == str(ext.store.ca_bundle_path)
        assert kwargs["ssl_cert_reqs"] == ssl.CERT_REQUIRED

    def test_build_grpc_server_credentials_returns_grpc_creds(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        import grpc

        ext = self._seed_extension_with_real_pki(tmp_path, fake_step_ca, token_provider)
        creds = ext.build_grpc_server_credentials()
        assert isinstance(creds, grpc.ServerCredentials)

    def test_server_material_raises_when_uninitialized(self, tmp_path: Path) -> None:
        ext = _make_extension(tmp_path)
        with pytest.raises(
            FileNotFoundError, match="call MTLSAgentExtension.initialize"
        ):
            ext.build_server_ssl_context()
        with pytest.raises(FileNotFoundError):
            ext.get_uvicorn_ssl_kwargs()
        with pytest.raises(FileNotFoundError):
            ext.build_grpc_server_credentials()


class TestClientMaterial:
    """Phase 4: client-side (outbound) TLS material builders."""

    def _seed_extension_with_real_pki(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> MTLSAgentExtension:
        """Reuse the server-material seed; same on-disk layout."""
        return TestServerMaterial()._seed_extension_with_real_pki(
            tmp_path, fake_step_ca, token_provider
        )

    def test_build_client_ssl_context_loads_cert_chain(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        import ssl

        ext = self._seed_extension_with_real_pki(tmp_path, fake_step_ca, token_provider)
        ctx = ext.build_client_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)
        # Default settings: verify_server_cert=True -> CERT_REQUIRED.
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_httpx_kwargs_returns_cert_tuple_and_verify_path(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        ext = self._seed_extension_with_real_pki(tmp_path, fake_step_ca, token_provider)
        kwargs = ext.get_httpx_client_kwargs()
        assert kwargs["cert"] == (
            str(ext.store.cert_path),
            str(ext.store.key_path),
        )
        assert kwargs["verify"] == str(ext.store.ca_bundle_path)

    def test_build_grpc_channel_credentials_returns_creds(
        self, tmp_path: Path, fake_step_ca: MagicMock, token_provider: AsyncMock
    ) -> None:
        import grpc

        ext = self._seed_extension_with_real_pki(tmp_path, fake_step_ca, token_provider)
        creds = ext.build_grpc_channel_credentials()
        assert isinstance(creds, grpc.ChannelCredentials)

    def test_client_material_raises_when_uninitialized(self, tmp_path: Path) -> None:
        ext = _make_extension(tmp_path)
        with pytest.raises(FileNotFoundError):
            ext.build_client_ssl_context()
        with pytest.raises(FileNotFoundError):
            ext.get_httpx_client_kwargs()
        with pytest.raises(FileNotFoundError):
            ext.build_grpc_channel_credentials()
