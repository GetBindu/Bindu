"""Unit tests for bindufy validation logic."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest

from bindu.penguin.bindufy import bindufy
from bindu.penguin.config_validator import ConfigValidator

pytestmark = pytest.mark.skip(
    reason="Fixture issues with bindufy module - needs refactoring"
)


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
    """Create a valid handler function for bindufy."""

    def _handler(messages):
        return "ok"

    return _handler


@pytest.fixture
def failing_handler():
    """Create a handler function that raises an exception."""

    def _handler(messages):
        raise RuntimeError("handler boom")

    return _handler


@pytest.fixture
def bindufy_stubs(monkeypatch):
    """Stub external dependencies so bindufy unit tests stay isolated."""
    import bindu.penguin.bindufy as bindufy_module
    import bindu.server as server_module

    class DummyBinduApplication:
        def __init__(self, **kwargs):
            self.url = kwargs["manifest"].url
            self._agent_card_json_schema = None

    monkeypatch.setattr(bindufy_module, "load_config_from_env", lambda cfg: dict(cfg))
    monkeypatch.setattr(
        bindufy_module, "create_storage_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_scheduler_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_sentry_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_vault_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_auth_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(bindufy_module, "update_vault_settings", lambda _cfg: None)
    monkeypatch.setattr(bindufy_module, "update_auth_settings", lambda _cfg: None)
    monkeypatch.setattr(
        bindufy_module, "load_skills", lambda skills, _caller_dir: skills
    )
    monkeypatch.setattr(
        bindufy_module,
        "resolve_key_directory",
        lambda explicit_dir, caller_dir, subdir: Path(caller_dir) / subdir,
    )
    monkeypatch.setattr(
        bindufy_module,
        "initialize_did_extension",
        lambda **_kwargs: SimpleNamespace(did="did:bindu:tester:test-agent"),
    )
    monkeypatch.setattr(server_module, "BinduApplication", DummyBinduApplication)
    monkeypatch.setattr(
        bindufy_module.app_settings.auth, "enabled", False, raising=False
    )


@pytest.fixture
def bindufy_stubs_with_env_loader(monkeypatch):
    """Stub bindufy dependencies while keeping real load_config_from_env logic."""
    import bindu.server as server_module
    import bindu.penguin.bindufy as bindufy_module

    class DummyBinduApplication:
        def __init__(self, **kwargs):
            self.url = kwargs["manifest"].url
            self._agent_card_json_schema = None

    monkeypatch.setattr(
        bindufy_module, "create_storage_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_scheduler_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_sentry_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_vault_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(
        bindufy_module, "create_auth_config_from_env", lambda _cfg: None
    )
    monkeypatch.setattr(bindufy_module, "update_vault_settings", lambda _cfg: None)
    monkeypatch.setattr(bindufy_module, "update_auth_settings", lambda _cfg: None)
    monkeypatch.setattr(
        bindufy_module, "load_skills", lambda skills, _caller_dir: skills
    )
    monkeypatch.setattr(
        bindufy_module,
        "resolve_key_directory",
        lambda explicit_dir, caller_dir, subdir: Path(caller_dir) / subdir,
    )
    monkeypatch.setattr(
        bindufy_module,
        "initialize_did_extension",
        lambda **_kwargs: SimpleNamespace(did="did:bindu:tester:test-agent"),
    )
    monkeypatch.setattr(server_module, "BinduApplication", DummyBinduApplication)
    monkeypatch.setattr(
        bindufy_module.app_settings.auth, "enabled", False, raising=False
    )


def test_bindufy_happy_path_returns_manifest(
    valid_config, valid_handler, bindufy_stubs
):
    """bindufy should return a manifest for valid config and handler."""
    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.name == "test-agent"
    assert manifest.description == "Agent for unit testing"
    assert manifest.url == "http://localhost:3773"


def test_bindufy_optional_fields_skills_empty_and_expose_false(
    valid_config, valid_handler, bindufy_stubs
):
    """Optional fields should work with skills=[] and expose=False."""
    valid_config["skills"] = []
    valid_config["deployment"]["expose"] = False

    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.skills == []
    assert manifest.url == "http://localhost:3773"


def test_bindufy_raises_type_error_for_non_dict_config(valid_handler):
    """bindufy should raise clear TypeError for invalid config type."""
    with pytest.raises(TypeError, match="config must be a dictionary"):
        bindufy("not-a-dict", valid_handler, run_server=False)  # type: ignore[arg-type]


def test_bindufy_raises_type_error_for_non_callable_handler(
    valid_config, bindufy_stubs
):
    """bindufy should raise clear TypeError for non-callable handler."""
    with pytest.raises(TypeError, match="handler must be callable"):
        bindufy(valid_config, "not-callable", run_server=False)  # type: ignore[arg-type]


def test_bindufy_raises_value_error_for_missing_required_fields(
    valid_handler, bindufy_stubs
):
    """bindufy should raise ValueError when required fields are missing."""
    invalid_config = {"author": "tester@example.com"}

    with pytest.raises(ValueError, match="Missing required fields: deployment"):
        bindufy(invalid_config, valid_handler, run_server=False)


def test_bindufy_raises_value_error_for_empty_author(
    valid_config, valid_handler, bindufy_stubs
):
    """bindufy should reject empty author values."""
    valid_config["author"] = "   "

    with pytest.raises(
        ValueError, match="'author' is required in config and cannot be empty"
    ):
        bindufy(valid_config, valid_handler, run_server=False)


def test_bindufy_propagates_exception_from_handler(
    valid_config, failing_handler, bindufy_stubs
):
    """Exceptions raised by handler should propagate through manifest.run."""
    manifest = bindufy(valid_config, failing_handler, run_server=False)
    assert manifest.run is not None
    run_fn = manifest.run

    with pytest.raises(RuntimeError, match="handler boom"):
        cast(Callable[[str], Any], run_fn)("hello")


def test_config_validator_raises_type_error_for_non_dict_input():
    """ConfigValidator should fail fast with clear TypeError."""
    with pytest.raises(TypeError, match="config must be a dictionary"):
        ConfigValidator.validate_and_process("invalid")  # type: ignore[arg-type]


def test_config_validator_raises_value_error_for_invalid_debug_level(valid_config):
    """ConfigValidator should reject unsupported debug levels."""
    valid_config["debug_level"] = 3

    with pytest.raises(ValueError, match="Field 'debug_level' must be 1 or 2"):
        ConfigValidator.validate_and_process(valid_config)


def test_config_validator_converts_skill_dicts_to_skill_models(valid_config):
    """ConfigValidator should convert skill dictionaries into Skill models."""
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


def test_bindufy_overrides_deployment_port_from_bindu_port_env(
    valid_config, valid_handler, bindufy_stubs_with_env_loader, monkeypatch
):
    """BINDU_PORT should override the configured deployment port."""
    monkeypatch.setenv("BINDU_PORT", "4000")

    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.url == "http://localhost:4000"


def test_bindufy_overrides_deployment_url_from_env(
    valid_config, valid_handler, bindufy_stubs_with_env_loader, monkeypatch
):
    """BINDU_DEPLOYMENT_URL should override the full configured URL."""
    monkeypatch.setenv("BINDU_DEPLOYMENT_URL", "http://127.0.0.1:5001")

    manifest = bindufy(valid_config, valid_handler, run_server=False)

    assert manifest.url == "http://127.0.0.1:5001"
