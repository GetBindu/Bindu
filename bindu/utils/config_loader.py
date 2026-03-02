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

    # Authentication configuration - load from env if not in user config
    if "auth" not in enriched_config:
        auth_enabled = os.getenv("AUTH__ENABLED", "").lower() in ("true", "1", "yes")
        auth_provider = os.getenv("AUTH__PROVIDER", "").lower()

        if auth_enabled and auth_provider:
            enriched_config["auth"] = {
                "enabled": auth_enabled,
                "provider": auth_provider,
            }
            logger.debug(
                f"Loaded AUTH__ENABLED={auth_enabled} and AUTH__PROVIDER={auth_provider} from environment"
            )

            # Load provider-specific configuration
            if auth_provider == "hydra":
                hydra_admin_url = os.getenv("HYDRA__ADMIN_URL")
                if hydra_admin_url:
                    enriched_config["auth"]["admin_url"] = hydra_admin_url
                    logger.debug("Loaded HYDRA__ADMIN_URL from environment")

                hydra_public_url = os.getenv("HYDRA__PUBLIC_URL")
                if hydra_public_url:
                    enriched_config["auth"]["public_url"] = hydra_public_url
                    logger.debug("Loaded HYDRA__PUBLIC_URL from environment")

                # Connection settings
                hydra_timeout = os.getenv("HYDRA__TIMEOUT")
                if hydra_timeout:
                    enriched_config["auth"]["timeout"] = int(hydra_timeout)
                    logger.debug("Loaded HYDRA__TIMEOUT from environment")

                hydra_verify_ssl = os.getenv("HYDRA__VERIFY_SSL", "true").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                enriched_config["auth"]["verify_ssl"] = hydra_verify_ssl
                logger.debug("Loaded HYDRA__VERIFY_SSL from environment")

                hydra_max_retries = os.getenv("HYDRA__MAX_RETRIES")
                if hydra_max_retries:
                    enriched_config["auth"]["max_retries"] = int(hydra_max_retries)
                    logger.debug("Loaded HYDRA__MAX_RETRIES from environment")

                # Cache settings
                hydra_cache_ttl = os.getenv("HYDRA__CACHE_TTL")
                if hydra_cache_ttl:
                    enriched_config["auth"]["cache_ttl"] = int(hydra_cache_ttl)
                    logger.debug("Loaded HYDRA__CACHE_TTL from environment")

                hydra_max_cache_size = os.getenv("HYDRA__MAX_CACHE_SIZE")
                if hydra_max_cache_size:
                    enriched_config["auth"]["max_cache_size"] = int(
                        hydra_max_cache_size
                    )
                    logger.debug("Loaded HYDRA__MAX_CACHE_SIZE from environment")

                # Auto-registration settings
                hydra_auto_register = os.getenv(
                    "HYDRA__AUTO_REGISTER_AGENTS", "true"
                ).lower() in ("true", "1", "yes")
                enriched_config["auth"]["auto_register_agents"] = hydra_auto_register
                logger.debug("Loaded HYDRA__AUTO_REGISTER_AGENTS from environment")

                hydra_client_prefix = os.getenv("HYDRA__AGENT_CLIENT_PREFIX")
                if hydra_client_prefix:
                    enriched_config["auth"]["agent_client_prefix"] = hydra_client_prefix
                    logger.debug("Loaded HYDRA__AGENT_CLIENT_PREFIX from environment")

    # Vault configuration - load from env if not in user config
    if "vault" not in enriched_config:
        vault_enabled = os.getenv("VAULT__ENABLED", "").lower() in ("true", "1", "yes")
        vault_url = os.getenv("VAULT__URL") or os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT__TOKEN") or os.getenv("VAULT_TOKEN")

        if vault_enabled or vault_url or vault_token:
            enriched_config["vault"] = {
                "enabled": vault_enabled,
            }
            if vault_url:
                enriched_config["vault"]["url"] = vault_url
                logger.debug(f"Loaded Vault URL from environment: {vault_url}")
            if vault_token:
                enriched_config["vault"]["token"] = vault_token
                logger.debug("Loaded Vault token from environment")

    return enriched_config


def create_auth_config_from_env(user_config: Dict[str, Any]) -> Dict[str, Any] | None:
    """Create auth configuration from validated config.

    Auth config is already enriched by load_config_from_env() and validated.
    This function simply extracts it from the validated config.

    Args:
        user_config: Validated configuration dictionary (already enriched)

    Returns:
        Auth configuration dictionary or None if not configured
    """
    return user_config.get("auth")


def create_vault_config_from_env(user_config: Dict[str, Any]) -> Dict[str, Any] | None:
    """Create vault configuration from validated config.

    Vault config is already enriched by load_config_from_env() and validated.
    This function simply extracts it from the validated config.

    Args:
        user_config: Validated configuration dictionary (already enriched)

    Returns:
        Vault configuration dictionary or None if not configured
    """
    return user_config.get("vault")


def update_auth_settings(auth_config: Dict[str, Any]) -> None:
    """Update global auth settings from configuration.

    Args:
        auth_config: Authentication configuration dictionary
    """
    from bindu.settings import app_settings

    if auth_config and auth_config.get("enabled"):
        # Auth is enabled - configure provider
        app_settings.auth.enabled = True
        app_settings.auth.provider = auth_config.get("provider", "hydra")

        provider = auth_config.get("provider", "hydra")

        if provider == "hydra":
            # Hydra-specific settings
            from bindu.settings import app_settings

            app_settings.hydra.enabled = True
            app_settings.hydra.admin_url = auth_config.get(
                "admin_url", app_settings.hydra.admin_url
            )
            app_settings.hydra.public_url = auth_config.get(
                "public_url", app_settings.hydra.public_url
            )
            app_settings.hydra.timeout = auth_config.get(
                "timeout", app_settings.hydra.timeout
            )
            app_settings.hydra.verify_ssl = auth_config.get(
                "verify_ssl", app_settings.hydra.verify_ssl
            )
            app_settings.hydra.max_retries = auth_config.get(
                "max_retries", app_settings.hydra.max_retries
            )
            app_settings.hydra.cache_ttl = auth_config.get(
                "cache_ttl", app_settings.hydra.cache_ttl
            )
            app_settings.hydra.max_cache_size = auth_config.get(
                "max_cache_size", app_settings.hydra.max_cache_size
            )
            app_settings.hydra.auto_register_agents = auth_config.get(
                "auto_register_agents", app_settings.hydra.auto_register_agents
            )
            app_settings.hydra.agent_client_prefix = auth_config.get(
                "agent_client_prefix", app_settings.hydra.agent_client_prefix
            )
        else:
            logger.warning(f"Unknown authentication provider: {provider}")


def update_vault_settings(vault_config: Dict[str, Any]) -> None:
    """Update global vault settings from configuration.

    Args:
        vault_config: Vault configuration dictionary
    """
    from bindu.settings import app_settings

    if vault_config:
        app_settings.vault.enabled = vault_config.get(
            "enabled", app_settings.vault.enabled
        )
        app_settings.vault.url = vault_config.get("url", app_settings.vault.url)
        app_settings.vault.token = vault_config.get("token", app_settings.vault.token)

        if app_settings.vault.enabled:
            logger.info(f"Vault integration enabled: {app_settings.vault.url}")
        else:
            logger.debug("Vault integration disabled")
