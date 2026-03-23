"""Payment and x402 extension test fixtures."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_payment_requirements() -> dict:
    """Create mock payment requirements for testing.

    Returns:
        dict: Valid payment requirements structure
    """
    return {
        "accepts": [
            {
                "scheme": "onchain",
                "network": "base-sepolia",
                "chainId": "84532",
                "to": "0x1234567890123456789012345678901234567890",
                "amount": "10000",
                "token": "USDC",
            }
        ]
    }


@pytest.fixture
def mock_payment_payload() -> dict:
    """Create mock payment payload for testing.

    Returns:
        dict: Valid payment payload structure
    """
    return {
        "scheme": "onchain",
        "network": "base-sepolia",
        "chainId": "84532",
        "to": "0x1234567890123456789012345678901234567890",
        "amount": "10000",
        "token": "USDC",
        "txHash": "0xabc123def456",
    }


@pytest.fixture
def mock_facilitator_client() -> MagicMock:
    """Create a mock facilitator client for payment verification.

    Returns:
        MagicMock: Mock facilitator client with async methods
    """
    client = MagicMock()
    client.verify_payment = MagicMock(return_value={"verified": True})
    client.settle_payment = MagicMock(return_value={"settled": True})
    return client
