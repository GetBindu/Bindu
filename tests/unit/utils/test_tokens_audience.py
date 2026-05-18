"""Tests for the audience-claim plumbing in get_client_credentials_token.

The token request needs to include ``audience=step-ca`` for step-ca's OIDC
provisioner to accept the resulting token. Verify the parameter is
forwarded into the form body.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@asynccontextmanager
async def _fake_client(client_mock: MagicMock) -> AsyncIterator[MagicMock]:
    """Async context manager that yields the mock — matches http_client()."""
    yield client_mock


class TestAudienceParameter:
    @pytest.mark.asyncio
    async def test_audience_forwarded_to_token_request(self) -> None:
        from bindu.utils.http import tokens

        captured_data: dict = {}

        async def fake_post(endpoint, *, headers=None, data=None, **kwargs):
            captured_data.update(data or {})
            resp = MagicMock()
            resp.status = 200
            resp.json = AsyncMock(
                return_value={"access_token": "tok", "id_token": "idtok"}
            )
            return resp

        client_mock = MagicMock()
        client_mock.post = fake_post

        with patch.object(
            tokens, "http_client", return_value=_fake_client(client_mock)
        ):
            result = await tokens.get_client_credentials_token(
                client_id="did:bindu:test:agent-1",
                client_secret="s3cret",  # pragma: allowlist secret
                scope="openid",
                audience="step-ca",
            )

        assert result is not None
        assert captured_data["audience"] == "step-ca"
        assert captured_data["scope"] == "openid"
        assert captured_data["grant_type"] == "client_credentials"

    @pytest.mark.asyncio
    async def test_audience_omitted_when_none(self) -> None:
        from bindu.utils.http import tokens

        captured_data: dict = {}

        async def fake_post(endpoint, *, headers=None, data=None, **kwargs):
            captured_data.update(data or {})
            resp = MagicMock()
            resp.status = 200
            resp.json = AsyncMock(return_value={"access_token": "tok"})
            return resp

        client_mock = MagicMock()
        client_mock.post = fake_post

        with patch.object(
            tokens, "http_client", return_value=_fake_client(client_mock)
        ):
            await tokens.get_client_credentials_token(
                client_id="did:bindu:test:agent-1",
                client_secret="s3cret",  # pragma: allowlist secret
            )

        # Confirm we didn't sneak an audience field in when none was requested
        # — deployments without mTLS shouldn't see any behavior change.
        assert "audience" not in captured_data
