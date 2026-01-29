"""Configuration loading and infrastructure setup utilities.

This module provides utilities for loading capability-specific configurations
from environment variables and setting up infrastructure components.
"""

import os
from typing import Any, Dict, cast, Literal

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.config_loader")


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


def load_config_from_env(config: Dict[str, Any]) -> Dict[str, Any]:
    """Load capability-specific configurations from environment variables.

    This function loads all infrastructure and capability configs from environment:
    - Storage: STORAGE_TYPE, DATABASE_URL
    - Scheduler: SCHEDULER_TYPE, REDIS_URL
    - Sentry: SENTRY_ENABLED, SENTRY_DSN
    - Telemetry: TELEMETRY_ENABLED
    - OLTP: OLTP_ENDPOINT, OLTP_SERVICE_NAME, OLTP_HEADERS (only if telemetry enabled)
    - Negotiation: OPENROUTER_API_KEY (when negotiation capability enabled)
    - Webhooks: WEBHOOK_URL, WEBHOOK_TOKEN (when push_notifications capability enabled)

    OLTP_HEADERS must be valid JSON: '{"Authorization": "Basic xxx"}'

    Args:
        config: User-provided configuration dictionary

    Returns:
        Configuration dictionary with environment variable fallbacks
    """
    # Create a copy to avoid mutating the input
    enriched_config = config.copy()
    capabilities = enriched_config.get("capabilities", {})

    # Storage configuration - load from env if not in user config
    if "storage" not in enriched_config:
        storage_type = os.getenv("STORAGE_TYPE", "memory")
        if storage_type:
            enriched_config["storage"] = {"type": storage_type}
            if storage_type == "postgres":
                database_url = os.getenv("DATABASE_URL")
                if not database_url:
                    raise ValueError(
                        "DATABASE_URL environment variable is required when STORAGE_TYPE=postgres"
                    )
                enriched_config["storage"]["postgres_url"] = database_url
                logger.debug("Loaded DATABASE_URL from environment")
            logger.debug(f"Loaded STORAGE_TYPE from environment: {storage_type}")

    # Scheduler configuration - load from env if not in user config
    if "scheduler" not in enriched_config:
        scheduler_type = os.getenv("SCHEDULER_TYPE", "memory")
        if scheduler_type:
            enriched_config["scheduler"] = {"type": scheduler_type}
            if scheduler_type == "redis":
                redis_url = os.getenv("REDIS_URL")
                if not redis_url:
                    raise ValueError(
                        "REDIS_URL environment variable is required when SCHEDULER_TYPE=redis"
                    )
                enriched_config["scheduler"]["redis_url"] = redis_url
                logger.debug("Loaded REDIS_URL from environment")
            logger.debug(f"Loaded SCHEDULER_TYPE from environment: {scheduler_type}")

    # Sentry configuration - load from env if not in user config
    if "sentry" not in enriched_config:
        sentry_enabled = os.getenv("SENTRY_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        if sentry_enabled:
            sentry_dsn = os.getenv("SENTRY_DSN")
            if not sentry_dsn:
                raise ValueError(
                    "SENTRY_DSN environment variable is required when SENTRY_ENABLED=true"
                )
            enriched_config["sentry"] = {
                "enabled": True,
                "dsn": sentry_dsn,
            }
            logger.debug(
                f"Loaded Sentry configuration from environment: enabled={sentry_enabled}"
            )

    # Telemetry configuration - load from env if not in user config
    if "telemetry" not in enriched_config:
        telemetry_enabled = os.getenv("TELEMETRY_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        enriched_config["telemetry"] = telemetry_enabled
        logger.debug(f"Loaded TELEMETRY_ENABLED from environment: {telemetry_enabled}")

    # OLTP (OpenTelemetry Protocol) configuration - only load if telemetry is enabled
    if enriched_config.get("telemetry"):
        if "oltp_endpoint" not in enriched_config:
            oltp_endpoint = os.getenv("OLTP_ENDPOINT")
            if oltp_endpoint:
                enriched_config["oltp_endpoint"] = oltp_endpoint
                logger.debug(f"Loaded OLTP_ENDPOINT from environment: {oltp_endpoint}")

        if "oltp_service_name" not in enriched_config:
            oltp_service_name = os.getenv("OLTP_SERVICE_NAME")
            if oltp_service_name:
                enriched_config["oltp_service_name"] = oltp_service_name
                logger.debug(
                    f"Loaded OLTP_SERVICE_NAME from environment: {oltp_service_name}"
                )

        if "oltp_headers" not in enriched_config:
            oltp_headers_str = os.getenv("OLTP_HEADERS")
            if oltp_headers_str:
                import json

                try:
                    enriched_config["oltp_headers"] = json.loads(oltp_headers_str)
                    logger.debug("Loaded OLTP_HEADERS from environment")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid OLTP_HEADERS format, expected JSON: {e}")

    # Push notifications and negotiation - only if push_notifications capability is enabled
    if capabilities.get("push_notifications"):
        # Webhook configuration
        if not enriched_config.get("global_webhook_url"):
            webhook_url = os.getenv("WEBHOOK_URL")
            if webhook_url:
                enriched_config["global_webhook_url"] = webhook_url
                logger.debug("Loaded WEBHOOK_URL from environment")

        if not enriched_config.get("global_webhook_token"):
            webhook_token = os.getenv("WEBHOOK_TOKEN")
            if webhook_token:
                enriched_config["global_webhook_token"] = webhook_token
                logger.debug("Loaded WEBHOOK_TOKEN from environment")

        # Negotiation API key for embeddings
        if capabilities.get("negotiation"):
            env_openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
            if env_openrouter_api_key:
                if "negotiation" not in enriched_config:
                    enriched_config["negotiation"] = {}
                if not enriched_config["negotiation"].get("embedding_api_key"):
                    enriched_config["negotiation"]["embedding_api_key"] = (
                        env_openrouter_api_key
                    )
                    logger.debug("Loaded OPENROUTER_API_KEY from environment")

    return enriched_config


def update_auth_settings(auth_config: Dict[str, Any]) -> None:
    """Update global auth settings from configuration.

    Args:
        auth_config: Authentication configuration dictionary
    """
    from bindu.settings import app_settings

    if auth_config and auth_config.get("enabled"):
        # Auth is enabled - configure all settings
        app_settings.auth.enabled = True
        app_settings.auth.domain = auth_config.get("domain", "")
        app_settings.auth.audience = auth_config.get("audience", "")
        app_settings.auth.algorithms = auth_config.get("algorithms", ["RS256"])
        app_settings.auth.issuer = auth_config.get("issuer", "")
        app_settings.auth.jwks_uri = auth_config.get("jwks_uri", "")
        app_settings.auth.public_endpoints = auth_config.get(
            "public_endpoints", app_settings.auth.public_endpoints
        )
        app_settings.auth.require_permissions = auth_config.get(
            "require_permissions", False
        )
        app_settings.auth.permissions = auth_config.get(
            "permissions", app_settings.auth.permissions
        )

        logger.info(
            f"Auth configuration loaded: domain={auth_config.get('domain')}, "
            f"audience={auth_config.get('audience')}"
        )
    else:
        # Auth is not provided or disabled - ensure it's disabled
        app_settings.auth.enabled = False
        logger.info("Authentication disabled")
