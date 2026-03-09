"""Tests for multi-option execution_cost support.

Covers the full stack: ConfigValidator schema validation →
X402AgentExtension construction → _create_payment_requirements output.

The feature allows agents to advertise more than one payment option, e.g.:
    "0.1 USDC on Base OR 0.0001 ETH on Mainnet"

Each layer is tested independently so a regression is caught at the exact
layer it breaks rather than in an end-to-end assertion.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bindu.extensions.x402.x402_agent_extension import X402AgentExtension
from bindu.penguin.config_validator import ConfigValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SINGLE_COST = {
    "amount": "1000000",
    "token": "USDC",
    "network": "base-sepolia",
    "pay_to_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
}

_COST_ETH = {
    "amount": "100000000000000",
    "token": "ETH",
    "network": "mainnet",
    "pay_to_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
}

_BASE_CONFIG: dict[str, Any] = {
    "author": "test@example.com",
    "name": "test-agent",
    "deployment": {"url": "http://localhost:3773"},
}


def _make_config(**overrides) -> dict[str, Any]:
    """Build a minimal valid config with optional overrides."""
    cfg = dict(_BASE_CONFIG)
    cfg.update(overrides)
    return cfg


# ===========================================================================
# ConfigValidator — execution_cost schema
# ===========================================================================


class TestConfigValidatorExecutionCost:
    """ConfigValidator correctly accepts and rejects execution_cost values."""

    def test_single_dict_is_accepted(self):
        cfg = _make_config(execution_cost=_SINGLE_COST)
        result = ConfigValidator.validate_and_process(cfg)
        assert result["execution_cost"] == _SINGLE_COST

    def test_list_of_one_dict_is_accepted(self):
        cfg = _make_config(execution_cost=[_SINGLE_COST])
        result = ConfigValidator.validate_and_process(cfg)
        assert result["execution_cost"] == [_SINGLE_COST]

    def test_list_of_two_dicts_is_accepted(self):
        cfg = _make_config(execution_cost=[_SINGLE_COST, _COST_ETH])
        result = ConfigValidator.validate_and_process(cfg)
        assert result["execution_cost"] == [_SINGLE_COST, _COST_ETH]

    def test_none_is_accepted(self):
        """execution_cost is optional; None must not raise."""
        cfg = _make_config(execution_cost=None)
        result = ConfigValidator.validate_and_process(cfg)
        assert result["execution_cost"] is None

    def test_absent_is_accepted(self):
        """execution_cost absent from config must not raise."""
        cfg = _make_config()  # no execution_cost key at all
        result = ConfigValidator.validate_and_process(cfg)
        assert "execution_cost" not in result or result.get("execution_cost") is None

    def test_empty_list_raises(self):
        cfg = _make_config(execution_cost=[])
        with pytest.raises(ValueError, match="cannot be empty"):
            ConfigValidator.validate_and_process(cfg)

    def test_list_containing_non_dict_raises(self):
        cfg = _make_config(execution_cost=[_SINGLE_COST, "bad"])
        with pytest.raises(ValueError, match="list of dicts"):
            ConfigValidator.validate_and_process(cfg)

    def test_wrong_type_raises(self):
        """A plain string as execution_cost must be rejected."""
        cfg = _make_config(execution_cost="0.1 USDC")
        with pytest.raises(ValueError, match="dict or a list"):
            ConfigValidator.validate_and_process(cfg)

    def test_integer_raises(self):
        cfg = _make_config(execution_cost=42)
        with pytest.raises(ValueError, match="dict or a list"):
            ConfigValidator.validate_and_process(cfg)


# ===========================================================================
# X402AgentExtension — payment_options construction
# ===========================================================================


class TestX402AgentExtensionPaymentOptions:
    """X402AgentExtension stores the full options list and derives primary fields."""

    def test_single_option_via_payment_options(self):
        ext = X402AgentExtension(payment_options=[_SINGLE_COST])
        assert ext.amount == _SINGLE_COST["amount"]
        assert ext.token == _SINGLE_COST["token"]
        assert ext.network == _SINGLE_COST["network"]
        assert ext.pay_to_address == _SINGLE_COST["pay_to_address"]
        assert ext.payment_options == [_SINGLE_COST]

    def test_multiple_options_primary_from_first(self):
        """Primary fields must always be derived from index 0."""
        ext = X402AgentExtension(payment_options=[_SINGLE_COST, _COST_ETH])
        # primary = _SINGLE_COST
        assert ext.amount == _SINGLE_COST["amount"]
        assert ext.token == _SINGLE_COST["token"]
        assert ext.network == _SINGLE_COST["network"]
        assert ext.pay_to_address == _SINGLE_COST["pay_to_address"]
        # full list preserved
        assert ext.payment_options is not None
        assert len(ext.payment_options) == 2
        assert ext.payment_options[1] == _COST_ETH

    def test_backward_compat_flat_args(self):
        """Old single-cost path (no payment_options) must still work."""
        ext = X402AgentExtension(
            amount="1000000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
        )
        assert ext.amount == "1000000"
        assert ext.payment_options is None

    def test_empty_payment_options_raises(self):
        with pytest.raises(ValueError, match="non-empty list|payment_options"):
            X402AgentExtension(payment_options=[])

    def test_non_dict_entry_in_payment_options_raises(self):
        with pytest.raises(ValueError, match="dictionary entries"):
            X402AgentExtension(payment_options=["bad"])  # type: ignore[list-item]

    def test_missing_pay_to_address_when_required_raises(self):
        """All entries are fine type-wise, but primary has no pay_to_address."""
        cost_no_addr = {
            "amount": "1000000",
            "token": "USDC",
            "network": "base-sepolia",
            "pay_to_address": "",
        }
        with pytest.raises(ValueError, match="pay_to_address"):
            X402AgentExtension(payment_options=[cost_no_addr], required=True)

    def test_required_false_allows_empty_pay_to_address(self):
        """When required=False the address check is skipped."""
        cost_no_addr = {
            "amount": "1000000",
            "token": "USDC",
            "network": "base-sepolia",
            "pay_to_address": "",
        }
        ext = X402AgentExtension(payment_options=[cost_no_addr], required=False)
        assert ext.amount == "1000000"


# ===========================================================================
# BinduApplication._create_payment_requirements — one entry per option
# ===========================================================================


class TestCreatePaymentRequirements:
    """_create_payment_requirements produces one PaymentRequirements per option."""

    def _make_app(self):
        """Build a BinduApplication instance with all heavy construction bypassed."""
        from bindu.server.applications import BinduApplication

        # Bypass __init__ entirely — we only want the method under test.
        app = object.__new__(BinduApplication)
        return app

    def _make_manifest(self, url: str = "http://localhost:3773") -> MagicMock:
        m = MagicMock()
        m.url = url
        m.name = "test-agent"
        return m

    def _mock_process_price(self, amount, network):
        """Deterministic stub: returns (amount, 'asset-'+network, {})."""
        return amount, f"asset-{network}", {}

    def test_returns_none_when_no_extension(self):
        app = self._make_app()
        result = app._create_payment_requirements(None, self._make_manifest())
        assert result is None

    def test_single_option_via_payment_options(self):
        app = self._make_app()
        ext = MagicMock()
        ext.payment_options = [_SINGLE_COST]
        ext.pay_to_address = _SINGLE_COST["pay_to_address"]

        with patch(
            "x402.common.process_price_to_atomic_amount",
            side_effect=self._mock_process_price,
        ):
            from bindu.server.applications import BinduApplication as _App

            result = _App._create_payment_requirements(app, ext, self._make_manifest())

        assert result is not None
        assert len(result) == 1
        assert result[0]._data["network"] == _SINGLE_COST["network"]

    def test_two_options_produces_two_requirements(self):
        """The critical multi-option test — one PaymentRequirements per entry."""
        app = self._make_app()
        ext = MagicMock()
        ext.payment_options = [_SINGLE_COST, _COST_ETH]
        ext.pay_to_address = _SINGLE_COST["pay_to_address"]

        with patch(
            "x402.common.process_price_to_atomic_amount",
            side_effect=self._mock_process_price,
        ):
            from bindu.server.applications import BinduApplication as _App

            result = _App._create_payment_requirements(app, ext, self._make_manifest())

        assert result is not None
        assert len(result) == 2

        networks = {r._data["network"] for r in result}
        assert "base-sepolia" in networks
        assert "mainnet" in networks

    def test_fallback_when_no_payment_options(self):
        """When payment_options is None, falls back to flat fields."""
        app = self._make_app()
        ext = MagicMock()
        ext.payment_options = None
        ext.amount = _SINGLE_COST["amount"]
        ext.network = _SINGLE_COST["network"]
        ext.pay_to_address = _SINGLE_COST["pay_to_address"]

        with patch(
            "x402.common.process_price_to_atomic_amount",
            side_effect=self._mock_process_price,
        ):
            from bindu.server.applications import BinduApplication as _App

            result = _App._create_payment_requirements(app, ext, self._make_manifest())

        assert result is not None
        assert len(result) == 1
        assert result[0]._data["network"] == _SINGLE_COST["network"]

    def test_pay_to_address_per_option(self):
        """Each option uses its own pay_to_address, not the primary's."""
        addr_a = "0x" + "A" * 40
        addr_b = "0x" + "B" * 40
        opt_a = {**_SINGLE_COST, "pay_to_address": addr_a}
        opt_b = {**_COST_ETH, "pay_to_address": addr_b}

        app = self._make_app()
        ext = MagicMock()
        ext.payment_options = [opt_a, opt_b]
        ext.pay_to_address = addr_a  # primary fallback — should not bleed through

        with patch(
            "x402.common.process_price_to_atomic_amount",
            side_effect=self._mock_process_price,
        ):
            from bindu.server.applications import BinduApplication as _App

            result = _App._create_payment_requirements(app, ext, self._make_manifest())

        assert result is not None
        pay_tos = [r._data["pay_to"] for r in result]
        assert addr_a in pay_tos
        assert addr_b in pay_tos

    def test_resource_url_includes_suffix(self):
        """The resource field must be manifest.url + resource_suffix."""
        app = self._make_app()
        ext = MagicMock()
        ext.payment_options = [_SINGLE_COST]
        ext.pay_to_address = _SINGLE_COST["pay_to_address"]

        with patch(
            "x402.common.process_price_to_atomic_amount",
            side_effect=self._mock_process_price,
        ):
            from bindu.server.applications import BinduApplication as _App

            result = _App._create_payment_requirements(
                app,
                ext,
                self._make_manifest(url="http://localhost:3773"),
                resource_suffix="/",
            )

        assert result is not None
        assert result[0]._data["resource"] == "http://localhost:3773/"
