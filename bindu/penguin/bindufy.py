#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""bindufy decorator for transforming regular agents into secure, networked agents."""

import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import urlparse
from uuid import uuid4

from bindu.common.models import (
    AgentManifest,
    DeploymentConfig,
    TelemetryConfig,
)
from bindu.extensions.x402 import X402AgentExtension
from bindu.penguin.did_setup import initialize_did_extension
from bindu.penguin.manifest import create_manifest, validate_agent_function
from bindu.settings import app_settings
from bindu.utils import add_extension_to_capabilities
from bindu.utils.config_loader import (
    create_storage_config_from_env,
    create_scheduler_config_from_env,
    create_sentry_config_from_env,
    load_config_from_env,
    update_auth_settings,
)
from bindu.utils.display import prepare_server_display
from bindu.utils.logging import get_logger
from bindu.utils.path_resolver import (
    resolve_key_directory,
)
from bindu.utils.server_runner import run_server as start_uvicorn_server
from bindu.utils.skill_loader import load_skills

# Configure logging for the module
logger = get_logger("bindu.penguin.bindufy")


def _parse_deployment_url(
    deployment_config: DeploymentConfig | None,
) -> tuple[str, int]:
    """Parse deployment URL to extract host and port.

    Args:
        deployment_config: Deployment configuration object

    Returns:
        Tuple of (host, port)
    """
    if not deployment_config:
        return app_settings.network.default_host, app_settings.network.default_port

    parsed_url = urlparse(deployment_config.url)
    host = parsed_url.hostname or app_settings.network.default_host
    port = parsed_url.port or app_settings.network.default_port

    return host, port


def _create_deployment_config(
    validated_config: Dict[str, Any],
) -> DeploymentConfig | None:
    """Create deployment config from validated config dict.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        DeploymentConfig instance or None if invalid/missing
    """
    deploy_dict = validated_config.get("deployment")
    if not deploy_dict:
        return None

    if "url" not in deploy_dict or "expose" not in deploy_dict:
        logger.warning(
            "Deployment config missing required fields (url, expose), using defaults"
        )
        return None

    return DeploymentConfig(
        url=deploy_dict["url"],
        expose=deploy_dict["expose"],
        protocol_version=deploy_dict.get("protocol_version", "1.0.0"),
        proxy_urls=deploy_dict.get("proxy_urls"),
        cors_origins=deploy_dict.get("cors_origins"),
        openapi_schema=deploy_dict.get("openapi_schema"),
    )


def bindufy(
    config: Dict[str, Any],
    handler: Callable[[list[dict[str, str]]], Any],
    run_server: bool = True,
    key_dir: str | Path | None = None,
) -> AgentManifest:
    """Transform an agent instance and handler into a bindu-compatible agent.

    Args:
        config: Configuration dictionary containing:
            - author: Agent author email (required for Hibiscus registration)
            - name: Human-readable agent name
            - id: Unique agent identifier (optional, auto-generated if not provided)
            - description: Agent description
            - version: Agent version string (default: "1.0.0")
            - recreate_keys: Force regeneration of existing keys (default: True)
            - skills: List of agent skills/capabilities
            - env_file: Path to .env file (optional, for local development)
            - capabilities: Technical capabilities (streaming, notifications, etc.)
            - agent_trust: Trust and security configuration
            - kind: Agent type ('agent', 'team', or 'workflow') (default: "agent")
            - debug_mode: Enable debug logging (default: False)
            - debug_level: Debug verbosity level (default: 1)
            - monitoring: Enable monitoring/metrics (default: False)
            - telemetry: Enable telemetry collection (default: True)
            - num_history_sessions: Number of conversation histories to maintain (default: 10)
            - documentation_url: URL to agent documentation
            - extra_metadata: Additional metadata dictionary
            - deployment: Deployment configuration dict
            - storage: Storage backend configuration dict
            - scheduler: Task scheduler configuration dict
            - global_webhook_url: Default webhook URL for all tasks (optional)
            - global_webhook_token: Authentication token for global webhook (optional)
        handler: The handler function that processes messages and returns responses.
                Must have signature: (messages: str) -> str
        run_server: If True, starts the uvicorn server (blocking). If False, returns manifest
                   immediately for testing/programmatic usage (default: True)
        key_dir: Directory for storing DID keys. If None, attempts to detect from caller's
                directory (may fail in REPL/notebooks). Falls back to current working directory.

    Returns:
        AgentManifest: The manifest for the bindufied agent

    Example:
        def my_handler(messages: str) -> str:
            result = agent.run(input=messages)
            return result.to_dict()["content"]

        config = {
            "author": "user@example.com",
            "name": "my-agent",
            "description": "A helpful assistant",
            "capabilities": {"streaming": True},
            "deployment": {"url": "http://localhost:3773", "protocol_version": "1.0.0"},
            "storage": {"type": "memory"},
            "scheduler": {"type": "memory"}
        }

        manifest = bindufy(agent, config, my_handler)
    """
    # Load capability-specific configs from environment variables (webhooks, negotiation)
    config = load_config_from_env(config)

    # Validate and process configuration
    from .config_validator import ConfigValidator

    validated_config = ConfigValidator.validate_and_process(config)

    # Update app_settings.auth based on config
    auth_config = validated_config.get("auth")
    if auth_config is not None:
        update_auth_settings(auth_config)

    # Generate agent_id if not provided
    agent_id = validated_config.get("id", uuid4().hex)

    # Create config objects directly from environment and validated config
    deployment_config = _create_deployment_config(validated_config)
    storage_config = create_storage_config_from_env(validated_config)
    scheduler_config = create_scheduler_config_from_env(validated_config)
    sentry_config = create_sentry_config_from_env(validated_config)

    # Validate that this is a protocol-compliant function
    handler_name = getattr(handler, "__name__", "<unknown>")
    logger.info(f"Validating handler function: {handler_name}")
    validate_agent_function(handler)
    logger.info(f"Agent ID: {agent_id}")

    # Get caller information for file paths
    frame = inspect.currentframe()
    if not frame or not frame.f_back:
        raise RuntimeError("Unable to determine caller file path")

    caller_file = inspect.getframeinfo(frame.f_back).filename
    caller_dir = Path(os.path.abspath(caller_file)).parent

    # Determine key directory with fallback strategy
    resolved_key_dir = resolve_key_directory(
        explicit_dir=key_dir, caller_dir=caller_dir, subdir=app_settings.did.pki_dir
    )

    # Initialize DID extension with key management
    did_extension = initialize_did_extension(
        agent_id=agent_id,
        author=validated_config.get("author"),
        agent_name=validated_config.get("name"),
        key_dir=resolved_key_dir.parent,  # Parent because initialize_did_extension adds pki_dir
        recreate_keys=validated_config["recreate_keys"],
        key_password=validated_config.get("key_password"),
    )

    # Load skills from configuration (supports both file-based and inline)
    logger.info("Loading agent skills...")
    skills_list = load_skills(
        validated_config.get("skills") or [],
        caller_dir,  # Always set at this point
    )

    # Set agent metadata for DID document
    agent_url = (
        deployment_config.url if deployment_config else app_settings.network.default_url
    )

    logger.info(f"DID Extension setup complete: {did_extension.did}")
    logger.info("Creating agent manifest...")

    # Update capabilities to include DID extension
    capabilities = add_extension_to_capabilities(
        validated_config.get("capabilities", {}), did_extension
    )

    # Only add x402 extension if execution_cost is configured
    execution_cost = validated_config.get("execution_cost")
    x402_extension = None

    if execution_cost:
        # Create X402 extension with payment configuration
        amount = execution_cost.get("amount")
        token = execution_cost.get("token", "USDC")
        network = execution_cost.get("network", "base-sepolia")
        pay_to_address = execution_cost.get("pay_to_address")

        if not amount:
            raise ValueError(
                "execution_cost.amount is required when execution_cost is configured"
            )

        logger.info(f"Execution cost configured: {amount} {token} on {network}")

        x402_extension = X402AgentExtension(
            amount=amount,
            token=token,
            network=network,
            required=True,  # Payment is required for paid agents
            pay_to_address=pay_to_address,
        )

        logger.info(f"X402 extension created: {x402_extension}")

        # Add x402 extension to capabilities
        capabilities = add_extension_to_capabilities(capabilities, x402_extension)

    # Create agent manifest with loaded skills
    _manifest = create_manifest(
        agent_function=handler,
        id=agent_id,
        did_extension=did_extension,
        name=validated_config["name"],
        description=validated_config["description"],
        skills=skills_list,
        capabilities=capabilities,
        agent_trust=validated_config["agent_trust"],
        version=validated_config["version"],
        url=agent_url,
        protocol_version=deployment_config.protocol_version
        if deployment_config
        else "1.0.0",
        kind=validated_config["kind"],
        debug_mode=validated_config["debug_mode"],
        debug_level=validated_config["debug_level"],
        monitoring=validated_config["monitoring"],
        telemetry=validated_config["telemetry"],
        oltp_endpoint=validated_config.get("oltp_endpoint"),
        oltp_service_name=validated_config.get("oltp_service_name"),
        num_history_sessions=validated_config["num_history_sessions"],
        enable_system_message=validated_config.get("enable_system_message", True),
        enable_context_based_history=validated_config.get(
            "enable_context_based_history", False
        ),
        negotiation=validated_config.get("negotiation"),
        documentation_url=validated_config["documentation_url"],
        extra_metadata=validated_config["extra_metadata"],
        global_webhook_url=validated_config.get("global_webhook_url"),
        global_webhook_token=validated_config.get("global_webhook_token"),
    )

    # Log manifest creation
    skill_count = len(_manifest.skills) if _manifest.skills else 0
    logger.info(f"Agent '{did_extension.did}' successfully bindufied!")
    logger.debug(
        f"Manifest: {_manifest.name} v{_manifest.version} | {_manifest.kind} | {skill_count} skills | {_manifest.url}"
    )

    logger.info(f"Starting deployment for agent: {agent_id}")

    # Import server components (deferred to avoid circular import)
    from bindu.server import BinduApplication

    # Storage and scheduler will be initialized in BinduApplication's lifespan
    # No need to create instances here - just pass the config

    # Create telemetry configuration
    telemetry_config = TelemetryConfig(
        enabled=validated_config["telemetry"],
        endpoint=validated_config.get("oltp_endpoint"),
        service_name=validated_config.get("oltp_service_name"),
        headers=validated_config.get("oltp_headers"),
        verbose_logging=validated_config.get("oltp_verbose_logging", False),
        service_version=validated_config.get("oltp_service_version", "1.0.0"),
        deployment_environment=validated_config.get(
            "oltp_deployment_environment", "production"
        ),
        batch_max_queue_size=validated_config.get("oltp_batch_max_queue_size", 2048),
        batch_schedule_delay_millis=validated_config.get(
            "oltp_batch_schedule_delay_millis", 5000
        ),
        batch_max_export_batch_size=validated_config.get(
            "oltp_batch_max_export_batch_size", 512
        ),
        batch_export_timeout_millis=validated_config.get(
            "oltp_batch_export_timeout_millis", 30000
        ),
    )

    # Create Bindu application with configs
    bindu_app = BinduApplication(
        penguin_id=agent_id,
        manifest=_manifest,
        version=validated_config["version"],
        auth_enabled=app_settings.auth.enabled,
        telemetry_config=telemetry_config,
        storage_config=storage_config,
        scheduler_config=scheduler_config,
        sentry_config=sentry_config,
    )

    # Parse deployment URL
    host, port = _parse_deployment_url(deployment_config)

    # Start server if requested (blocking), otherwise return manifest immediately
    if run_server:
        # Display server startup banner
        prepare_server_display(
            host=host, port=port, agent_id=agent_id, agent_did=did_extension.did
        )

        # Run server with graceful shutdown handling
        start_uvicorn_server(bindu_app, host=host, port=port, display_info=True)
    else:
        logger.info(
            "Server not started (run_server=False). Manifest returned for programmatic use."
        )

    return _manifest
