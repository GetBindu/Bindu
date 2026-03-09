import pytest
from bindu.penguin.config_validator import ConfigValidator


def test_missing_author():
    config = {
        "name": "agent",
        "deployment": {"url": "http://localhost:3773"},
    }

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    assert "author" in str(exc.value)


def test_missing_name():
    config = {
        "author": "test@example.com",
        "deployment": {"url": "http://localhost:3773"},
    }

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    assert "name" in str(exc.value)


def test_missing_deployment_url():
    config = {
        "author": "test@example.com",
        "name": "agent",
        "deployment": {},
    }

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    assert "deployment.url" in str(exc.value)


def test_execution_cost_accepts_single_dict():
    config = {
        "author": "test@example.com",
        "name": "agent",
        "deployment": {"url": "http://localhost:3773"},
        "execution_cost": {
            "amount": "0.1",
            "token": "USDC",
            "network": "base-sepolia",
            "pay_to_address": "0x123",
        },
    }

    validated = ConfigValidator.validate_and_process(config)
    assert isinstance(validated["execution_cost"], dict)
    assert validated["execution_cost"]["amount"] == "0.1"


def test_execution_cost_accepts_list_of_dicts():
    config = {
        "author": "test@example.com",
        "name": "agent",
        "deployment": {"url": "http://localhost:3773"},
        "execution_cost": [
            {
                "amount": "0.1",
                "token": "USDC",
                "network": "base",
                "pay_to_address": "0xabc",
            },
            {
                "amount": "0.0001",
                "token": "ETH",
                "network": "ethereum",
                "pay_to_address": "0xdef",
            },
        ],
    }

    validated = ConfigValidator.validate_and_process(config)
    assert isinstance(validated["execution_cost"], list)
    assert len(validated["execution_cost"]) == 2


def test_execution_cost_rejects_invalid_type():
    config = {
        "author": "test@example.com",
        "name": "agent",
        "deployment": {"url": "http://localhost:3773"},
        "execution_cost": "invalid",
    }

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    assert "execution_cost" in str(exc.value)
