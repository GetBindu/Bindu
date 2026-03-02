"""
Configuration validation and processing for bindu agents.

This module provides utilities to validate and process agent configurations,
ensuring they meet the required schema and have proper defaults.
"""

import os
from typing import Any, Dict

from bindu import __version__
from bindu.common.protocol.types import AgentCapabilities, Skill


class ConfigValidator:
    """Validates and processes agent configuration."""

    DEFAULTS = {
        "name": "bindu-agent",
        "description": "A Bindu agent",
        "version": __version__,
        "recreate_keys": False,
        "skills": [],
        "capabilities": {},
        "storage": {"type": "memory"},
        "scheduler": {"type": "memory"},
        "kind": "agent",
        "debug_mode": False,
        "debug_level": 1,
        "monitoring": False,
        "telemetry": True,
        "num_history_sessions": 10,
        "documentation_url": None,
        "extra_metadata": {},
        "agent_trust": None,
        "key_password": None,
        "auth": None,
        "oltp_endpoint": None,
        "oltp_service_name": None,
        "oltp_verbose_logging": False,
        "oltp_service_version": "1.0.0",
        "oltp_deployment_environment": "production",
        "oltp_batch_max_queue_size": 2048,
        "oltp_batch_schedule_delay_millis": 5000,
        "oltp_batch_max_export_batch_size": 512,
        "oltp_batch_export_timeout_millis": 30000,
    }

    # Required fields (supports nested keys via dot notation)
    REQUIRED_FIELDS = [
        "author",
        "name",
        "deployment.url",
    ]

    @classmethod
    def validate_and_process(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and process agent configuration."""
        # 🔥 Validate required fields first (fail-fast)
        cls._validate_required_fields(config)

        # Start with defaults
        processed_config = cls.DEFAULTS.copy()

        # Update with provided config
        processed_config.update(config)

        # Process complex fields
        processed_config = cls._process_complex_fields(processed_config)

        # Validate field types
        cls._validate_field_types(processed_config)

        return processed_config

    # ------------------------------------------------------------------
    # Required field validation (NEW IMPROVED VERSION)
    # ------------------------------------------------------------------

    @classmethod
    def _validate_required_fields(cls, config: Dict[str, Any]) -> None:
        """Validate required fields including nested fields."""
        missing = []

        for field in cls.REQUIRED_FIELDS:
            keys = field.split(".")
            value = config

            for key in keys:
                if not isinstance(value, dict) or key not in value:
                    missing.append(field)
                    break
                value = value[key]

            if field not in missing and (
                value is None or (isinstance(value, str) and not value.strip())
            ):
                missing.append(field)

        if missing:
            formatted_fields = "\n".join(f"- {f}" for f in missing)

            example = """{
  "author": "you@example.com",
  "name": "my-agent",
  "deployment": {"url": "http://localhost:3773"}
}"""

            raise ValueError(
                f"Invalid Bindu configuration.\n\n"
                f"Missing required field(s):\n"
                f"{formatted_fields}\n\n"
                f"Example:\n{example}"
            )

    # ------------------------------------------------------------------
    # Complex field processing
    # ------------------------------------------------------------------

    @classmethod
    def _process_complex_fields(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(config.get("skills"), list) and config["skills"]:
            if isinstance(config["skills"][0], dict):
                config["skills"] = [Skill(**skill) for skill in config["skills"]]

        if isinstance(config.get("capabilities"), dict):
            config["capabilities"] = AgentCapabilities(**config["capabilities"])

        if config.get("auth"):
            cls._validate_auth_config(config["auth"])

        if config.get("telemetry"):
            cls._process_oltp_config(config)

        return config

    # ------------------------------------------------------------------
    # Field type validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_field_types(cls, config: Dict[str, Any]) -> None:
        string_fields = [
            "author",
            "name",
            "description",
            "version",
            "kind",
            "key_password",
        ]

        for field in string_fields:
            if (
                field in config
                and config[field] is not None
                and not isinstance(config[field], str)
            ):
                raise ValueError(f"Field '{field}' must be a string")

        bool_fields = ["recreate_keys", "debug_mode", "monitoring", "telemetry"]
        for field in bool_fields:
            if field in config and not isinstance(config[field], bool):
                raise ValueError(f"Field '{field}' must be a boolean")

        if "debug_level" in config:
            if not isinstance(config["debug_level"], int) or config[
                "debug_level"
            ] not in [1, 2]:
                raise ValueError("Field 'debug_level' must be 1 or 2")

        if "num_history_sessions" in config:
            if (
                not isinstance(config["num_history_sessions"], int)
                or config["num_history_sessions"] < 0
            ):
                raise ValueError(
                    "Field 'num_history_sessions' must be a non-negative integer"
                )

        if config.get("kind") not in ["agent", "team", "workflow"]:
            raise ValueError("Field 'kind' must be one of: agent, team, workflow")

    # ------------------------------------------------------------------
    # Auth validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_auth_config(cls, auth_config: Dict[str, Any]) -> None:
        if not isinstance(auth_config, dict):
            raise ValueError("Field 'auth' must be a dictionary")

        if not auth_config.get("enabled", False):
            return

        provider = auth_config.get("provider", "hydra").lower()

        if provider == "hydra":
            cls._validate_hydra_config(auth_config)
        else:
            raise ValueError(
                f"Unknown auth provider: '{provider}'. Supported providers: hydra"
            )

    @classmethod
    def _validate_hydra_config(cls, auth_config: Dict[str, Any]) -> None:
        if "admin_url" in auth_config:
            admin_url = auth_config["admin_url"]
            if not admin_url.startswith(("http://", "https://")):
                raise ValueError(
                    f"Invalid Hydra admin_url: '{admin_url}'. "
                    f"Expected format: 'https://hydra-admin.getbindu.com'"
                )

    # ------------------------------------------------------------------
    # Telemetry processing
    # ------------------------------------------------------------------

    @classmethod
    def _process_oltp_config(cls, config: Dict[str, Any]) -> None:
        oltp_endpoint = config.get("oltp_endpoint")
        if oltp_endpoint and isinstance(oltp_endpoint, str):
            if oltp_endpoint.startswith("env:"):
                config["oltp_endpoint"] = os.getenv(oltp_endpoint[4:])

    # ------------------------------------------------------------------
    # Public helper
    # ------------------------------------------------------------------

    @classmethod
    def create_bindufy_config(cls, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create bindufy configuration from raw config."""
        return cls.validate_and_process(raw_config)


def load_and_validate_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration from file path."""
    import json

    if not os.path.isabs(config_path):
        caller_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(caller_dir, config_path)

    with open(config_path, "r") as f:
        raw_config = json.load(f)

    return ConfigValidator.create_bindufy_config(raw_config)
