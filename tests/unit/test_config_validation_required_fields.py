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
