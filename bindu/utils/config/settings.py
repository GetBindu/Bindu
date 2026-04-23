"""Settings preparation utilities for configuration.

This module prepares configuration dictionaries without directly mutating
global settings. The caller is responsible for applying these to app_settings.
"""

from typing import Any, Dict, Optional

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.config.settings")


def _remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the dictionary without None-valued entries."""
    return {key: value for key, value in data.items() if value is not None}


def prepare_auth_settings(auth_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Prepare auth settings from configuration.

    Returns a dictionary of settings to apply, rather than mutating global state.
    The caller should apply these to app_settings.

    Args:
        auth_config: Authentication configuration dictionary

    Returns:
        Dictionary of auth settings to apply, or None if auth is disabled
    """
    if not auth_config or not auth_config.get("enabled"):
        return None

    provider = auth_config.get("provider", "hydra")

    settings_to_apply = {
        "auth": {
            "enabled": True,
            "provider": provider,
        }
    }

    if provider == "hydra":
        # Prepare Hydra-specific settings
        settings_to_apply["hydra"] = {
            "enabled": True,
            "admin_url": auth_config.get("admin_url"),
            "public_url": auth_config.get("public_url"),
            "timeout": auth_config.get("timeout"),
            "verify_ssl": auth_config.get("verify_ssl"),
            "max_retries": auth_config.get("max_retries"),
            "cache_ttl": auth_config.get("cache_ttl"),
            "max_cache_size": auth_config.get("max_cache_size"),
            "auto_register_agents": auth_config.get("auto_register_agents"),
            "agent_client_prefix": auth_config.get("agent_client_prefix"),
        }
        settings_to_apply["hydra"] = _remove_none_values(settings_to_apply["hydra"])
    else:
        logger.warning(f"Unknown authentication provider: {provider}")

    return settings_to_apply


def prepare_vault_settings(vault_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Prepare vault settings from configuration.

    Returns a dictionary of settings to apply, rather than mutating global state.
    The caller should apply these to app_settings.

    Args:
        vault_config: Vault configuration dictionary

    Returns:
        Dictionary of vault settings to apply, or None if not configured
    """
    if not vault_config:
        return None

    settings_to_apply = {
        "vault": {
            "enabled": vault_config.get("enabled"),
            "url": vault_config.get("url"),
            "token": vault_config.get("token"),
        }
    }

    settings_to_apply["vault"] = _remove_none_values(settings_to_apply["vault"])

    if settings_to_apply["vault"].get("enabled"):
        logger.info(
            f"Vault integration enabled: {settings_to_apply['vault'].get('url')}"
        )
    else:
        logger.debug("Vault integration disabled")

    return settings_to_apply


# Backward compatibility - these functions apply settings directly
def update_auth_settings(auth_config: Dict[str, Any]) -> None:
    """Update global auth settings from configuration.

    DEPRECATED: Use prepare_auth_settings() instead and apply manually.
    This function is kept for backward compatibility.

    Args:
        auth_config: Authentication configuration dictionary
    """
    settings = prepare_auth_settings(auth_config)
    if not settings:
        return

    from bindu.settings import app_settings

    # Apply auth settings
    if "auth" in settings:
        for key, value in settings["auth"].items():
            setattr(app_settings.auth, key, value)

    # Apply hydra settings
    if "hydra" in settings:
        for key, value in settings["hydra"].items():
            setattr(app_settings.hydra, key, value)


def update_vault_settings(vault_config: Dict[str, Any]) -> None:
    """Update global vault settings from configuration.

    DEPRECATED: Use prepare_vault_settings() instead and apply manually.
    This function is kept for backward compatibility.

    Args:
        vault_config: Vault configuration dictionary
    """
    settings = prepare_vault_settings(vault_config)
    if not settings:
        return

    from bindu.settings import app_settings

    # Apply vault settings
    if "vault" in settings:
        for key, value in settings["vault"].items():
            setattr(app_settings.vault, key, value)
