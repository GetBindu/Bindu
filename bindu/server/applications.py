# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""
Bindu Application Server Module.

This module provides the core BinduApplication class - a Starlette-based ASGI application
that serves AI agents following the A2A (Agent-to-Agent) protocol.

"""

from __future__ import annotations as _annotations

from contextlib import asynccontextmanager
from functools import partial
from typing import Any, AsyncIterator, Callable, Sequence
from uuid import UUID, uuid4

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Lifespan, Receive, Scope, Send

from bindu.common.models import (
    AgentManifest,
    TelemetryConfig,
    StorageConfig,
    SchedulerConfig,
    SentryConfig,
)
from bindu.settings import app_settings
from bindu.utils import get_x402_extension_from_capabilities
from bindu.utils.retry import execute_with_retry

from .scheduler.base import Scheduler
from .storage.base import Storage
from .task_manager import TaskManager
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.applications")

# Constants
UNKNOWN_AUTH_PROVIDER_ERROR = (
    "Unknown authentication provider: '{provider}'. Supported providers: {supported}"
)
TASKMANAGER_NOT_INITIALIZED_ERROR = "TaskManager was not properly initialized."


class BinduApplication(Starlette):
    """Bindu application class for creating Bindu-compatible servers."""

    def __init__(
        self,
        storage_config: StorageConfig | None = None,
        scheduler_config: SchedulerConfig | None = None,
        manifest: AgentManifest | None = None,
        penguin_id: UUID | None = None,
        url: str = "http://localhost",
        port: int = 3773,
        version: str = "1.0.0",
        description: str | None = None,
        debug: bool = False,
        lifespan: Lifespan | None = None,
        routes: Sequence[Route] | None = None,
        middleware: Sequence[Middleware] | None = None,
        auth_enabled: bool = False,
        telemetry_config: TelemetryConfig | None = None,
        sentry_config: SentryConfig | None = None,
        cors_origins: list[str] | None = None,
    ):
        """Initialize Bindu application.

        Args:
            storage_config: Storage configuration (will be initialized in lifespan)
            scheduler_config: Scheduler configuration (will be initialized in lifespan)
            manifest: Agent manifest to serve
            penguin_id: Unique server identifier (auto-generated if not provided)
            url: Server URL
            version: Server version
            description: Server description
            debug: Enable debug mode
            lifespan: Optional custom lifespan
            routes: Optional custom routes
            middleware: Optional middleware
            auth_enabled: Enable Hydra OAuth2 authentication middleware
            telemetry_config: Optional telemetry configuration (defaults to disabled)
            sentry_config: Optional Sentry configuration (defaults to disabled)
        """
        # Generate penguin_id if not provided
        if penguin_id is None:
            penguin_id = uuid4()

        # Store configs for lifespan initialization
        self._storage_config = storage_config
        self._scheduler_config = scheduler_config
        self._telemetry_config = telemetry_config or TelemetryConfig()
        self._sentry_config = sentry_config or SentryConfig()

        # Create default lifespan if none provided
        if lifespan is None:
            lifespan = self._create_default_lifespan(manifest)

        # Setup middleware chain
        x402_ext = get_x402_extension_from_capabilities(manifest)
        payment_requirements_for_middleware = None
        if x402_ext:
            # Type narrowing: if x402_ext exists, manifest must exist
            assert manifest is not None
            payment_requirements_for_middleware = self._create_payment_requirements(
                x402_ext, manifest, resource_suffix="/"
            )

        # Type narrowing: manifest should exist for middleware setup
        assert manifest is not None
        middleware_list = self._setup_middleware(
            middleware,
            x402_ext,
            payment_requirements_for_middleware,
            manifest,
            auth_enabled,
            cors_origins,
        )

        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware_list if middleware_list else None,
            lifespan=lifespan,
        )

        self.penguin_id = penguin_id
        self.url = url
        self.version = version
        self.description = description
        self.manifest = manifest
        self.default_input_modes = ["application/json"]
        self.task_manager: TaskManager | None = None
        self._storage: Storage | None = None
        self._scheduler: Scheduler | None = None
        self._agent_card_json_schema: bytes | None = None
        self._x402_ext = x402_ext
        self._payment_session_manager = None
        self._payment_requirements = None
        self._paywall_config = None

        # Initialize payment session manager and payment config if x402 enabled
        if x402_ext and payment_requirements_for_middleware:
            self._setup_payment_session_manager(
                manifest, payment_requirements_for_middleware
            )

        # In-memory not a good practice, but for development purposes
        # in production, use a database or redis
        self.payment_sessions: dict[str, dict[str, Any]] = {}

        # Register all routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all application routes."""
        from .endpoints import (
            agent_card_endpoint,
            agent_run_endpoint,
            did_resolve_endpoint,
            negotiation_endpoint,
            skill_detail_endpoint,
            skill_documentation_endpoint,
            skills_list_endpoint,
            metrics_endpoint,
        )

        # Add health endpoint import
        from .endpoints.health import health_endpoint

        # Protocol endpoints
        self._add_route(
            "/.well-known/agent.json",
            agent_card_endpoint,
            ["HEAD", "GET", "OPTIONS"],
            with_app=True,
        )

        # Root endpoint - redirect GET to agent card, POST for A2A protocol
        from starlette.responses import RedirectResponse

        async def root_redirect(app: BinduApplication, request: Request) -> Response:
            """Redirect root GET requests to agent card."""
            return RedirectResponse(url="/.well-known/agent.json", status_code=302)

        self._add_route("/", root_redirect, ["GET"], with_app=True)
        self._add_route("/", agent_run_endpoint, ["POST"], with_app=True)

        # DID endpoints
        self._add_route(
            "/did/resolve", did_resolve_endpoint, ["GET", "POST"], with_app=True
        )

        # Skills endpoints
        self._add_route(
            "/agent/skills",
            skills_list_endpoint,
            ["GET"],
            with_app=True,
        )
        self._add_route(
            "/agent/skills/{skill_id}",
            skill_detail_endpoint,
            ["GET"],
            with_app=True,
        )
        self._add_route(
            "/agent/skills/{skill_id}/documentation",
            skill_documentation_endpoint,
            ["GET"],
            with_app=True,
        )
        # Register health endpoint (backward-compat, always ready=True)
        self._add_route("/health", health_endpoint, ["GET"], with_app=True)

        # Register metrics endpoint
        self._add_route("/metrics", metrics_endpoint, ["GET"], with_app=True)

        # Negotiation endpoint
        self._add_route(
            "/agent/negotiation",
            negotiation_endpoint,
            ["POST"],
            with_app=True,
        )

        if self._x402_ext:
            self._register_payment_endpoints()

    def _register_payment_endpoints(self) -> None:
        """Register payment session endpoints."""
        from .endpoints import (
            payment_capture_endpoint,
            payment_status_endpoint,
            start_payment_session_endpoint,
        )

        self._add_route(
            "/api/start-payment-session",
            start_payment_session_endpoint,
            ["POST"],
            with_app=True,
        )
        self._add_route(
            "/payment-capture",
            payment_capture_endpoint,
            ["GET"],
            with_app=True,
        )
        self._add_route(
            "/api/payment-status/{session_id}",
            payment_status_endpoint,
            ["GET"],
            with_app=True,
        )

    def _add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: list[str],
        with_app: bool = False,
    ) -> None:
        """Add a route with appropriate wrapper.

        Args:
            path: Route path
            endpoint: Endpoint function
            methods: HTTP methods
            with_app: Pass app instance to endpoint
        """
        if with_app:
            handler = partial(self._wrap_with_app, endpoint)
        else:
            handler = endpoint

        self.router.add_route(path, handler, methods=methods)

    async def _wrap_with_app(self, endpoint: Callable, request: Request) -> Response:
        """Wrap endpoint that requires app instance."""
        return await endpoint(self, request)

    def _create_default_lifespan(
        self,
        manifest: AgentManifest | None,
    ) -> Lifespan:
        """Create default Lifespan that manages storage, scheduler, TaskManager lifecycle and observability."""

        @asynccontextmanager
        async def lifespan(app: BinduApplication) -> AsyncIterator[None]:
            # Initialize storage in the correct event loop
            logger.info("🔧 Initializing storage...")
            from .storage.factory import create_storage

            # Override settings if storage_config is provided
            if self._storage_config:
                if (
                    self._storage_config.type == "postgres"
                    and self._storage_config.database_url
                ):
                    app_settings.storage.backend = "postgres"
                    app_settings.storage.postgres_url = (
                        self._storage_config.database_url
                    )
                    app_settings.storage.run_migrations_on_startup = getattr(
                        self._storage_config, "run_migrations_on_startup", False
                    )
                elif self._storage_config.type == "memory":
                    app_settings.storage.backend = "memory"

            # Retry storage initialization for transient connection failures
            # Type narrowing: manifest should exist at this point
            assert self.manifest is not None
            storage = await execute_with_retry(
                create_storage,
                max_attempts=app_settings.retry.storage_max_attempts,
                min_wait=app_settings.retry.storage_min_wait,
                max_wait=app_settings.retry.storage_max_wait,
                did=self.manifest.did_extension.did,
            )
            app._storage = storage
            logger.info(f"✅ Storage initialized: {type(storage).__name__}")

            # Initialize scheduler
            logger.info("🔧 Initializing scheduler...")
            from .scheduler.factory import create_scheduler

            # Retry scheduler initialization for transient connection failures
            scheduler = await execute_with_retry(
                create_scheduler,
                self._scheduler_config,
                max_attempts=app_settings.retry.scheduler_max_attempts,
                min_wait=app_settings.retry.scheduler_min_wait,
                max_wait=app_settings.retry.scheduler_max_wait,
            )
            app._scheduler = scheduler
            logger.info(f"✅ Scheduler initialized: {type(scheduler).__name__}")

            # Setup observability if enabled
            if self._telemetry_config.enabled:
                self._setup_observability()

            # Initialize Sentry error tracking
            # Override settings if sentry_config is provided
            if self._sentry_config.enabled:
                logger.info("🔧 Initializing Sentry...")
                # Override app_settings with config values
                if self._sentry_config.dsn:
                    self._apply_sentry_config(self._sentry_config)
                self._initialize_sentry()
            else:
                # Try to initialize from environment variables
                self._initialize_sentry(source="environment variables")

            # Start payment session manager cleanup task if x402 enabled
            if app._payment_session_manager:
                await app._payment_session_manager.start_cleanup_task()

            # Start TaskManager
            if manifest:
                logger.info("🔧 Starting TaskManager...")
                task_manager = TaskManager(
                    scheduler=scheduler, storage=storage, manifest=manifest
                )
                async with task_manager:
                    app.task_manager = task_manager
                    logger.info("✅ TaskManager started")
                    yield
                logger.info("🛑 TaskManager stopped")
            else:
                yield

            # Stop payment session manager cleanup task
            if app._payment_session_manager:
                await app._payment_session_manager.stop_cleanup_task()

            # Cleanup storage
            logger.info("🧹 Cleaning up storage...")
            from .storage.factory import close_storage

            await close_storage(storage)
            logger.info("✅ Storage cleanup complete")

        return lifespan

    def _apply_sentry_config(self, config: SentryConfig) -> None:
        """Apply Sentry configuration to app settings.

        Args:
            config: Sentry configuration to apply

        Note:
            This method should only be called after verifying config.dsn is not None
        """
        app_settings.sentry.enabled = True
        # Type narrowing: dsn is checked before calling this method (line 361)
        assert config.dsn is not None, "Sentry DSN must be provided"
        app_settings.sentry.dsn = config.dsn
        app_settings.sentry.environment = config.environment
        if config.release:
            app_settings.sentry.release = config.release
        app_settings.sentry.traces_sample_rate = config.traces_sample_rate
        app_settings.sentry.profiles_sample_rate = config.profiles_sample_rate
        app_settings.sentry.enable_tracing = config.enable_tracing
        app_settings.sentry.send_default_pii = config.send_default_pii
        app_settings.sentry.debug = config.debug

    def _initialize_sentry(self, source: str = "") -> None:
        """Initialize Sentry error tracking.

        Args:
            source: Optional source description for logging (e.g., 'environment variables')
        """
        from bindu.observability import init_sentry

        sentry_initialized = init_sentry()
        if sentry_initialized:
            source_msg = f" from {source}" if source else " successfully"
            logger.info(f"✅ Sentry initialized{source_msg}")
        else:
            logger.debug("Sentry not initialized (disabled or not configured)")

    def _setup_observability(self) -> None:
        """Set up OpenTelemetry observability."""
        from bindu.observability import setup as setup_observability

        config = self._telemetry_config
        try:
            setup_observability(
                oltp_endpoint=config.endpoint,
                oltp_service_name=config.service_name,
                oltp_headers=config.headers,
                verbose_logging=config.verbose_logging,
                service_version=config.service_version,
                deployment_environment=config.deployment_environment,
                batch_max_queue_size=config.batch_max_queue_size,
                batch_schedule_delay_millis=config.batch_schedule_delay_millis,
                batch_max_export_batch_size=config.batch_max_export_batch_size,
                batch_export_timeout_millis=config.batch_export_timeout_millis,
            )
            if config.verbose_logging:
                logger.info(
                    "OpenInference telemetry initialized in lifespan",
                    endpoint=config.endpoint or "console",
                    service_name=config.service_name or "bindu-agent",
                )
        except Exception as exc:
            logger.warning("OpenInference telemetry setup failed", error=str(exc))

    def _create_payment_requirements(
        self,
        x402_ext: Any,
        manifest: AgentManifest,
        resource_suffix: str = "/",
    ) -> list[Any] | None:
        """Create payment requirements for X402 extension.

        Args:
            x402_ext: X402 extension instance
            manifest: Agent manifest
            resource_suffix: Suffix to append to manifest URL for resource path

        Returns:
            List of PaymentRequirements or None
        """
        if not x402_ext:
            return None

        from x402.common import process_price_to_atomic_amount
        from x402.types import PaymentRequirements, SupportedNetworks
        from typing import cast

        # When multiple payment options are configured on the extension, create a
        # PaymentRequirements entry for each one. Otherwise, fall back to the single
        # amount/network configuration for backward compatibility.
        payment_requirements: list[PaymentRequirements] = []

        options: list[dict[str, Any]]
        if getattr(x402_ext, "payment_options", None):
            options = list(x402_ext.payment_options)
        else:
            options = [
                {
                    "amount": x402_ext.amount,
                    "network": x402_ext.network,
                    "pay_to_address": x402_ext.pay_to_address,
                }
            ]

        for opt in options:
            amount = opt.get("amount")
            network = opt.get("network") or app_settings.x402.default_network
            pay_to_address = opt.get("pay_to_address") or x402_ext.pay_to_address

            # Type narrowing: amount should be present in payment options
            assert amount is not None, "Payment amount is required"
            max_amount_required, asset_address, eip712_domain = (
                process_price_to_atomic_amount(amount, network)
            )

            payment_requirements.append(
                PaymentRequirements(
                    scheme="exact",
                    network=cast(SupportedNetworks, network),
                    asset=asset_address,
                    max_amount_required=max_amount_required,
                    resource=f"{manifest.url}{resource_suffix}",
                    description=f"Payment required to use {manifest.name}",
                    mime_type="",
                    pay_to=pay_to_address,
                    max_timeout_seconds=60,
                    output_schema={
                        "input": {
                            "type": "http",
                            "method": "POST",
                            "discoverable": True,
                        },
                        "output": {},
                    },
                    extra=eip712_domain,
                )
            )

        return payment_requirements

    def _setup_middleware(
        self,
        middleware: Sequence[Middleware] | None,
        x402_ext: Any,
        payment_requirements: list[Any] | None,
        manifest: AgentManifest,
        auth_enabled: bool,
        cors_origins: list[str] | None = None,
    ) -> list[Middleware]:
        """Set up middleware chain with CORS, X402 and Hydra middleware.

        Args:
            middleware: Custom middleware to include
            x402_ext: X402 extension instance
            payment_requirements: Payment requirements for X402
            manifest: Agent manifest
            auth_enabled: Whether authentication is enabled
            cors_origins: List of allowed CORS origins

        Returns:
            List of configured middleware
        """
        middleware_list = list(middleware) if middleware else []

        # Add CORS middleware if origins are specified
        if cors_origins:
            from starlette.middleware.cors import CORSMiddleware

            logger.info(f"CORS middleware enabled for origins: {cors_origins}")
            cors_middleware = Middleware(
                CORSMiddleware,  # type: ignore[arg-type]
                allow_origins=cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["*"],
            )
            # CORS must be first in middleware chain
            middleware_list.insert(0, cors_middleware)
            logger.info("CORS middleware added to position 0 in middleware chain")

        # Add X402 middleware if configured
        if x402_ext and payment_requirements:
            from .middleware import X402Middleware

            logger.info(
                f"X402 payment middleware enabled: "
                f"{x402_ext.amount} {x402_ext.token} on {x402_ext.network})"
            )

            facilitator_config = {"url": app_settings.x402.facilitator_url}
            x402_middleware = Middleware(
                X402Middleware,  # type: ignore[arg-type]
                manifest=manifest,
                facilitator_config=facilitator_config,
                x402_ext=x402_ext,
                payment_requirements=payment_requirements,
            )
            middleware_list.append(x402_middleware)

        # Add authentication middleware if requested or globally enabled
        # (previous behavior required both flags; we now treat settings as authoritative
        # so that enabling auth via config always installs the middleware).
        if auth_enabled or app_settings.auth.enabled:
            if app_settings.auth.enabled:
                # ensure config value drives logging
                logger.info("Authentication middleware enabled")
            auth_middleware = self._create_auth_middleware()
            # Add auth middleware after CORS and X402
            middleware_list.append(auth_middleware)

        # Add metrics middleware (should be last to capture all requests)
        from .middleware import MetricsMiddleware

        metrics_middleware = Middleware(MetricsMiddleware)  # type: ignore[arg-type]
        middleware_list.append(metrics_middleware)
        logger.info("Metrics middleware enabled for Prometheus monitoring")

        return middleware_list

    def _create_auth_middleware(self) -> Middleware:
        """Create authentication middleware based on provider.

        Returns:
            Configured auth middleware

        Raises:
            ValueError: If authentication provider is unknown
        """
        from .middleware.auth import HydraMiddleware

        provider = app_settings.auth.provider.lower()

        if provider == "hydra":
            logger.info("Hydra OAuth2 authentication enabled")
            return Middleware(HydraMiddleware, auth_config=app_settings.hydra)  # type: ignore[arg-type]
        else:
            logger.error(f"Unknown authentication provider: {provider}")
            raise ValueError(
                UNKNOWN_AUTH_PROVIDER_ERROR.format(provider=provider, supported="hydra")
            )

    def _setup_payment_session_manager(
        self,
        manifest: AgentManifest,
        payment_requirements_for_middleware: list[Any],
    ) -> None:
        """Initialize payment session manager and related configuration.

        Args:
            manifest: Agent manifest
            payment_requirements_for_middleware: Payment requirements from middleware setup
        """
        from bindu.server.middleware.x402.payment_session_manager import (
            PaymentSessionManager,
        )
        from x402.types import PaywallConfig
        import os

        self._payment_session_manager = PaymentSessionManager()

        # Create payment requirements for endpoints (with /payment-capture resource)
        self._payment_requirements = [
            req.model_copy(update={"resource": f"{manifest.url}/payment-capture"})
            for req in payment_requirements_for_middleware
        ]

        self._paywall_config = PaywallConfig(
            cdp_client_key=os.getenv("CDP_CLIENT_KEY") or "",
            app_name=f"{manifest.name} - x402 Payment",
            app_logo="/assets/light.svg",
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests with TaskManager validation.

        Health, readiness, and metrics endpoints are exempt from the startup
        gate so that Kubernetes (and other orchestrators) can probe the pod
        while storage/scheduler initialisation is still in progress.
        """
        if scope["type"] == "http" and (
            self.task_manager is None or not self.task_manager.is_running
        ):
            path = scope.get("path", "")
            # Allow observability and probe endpoints through before full startup
            if path not in ("/health", "/healthz", "/metrics"):
                raise RuntimeError(TASKMANAGER_NOT_INITIALIZED_ERROR)
        await super().__call__(scope, receive, send)
