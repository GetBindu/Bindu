"""Settings configuration for the bindu agent system.

This module defines the configuration settings for the application using pydantic models.
"""

from pydantic import Field, computed_field, BaseModel, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices
from typing import Literal


class ProjectSettings(BaseSettings):
    """
    Project-level configuration settings.

    Contains general application settings like environment, debug mode,
    and project metadata.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROJECT__",
        extra="allow",
    )

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "PROJECT__ENVIRONMENT"),
    )
    name: str = "bindu Agent"
    version: str = "0.1.0"

    @computed_field
    @property
    def debug(self) -> bool:
        """Compute debug mode based on environment."""
        return self.environment != "production"

    @computed_field
    @property
    def testing(self) -> bool:
        """Compute testing mode based on environment."""
        return self.environment == "testing"


class DIDSettings(BaseSettings):
    """DID (Decentralized Identity) configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DID__",
        extra="allow",
    )

    # DID Configuration
    config_filename: str = "did.json"
    method: str = "key"
    agent_extension_metadata: str = "did.message.signature"

    # DID File Names
    private_key_filename: str = "private.pem"
    public_key_filename: str = "public.pem"

    # DID Document Constants
    w3c_context: str = "https://www.w3.org/ns/did/v1"
    bindu_context: str = "https://getbindu.com/ns/v1"
    verification_key_type: str = "Ed25519VerificationKey2020"
    key_fragment: str = "key-1"
    service_fragment: str = "agent-service"
    service_type: str = "binduAgentService"

    # DID Method Prefixes
    method_bindu: str = "bindu"
    method_key: str = "key"
    multibase_prefix: str = "z"  # Base58btc prefix for ed25519

    # DID Extension
    extension_uri: str = "https://github.com/getbindu/bindu"
    extension_description: str = "DID-based identity management for bindu agents"
    resolver_endpoint: str = "/did/resolve"
    info_endpoint: str = "/agent/info"

    # DID Key Directory
    pki_dir: str = ".bindu"

    # DID Validation
    prefix: str = "did:"
    min_parts: int = 3
    bindu_parts: int = 4

    # Text Encoding
    text_encoding: str = "utf-8"
    base58_encoding: str = "ascii"


class NetworkSettings(BaseSettings):
    """Network and connectivity configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NETWORK__",
        extra="allow",
    )

    # Default Host and URL
    default_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("HOST", "NETWORK__DEFAULT_HOST"),
    )
    default_port: int = Field(
        default=3773,
        validation_alias=AliasChoices("PORT", "NETWORK__DEFAULT_PORT"),
    )

    # Timeouts (seconds)
    request_timeout: int = 30
    connection_timeout: int = 10

    @computed_field
    @property
    def default_url(self) -> str:
        """Compute default URL from host and port."""
        return f"http://{self.default_host}:{self.default_port}"


class TunnelSettings(BaseSettings):
    """FRP tunnel configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TUNNEL__",
        extra="allow",
    )

    # Tunnel timeout (seconds)
    timeout_seconds: int = 30

    # Error message for tunnel failures
    error_message: str = (
        "Could not create tunnel. Please check the logs below for more information:"
    )

    # Default FRP server configuration
    default_server_address: str = "142.132.241.44:7000"
    default_tunnel_domain: str = "tunnel.getbindu.com"

    # FRP client version
    frpc_version: str = "0.61.0"


class DeploymentSettings(BaseSettings):
    """Deployment and server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DEPLOYMENT__",
        extra="allow",
    )

    # Server Types
    server_type_agent: str = "agent"
    server_type_mcp: str = "mcp"

    # Endpoint Types
    endpoint_type_json_rpc: str = "json-rpc"
    endpoint_type_http: str = "http"
    endpoint_type_sse: str = "sse"

    # Docker Configuration
    docker_port: int = 8080
    docker_healthcheck_path: str = "/healthz"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOGGING__",
        extra="allow",
    )

    # Log Directory and File
    log_dir: str = "logs"
    log_filename: str = "bindu_server.log"

    # Log Rotation and Retention
    log_rotation: str = "10 MB"
    log_retention: str = "1 week"

    # Log Format
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}:{function}:{line} | {message}"

    # Log Levels
    default_level: str = "INFO"

    # Rich Theme Colors
    theme_info: str = "bold cyan"
    theme_warning: str = "bold yellow"
    theme_error: str = "bold red"
    theme_critical: str = "bold white on red"
    theme_debug: str = "dim blue"
    theme_did: str = "bold green"
    theme_security: str = "bold magenta"
    theme_agent: str = "bold blue"

    # Rich Console Settings
    traceback_width: int = 120
    show_locals: bool = True


class ObservabilitySettings(BaseSettings):
    """Observability and instrumentation configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OBSERVABILITY__",
        extra="allow",
    )

    # OpenInference Instrumentor Mapping
    instrumentor_map: dict[str, tuple[str, str]] = {
        "agno": ("openinference.instrumentation.agno", "AgnoInstrumentor"),
        "crewai": ("openinference.instrumentation.crewai", "CrewAIInstrumentor"),
        "langchain": (
            "openinference.instrumentation.langchain",
            "LangChainInstrumentor",
        ),
        "llama-index": (
            "openinference.instrumentation.llama_index",
            "LlamaIndexInstrumentor",
        ),
        "dspy": ("openinference.instrumentation.dspy", "DSPyInstrumentor"),
        "haystack": ("openinference.instrumentation.haystack", "HaystackInstrumentor"),
        "instructor": (
            "openinference.instrumentation.instructor",
            "InstructorInstrumentor",
        ),
        "pydantic-ai": (
            "openinference.instrumentation.pydantic_ai",
            "PydanticAIInstrumentor",
        ),
        "autogen": (
            "openinference.instrumentation.autogen_agentchat",
            "AutogenAgentChatInstrumentor",
        ),
        "smolagents": (
            "openinference.instrumentation.smolagents",
            "SmolAgentsInstrumentor",
        ),
        "litellm": ("openinference.instrumentation.litellm", "LiteLLMInstrumentor"),
        "openai": ("openinference.instrumentation.openai", "OpenAIInstrumentor"),
        "anthropic": (
            "openinference.instrumentation.anthropic",
            "AnthropicInstrumentor",
        ),
        "mistralai": (
            "openinference.instrumentation.mistralai",
            "MistralAIInstrumentor",
        ),
        "groq": ("openinference.instrumentation.groq", "GroqInstrumentor"),
        "bedrock": ("openinference.instrumentation.bedrock", "BedrockInstrumentor"),
        "vertexai": ("openinference.instrumentation.vertexai", "VertexAIInstrumentor"),
        "google-genai": (
            "openinference.instrumentation.google_genai",
            "GoogleGenAIInstrumentor",
        ),
    }

    # OpenTelemetry Base Packages
    base_packages: list[str] = [
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp",
    ]


class X402Settings(BaseSettings):
    """x402 payments configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="X402__",
        extra="allow",
    )

    provider: str = "coinbase"
    facilitator_url: str = "https://x402.org/facilitator"
    default_network: str = "base-sepolia"
    pay_to_env: str = "X402_PAY_TO"
    max_timeout_seconds: int = 600

    # Extension URI
    extension_uri: str = "https://github.com/google-a2a/a2a-x402/v0.1"

    # Protected methods that require payment
    protected_methods: list[str] = [
        "message/send",
    ]

    # Metadata keys
    meta_status_key: str = "x402.payment.status"
    meta_required_key: str = "x402.payment.required"
    meta_payload_key: str = "x402.payment.payload"
    meta_receipts_key: str = "x402.payment.receipts"
    meta_error_key: str = "x402.payment.error"

    # Status values
    status_required: str = "payment-required"
    status_submitted: str = "payment-submitted"
    status_verified: str = "payment-verified"
    status_completed: str = "payment-completed"
    status_failed: str = "payment-failed"

    # ---------------------------------------------------------------------------
    # SKALE Network Configuration
    # SKALE provides gasless x402 payments — zero transaction fees for agents.
    # Docs: https://blog.skale.space/blog/using-skale-for-gasless-x402-payments
    # ---------------------------------------------------------------------------

    # SKALE facilitator endpoint (dirtroad.dev runs the reference facilitator)
    skale_facilitator_url: str = "https://facilitator.dirtroad.dev"

    # SKALE Europa Hub chain ID (eip155 format required by x402 protocol)
    skale_network: str = "eip155:2046399126"

    # Bridged USDC on SKALE Europa Hub
    # Contract: https://elated-tan-skat.explorer.mainnet.skalenodes.com/
    skale_payment_token: str = "0x2aebcdc4f9f9149a50422fff86198cb0939ea165"

    # Human-readable token name for 402 response
    skale_payment_token_name: str = "Bridged USDC (SKALE Europa)"

    # Default payment amount in USDC micro-units (6 decimals)
    # 10000 = 0.01 USDC per agent call
    skale_default_amount: str = "10000"

    # RPC URLs by network
    # Always check https://chainlist.org for latest RPC URLs
    rpc_urls_by_network: dict[str, list[str]] = {
        "base-sepolia": [
            "https://sepolia.base.org",
            "https://base-sepolia.public.blastapi.io",
            "https://rpc.ankr.com/base_sepolia",
            "https://base-sepolia.blockpi.network/v1/rpc/public",
            "https://base-sepolia-rpc.publicnode.com",
        ],
        "base": [
            "https://mainnet.base.org",
            "https://base.blockpi.network/v1/rpc/public",
            "https://base-rpc.publicnode.com",
            "https://1rpc.io/base",
            "https://base.drpc.org",
        ],
        "ethereum": [
            "https://eth.llamarpc.com",
            "https://ethereum-rpc.publicnode.com",
            "https://rpc.ankr.com/eth",
            "https://ethereum.public.blockpi.network/v1/rpc/public",
        ],
        # SKALE Europa Hub — gasless transactions (no ETH needed for gas)
        # Chain ID: 2046399126
        # Docs: https://docs.skale.space/
        "eip155:2046399126": [
            "https://mainnet.skalenodes.com/v1/elated-tan-skat",
        ],
        # Alias for convenience
        "skale-europa": [
            "https://mainnet.skalenodes.com/v1/elated-tan-skat",
        ],
    }


class AgentSettings(BaseSettings):
    """Agent behavior and protocol configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT__",
        extra="allow",
    )

    # A2A Protocol Method Handlers
    method_handlers: dict[str, str] = {
        "message/send": "send_message",
        "message/stream": "stream_message",
        "tasks/get": "get_task",
        "tasks/cancel": "cancel_task",
        "tasks/list": "list_tasks",
        "contexts/list": "list_contexts",
        "contexts/clear": "clear_context",
        "tasks/feedback": "task_feedback",
        "tasks/pushNotificationConfig/set": "set_task_push_notification",
        "tasks/pushNotificationConfig/get": "get_task_push_notification",
        "tasks/pushNotificationConfig/list": "list_task_push_notifications",
        "tasks/pushNotificationConfig/delete": "delete_task_push_notification",
    }

    # Task State Configuration (A2A Protocol)
    non_terminal_states: frozenset[str] = frozenset(
        {
            "submitted",
            "working",
            "input-required",
            "auth-required",
        }
    )

    terminal_states: frozenset[str] = frozenset(
        {
            "completed",
            "failed",
            "canceled",
            "rejected",
        }
    )

    # message/stream polling behavior
    stream_poll_interval_seconds: float = 0.1
    stream_missing_task_retries: int = 2
    stream_missing_task_retry_delay_seconds: float = 0.05

    # Structured Response System Prompt
    structured_response_system_prompt: str = """
    You are an AI agent in the Bindu framework following the A2A Protocol.

Goal
- If the user's request is underspecified, ask exactly one high-impact clarifying question
  using the required state JSON.
- If the request is sufficiently specified, return the normal completion
  (text/markdown/code/etc.).

Strict Output Rule for Clarification
- When clarification is needed, return ONLY this JSON (no extra text, no code fences):
{
  "state": "input-required",
  "prompt": "Your specific question here"
}
Underspecification Heuristics (ask if any of these matter and are missing)
- Platform / channel
- Audience
- Purpose / goal
- Tone / voice
- Format
- Length constraint
- Style constraints
- Language / locale
- Visual context
- Domain context
- Compliance constraints

Decision Rubric
1) Can you deliver a high-quality, low-regret result without knowing any of the missing items above?
   - YES → Provide completion immediately (do NOT ask).
   - NO → Ask exactly ONE clarifying question that most increases quality.
2) If multiple items are missing, prefer a **single multiple-choice question**
   capturing the most impactful dimension (e.g., platform) and include an "Other" option.
3) Never chain questions. Ask one, then wait for the user's answer.
4) If the user explicitly says "any/you pick/default," proceed without further questions and choose sensible defaults.
5) If the user has previously specified a stable preference in this conversation
   (e.g., "Instagram captions"), apply it silently.

Question Crafting Guidelines
- Be specific, short, and action-oriented.
- Prefer multiple choice with 3–5 options + "Other".
- Mention the default you'll use if they don't care (e.g., "If no preference, I'll format for Instagram").

{{ ... }}
Allowed Outputs
- Clarification needed → ONLY the state JSON above.
- Otherwise → Normal completion (no JSON).

Few-Shot Examples

(1) User: "provide sunset quote"
→ Missing: platform/length/tone.
Return:
{
  "state": "input-required",
  "prompt": "Do you want this as an Instagram caption, a Pinterest pin text, or a "
            "general quote? (Options: Instagram, Pinterest, General, Other)"
}

(2) User: "write a caption for my beach photo"
→ Missing: platform. Caption implies short & casual; platform most impactful.
Return:
{
  "state": "input-required",
  "prompt": "Which platform should I format the caption for? (Options: Instagram, TikTok, Pinterest, LinkedIn, Other)"
}

Defaults (use only if user says 'any/you pick/default' or prior context establishes them)
- Platform: Instagram
- Tone: concise, warm, professional (or playful for captions)
- Length: short
- Language: same as user's request
- Hashtags: none unless platform is Instagram/Pinterest and user implies discoverability; then add 2–3 relevant tags.

CRITICAL
- When returning the state JSON, return ONLY the JSON object with no additional text before or after.

   """

    # Enable/disable structured response system
    enable_structured_responses: bool = True


class AuthSettings(BaseSettings):
    """Authentication and authorization configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUTH__",
        extra="allow",
    )

    enabled: bool = False
    provider: str = "hydra"
    algorithms: list[str] = ["RS256"]
    leeway: int = 10

    public_endpoints: list[str] = [
        "/.well-known/agent.json",
        "/.well-known/*",
        "/did/resolve",
        "/agent/info",
        "/agent/negotiation",
        "/agent/skills",
        "/agent/skills/*",
        "/health",
        "/healthz",
        "/metrics",
        "/payment-capture",
        "/api/start-payment-session",
        "/api/payment-status/*",
    ]

    require_permissions: bool = False
    permissions: dict[str, list[str]] = {
        "message/send": ["agent:write"],
        "tasks/get": ["agent:read"],
        "tasks/cancel": ["agent:write"],
        "tasks/list": ["agent:read"],
        "contexts/list": ["agent:read"],
        "tasks/feedback": ["agent:write"],
    }


# ============================================================================
# Ory Configuration Models
# ============================================================================


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration for external services."""

    name: str = Field(..., description="Provider name (notion, google, github, etc.)")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    auth_url: HttpUrl = Field(..., description="Authorization URL")
    token_url: HttpUrl = Field(..., description="Token URL")
    userinfo_url: HttpUrl | None = Field(None, description="User info URL")
    scope: str = Field(..., description="Default scope")
    redirect_uri: HttpUrl = Field(..., description="Redirect URI")


# ============================================================================
# Hydra Settings
# ============================================================================


class HydraSettings(BaseSettings):
    """Ory Hydra OAuth2 authentication configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HYDRA__",
        extra="allow",
    )

    enabled: bool = False
    admin_url: str = "https://hydra-admin.getbindu.com"
    public_url: str = "https://hydra.getbindu.com"
    timeout: int = 10
    verify_ssl: bool = True
    max_retries: int = 3
    cache_ttl: int = 300
    max_cache_size: int = 1000
    auto_register_agents: bool = True
    agent_client_prefix: str = "agent-"

    default_agent_scopes: list[str] = [
        "openid",
        "offline",
        "agent:read",
        "agent:write",
    ]

    default_grant_types: list[str] = [
        "client_credentials",
        "authorization_code",
        "refresh_token",
    ]

    public_endpoints: list[str] = [
        "/.well-known/agent.json",
        "/.well-known/*",
        "/did/resolve",
        "/agent/info",
        "/agent/negotiation",
        "/agent/skills",
        "/agent/skills/*",
        "/health",
        "/healthz",
        "/metrics",
        "/payment-capture",
        "/favicon.ico",
        "/oauth/*",
    ]


class StorageSettings(BaseSettings):
    """Storage backend configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    backend: Literal["memory", "postgres"] = Field(
        default="memory",
        validation_alias=AliasChoices("backend", "STORAGE_TYPE"),
    )

    postgres_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("postgres_url", "DATABASE_URL"),
    )
    postgres_pool_min: int = 2
    postgres_pool_max: int = 10
    postgres_timeout: int = 60
    postgres_command_timeout: int = 30

    postgres_did: str | None = Field(
        default=None,
        validation_alias=AliasChoices("postgres_did", "POSTGRES_DID", "DID"),
    )

    postgres_max_retries: int = 3
    postgres_retry_delay: float = 1.0
    run_migrations_on_startup: bool = False


class SchedulerSettings(BaseSettings):
    """Scheduler backend configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    backend: Literal["memory", "redis"] = Field(
        default="memory",
        validation_alias=AliasChoices("backend", "SCHEDULER_TYPE"),
    )

    redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("redis_url", "REDIS_URL"),
    )
    redis_host: str | None = None
    redis_port: int | None = None
    redis_password: str | None = None
    redis_db: int | None = None
    queue_name: str = "bindu:tasks"
    max_connections: int = 10
    retry_on_timeout: bool = True
    poll_timeout: int = Field(
        default=1,
        validation_alias=AliasChoices("poll_timeout", "REDIS_POLL_TIMEOUT"),
        description="Timeout in seconds for Redis blpop operations.",
    )


class RetrySettings(BaseSettings):
    """Retry mechanism configuration settings using Tenacity."""

    worker_max_attempts: int = 3
    worker_min_wait: float = 1.0
    worker_max_wait: float = 10.0

    storage_max_attempts: int = 5
    storage_min_wait: float = 0.5
    storage_max_wait: float = 5.0

    scheduler_max_attempts: int = 3
    scheduler_min_wait: float = 1.0
    scheduler_max_wait: float = 8.0

    api_max_attempts: int = 4
    api_min_wait: float = 1.0
    api_max_wait: float = 15.0


class NegotiationSettings(BaseSettings):
    """Negotiation and capability assessment configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NEGOTIATION__",
        extra="allow",
    )

    skill_match_weight: float = 0.55
    io_compatibility_weight: float = 0.20
    performance_weight: float = 0.15
    load_weight: float = 0.05
    cost_weight: float = 0.05

    default_latency_ms: int = 5000
    max_keyword_length: int = 100
    max_task_text_length: int = 10000
    min_score_threshold: float = 0.0

    use_embeddings: bool = True
    embedding_provider: str = "openrouter"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_weight: float = 0.7
    keyword_weight: float = 0.3
    embedding_batch_size: int = 32
    embedding_cache_size: int = 1000


class VaultSettings(BaseSettings):
    """HashiCorp Vault configuration for DID keys and Hydra credentials storage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VAULT__",
        extra="allow",
    )

    url: str = Field(
        default="http://localhost:8200",
        validation_alias=AliasChoices("VAULT__URL", "VAULT_ADDR"),
        description="Vault server URL",
    )
    token: str = Field(
        default="",
        validation_alias=AliasChoices("VAULT__TOKEN", "VAULT_TOKEN"),
        description="Vault authentication token",
    )
    enabled: bool = Field(
        default=False,
        description="Enable Vault integration",
    )


class OAuthSettings(BaseSettings):
    """OAuth provider configuration for user credential management (v0)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OAUTH__",
        extra="allow",
    )

    callback_base_url: str = Field(
        default="http://localhost:3773",
        description="Base URL for OAuth callbacks",
    )

    notion_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("OAUTH__NOTION_CLIENT_ID", "NOTION_CLIENT_ID"),
    )
    notion_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OAUTH__NOTION_CLIENT_SECRET", "NOTION_CLIENT_SECRET"
        ),
    )

    google_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("OAUTH__GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    )
    google_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OAUTH__GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"
        ),
    )

    github_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("OAUTH__GITHUB_CLIENT_ID", "GITHUB_CLIENT_ID"),
    )
    github_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OAUTH__GITHUB_CLIENT_SECRET", "GITHUB_CLIENT_SECRET"
        ),
    )


class SentrySettings(BaseSettings):
    """Sentry error tracking and performance monitoring configuration."""

    enabled: bool = False
    dsn: str = ""

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("SENTRY__ENVIRONMENT", "ENVIRONMENT"),
    )

    release: str = ""
    traces_sample_rate: float = 1.0
    profiles_sample_rate: float = 0.1
    enable_tracing: bool = True
    enable_profiling: bool = False
    send_default_pii: bool = False
    max_breadcrumbs: int = 100
    attach_stacktrace: bool = True

    integrations: list[str] = [
        "starlette",
        "sqlalchemy",
        "redis",
        "asyncio",
    ]

    default_tags: dict[str, str] = {}

    filter_transactions: list[str] = [
        "/healthz",
        "/health",
        "/metrics",
        "/favicon.ico",
    ]

    ignore_errors: list[str] = [
        "KeyboardInterrupt",
        "SystemExit",
    ]

    server_name: str = ""
    debug: bool = False


class GrpcSettings(BaseSettings):
    """gRPC adapter configuration for language-agnostic agent support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GRPC__",
        extra="allow",
    )

    enabled: bool = Field(
        default=False,
        description="Enable gRPC server for language-agnostic SDK support",
    )

    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the gRPC server to",
    )

    port: int = Field(
        default=3774,
        description="Port for the gRPC server (default: 3774)",
    )

    max_workers: int = Field(
        default=10,
        description="Maximum number of gRPC server worker threads",
    )

    max_message_length: int = Field(
        default=4 * 1024 * 1024,
        description="Maximum gRPC message size in bytes (default: 4MB)",
    )

    handler_timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for calling SDK's HandleMessages",
    )

    health_check_interval: int = Field(
        default=30,
        description="Interval in seconds for health checking registered agents",
    )


class MTLSSettings(BaseSettings):
    """mTLS certificate lifecycle configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="BINDU_MTLS_",
        env_file=".env",
        extra="ignore",
    )

    enabled: bool = False
    cert_ttl_hours: int = 24
    certs_dir: str = "~/.bindu/certs"


class Settings(BaseSettings):
    """Main settings class that aggregates all configuration components."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="allow",
    )

    project: ProjectSettings = ProjectSettings()
    did: DIDSettings = DIDSettings()
    network: NetworkSettings = NetworkSettings()
    tunnel: TunnelSettings = TunnelSettings()
    deployment: DeploymentSettings = DeploymentSettings()
    logging: LoggingSettings = LoggingSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    x402: X402Settings = X402Settings()
    agent: AgentSettings = AgentSettings()
    auth: AuthSettings = AuthSettings()
    hydra: HydraSettings = HydraSettings()
    vault: VaultSettings = VaultSettings()
    oauth: OAuthSettings = OAuthSettings()
    storage: StorageSettings = StorageSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    retry: RetrySettings = RetrySettings()
    negotiation: NegotiationSettings = NegotiationSettings()
    sentry: SentrySettings = SentrySettings()
    grpc: GrpcSettings = GrpcSettings()
    mtls: MTLSSettings = MTLSSettings()


app_settings = Settings()