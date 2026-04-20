"""Minimal tests for bindufy module."""

from unittest.mock import Mock
import pytest
from uuid import UUID

from bindu.penguin.bindufy import (
    _generate_agent_id,
    _normalize_execution_costs,
    _setup_x402_extension,
    _parse_deployment_url,
    bindufy,
)


class TestBindufyUtilities:
    """Test bindufy utility functions."""

    def test_generate_agent_id_deterministic(self):
        """Test that agent ID generation is deterministic."""
        config1 = {"author": "test@example.com", "name": "TestAgent"}
        config2 = {"author": "test@example.com", "name": "TestAgent"}

        id1 = _generate_agent_id(config1)
        id2 = _generate_agent_id(config2)

        assert isinstance(id1, UUID)
        assert id1 == id2

    def test_generate_agent_id_different_for_different_inputs(self):
        """Test that different inputs produce different IDs."""
        config1 = {"author": "test@example.com", "name": "Agent1"}
        config2 = {"author": "test@example.com", "name": "Agent2"}

        id1 = _generate_agent_id(config1)
        id2 = _generate_agent_id(config2)

        assert id1 != id2

    def test_normalize_execution_costs_single_dict(self):
        """Test normalizing single dict to list."""
        cost = {"amount": "100", "token": "USDC", "network": "base"}

        result = _normalize_execution_costs(cost)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["amount"] == "100"

    def test_normalize_execution_costs_list(self):
        """Test normalizing list of dicts."""
        costs = [
            {"amount": "100", "token": "USDC", "network": "base"},
            {"amount": "200", "token": "ETH", "network": "ethereum"},
        ]

        result = _normalize_execution_costs(costs)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_normalize_execution_costs_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _normalize_execution_costs([])

    def test_normalize_execution_costs_invalid_type_raises(self):
        """Test that invalid type raises ValueError."""
        with pytest.raises(ValueError, match="must be either a dict or a list"):
            _normalize_execution_costs("invalid")

    def test_setup_x402_extension(self):
        """Test creating X402 extension from costs."""
        costs = [
            {
                "amount": "100",
                "token": "USDC",
                "network": "base-sepolia",
                "pay_to_address": "0x123",
            }
        ]

        extension = _setup_x402_extension(costs)

        assert extension is not None
        assert extension.amount == "100"
        assert extension.token == "USDC"

    def test_parse_deployment_url_with_port(self):
        """Test parsing deployment URL with port."""
        mock_config = Mock()
        mock_config.url = "http://localhost:8080"

        host, port = _parse_deployment_url(mock_config)

        assert host == "localhost"
        assert port == 8080

    def test_parse_deployment_url_without_port(self):
        """Test parsing deployment URL without port uses default."""
        mock_config = Mock()
        mock_config.url = "http://localhost"

        host, port = _parse_deployment_url(mock_config)

        assert host == "localhost"
        assert port == 3773

    def test_parse_deployment_url_none_returns_defaults(self):
        """Test that None config returns default values."""
        host, port = _parse_deployment_url(None)

        assert host == "localhost"
        assert port == 3773

    def test_normalize_execution_costs_validates_dict_entries(self):
        """Test that non-dict entries in list raise ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            _normalize_execution_costs([{"amount": "100"}, "invalid"])

    def test_normalize_execution_costs_requires_amount(self):
        """Test that missing amount raises ValueError."""
        with pytest.raises(ValueError, match="amount is required"):
            _normalize_execution_costs({"token": "USDC"})

    def test_normalize_execution_costs_uses_defaults(self):
        """Test that default token and network are used."""
        costs = [{"amount": "100"}]
        result = _normalize_execution_costs(costs)

        assert result[0]["token"] == "USDC"
        assert result[0]["network"] == "base-sepolia"

    def test_normalize_execution_costs_multiple_entries(self):
        """Test normalizing multiple cost entries."""
        costs = [
            {"amount": "100", "token": "USDC"},
            {"amount": "200", "token": "ETH", "network": "ethereum"},
        ]
        result = _normalize_execution_costs(costs)

        assert len(result) == 2
        assert result[0]["amount"] == "100"
        assert result[1]["amount"] == "200"

    def test_setup_x402_extension_with_multiple_options(self):
        """Test X402 extension with multiple payment options."""
        costs = [
            {
                "amount": "100",
                "token": "USDC",
                "network": "base-sepolia",
                "pay_to_address": "0x123",
            },
            {
                "amount": "200",
                "token": "ETH",
                "network": "ethereum",
                "pay_to_address": "0x456",
            },
        ]

        extension = _setup_x402_extension(costs)

        assert extension.amount == "100"
        assert extension.token == "USDC"
        assert extension.payment_options == costs

    def test_setup_x402_extension_with_address(self):
        """Test X402 extension with pay_to_address."""
        costs = [
            {
                "amount": "100",
                "token": "USDC",
                "network": "base-sepolia",
                "pay_to_address": "0x123",
            }
        ]

        extension = _setup_x402_extension(costs)

        assert extension.pay_to_address == "0x123"


def test_bindufy_non_callable_handler_raises_clear_error():
    """bindufy should fail fast with a clear handler validation message."""
    config = {
        "author": "test@example.com",
        "name": "Test Agent",
        "deployment": {"url": "http://localhost:3773"},
    }

    with pytest.raises(
        TypeError,
        match="callable function or coroutine function",
    ):
        bindufy(config=config, handler="not_callable", run_server=False)  # type: ignore[arg-type]
