"""Configuration enrichment from environment variables."""

import os
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.config.enricher")


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

    # Deployment configuration - support environment-based URL/port overrides
    deployment_dict = enriched_config.get("deployment")
    if isinstance(deployment_dict, dict):
        deployment_url_override = os.getenv("BINDU_DEPLOYMENT_URL")
        deployment_host_override = os.getenv("BINDU_HOST")
        deployment_port_override = os.getenv("BINDU_PORT") or os.getenv("PORT")

        if deployment_url_override:
            deployment_dict["url"] = deployment_url_override
            logger.debug("Loaded BINDU_DEPLOYMENT_URL from environment")
        elif deployment_host_override or deployment_port_override:
            existing_url = deployment_dict.get("url", "http://localhost:3773")
            parsed_url = urlparse(existing_url)

            scheme = parsed_url.scheme or "http"
            host = deployment_host_override or parsed_url.hostname or "localhost"

            if deployment_port_override:
                try:
                    port = int(deployment_port_override)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid deployment port '{deployment_port_override}'. "
                        "BINDU_PORT/PORT must be an integer"
                    ) from exc
            else:
                port = parsed_url.port or 3773

            netloc = f"{host}:{port}"
            deployment_dict["url"] = urlunparse(
                (
                    scheme,
                    netloc,
                    parsed_url.path or "",
                    parsed_url.params,
                    parsed_url.query,
                    parsed_url.fragment,
                )
            )
            logger.debug(
                f"Applied deployment override from environment: {deployment_dict['url']}"
            )

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
            auth_config: Dict[str, Any] = {
                "enabled": auth_enabled,
                "provider": auth_provider,
            }
            enriched_config["auth"] = auth_config
            logger.debug(
                f"Loaded AUTH__ENABLED={auth_enabled} and AUTH__PROVIDER={auth_provider} from environment"
            )

            # Load provider-specific configuration
            if auth_provider == "hydra":
                hydra_admin_url = os.getenv("HYDRA__ADMIN_URL")
                if hydra_admin_url:
                    auth_config["admin_url"] = hydra_admin_url
                    logger.debug("Loaded HYDRA__ADMIN_URL from environment")

                hydra_public_url = os.getenv("HYDRA__PUBLIC_URL")
                if hydra_public_url:
                    auth_config["public_url"] = hydra_public_url
                    logger.debug("Loaded HYDRA__PUBLIC_URL from environment")

                # Connection settings
                hydra_timeout = os.getenv("HYDRA__TIMEOUT")
                if hydra_timeout:
                    auth_config["timeout"] = int(hydra_timeout)
                    logger.debug("Loaded HYDRA__TIMEOUT from environment")

                hydra_verify_ssl = os.getenv("HYDRA__VERIFY_SSL", "true").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                auth_config["verify_ssl"] = hydra_verify_ssl
                logger.debug("Loaded HYDRA__VERIFY_SSL from environment")

                hydra_max_retries = os.getenv("HYDRA__MAX_RETRIES")
                if hydra_max_retries:
                    auth_config["max_retries"] = int(hydra_max_retries)
                    logger.debug("Loaded HYDRA__MAX_RETRIES from environment")

                # Cache settings
                hydra_cache_ttl = os.getenv("HYDRA__CACHE_TTL")
                if hydra_cache_ttl:
                    auth_config["cache_ttl"] = int(hydra_cache_ttl)
                    logger.debug("Loaded HYDRA__CACHE_TTL from environment")

                hydra_max_cache_size = os.getenv("HYDRA__MAX_CACHE_SIZE")
                if hydra_max_cache_size:
                    auth_config["max_cache_size"] = int(hydra_max_cache_size)
                    logger.debug("Loaded HYDRA__MAX_CACHE_SIZE from environment")

                # Auto-registration settings
                hydra_auto_register = os.getenv(
                    "HYDRA__AUTO_REGISTER_AGENTS", "true"
                ).lower() in ("true", "1", "yes")
                auth_config["auto_register_agents"] = hydra_auto_register
                logger.debug("Loaded HYDRA__AUTO_REGISTER_AGENTS from environment")

                hydra_client_prefix = os.getenv("HYDRA__AGENT_CLIENT_PREFIX")
                if hydra_client_prefix:
                    auth_config["agent_client_prefix"] = hydra_client_prefix
                    logger.debug("Loaded HYDRA__AGENT_CLIENT_PREFIX from environment")

    # Vault configuration - load from env if not in user config
    if "vault" not in enriched_config:
        vault_enabled = os.getenv("VAULT__ENABLED", "").lower() in ("true", "1", "yes")
        vault_url = os.getenv("VAULT__URL") or os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT__TOKEN") or os.getenv("VAULT_TOKEN")

        if vault_enabled or vault_url or vault_token:
            vault_config: Dict[str, Any] = {
                "enabled": vault_enabled,
            }
            if vault_url:
                vault_config["url"] = vault_url
                logger.debug(f"Loaded Vault URL from environment: {vault_url}")
            if vault_token:
                vault_config["token"] = vault_token
                logger.debug("Loaded Vault token from environment")
            enriched_config["vault"] = vault_config

    return enriched_config
