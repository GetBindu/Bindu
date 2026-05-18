"""Tests for the mTLS plumbing in AsyncHTTPClient and HybridAuthClient.

These tests focus on the wiring change — that an ssl_context handed in at
construction time reaches the underlying aiohttp connector, and that
HybridAuthClient threads an mtls_extension through to its inner HTTP client.
"""

from __future__ import annotations

import ssl
from pathlib import Path
from unittest.mock import MagicMock

from bindu.utils.http import AsyncHTTPClient, HybridAuthClient


class TestAsyncHTTPClientSSLContext:
    def test_defaults_to_no_ssl_context(self) -> None:
        client = AsyncHTTPClient(base_url="https://example.com")
        assert client.ssl_context is None
        # verify_ssl preserved as fallback.
        assert client.verify_ssl is True

    def test_accepts_ssl_context(self) -> None:
        ctx = ssl.create_default_context()
        client = AsyncHTTPClient(base_url="https://example.com", ssl_context=ctx)
        assert client.ssl_context is ctx


class TestHybridAuthClientMTLSWiring:
    def test_constructor_accepts_mtls_extension(self, tmp_path: Path) -> None:
        did_ext = MagicMock()
        mtls_ext = MagicMock()
        client = HybridAuthClient(
            agent_id="agent-1",
            credentials_dir=tmp_path,
            did_extension=did_ext,
            mtls_extension=mtls_ext,
        )
        assert client.mtls_extension is mtls_ext

    def test_default_mtls_extension_is_none(self, tmp_path: Path) -> None:
        client = HybridAuthClient(
            agent_id="agent-1",
            credentials_dir=tmp_path,
            did_extension=MagicMock(),
        )
        assert client.mtls_extension is None

    def test_build_http_client_passes_ssl_context_when_mtls_set(
        self, tmp_path: Path
    ) -> None:
        ctx = ssl.create_default_context()
        mtls_ext = MagicMock()
        mtls_ext.build_client_ssl_context.return_value = ctx
        client = HybridAuthClient(
            agent_id="agent-1",
            credentials_dir=tmp_path,
            did_extension=MagicMock(),
            mtls_extension=mtls_ext,
        )
        http = client._build_http_client(base_url="https://peer.example.com")
        assert http.ssl_context is ctx
        mtls_ext.build_client_ssl_context.assert_called_once()

    def test_build_http_client_omits_ssl_context_when_no_mtls(
        self, tmp_path: Path
    ) -> None:
        client = HybridAuthClient(
            agent_id="agent-1",
            credentials_dir=tmp_path,
            did_extension=MagicMock(),
        )
        http = client._build_http_client(base_url="https://peer.example.com")
        assert http.ssl_context is None
