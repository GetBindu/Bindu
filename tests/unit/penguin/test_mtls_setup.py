"""Tests for the bindu.penguin.mtls_setup wrapper.

The wrapper is mostly a guard layer in front of the async extension; tests
focus on the toggle behavior (off-by-default, refusal without Hydra
credentials) and on the success path that returns an initialized extension.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from bindu.common.models import AgentCredentials
from bindu.penguin.mtls_setup import initialize_mtls_extension


@pytest.fixture
def fake_credentials() -> AgentCredentials:
    return AgentCredentials(
        agent_id="agent-123",
        client_id="did:bindu:raahul:test:agent-123",
        client_secret="s3cret",  # pragma: allowlist secret
        created_at="2026-05-17T00:00:00Z",
        scopes=["openid"],
    )


class TestToggleGuards:
    def test_returns_none_when_mtls_disabled(
        self, tmp_path: Path, fake_credentials: AgentCredentials
    ) -> None:
        with patch("bindu.penguin.mtls_setup.app_settings") as settings:
            settings.mtls.enabled = False
            result = initialize_mtls_extension(
                agent_id="agent-123",
                agent_did="did:bindu:raahul:test:agent-123",
                agent_url="https://agent.example.com",
                pki_dir=tmp_path,
                hydra_credentials=fake_credentials,
            )
        assert result is None

    def test_returns_none_when_hydra_credentials_missing(self, tmp_path: Path) -> None:
        with patch("bindu.penguin.mtls_setup.app_settings") as settings:
            settings.mtls.enabled = True
            result = initialize_mtls_extension(
                agent_id="agent-123",
                agent_did="did:bindu:raahul:test:agent-123",
                agent_url="https://agent.example.com",
                pki_dir=tmp_path,
                hydra_credentials=None,
            )
        assert result is None


class TestBootstrapPath:
    def test_returns_extension_on_success(
        self, tmp_path: Path, fake_credentials: AgentCredentials
    ) -> None:
        fake_extension = AsyncMock()
        fake_extension.initialize = AsyncMock(return_value=True)
        fake_extension.close = AsyncMock()
        fake_extension.store = AsyncMock()

        with (
            patch("bindu.penguin.mtls_setup.app_settings") as settings,
            patch(
                "bindu.penguin.mtls_setup.MTLSAgentExtension",
                return_value=fake_extension,
            ),
        ):
            settings.mtls.enabled = True
            settings.vault.enabled = False

            result = initialize_mtls_extension(
                agent_id="agent-123",
                agent_did="did:bindu:raahul:test:agent-123",
                agent_url="https://agent.example.com",
                pki_dir=tmp_path,
                hydra_credentials=fake_credentials,
            )
        assert result is fake_extension
        fake_extension.initialize.assert_awaited_once()
        fake_extension.close.assert_awaited_once()

    def test_returns_none_when_initialize_fails(
        self, tmp_path: Path, fake_credentials: AgentCredentials
    ) -> None:
        fake_extension = AsyncMock()
        fake_extension.initialize = AsyncMock(return_value=False)
        fake_extension.close = AsyncMock()

        with (
            patch("bindu.penguin.mtls_setup.app_settings") as settings,
            patch(
                "bindu.penguin.mtls_setup.MTLSAgentExtension",
                return_value=fake_extension,
            ),
        ):
            settings.mtls.enabled = True
            settings.vault.enabled = False

            result = initialize_mtls_extension(
                agent_id="agent-123",
                agent_did="did:bindu:raahul:test:agent-123",
                agent_url="https://agent.example.com",
                pki_dir=tmp_path,
                hydra_credentials=fake_credentials,
            )
        assert result is None
        # Still closed cleanly even on failure.
        fake_extension.close.assert_awaited_once()

    def test_unexpected_exception_returns_none(
        self, tmp_path: Path, fake_credentials: AgentCredentials
    ) -> None:
        with (
            patch("bindu.penguin.mtls_setup.app_settings") as settings,
            patch(
                "bindu.penguin.mtls_setup.MTLSAgentExtension",
                side_effect=RuntimeError("boom"),
            ),
        ):
            settings.mtls.enabled = True
            result = initialize_mtls_extension(
                agent_id="agent-123",
                agent_did="did:bindu:raahul:test:agent-123",
                agent_url="https://agent.example.com",
                pki_dir=tmp_path,
                hydra_credentials=fake_credentials,
            )
        assert result is None
