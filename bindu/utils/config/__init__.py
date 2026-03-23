"""Configuration loading utilities with factory pattern.

This package provides utilities for loading configurations from environment
variables with a unified approach.
"""

from .base import ConfigLoader
from .env_loader import (
    create_storage_config_from_env,
    create_scheduler_config_from_env,
    create_tunnel_config_from_env,
    create_sentry_config_from_env,
    create_auth_config_from_env,
    create_vault_config_from_env,
)
from .enricher import load_config_from_env
from .path_resolver import resolve_key_directory
from .settings import (
    prepare_auth_settings,
    prepare_vault_settings,
    update_auth_settings,
    update_vault_settings,
)

__all__ = [
    # Base factory
    "ConfigLoader",
    # Config creators
    "create_storage_config_from_env",
    "create_scheduler_config_from_env",
    "create_tunnel_config_from_env",
    "create_sentry_config_from_env",
    "create_auth_config_from_env",
    "create_vault_config_from_env",
    # Config enrichment
    "load_config_from_env",
    # Path resolution
    "resolve_key_directory",
    # Settings preparation (recommended)
    "prepare_auth_settings",
    "prepare_vault_settings",
    # Settings updates (deprecated - mutates global state)
    "update_auth_settings",
    "update_vault_settings",
]
