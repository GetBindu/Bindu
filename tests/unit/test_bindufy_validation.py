"""Unit tests for bindufy validation logic."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
import importlib

bindufy_module = importlib.import_module("bindu.penguin.bindufy")
from bindu.penguin.bindufy import bindufy
from bindu.penguin.config_validator import ConfigValidator

@pytest.fixture
def valid_config() -> dict:
    """Create a minimal valid bindufy config."""
    return {
        "author": "tester@example.com",
        "name": "test-agent",
        "description": "Agent for unit testing",
        "deployment": {
            "url": "http://localhost:3773",
            "expose": True,
            "protocol_version": "1.0.0",
        },
    }


@pytest.fixture
def valid_handler():
    def _handler(messages):
        return "ok"

    return _handler


@pytest.fixture
def failing_handler():
    def _handler(messages):
        raise RuntimeError("handler boom")

    return _handler


@pytest.fixture
def bindufy_stubs(monkeypatch):
    """Stub external dependencies so bindufy unit tests stay isolated."""
    import bindu.server as server_module

    class DummyBinduApplication:
        def __init__(self, **kwargs):
            self.url = kwargs["manifest"].url
            self._agent_card_json_schema = None

    monkeypatch.setattr(bindufy_module, "load_config_from_env", lambda cfg: dict(cfg), raising=False)
    monkeypatch.setattr(bindufy_module, "create_storage_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_scheduler_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_sentry_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_vault_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_auth_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "update_vault_settings", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "update_auth_settings", lambda _cfg: None, raising=False)

    monkeypatch.setattr(
        bindufy_module,
        "load_skills",
        lambda skills, _caller_dir: skills,
        raising=False,
    )

    monkeypatch.setattr(
        bindufy_module,
        "resolve_key_directory",
        lambda explicit_dir, caller_dir, subdir: Path(caller_dir) / subdir,
        raising=False,
    )

    monkeypatch.setattr(
        bindufy_module,
        "initialize_did_extension",
        lambda **_kwargs: SimpleNamespace(did="did:bindu:tester:test-agent"),
        raising=False,
    )

    monkeypatch.setattr(server_module, "BinduApplication", DummyBinduApplication)

    monkeypatch.setattr(
        bindufy_module.app_settings.auth,
        "enabled",
        False,
        raising=False,
    )


@pytest.fixture
def bindufy_stubs_with_env_loader(monkeypatch):
    import bindu.server as server_module

    class DummyBinduApplication:
        def __init__(self, **kwargs):
            self.url = kwargs["manifest"].url
            self._agent_card_json_schema = None

    monkeypatch.setattr(bindufy_module, "create_storage_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_scheduler_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_sentry_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_vault_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "create_auth_config_from_env", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "update_vault_settings", lambda _cfg: None, raising=False)
    monkeypatch.setattr(bindufy_module, "update_auth_settings", lambda _cfg: None, raising=False)

    monkeypatch.setattr(
        bindufy_module,
        "load_skills",
        lambda skills, _caller_dir: skills,
        raising=False,
    )

    monkeypatch.setattr(
        bindufy_module,
        "resolve_key_directory",
        lambda explicit_dir, caller_dir, subdir: Path(caller_dir) / subdir,
        raising=False,
    )

    monkeypatch.setattr(
        bindufy_module,
        "initialize_did_extension",
        lambda **_kwargs: SimpleNamespace(did="did:bindu:tester:test-agent"),
        raising=False,
    )

    monkeypatch.setattr(server_module, "BinduApplication", DummyBinduApplication)

    monkeypatch.setattr(
        bindufy_module.app_settings.auth,
        "enabled",
        False,
        raising=False,
    )


def test_bindufy_happy_path_returns_manifest(valid_config, valid_handler, bindufy_stubs):
    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.name == "test-agent"
    assert manifest.description == "Agent for unit testing"
    assert manifest.url == "http://localhost:3773"


def test_bindufy_optional_fields_skills_empty_and_expose_false(valid_config, valid_handler, bindufy_stubs):
    valid_config["skills"] = []
    valid_config["deployment"]["expose"] = False

    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.skills == []
    assert manifest.url == "http://localhost:3773"


def test_bindufy_raises_type_error_for_non_dict_config(valid_handler):
    with pytest.raises(TypeError):
        bindufy("not-a-dict", valid_handler, run_server=False)


def test_bindufy_raises_type_error_for_non_callable_handler(valid_config, bindufy_stubs):
    with pytest.raises(TypeError, match="handler must be callable"):
        bindufy(valid_config, "not-callable", run_server=False)


def test_bindufy_raises_value_error_for_missing_required_fields(valid_handler, bindufy_stubs):
    invalid_config = {"author": "tester@example.com"}

    with pytest.raises(ValueError):
        bindufy(invalid_config, valid_handler, run_server=False)


def test_bindufy_raises_value_error_for_empty_author(valid_config, valid_handler, bindufy_stubs):
    valid_config["author"] = "   "

    with pytest.raises(ValueError):
        bindufy(valid_config, valid_handler, run_server=False)


def test_bindufy_propagates_exception_from_handler(valid_config, failing_handler, bindufy_stubs):
    manifest = bindufy(valid_config, failing_handler, run_server=False)

    run_fn = manifest.run

    with pytest.raises(RuntimeError, match="handler boom"):
        cast(Callable[[str], Any], run_fn)("hello")


def test_config_validator_raises_type_error_for_non_dict_input():
    with pytest.raises(ValueError):
        ConfigValidator.validate_and_process("invalid")


def test_config_validator_raises_value_error_for_invalid_debug_level(valid_config):
    valid_config["debug_level"] = 3

    with pytest.raises(ValueError):
        ConfigValidator.validate_and_process(valid_config)


def test_config_validator_converts_skill_dicts_to_skill_models(valid_config):
    valid_config["skills"] = [
        {
            "id": "summarize",
            "name": "summarize",
            "description": "Summarize text",
            "tags": ["nlp"],
            "examples": ["summarize this"],
            "inputModes": ["text/plain"],
            "outputModes": ["text/plain"],
        }
    ]

    processed = ConfigValidator.validate_and_process(valid_config)

    assert len(processed["skills"]) == 1
    assert processed["skills"][0]["id"] == "summarize"


def test_bindufy_overrides_deployment_port_from_bindu_port_env(valid_config, valid_handler, bindufy_stubs_with_env_loader, monkeypatch):
    monkeypatch.setenv("BINDU_PORT", "4000")

    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.url == "http://localhost:4000"


def test_bindufy_overrides_deployment_url_from_env(valid_config, valid_handler, bindufy_stubs_with_env_loader, monkeypatch):
    monkeypatch.setenv("BINDU_DEPLOYMENT_URL", "http://127.0.0.1:5001")

    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.url == "http://127.0.0.1:5001"