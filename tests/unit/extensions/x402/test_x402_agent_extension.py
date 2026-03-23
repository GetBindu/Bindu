"""Tests for X402 Agent Extension."""

import pytest

from bindu.extensions.x402.x402_agent_extension import X402AgentExtension


class TestX402AgentExtensionInitialization:
    """Test X402AgentExtension initialization."""

    def test_init_with_minimal_params(self):
        """Test initialization with minimal required parameters."""
        ext = X402AgentExtension(amount="1000000", pay_to_address="0x1234567890abcdef")

        assert ext.amount == "1000000"
        assert ext.token == "USDC"
        assert ext.network == "base-sepolia"
        assert ext.pay_to_address == "0x1234567890abcdef"
        assert ext.required is True

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        ext = X402AgentExtension(
            amount="2000000",
            token="USDT",
            network="ethereum-mainnet",
            pay_to_address="0xabcdef1234567890",
            required=False,
            description="Payment for service",
        )

        assert ext.amount == "2000000"
        assert ext.token == "USDT"
        assert ext.network == "ethereum-mainnet"
        assert ext.pay_to_address == "0xabcdef1234567890"
        assert ext.required is False
        assert ext._description == "Payment for service"

    def test_init_missing_amount_raises_error(self):
        """Test that missing amount raises ValueError."""
        with pytest.raises(ValueError, match="amount is required"):
            X402AgentExtension(pay_to_address="0x1234")

    def test_init_missing_pay_to_address_when_required(self):
        """Test that missing pay_to_address raises error when required=True."""
        with pytest.raises(ValueError, match="pay_to_address is required"):
            X402AgentExtension(amount="1000000", required=True)

    def test_init_missing_pay_to_address_when_not_required(self):
        """Test that missing pay_to_address is allowed when required=False."""
        ext = X402AgentExtension(amount="1000000", pay_to_address="", required=False)

        assert ext.pay_to_address == ""
        assert ext.required is False


class TestX402AgentExtensionWithPaymentOptions:
    """Test X402AgentExtension with payment_options."""

    def test_init_with_payment_options(self):
        """Test initialization with payment_options list."""
        payment_options = [
            {
                "amount": "1000000",
                "token": "USDC",
                "network": "base-sepolia",
                "pay_to_address": "0x1234",
            },
            {
                "amount": "2000000",
                "token": "USDT",
                "network": "ethereum-mainnet",
                "pay_to_address": "0x5678",
            },
        ]

        ext = X402AgentExtension(payment_options=payment_options)

        # Should use first option as primary
        assert ext.amount == "1000000"
        assert ext.token == "USDC"
        assert ext.network == "base-sepolia"
        assert ext.pay_to_address == "0x1234"
        assert ext.payment_options == payment_options

    def test_init_with_payment_options_uses_defaults(self):
        """Test that payment_options can use default values."""
        payment_options = [{"amount": "1000000", "pay_to_address": "0x1234"}]

        ext = X402AgentExtension(
            payment_options=payment_options, token="DAI", network="polygon"
        )

        # Should use defaults for missing fields
        assert ext.token == "DAI"
        assert ext.network == "polygon"

    def test_init_with_empty_payment_options_raises_error(self):
        """Test that empty payment_options list raises error."""
        with pytest.raises(ValueError, match="amount is required"):
            X402AgentExtension(payment_options=[])

    def test_init_with_invalid_payment_options_type_raises_error(self):
        """Test that invalid payment_options type raises error."""
        with pytest.raises(ValueError, match="must be a non-empty list"):
            X402AgentExtension(payment_options="not-a-list")  # type: ignore[arg-type]

    def test_init_with_non_dict_payment_option_raises_error(self):
        """Test that non-dict payment option raises error."""
        with pytest.raises(ValueError, match="must contain only dictionary entries"):
            X402AgentExtension(payment_options=["not-a-dict"])  # type: ignore[list-item]

    def test_init_with_payment_options_missing_pay_to_address(self):
        """Test that missing pay_to_address in payment_options raises error when required."""
        payment_options = [{"amount": "1000000", "token": "USDC"}]

        with pytest.raises(ValueError, match="pay_to_address is required"):
            X402AgentExtension(payment_options=payment_options, required=True)


class TestX402AgentExtensionMethods:
    """Test X402AgentExtension methods."""

    def test_repr(self):
        """Test string representation."""
        ext = X402AgentExtension(
            amount="1000000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0x1234567890abcdef1234567890",
        )

        repr_str = repr(ext)

        assert "X402AgentExtension" in repr_str
        assert "amount=1000000" in repr_str
        assert "token=USDC" in repr_str
        assert "network=base-sepolia" in repr_str
        assert "0x12345678" in repr_str  # Truncated address
        assert "required=True" in repr_str

    def test_agent_extension_property(self):
        """Test agent_extension cached property."""
        ext = X402AgentExtension(amount="1000000", pay_to_address="0x1234")

        agent_ext = ext.agent_extension

        assert "uri" in agent_ext
        assert isinstance(agent_ext["uri"], str)

        # Test that it's cached
        agent_ext2 = ext.agent_extension
        assert agent_ext is agent_ext2


class TestX402AgentExtensionEdgeCases:
    """Test edge cases for X402AgentExtension."""

    def test_init_with_usd_amount_string(self):
        """Test initialization with USD amount string."""
        ext = X402AgentExtension(amount="$1.00", pay_to_address="0x1234")

        assert ext.amount == "$1.00"

    def test_init_with_large_amount(self):
        """Test initialization with very large amount."""
        large_amount = "999999999999999999"
        ext = X402AgentExtension(amount=large_amount, pay_to_address="0x1234")

        assert ext.amount == large_amount

    def test_init_with_different_tokens(self):
        """Test initialization with different token types."""
        tokens = ["USDC", "USDT", "DAI", "ETH", "MATIC"]

        for token in tokens:
            ext = X402AgentExtension(
                amount="1000000", token=token, pay_to_address="0x1234"
            )
            assert ext.token == token

    def test_init_with_different_networks(self):
        """Test initialization with different networks."""
        networks = [
            "base-sepolia",
            "ethereum-mainnet",
            "polygon",
            "arbitrum",
            "optimism",
        ]

        for network in networks:
            ext = X402AgentExtension(
                amount="1000000", network=network, pay_to_address="0x1234"
            )
            assert ext.network == network

    def test_init_with_long_pay_to_address(self):
        """Test initialization with full-length Ethereum address."""
        address = "0x" + "a" * 40
        ext = X402AgentExtension(amount="1000000", pay_to_address=address)

        assert ext.pay_to_address == address

    def test_init_with_multiple_payment_options_preserves_all(self):
        """Test that all payment options are preserved."""
        payment_options = [
            {"amount": "1000000", "token": "USDC", "pay_to_address": "0x1"},
            {"amount": "2000000", "token": "USDT", "pay_to_address": "0x2"},
            {"amount": "3000000", "token": "DAI", "pay_to_address": "0x3"},
        ]

        ext = X402AgentExtension(payment_options=payment_options)

        assert ext.payment_options is not None
        assert len(ext.payment_options) == 3
        assert ext.payment_options[1]["token"] == "USDT"
        assert ext.payment_options[2]["amount"] == "3000000"

    def test_init_with_description(self):
        """Test initialization with description."""
        description = "Payment for AI service execution"
        ext = X402AgentExtension(
            amount="1000000", pay_to_address="0x1234", description=description
        )

        assert ext._description == description

    def test_init_required_false_allows_empty_address(self):
        """Test that required=False allows empty pay_to_address."""
        ext = X402AgentExtension(amount="1000000", pay_to_address="", required=False)

        assert ext.pay_to_address == ""
        assert ext.required is False
