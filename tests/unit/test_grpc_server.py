"""Tests for the gRPC server TLS wiring."""

from __future__ import annotations

import pytest

from bindu.server.applications import BinduApplication
from bindu.server.grpc.server import GrpcServer


@pytest.mark.asyncio
async def test_start_tls_missing_paths_raises(mock_manifest):
    app = BinduApplication(manifest=mock_manifest)
    server = GrpcServer(app, tls_enabled=True)

    with pytest.raises(ValueError, match="certificate/key paths"):
        await server.start()


@pytest.mark.asyncio
async def test_start_tls_missing_cert_file_raises(tmp_path, mock_manifest):
    app = BinduApplication(manifest=mock_manifest)
    key_path = tmp_path / "server.key"
    key_path.write_text("not-a-key")
    server = GrpcServer(
        app,
        tls_enabled=True,
        tls_cert_path=str(tmp_path / "missing.crt"),
        tls_key_path=str(key_path),
    )

    with pytest.raises(FileNotFoundError):
        await server.start()


@pytest.mark.asyncio
async def test_start_tls_missing_key_file_raises(tmp_path, mock_manifest):
    app = BinduApplication(manifest=mock_manifest)
    cert_path = tmp_path / "server.crt"
    cert_path.write_text("not-a-cert")
    server = GrpcServer(
        app,
        tls_enabled=True,
        tls_cert_path=str(cert_path),
        tls_key_path=str(tmp_path / "missing.key"),
    )

    with pytest.raises(FileNotFoundError):
        await server.start()
