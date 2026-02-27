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

    # Default values for optional fields
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

    # Required fields that must be present
    REQUIRED_FIELDS = ["author", "deployment"]

    @classmethod
    def validate_and_process(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and process agent configuration.

        Args:
            config: Raw configuration dictionary

        Returns:
            Processed configuration with defaults applied

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Check required fields
        missing_fields = [field for field in cls.REQUIRED_FIELDS if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Start with defaults
        processed_config = cls.DEFAULTS.copy()

        # Update with provided config
        processed_config.update(config)

        # Process complex fields
        processed_config = cls._process_complex_fields(processed_config)

        # Validate field types
        cls._validate_field_types(processed_config)

        return processed_config

    @classmethod
    def _process_complex_fields(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process fields that need special handling."""
        # Process skills if provided as dict list
        if isinstance(config.get("skills"), list) and config["skills"]:
            if isinstance(config["skills"][0], dict):
                config["skills"] = [Skill(**skill) for skill in config["skills"]]

        # Process capabilities
        if isinstance(config.get("capabilities"), dict):
            config["capabilities"] = AgentCapabilities(**config["capabilities"])

        # TODO: Process agent_trust - IN DEVELOPMENT PHASE
        # Agent trust validation is currently in development
        # Keep as dict for now - TypedDict validation will be added in future
        if isinstance(config.get("agent_trust"), dict):
            pass  # Keep as dict, validation to be implemented

        # Process key password - support environment variable and prompt
        if config.get("key_password"):
            config["key_password"] = config["key_password"]

        # Validate auth configuration if provided
        if config.get("auth"):
            cls._validate_auth_config(config["auth"])

        # Process OLTP configuration only if telemetry is enabled
        if config.get("telemetry"):
            cls._process_oltp_config(config)

        return config

    @classmethod
    def _validate_field_types(cls, config: Dict[str, Any]) -> None:
        """Validate that fields have correct types."""
        # Validate string fields
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

        # Validate boolean fields
        bool_fields = ["recreate_keys", "debug_mode", "monitoring", "telemetry"]
        for field in bool_fields:
            if field in config and not isinstance(config[field], bool):
                raise ValueError(f"Field '{field}' must be a boolean")

        # Validate numeric fields
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

        # Validate kind
        if config.get("kind") not in ["agent", "team", "workflow"]:
            raise ValueError("Field 'kind' must be one of: agent, team, workflow")

    @classmethod
    def _validate_auth_config(cls, auth_config: Dict[str, Any]) -> None:
        """Validate authentication configuration.

        Args:
            auth_config: Auth configuration dictionary

        Raises:
            ValueError: If auth configuration is invalid
        """
        if not isinstance(auth_config, dict):
            raise ValueError("Field 'auth' must be a dictionary")

        # Check if enabled
        if not auth_config.get("enabled", False):
            return  # Auth disabled, no further validation needed

        # Get provider (default to hydra)
        provider = auth_config.get("provider", "hydra").lower()

        # Validate based on provider
        if provider == "hydra":
            cls._validate_hydra_config(auth_config)
        else:
            raise ValueError(
                f"Unknown auth provider: '{provider}'. Supported providers: hydra"
            )

    @classmethod
    def _validate_hydra_config(cls, auth_config: Dict[str, Any]) -> None:
        """Validate Hydra-specific configuration.

        Args:
            auth_config: Auth configuration dictionary

        Raises:
            ValueError: If Hydra configuration is invalid
        """
        # Validate admin_url and public_url if provided
        if "admin_url" in auth_config:
            admin_url = auth_config["admin_url"]
            if not admin_url.startswith("http://") and not admin_url.startswith(
                "https://"
            ):
                raise ValueError(
                    f"Invalid Hydra admin_url: '{admin_url}'. "
                    f"Expected format: 'https://hydra-admin.getbindu.com'"
                )

        if "public_url" in auth_config:
            public_url = auth_config["public_url"]
            if not public_url.startswith("http://") and not public_url.startswith(
                "https://"
            ):
                raise ValueError(
                    f"Invalid Hydra public_url: '{public_url}'. "
                    f"Expected format: 'https://hydra.getbindu.com'"
                )

        # Validate timeout
        if "timeout" in auth_config:
            timeout = auth_config["timeout"]
            if not isinstance(timeout, int) or timeout <= 0:
                raise ValueError(
                    f"Invalid Hydra timeout: '{timeout}'. "
                    f"Expected positive integer (seconds)"
                )

        # Validate verify_ssl
        if "verify_ssl" in auth_config:
            verify_ssl = auth_config["verify_ssl"]
            if not isinstance(verify_ssl, bool):
                raise ValueError(
                    f"Invalid Hydra verify_ssl: '{verify_ssl}'. "
                    f"Expected boolean (true/false)"
                )

        # Validate max_retries
        if "max_retries" in auth_config:
            max_retries = auth_config["max_retries"]
            if not isinstance(max_retries, int) or max_retries < 0:
                raise ValueError(
                    f"Invalid Hydra max_retries: '{max_retries}'. "
                    f"Expected non-negative integer"
                )

        # Validate cache_ttl
        if "cache_ttl" in auth_config:
            cache_ttl = auth_config["cache_ttl"]
            if not isinstance(cache_ttl, int) or cache_ttl <= 0:
                raise ValueError(
                    f"Invalid Hydra cache_ttl: '{cache_ttl}'. "
                    f"Expected positive integer (seconds)"
                )

        # Validate max_cache_size
        if "max_cache_size" in auth_config:
            max_cache_size = auth_config["max_cache_size"]
            if not isinstance(max_cache_size, int) or max_cache_size <= 0:
                raise ValueError(
                    f"Invalid Hydra max_cache_size: '{max_cache_size}'. "
                    f"Expected positive integer"
                )

        # Validate auto_register_agents
        if "auto_register_agents" in auth_config:
            auto_register = auth_config["auto_register_agents"]
            if not isinstance(auto_register, bool):
                raise ValueError(
                    f"Invalid Hydra auto_register_agents: '{auto_register}'. "
                    f"Expected boolean (true/false)"
                )

        # Validate agent_client_prefix
        if "agent_client_prefix" in auth_config:
            prefix = auth_config["agent_client_prefix"]
            if not isinstance(prefix, str) or not prefix:
                raise ValueError(
                    f"Invalid Hydra agent_client_prefix: '{prefix}'. "
                    f"Expected non-empty string"
                )

    @classmethod
    def _process_oltp_config(cls, config: Dict[str, Any]) -> None:
        """Process OLTP configuration when telemetry is enabled.

        This function extracts OLTP endpoint, service name, and verbose logging from the config,
        supporting environment variable references.

        Args:
            config: Configuration dictionary (modified in place)
        """
        # Process OLTP endpoint - support environment variable
        oltp_endpoint = config.get("oltp_endpoint")
        if oltp_endpoint and isinstance(oltp_endpoint, str):
            if oltp_endpoint.startswith("env:"):
                env_var = oltp_endpoint[4:]  # Remove 'env:' prefix
                config["oltp_endpoint"] = os.getenv(env_var)
            # else: use the value as-is

        # Process OLTP service name - support environment variable
        oltp_service_name = config.get("oltp_service_name")
        if oltp_service_name and isinstance(oltp_service_name, str):
            if oltp_service_name.startswith("env:"):
                env_var = oltp_service_name[4:]  # Remove 'env:' prefix
                config["oltp_service_name"] = os.getenv(env_var)
            # else: use the value as-is

        # Process verbose logging flag - support environment variable
        oltp_verbose_logging = config.get("oltp_verbose_logging")
        if oltp_verbose_logging and isinstance(oltp_verbose_logging, str):
            if oltp_verbose_logging.startswith("env:"):
                env_var = oltp_verbose_logging[4:]  # Remove 'env:' prefix
                env_value = os.getenv(env_var, "false").lower()
                config["oltp_verbose_logging"] = env_value in ("true", "1", "yes")
            # else: use the value as-is

    @classmethod
    def create_bindufy_config(cls, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a configuration dict ready for bindufy function.

        This is a convenience method that validates, processes, and ensures
        the config is in the right format for the bindufy function.

        Args:
            raw_config: Raw configuration (e.g., from JSON file)

        Returns:
            Configuration dictionary ready for bindufy
        """
        # Validate and process
        config = cls.validate_and_process(raw_config)

        # Ensure nested configs are dictionaries (not model instances)
        # for compatibility with bindufy
        if "deployment" not in config:
            config["deployment"] = {}
        if "storage" not in config:
            config["storage"] = {}
        if "scheduler" not in config:
            config["scheduler"] = {}

        return config


def load_and_validate_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from file and validate it.

    Args:
        config_path: Path to configuration file (JSON)

    Returns:
        Validated and processed configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    import json

    # Handle relative paths
    if not os.path.isabs(config_path):
        caller_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(caller_dir, config_path)

    # Load config
    with open(config_path, "r") as f:
        raw_config = json.load(f)

    # Validate and return
    return ConfigValidator.create_bindufy_config(raw_config)
