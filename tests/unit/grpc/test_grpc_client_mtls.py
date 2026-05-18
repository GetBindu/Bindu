"""Tests for the channel-credentials wiring in GrpcAgentClient.

Phase 4: outbound gRPC must use ``grpc.secure_channel`` when channel
credentials are supplied. The default (None) preserves the existing
``grpc.insecure_channel`` behavior for SDK-on-the-same-host setups.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import grpc

from bindu.grpc.client import GrpcAgentClient


class TestChannelCredentialsWiring:
    def test_default_is_insecure_channel(self) -> None:
        client = GrpcAgentClient(callback_address="localhost:50052")
        with (
            patch("bindu.grpc.client.grpc.insecure_channel") as fake_insecure,
            patch("bindu.grpc.client.grpc.secure_channel") as fake_secure,
        ):
            fake_insecure.return_value = MagicMock(spec=grpc.Channel)
            client._ensure_connected()
            fake_insecure.assert_called_once()
            fake_secure.assert_not_called()

    def test_secure_channel_when_credentials_provided(self) -> None:
        creds = MagicMock(spec=grpc.ChannelCredentials)
        client = GrpcAgentClient(
            callback_address="agent.example.com:50052",
            channel_credentials=creds,
        )
        with (
            patch("bindu.grpc.client.grpc.insecure_channel") as fake_insecure,
            patch("bindu.grpc.client.grpc.secure_channel") as fake_secure,
        ):
            fake_secure.return_value = MagicMock(spec=grpc.Channel)
            client._ensure_connected()
            fake_secure.assert_called_once()
            assert fake_secure.call_args.args[0] == "agent.example.com:50052"
            assert fake_secure.call_args.args[1] is creds
            fake_insecure.assert_not_called()

    def test_channel_built_only_once(self) -> None:
        client = GrpcAgentClient(callback_address="localhost:50052")
        with patch("bindu.grpc.client.grpc.insecure_channel") as fake_insecure:
            fake_insecure.return_value = MagicMock(spec=grpc.Channel)
            client._ensure_connected()
            client._ensure_connected()
            assert fake_insecure.call_count == 1
