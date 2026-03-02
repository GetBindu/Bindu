# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Sentry integration for error tracking and performance monitoring.

This module provides Sentry initialization and configuration for the Bindu framework.
It integrates with FastAPI/Starlette, SQLAlchemy, Redis, and other components to provide
comprehensive error tracking and performance monitoring.

Features:
- Automatic error capture and reporting
- Performance transaction tracking
- Breadcrumb logging for debugging context
- Release tracking for deployment monitoring
- Custom tags and context for filtering
- PII scrubbing for privacy compliance
"""

from __future__ import annotations as _annotations

import socket
from typing import Any

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.observability.sentry")


def init_sentry() -> bool:
    """Initialize Sentry SDK with configuration from settings.

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise
    """
    if not app_settings.sentry.enabled:
        logger.info("Sentry is disabled")
        return False

    if not app_settings.sentry.dsn:
        logger.warning("Sentry is enabled but DSN is not configured")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        # Build integrations list
        integrations: list[Any] = []

        # Core integrations
        if "asyncio" in app_settings.sentry.integrations:
            integrations.append(AsyncioIntegration())

        # Starlette integration (Bindu uses Starlette, not FastAPI)
        # This covers all endpoints in bindu/server/endpoints/
        if "starlette" in app_settings.sentry.integrations:
            integrations.append(
                StarletteIntegration(
                    transaction_style="url",  # Group by URL pattern
                    failed_request_status_codes={
                        500,
                        501,
                        502,
                        503,
                        504,
                        505,
                        506,
                        507,
                        508,
                        509,
                        510,
                        511,
                    },  # Track 5xx as errors
                )
            )

        # Database and cache integrations (both are required dependencies in Bindu)
        if "sqlalchemy" in app_settings.sentry.integrations:
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            integrations.append(SqlalchemyIntegration())

        if "redis" in app_settings.sentry.integrations:
            from sentry_sdk.integrations.redis import RedisIntegration

            integrations.append(RedisIntegration())

        # Determine release version
        release = app_settings.sentry.release
        if not release:
            try:
                from bindu._version import __version__

                release = f"bindu@{__version__}"
            except ImportError:
                release = f"bindu@{app_settings.project.version}"

        # Determine server name
        server_name = app_settings.sentry.server_name
        if not server_name:
            try:
                server_name = socket.gethostname()
            except OSError as error:
                logger.warning("Failed to detect hostname", error=str(error))
                server_name = "unknown"

        # Build default tags
        default_tags = {
            "environment": app_settings.sentry.environment,
            "server_name": server_name,
            **app_settings.sentry.default_tags,
        }

        # Initialize Sentry SDK
        sentry_sdk.init(
            dsn=app_settings.sentry.dsn,
            environment=app_settings.sentry.environment,
            release=release,
            server_name=server_name,
            integrations=integrations,
            traces_sample_rate=app_settings.sentry.traces_sample_rate,
            profiles_sample_rate=app_settings.sentry.profiles_sample_rate,
            send_default_pii=app_settings.sentry.send_default_pii,
            max_breadcrumbs=app_settings.sentry.max_breadcrumbs,
            attach_stacktrace=app_settings.sentry.attach_stacktrace,
            debug=app_settings.sentry.debug,
            before_send=_before_send,
            before_send_transaction=_before_send_transaction,
            ignore_errors=app_settings.sentry.ignore_errors,
        )

        # Set default tags
        for key, value in default_tags.items():
            sentry_sdk.set_tag(key, value)

        logger.info(
            "Sentry initialized",
            environment=app_settings.sentry.environment,
            release=release,
            traces_sample_rate=app_settings.sentry.traces_sample_rate,
        )

        return True

    except ImportError as error:
        logger.error("Failed to import Sentry SDK", error=str(error))
        return False
    except (RuntimeError, ValueError, TypeError, OSError) as error:
        logger.error("Failed to initialize Sentry", error=str(error))
        return False


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Filter and modify events before sending to Sentry.

    This hook is called before every error event is sent to Sentry.
    Use it to:
    - Scrub sensitive data (passwords, tokens, etc.)
    - Filter out noise (expected errors, health checks, etc.)
    - Add custom context or tags

    Args:
        event: The error event dictionary
        hint: Additional context about the event

    Returns:
        Modified event dict, or None to drop the event
    """
    # Scrub sensitive data from request headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "x-api-key", "cookie", "x-auth-token"]

        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"

    # Scrub sensitive data from request data
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            sensitive_keys = ["password", "token", "secret", "api_key", "private_key"]
            for key in sensitive_keys:
                if key in data:
                    data[key] = "[Filtered]"

    return event


def _before_send_transaction(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any] | None:
    """Filter transactions before sending to Sentry.

    This hook is called before every performance transaction is sent to Sentry.
    Use it to filter out noise like health checks, metrics endpoints, etc.

    Args:
        event: The transaction event dictionary
        hint: Additional context about the event

    Returns:
        Modified event dict, or None to drop the transaction
    """
    # Filter out health check and metrics transactions
    if "transaction" in event:
        transaction_name = event["transaction"]

        # Check if transaction matches any filter pattern
        for pattern in app_settings.sentry.filter_transactions:
            if pattern in transaction_name:
                return None  # Drop this transaction

    return event
