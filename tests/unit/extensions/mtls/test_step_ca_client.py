"""Tests for the StepCAClient HTTP surface.

These tests mock the underlying AsyncHTTPClient so we exercise the
on-the-wire contract with step-ca (request shapes, response parsing,
error handling) without needing a live CA.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bindu.extensions.mtls.step_ca_client import StepCAClient, StepCAError


def _mock_response(
    *,
    status: int = 200,
    body: bytes = b"",
    json_payload: dict[str, Any] | None = None,
) -> MagicMock:
    """Build an aiohttp.ClientResponse stand-in that StepCAClient understands."""
    response = MagicMock()
    response.status = status
    response._body = body
    response.read = AsyncMock(return_value=body)
    response.json = AsyncMock(return_value=json_payload or {})
    return response


@pytest.fixture
def client() -> StepCAClient:
    return StepCAClient(
        ca_url="https://ca.example.com",
        ca_root_url="https://ca.example.com/roots.pem",
    )


class TestFetchRootCA:
    @pytest.mark.asyncio
    async def test_returns_pem_body(self, client: StepCAClient) -> None:
        pem = (
            b"-----BEGIN CERTIFICATE-----\nMIIBkTCCATug...\n-----END CERTIFICATE-----\n"
        )
        client._roots_client.get = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(body=pem)
        )
        result = await client.fetch_root_ca()
        assert result == pem

    @pytest.mark.asyncio
    async def test_rejects_non_pem_response(self, client: StepCAClient) -> None:
        client._roots_client.get = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(body=b"not a cert")
        )
        with pytest.raises(StepCAError, match="did not return a PEM payload"):
            await client.fetch_root_ca()

    @pytest.mark.asyncio
    async def test_calls_root_path(self, client: StepCAClient) -> None:
        pem = b"-----BEGIN CERTIFICATE-----\nxxx\n-----END CERTIFICATE-----\n"
        client._roots_client.get = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(body=pem)
        )
        await client.fetch_root_ca()
        client._roots_client.get.assert_awaited_once()  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        called_path = client._roots_client.get.call_args.args[0]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert called_path == "/roots.pem"


class TestSignCSR:
    CSR_PEM = b"-----BEGIN CERTIFICATE REQUEST-----\nMIIBxxx\n-----END CERTIFICATE REQUEST-----\n"
    CERT_PEM = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----\n"
    CHAIN_PEM = "-----BEGIN CERTIFICATE-----\nBBB\n-----END CERTIFICATE-----\n"

    @pytest.mark.asyncio
    async def test_posts_csr_and_token_and_parses_response(
        self, client: StepCAClient
    ) -> None:
        client._api_client.post = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(
                json_payload={"crt": self.CERT_PEM, "ca": self.CHAIN_PEM}
            )
        )
        cert, chain = await client.sign_csr(
            self.CSR_PEM, "fake-oidc-token", ttl_hours=4
        )
        assert cert == self.CERT_PEM.encode("ascii")
        assert chain == self.CHAIN_PEM.encode("ascii")

        call = client._api_client.post.call_args  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert call.args[0] == "/1.0/sign"
        body = call.kwargs["json"]
        assert body["csr"] == self.CSR_PEM.decode("ascii")
        assert body["ott"] == "fake-oidc-token"
        assert "notAfter" in body and body["notAfter"]
        assert call.kwargs["headers"]["Authorization"] == "Bearer fake-oidc-token"

    @pytest.mark.asyncio
    async def test_raises_on_missing_crt_field(self, client: StepCAClient) -> None:
        client._api_client.post = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(json_payload={"ca": self.CHAIN_PEM})
        )
        with pytest.raises(StepCAError, match="Unexpected sign response shape"):
            await client.sign_csr(self.CSR_PEM, "tok")

    @pytest.mark.asyncio
    async def test_raises_on_non_dict_response(self, client: StepCAClient) -> None:
        client._api_client.post = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(json_payload=None)
        )
        # json() returns {} from the helper when payload is None -> dict without keys.
        with pytest.raises(StepCAError):
            await client.sign_csr(self.CSR_PEM, "tok")


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_true_on_200(self, client: StepCAClient) -> None:
        client._api_client.get = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(status=200)
        )
        assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_returns_false_on_error_status(self, client: StepCAClient) -> None:
        client._api_client.get = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            return_value=_mock_response(status=503)
        )
        assert await client.health_check() is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, client: StepCAClient) -> None:
        client._api_client.get = AsyncMock(  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
            side_effect=ConnectionError("boom")
        )
        # health_check is documented to never raise.
        assert await client.health_check() is False


class TestURLParsing:
    def test_strips_trailing_slash_from_ca_url(self) -> None:
        c = StepCAClient(
            ca_url="https://ca.example.com/",
            ca_root_url="https://ca.example.com/roots.pem",
        )
        assert c.ca_url == "https://ca.example.com"

    def test_splits_root_url_into_base_and_path(self) -> None:
        c = StepCAClient(
            ca_url="https://ca.example.com",
            ca_root_url="https://static.cdn.example.com/bindu/roots.pem",
        )
        assert c._roots_base == "https://static.cdn.example.com"
        assert c._roots_path == "/bindu/roots.pem"
