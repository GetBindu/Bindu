"""Environment-based configuration.

This module uses the ConfigLoader base class to eliminate code duplication
across different configuration types.
"""

import os
from typing import Any, Dict, Literal, Optional, cast

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.config.env_loader")


def create_storage_config_from_env(user_config: Dict[str, Any]):
    """Create StorageConfig from environment variables and user config.

    Args:
        user_config: User-provided configuration dictionary

    Returns:
        StorageConfig instance or None if not configured
    """
    from bindu.common.models import StorageConfig

    # Check if user already provided storage config
    if "storage" in user_config:
        storage_dict = user_config["storage"]
        storage_type = storage_dict.get("type")
        if storage_type not in ("postgres", "memory"):
            logger.warning(f"Invalid storage type: {storage_type}, using memory")
            storage_type = "memory"
        return StorageConfig(
            type=storage_type,
            database_url=storage_dict.get("postgres_url"),
        )

    # Load from environment
    storage_type = os.getenv("STORAGE_TYPE")
    if not storage_type:
        return None

    if storage_type not in ("postgres", "memory"):
        logger.warning(f"Invalid storage type: {storage_type}, using memory")
        storage_type = "memory"

    logger.debug(f"Loaded STORAGE_TYPE from environment: {storage_type}")

    # Get database URL from environment
    database_url = None
    if storage_type == "postgres":
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.debug("Loaded DATABASE_URL from environment")

    return StorageConfig(
        type=cast(Literal["postgres", "memory"], storage_type),
        database_url=database_url,
    )


def create_scheduler_config_from_env(user_config: Dict[str, Any]):
    """Create SchedulerConfig from environment variables and user config.

    Args:
        user_config: User-provided configuration dictionary

    Returns:
        SchedulerConfig instance or None if not configured
    """
    from bindu.common.models import SchedulerConfig

    # Check if user already provided scheduler config
    if "scheduler" in user_config:
        scheduler_dict = user_config["scheduler"]
        scheduler_type = scheduler_dict.get("type")
        if scheduler_type not in ("redis", "memory"):
            logger.warning(f"Invalid scheduler type: {scheduler_type}, using memory")
            scheduler_type = "memory"
        return SchedulerConfig(
            type=scheduler_type,
            redis_url=scheduler_dict.get("redis_url"),
        )

    # Load from environment
    scheduler_type = os.getenv("SCHEDULER_TYPE")
    if not scheduler_type:
        return None

    if scheduler_type not in ("redis", "memory"):
        logger.warning(f"Invalid scheduler type: {scheduler_type}, using memory")
        scheduler_type = "memory"

    logger.debug(f"Loaded SCHEDULER_TYPE from environment: {scheduler_type}")

    # Get Redis URL from environment
    redis_url = None
    if scheduler_type == "redis":
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            logger.debug("Loaded REDIS_URL from environment")

    return SchedulerConfig(
        type=cast(Literal["redis", "memory"], scheduler_type), redis_url=redis_url
    )


def create_tunnel_config_from_env(user_config: Dict[str, Any]):
    """Create TunnelConfig from environment variables and user config.

    Args:
        user_config: User-provided configuration dictionary

    Returns:
        TunnelConfig instance or None if not configured
    """
    from bindu.tunneling.config import TunnelConfig

    # Check if user already provided tunnel config
    if "tunnel" in user_config:
        tunnel_dict = user_config["tunnel"]
        return TunnelConfig(
            enabled=tunnel_dict.get("enabled", False),
            server_address=tunnel_dict.get("server_address", "142.132.241.44:7000"),
            subdomain=tunnel_dict.get("subdomain"),
            tunnel_domain=tunnel_dict.get("tunnel_domain", "tunnel.getbindu.com"),
            protocol=tunnel_dict.get("protocol", "http"),
            use_tls=tunnel_dict.get("use_tls", False),
            local_host=tunnel_dict.get("local_host", "127.0.0.1"),
        )

    # Load from environment
    tunnel_enabled = os.getenv("TUNNEL_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    if not tunnel_enabled:
        return None

    logger.debug("Tunnel enabled from environment")

    return TunnelConfig(
        enabled=True,
        server_address=os.getenv("TUNNEL_SERVER_ADDRESS", "142.132.241.44:7000"),
        subdomain=os.getenv("TUNNEL_SUBDOMAIN"),
        tunnel_domain=os.getenv("TUNNEL_DOMAIN", "tunnel.getbindu.com"),
        protocol=os.getenv("TUNNEL_PROTOCOL", "http"),
        use_tls=os.getenv("TUNNEL_USE_TLS", "false").lower() in ("true", "1", "yes"),
        local_host=os.getenv("TUNNEL_LOCAL_HOST", "127.0.0.1"),
    )


def create_sentry_config_from_env(user_config: Dict[str, Any]):
    """Create SentryConfig from environment variables and user config.

    Args:
        user_config: User-provided configuration dictionary

    Returns:
        SentryConfig instance or None if not configured
    """
    from bindu.common.models import SentryConfig

    # Check if user already provided sentry config
    if "sentry" in user_config:
        sentry_dict = user_config["sentry"]
        if not sentry_dict.get("enabled"):
            return None
        return SentryConfig(
            enabled=True,
            dsn=sentry_dict.get("dsn"),
            environment=sentry_dict.get("environment", "development"),
            release=sentry_dict.get("release"),
            traces_sample_rate=sentry_dict.get("traces_sample_rate", 1.0),
            profiles_sample_rate=sentry_dict.get("profiles_sample_rate", 0.1),
            enable_tracing=sentry_dict.get("enable_tracing", True),
            send_default_pii=sentry_dict.get("send_default_pii", False),
            debug=sentry_dict.get("debug", False),
        )

    # Load from environment
    sentry_enabled = os.getenv("SENTRY_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if not sentry_enabled:
        return None

    from bindu.settings import app_settings

    sentry_dsn = os.getenv("SENTRY_DSN")
    logger.debug(
        f"Loaded Sentry configuration: enabled={sentry_enabled}, dsn={'***' if sentry_dsn else 'None'}"
    )

    return SentryConfig(
        enabled=True,
        dsn=sentry_dsn,
        environment=app_settings.sentry.environment,
        traces_sample_rate=app_settings.sentry.traces_sample_rate,
        profiles_sample_rate=app_settings.sentry.profiles_sample_rate,
        enable_tracing=app_settings.sentry.enable_tracing,
        send_default_pii=app_settings.sentry.send_default_pii,
        debug=app_settings.sentry.debug,
    )


def create_auth_config_from_env(
    user_config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Create auth configuration from validated config.

    Auth config is already enriched by load_config_from_env() and validated.
    This function simply extracts it from the validated config.

    Args:
        user_config: Validated configuration dictionary (already enriched)

    Returns:
        Auth configuration dictionary or None if not configured
    """
    return user_config.get("auth")


def create_vault_config_from_env(
    user_config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Create vault configuration from validated config.

    Vault config is already enriched by load_config_from_env() and validated.
    This function simply extracts it from the validated config.

    Args:
        user_config: Validated configuration dictionary (already enriched)

    Returns:
        Vault configuration dictionary or None if not configured
    """
    return user_config.get("vault")
