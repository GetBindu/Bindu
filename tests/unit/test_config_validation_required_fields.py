import pytest

from bindu.penguin.config_validator import ConfigValidator


def test_missing_author():
    config = {
        "name": "test-agent",
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


def test_missing_deployment():
    config = {
        "author": "test@example.com",
        "name": "test-agent",
    }

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    assert "deployment.url" in str(exc.value)


def test_missing_deployment_url():
    config = {
        "author": "test@example.com",
        "name": "test-agent",
        "deployment": {},
    }

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    assert "deployment.url" in str(exc.value)


def test_multiple_missing_fields():
    config = {}

    with pytest.raises(ValueError) as exc:
        ConfigValidator.validate_and_process(config)

    error_message = str(exc.value)

    assert "author" in error_message
    assert "name" in error_message
    assert "deployment.url" in error_message