"""Base configuration loader with factory pattern.

This module provides a unified approach to loading configurations from
environment variables, eliminating code duplication across config loaders.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.config.base")

T = TypeVar("T")


class ConfigLoader:
    """Unified configuration loader using factory pattern to eliminate duplication."""

    @staticmethod
    def load_from_env_or_user(
        config_key: str,
        user_config: Dict[str, Any],
        env_loader: Callable[[Dict[str, Any]], Optional[T]],
    ) -> Optional[T]:
        """Load config from user config or environment variables.

        Args:
            config_key: Key in user_config dict (e.g., 'storage', 'scheduler')
            user_config: User-provided configuration dictionary
            env_loader: Function to load from environment if not in user_config

        Returns:
            Configuration object or None
        """
        # Check if user already provided config
        if config_key in user_config:
            return user_config[config_key]

        # Load from environment
        return env_loader(user_config)

    @staticmethod
    def load_typed_config(
        config_key: str,
        user_config: Dict[str, Any],
        config_class: Type[T],
        type_field: str = "type",
        valid_types: Optional[List[str]] = None,
        default_type: Optional[str] = None,
        env_prefix: str = "",
        type_specific_loaders: Optional[
            Dict[str, Callable[[str], Dict[str, Any]]]
        ] = None,
    ) -> Optional[T]:
        """Load typed configuration (storage, scheduler, etc.) with validation.

        This is a DRY factory method that handles the common pattern of:
        1. Check user config
        2. Load type from environment
        3. Validate type
        4. Load type-specific settings
        5. Create config object

        Args:
            config_key: Key in user_config (e.g., 'storage')
            user_config: User-provided configuration
            config_class: Class to instantiate (e.g., StorageConfig)
            type_field: Field name for type (default: 'type')
            valid_types: List of valid type values
            default_type: Default type if not specified
            env_prefix: Environment variable prefix (e.g., 'STORAGE_')
            type_specific_loaders: Dict mapping type to loader function

        Returns:
            Configuration object or None
        """
        # Check if user already provided config
        if config_key in user_config:
            config_dict = user_config[config_key]
            config_type = config_dict.get(type_field)

            # Validate type
            if valid_types and config_type not in valid_types:
                logger.warning(
                    f"Invalid {config_key} type: {config_type}, using {default_type}"
                )
                config_type = default_type

            return config_class(**config_dict)

        # Load from environment
        env_type_key = f"{env_prefix}TYPE"
        config_type = os.getenv(env_type_key, default_type)

        if not config_type:
            return None

        # Validate type
        if valid_types and config_type not in valid_types:
            logger.warning(
                f"Invalid {config_key} type: {config_type}, using {default_type}"
            )
            config_type = default_type

        logger.debug(f"Loaded {env_type_key} from environment: {config_type}")

        # Load type-specific settings
        config_data = {type_field: config_type}

        if type_specific_loaders and config_type in type_specific_loaders:
            loader = type_specific_loaders[config_type]
            type_specific_data = loader(env_prefix)
            config_data.update(type_specific_data)

        return config_class(**config_data)

    @staticmethod
    def load_boolean_from_env(
        env_key: str, default: bool = False, true_values: tuple = ("true", "1", "yes")
    ) -> bool:
        """Load boolean value from environment variable.

        Args:
            env_key: Environment variable name
            default: Default value if not set
            true_values: Tuple of values considered True

        Returns:
            Boolean value
        """
        value = os.getenv(env_key, str(default)).lower()
        return value in true_values

    @staticmethod
    def load_dict_from_user_or_env(
        config_key: str,
        user_config: Dict[str, Any],
        env_loaders: Dict[str, Callable[[], Any]],
        required_when_enabled: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Load dictionary config from user config or environment variables.

        Args:
            config_key: Key in user_config
            user_config: User-provided configuration
            env_loaders: Dict mapping field names to loader functions
            required_when_enabled: List of required fields when config is enabled

        Returns:
            Configuration dictionary or None
        """
        # Check if user already provided config
        if config_key in user_config:
            return user_config[config_key]

        # Load from environment
        config_dict: Dict[str, Any] = {}

        for field, loader in env_loaders.items():
            value = loader()
            if value is not None:
                config_dict[field] = value

        # Validate required fields
        if required_when_enabled and config_dict.get("enabled"):
            for field in required_when_enabled:
                if field not in config_dict or config_dict[field] is None:
                    raise ValueError(
                        f"{field} is required when {config_key} is enabled"
                    )

        return config_dict if config_dict else None
